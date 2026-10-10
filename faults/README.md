# faults

故障實驗室的定義，也是評測集的標準答案。每種故障一個資料夾：

```
faults/<fault-id>/
  sparkapplication.yaml   壞掉的 SparkApplication
  answer.yaml             標準答案與修法（格式見 _template/answer.yaml）
  README.md               怎麼重現、為什麼會壞、手動怎麼修
```

候選清單在 [docs/TDD.md](../docs/TDD.md) 的「故障清單」。階段 1 親手重現後才建立各自的資料夾。
