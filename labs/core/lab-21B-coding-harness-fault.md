# Lab 21B — 孤儿 Session 注入与阻断｜故障注入

## 实验目标

把不存在的 parent 注入 branch 创建，验证系统在写入前 fail-closed，数据库中不留下 orphan session。

## 环境与版本

与 Lab 21A 相同；无外部依赖。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch21_coding_harness.py --fault
```

实际输出的核心字段：

```json
{"error":"parent_session_missing","ancestry":["root"],"orphan_rows":0,"reopened_from_sqlite":true,"evidence_level":"L3_CONTAINED","passed":true}
```

## 调试断点

停在 `SessionLedger.create` 的 parent query 与 insert 之间；确认 exception 发生后没有 commit，重开数据库再查 `orphan` 行数仍为 0。

## 验收标准

退出码 0、`system_detected=true`、`contained=true`、`orphan_rows=0`。`passed=true` 表示故障 oracle 命中，不表示业务已经恢复到另一个分支。
