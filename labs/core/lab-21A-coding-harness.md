# Lab 21A — Session 分支与压缩后恢复｜正常路径

## 实验目标

真实创建 SQLite session tree，写入 constraint/failure/decision，关闭连接后重新打开并压缩；证明 ancestry 与任务关键事实仍可恢复。

## 环境与版本

Python 3.11–3.13；标准库 `sqlite3`；macOS/Linux、arm64/x86_64 均可；无需模型、网络、Docker 或 API key。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

入口 `examples/chapters/ch21_coding_harness.py`；机制位于 `src/agentlab/specialized_system.py::SessionLedger`，场景位于 `course_scenarios.py::coding_harness`。

```bash
python examples/chapters/ch21_coding_harness.py
```

实际输出的核心字段：

```json
{"ancestry":["root","branch"],"fact_kinds":["constraint","failure","decision"],"orphan_rows":0,"reopened_from_sqlite":true,"evidence_level":"L1_MECHANISM","passed":true}
```

## 调试断点

在 `SessionLedger.create`、`record`、`ancestry` 和 `compact` 停下；确认 `close()` 后新 connection 从文件读取，而不是沿用 Python 对象。

## 验收标准

退出码 0；ancestry 为 `root → branch`；三类事实都存在；digest 为 64 位 SHA-256。证据只覆盖本地 lineage/compaction，不代表真实 Coding Agent 任务成功率。
