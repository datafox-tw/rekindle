# Rekindle

Spark on Kubernetes 的故障分診與自動復原平台。Spark job 失敗後收集三層訊號、比對過往案例，沒見過的才交給 agent 調查，最後改設定重送並驗證。

- 需求：[docs/PRD.md](docs/PRD.md)
- 技術設計：[docs/TDD.md](docs/TDD.md)
- 每日紀錄：[daily-logs/](daily-logs/)

## 目前狀態

骨架階段。Backend 的路由、資料模型和分診循環的接線已經在，節點與服務的內容都還是 stub。Spark job、叢集設定、故障定義從階段 0 開始補。

## 目錄

| 路徑 | 內容 |
|---|---|
| `backend/` | FastAPI、資料模型、收集與復原的服務、LangGraph 分診循環 |
| `frontend/` | React + Vite |
| `faults/` | 故障定義與標準答案 |
| `spark-jobs/` | TPC-DS 與 Binance 的 PySpark job |
| `infra/` | kind、GKE、Spark Operator、平台服務的部署設定 |
| `eval/` | 評測腳本與結果 |

## 開發

需要 Python 3.12、[uv](https://docs.astral.sh/uv/) 和 Node.js。把 `.env.example` 複製成 `.env` 並填入 Gemini API key。

Backend（http://localhost:8000，API 文件在 `/docs`）：

```bash
cd backend && uv run uvicorn app.main:app --reload
```

測試：

```bash
cd backend && uv run pytest
```

Frontend（http://localhost:5173，`/api` 會轉給 backend）：

```bash
cd frontend && npm install && npm run dev
```
