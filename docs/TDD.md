# Rekindle TDD（技術設計文件）

狀態：草稿 v0.2 ｜ 2026-10-10 ｜ 需求見 [PRD.md](PRD.md)

目前只有骨架：目錄、資料模型、API 路由和分診循環的接線已經建立，節點與服務的內容都還是 stub。文中的設計會隨實作修改。

Rekindle 是 Spark on Kubernetes + FastAPI + Postgres + LangGraph + React/Vite 的系統。

## 技術棧

| 層 | 選擇 | 用途 |
|---|---|---|
| 資料處理 | Apache Spark（PySpark、Spark SQL） | 跑 TPC-DS 與 Binance 的 job，也是故障的來源 |
| 叢集 | Kubernetes：本機用 kind，線上用 GKE Standard（單一 zone） | 執行環境 |
| Spark on K8s | Kubeflow Spark Operator（`SparkApplication` CRD）、Spark History Server | 送出與管理 job；人工檢視用 |
| 儲存 | GCS 放 event log 與 Parquet 資料；本機用 PVC | |
| 後端 | Python、FastAPI、Pydantic、SQLAlchemy | API、收集、指紋、復原 |
| 資料庫 | Postgres + pgvector | 案件、案例庫、執行紀錄、評測結果 |
| Agent | LangGraph 負責分診循環；agno 用在 baseline 與後期的單一 agent | |
| LLM | Gemini：調查用 `gemini-3.6-flash`，輕量分類用 `gemini-3.1-flash-lite`。模型名稱放在 `config.py`，可以用環境變數覆寫 | |
| Embedding | `gemini-embedding-2` | 指紋的近似比對 |
| 前端 | React + Vite，用 SSE 串流時間軸 | |
| 部署 | Terraform 建 GKE，Helm 裝 Spark Operator，kustomize 管自己的服務（kind 與 GKE 兩組 overlay） | |

選 PySpark 而不是 Scala：後端和 agent 都是 Python，而且 Python worker 的記憶體算在 JVM heap 之外，`memoryOverhead` 不夠就會被 OOMKilled，剛好是一種真實又容易重現的故障。

## 叢集配置

- **節點池**：`system` 是一個常駐的小節點，放 API、worker、Postgres、History Server 和 Spark driver。`spark-spot` 是 spot 節點池，自動伸縮、可以縮到零，加上 taint 讓只有 executor 會排上去。driver 不放 spot，因為 driver 被回收整個 job 就沒了。
- **Namespace**：`rekindle-system` 放平台服務，`spark-jobs` 放 driver 與 executor。
- **權限**：後端的 ServiceAccount 只能在 `spark-jobs` 讀 pod、event、log，以及建立和刪除 `SparkApplication`。
- **資源上限**：`spark-jobs` 設 ResourceQuota，限制 CPU 與記憶體總量。

## 目錄

```
infra/                  kind 設定、Terraform、Helm values、kustomize
spark-jobs/             TPC-DS 與 Binance 的 PySpark job
faults/<fault-id>/      每種故障一個資料夾：壞掉的 SparkApplication、answer.yaml（標準答案與修法）、說明
backend/app/
  main.py               FastAPI 路由
  config.py             設定：模型名稱、embedding 維度、重試上限
  models.py             Postgres 資料模型
  fix_whitelist.yaml    修法白名單
  services/
    collector.py        收集 K8s 事件、pod log、event log
    eventlog.py         串流解析 event log，算出 stage 與 task 的摘要指標
    fingerprint.py      正規化、簽章、embedding
    casebase.py         案例庫的查詢、寫回、降級
    recovery.py         白名單檢查、重送、驗證
    redaction.py        上傳檔案的遮蔽
  agent/
    graph.py            LangGraph 分診循環
    tools.py            調查用的唯讀工具
    schemas.py          歸因分類表、歸因與修法的結構化輸出
backend/tests/          路由、資料表、循環接線與分支規則的測試
eval/                   評測腳本、agno baseline、結果
frontend/               React/Vite
docs/                   PRD、TDD
daily-logs/             每日文章
```

