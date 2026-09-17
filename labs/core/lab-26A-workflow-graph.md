# Lab 26A — SQLite Checkpoint 跨实例恢复与 Effect Once｜正常路径

## 实验目标

执行两个 graph node 后关闭实例，从同一 SQLite checkpoint 新建实例继续到 FINISHED，并验证 `apply` effect 唯一键只产生一条记录。

## 环境与版本

Python 3.11–3.13；标准库 SQLite；无需 LangGraph/ADK/MAF 或模型。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch26_workflow_graph.py
```

实际输出：

```json
{"process_boundary":"close_reopen_sqlite","history":["collect","approve","apply","verify"],"final_node":"FINISHED","effect_count":1,"evidence_level":"L1_MECHANISM","passed":true}
```

## 调试断点

在 `DurableGraph.start/resume/step`、version compare 和 `effects insert or ignore` 停下；确认第二实例读取的是文件状态。

## 验收标准

退出码 0、完整 history、FINISHED、effect_count 恰为 1。该 Core Lab 与仓库三组上游 L5 实验是不同证据。
