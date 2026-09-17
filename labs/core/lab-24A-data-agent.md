# Lab 24A — 只读聚合、Query Plan 与结果摘要｜正常路径

## 实验目标

对真实 SQLite 文件执行受限聚合，记录列、行、query plan、截断标志和 result digest，再由独立连接核对源表行数。

## 环境与版本

Python 3.11–3.13；标准库 `sqlite3`；无需模型、网络、Docker 或 API key。

## 环境准备

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## 实验代码

```bash
python examples/chapters/ch24_data_agent.py
```

实际输出的核心字段：

```json
{"columns":["status","total"],"rows":[["open",100],["paid",10]],"query_plan":["SCAN invoices USING INDEX invoices_status"],"result_sha256":"95745e3c04ef0fac","truncated":false,"verified_row_count":3,"evidence_level":"L1_MECHANISM"}
```

## 调试断点

在 `ReadOnlyDataAgent.__init__`、`execute` 的 `EXPLAIN QUERY PLAN`、`fetchmany(max_rows+1)` 与 digest 计算处停下。

## 验收标准

退出码 0；聚合值和 plan 存在；`truncated=false`；独立连接确认三条源记录。本实验不评估 Text-to-SQL 模型能力。