## 資料模型

- `runs`：一次 `SparkApplication` 執行。來源（實驗室、評測）、設定、狀態、耗時、估算成本、`parent_run_id`（重送時指向原本那次）。
- `incidents`：一個案件。對應的 run、指紋、歸因、命中或未命中、最終狀態。
- `evidence`：各層訊號的摘要，以及原始檔在 GCS 的位置。
- `cases`：案例庫。簽章雜湊、embedding、歸因類別、修法（設定 diff）、驗證狀態、命中次數、套用後的成功與失敗次數。
- `agent_steps`：每個節點的輸入輸出摘要、token 數、耗時。時間軸和成本統計都從這張表來。
- `reports`：上傳診斷的報告，有到期時間。
- `eval_results`：每次評測的逐案結果。

## 設計選擇

### 觸發

不是所有故障都會讓 job 失敗，所以觸發條件有三種：`SparkApplication` 進入失敗狀態；超過逾時還沒結束（例如 executor 一直排不上）；成功但耗時超過基準的某個倍數（例如資料傾斜）。

### 收集

- **K8s 層**：pod 狀態、容器結束原因與 exit code、namespace 內的事件。
- **Log 層**：driver 與 executor 的 log。只留錯誤前後的片段和例外堆疊，不整份送進 LLM。
- **Spark 層**：event log。自己寫串流解析器，算出每個 stage 的耗時、task 耗時與 shuffle 讀取量的分布（最大值除以中位數當作傾斜程度）、spill 量、executor 被移除的原因。

實驗室和上傳診斷共用同一個解析器。History Server 留給人看，不當程式的資料來源。

### 指紋

1. 取出關鍵錯誤：例外類別、訊息、堆疊最上面幾層、K8s 的結束原因。
2. 正規化：把 application ID、pod 名稱、executor 編號、IP、時間、路徑、數字換成佔位符。
3. 正規化後的字串算 SHA-256，當作精確比對的簽章。
4. 同一段字串加上結構化特徵（哪一層、exit code、失敗的 stage 類型）算 embedding，用於近似比對。

### 案例庫查詢

- 簽章完全相同：命中。
- 否則用 pgvector 找最相近的已驗證案例，相似度超過門檻才算命中。門檻用評測集調，目標是壓低誤命中率。
- 其餘視為未命中，進入調查。
- 被降級的案例不參與自動套用，但會當作參考資料提供給調查 agent。

### 分診循環（LangGraph）

```
collect → fingerprint → lookup ─ 命中 ───────────────────────────┐
                               └ 未命中 → investigate → classify → propose_fix
                                                                  ↓
                              write_back ← verify ← resubmit ← validate_fix
```

| 節點 | 用 LLM | 做什麼 |
|---|---|---|
| collect、fingerprint、lookup | 否 | 如上 |
| investigate | 是 | 帶工具的調查迴圈，有步數上限。工具都是唯讀：查事件、查 log 片段、查 event log 摘要、看目前設定 |
| classify | 是 | 結構化輸出：固定分類表中的一個類別、信心、證據。分類表包含「設定修不了，需要人處理」 |
| propose_fix | 是 | 結構化輸出：設定 diff 與理由 |
| validate_fix | 否 | 檢查白名單與上下限，不合格就退回，重試有上限 |
| resubmit | 否 | 以新設定建立新的 `SparkApplication` |
| verify | 否 | 重送的 job 成功，且耗時在基準範圍內 |
| write_back | 否 | 更新案例庫：新增、累計成功，或降級 |

原則是 LLM 只出現在需要判斷的節點。收集、比對、檢查、重送都是確定性的程式，所以命中路徑完全不花調查的 token。狀態用 LangGraph 的 Postgres checkpointer 保存，循環中斷後可以接著跑。

驗證失敗時，如果是命中路徑，退回 investigate 並降級該案例；如果已經調查過，在重送額度內再試一次，用完就標成「需要人處理」。

### agno 的定位

LangGraph 適合這個循環，因為它需要明確的狀態、分支和 checkpoint。agno 用在不需要圖狀流程的地方：

- **評測的 baseline**：同一份證據交給單一的工具型 agent，和 LangGraph 循環比準確率與 token 成本。
- **階段 5 的自然語言 SQL agent**。

兩套框架就是兩份維護成本。時間不夠時，這部分最先砍。

### 修法白名單

定義在 `backend/app/fix_whitelist.yaml`，每個設定有型別和上下限，上限跟著節點規格走（階段 1 填入）。初版包含：

- 記憶體與資源：`spark.executor.memory`、`spark.executor.memoryOverhead`、`spark.executor.cores`、`spark.executor.instances`、`spark.driver.memory`
- Shuffle 與 AQE：`spark.sql.shuffle.partitions`、`spark.sql.adaptive.enabled`、`spark.sql.adaptive.skewJoin.enabled`、`spark.sql.autoBroadcastJoinThreshold`
- 節點回收：`spark.decommission.enabled`、`spark.storage.decommission.shuffleBlocks.enabled`

### 上傳診斷

這條路徑只走 collect（只有 event log）、fingerprint、lookup、investigate、classify，沒有重送。遮蔽在 `redaction.py` 做，發生在儲存與 LLM 之前：環境資訊只保留允許清單內的設定，SQL 文字與查詢計畫中的字面值、檔案路徑、主機名稱都換成佔位符。

### 即時執行與重播

即時執行和重播用同一種事件格式，經由同一個 SSE 端點送到前端。重播是把 `agent_steps` 和 `evidence` 依原本的順序送出，時間可以壓縮。

## 故障清單（候選）

階段 1 親手重現後才定案。挑選原則是三層訊號都要涵蓋到，而且都能用白名單內的設定修好。

| # | 故障 | 怎麼做出來 | 主要訊號 | 修法 |
|---|---|---|---|---|
| 1 | Executor 被 OOMKilled | Python UDF 吃掉 heap 外的記憶體，`memoryOverhead` 設太小 | K8s：結束原因 `OOMKilled`、exit code 137 | 調高 `spark.executor.memoryOverhead` |
| 2 | Executor JVM heap OOM | 關掉 AQE、分區數太少，單一分區太大 | executor log：`java.lang.OutOfMemoryError` | 調高 `spark.sql.shuffle.partitions` 或 `spark.executor.memory` |
| 3 | 資料傾斜 | Binance 成交資料依交易對 join，關掉 AQE | event log：task 耗時與 shuffle 讀取量的長尾 | 打開 AQE 與 skew join |
| 4 | Spot 節點被回收 | 執行中刪掉 executor 所在的節點 | K8s 事件、driver log：executor lost、`FetchFailedException` | 打開 decommission 設定，或直接重送 |
| 5 | Driver OOM | `autoBroadcastJoinThreshold` 設太高，大表被 broadcast | driver log、driver pod 的結束原因 | 調低 `spark.sql.autoBroadcastJoinThreshold` |
| 6 | Executor 排不上 | executor 要求的資源超過節點規格 | K8s 事件：`FailedScheduling` | 調低 `spark.executor.memory` 或 `spark.executor.cores` |

第 3 種不會失敗只會變慢，第 6 種不會失敗只會卡住，所以觸發條件才需要三種。

## 資料流

**故障實驗室（即時）**
前端 `POST /api/lab/runs` > 後端檢查配額 > 建立壞掉的 `SparkApplication` > 觸發條件成立 > 分診循環 > 每個節點寫入 `agent_steps` 並經 SSE 推給前端 > 重送 > 驗證 > 寫回案例庫 > 前端顯示修復前後的耗時與成本。

**故障實驗室（重播）**
前端要求某個故障的錄製案件 > 後端從 `agent_steps` 與 `evidence` 讀出 > 經同一個 SSE 端點送出。

**上傳診斷**
前端 `POST /api/uploads` > 檢查大小與格式 > 串流解壓縮並遮蔽 > 解析 event log > 指紋與查詢 > 未命中才調查 > 產生報告 > 刪除原始檔 > 使用者同意時才把去識別化的指紋寫入案例庫。

**評測**
`eval/` 的腳本逐一送出評測集的 job > 走完整個循環 > 和 `answer.yaml` 比對 > 結果寫入 `eval_results` > `GET /api/metrics` 提供給評測數字頁。

## 評測

評測集不能只有 6 個案件，否則命中率必然是 100%，準確率也沒有意義。組成如下：

- **變體**：每種故障配上不同的 job（不同的 TPC-DS 查詢、Binance job）和資料規模。
- **分組**：一部分先跑過、進案例庫（看過的）；一部分保留（沒看過的），用來測指紋能不能認出同一類故障。
- **對照**：健康的 job，以及分類表以外的故障。用來測誤命中，以及系統會不會在不該修的時候硬修。

每次評測跑兩種設定：案例庫清空，和案例庫已有內容。兩者的修復時間與 token 成本差距就是重用的價值。agno baseline 用同一份評測集。

程式本身的測試：指紋正規化、白名單檢查、event log 解析（包含不完整的檔案）、遮蔽規則，都用固定的樣本檔做單元測試。

## 故障模式

- **Log 拿不到**：executor pod 被刪除或節點被回收後，log 就消失。設定 `spark.kubernetes.executor.deleteOnTermination=false` 保留失敗的 pod，GKE 上另以 Cloud Logging 備援。仍然缺少時，在證據中標記「這一層沒有資料」，不讓 agent 猜。
- **Event log 不完整**：driver 被強制結束時檔案會停在 `.inprogress`。解析器要能處理被截斷的檔案。
- **誤命中**：套了錯的修法。靠驗證擋下，退回調查並降級該案例。
- **修法不合格**：LLM 提出白名單以外或超過上限的設定。`validate_fix` 拒絕，重試用完就標成「需要人處理」。
- **靠加資源掩蓋問題**：一直加記憶體也能讓 job 過。用上限擋，並記錄修復前後的成本，讓變貴的修法看得出來。
- **重送迴圈**：每個案件的重送次數有上限。
- **Log 內容的 prompt injection**：log 是不可信的輸入。調查工具全是唯讀，LLM 的輸出只接受結構化格式並經過白名單檢查，上傳路徑完全沒有重送能力。
- **惡意上傳**：超大檔案、解壓縮炸彈。限制大小，串流處理，解壓後超過上限就中止。
- **Spot 沒有容量**：executor 起不來。即時執行逾時後改播錄製的案件。
- **LLM 無法使用或超過每日上限**：命中路徑不受影響。未命中的案件停在「已收集、待調查」，之後再補跑。
- **成本超支**：ResourceQuota、`spark.executor.instances` 上限、即時執行配額、GCP 預算警示。

## 未決事項

- **Spark 版本**：3.5 或 4.x。階段 0 確認 Spark Operator 與 TPC-DS 工具的相容性後鎖定。
- **TPC-DS 資料怎麼產生**：tpcds-kit，或用 DuckDB 的 tpcds extension 匯出 Parquet。以及本機與 GKE 各用多大的 scale factor。
- **Embedding 維度**：`config.py` 先設 768。pgvector 的向量索引上限是 2000 維，所以不能直接用太大的輸出。要確認 `gemini-embedding-2` 支援指定輸出維度。
- **重試上限**：修法提案與重送目前各設 2 次，是占位值。
- **對外入口**：GKE Ingress 要另付 load balancer 的費用；也可以用 Cloudflare Tunnel 之類的方式省掉。階段 3 之前決定。
- **GKE 的實際月費**：用價格計算機確認常駐節點的規格與費用。
- **Agent 的追蹤工具**：`agent_steps` 已經夠用來算成本；要不要另外接 LangSmith 之類的工具，等階段 2 再看。
