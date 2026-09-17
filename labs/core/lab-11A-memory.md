# Lab 11A — 双时态偏好与来源解析｜正常路径

## 实验目标

验证长期记忆读取经过 tenant、subject、key 与 valid-time 过滤，并返回稳定 memory identity，而非从聊天文本临时猜测。

## 环境与版本

Python 3.11–3.13，无网络/API key。写入 `mem-zh`：tenant A、subject user-7、key `preferred_language`、value `zh-CN`、authority 100、confidence 1.0、valid/recorded UTC 时间及 CRM source。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；实验使用固定 UTC 时间，避免当前时钟导致不确定结果。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch11_memory.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"invariant_holds":true,"observation":{"candidates":["mem-zh"],"quarantined":{},"selected":"mem-zh","value":"zh-CN"},"passed":true,"scenario":"memory"}
```

## 调试断点

观察 `parse_utc`、scope/time filter、authority sort 和 resolution；记录每条 memory identity 被保留或隔离的原因。

## 验收标准

PASS 要求 selected identity/value 准确且无 quarantine。将 query time 移到 valid_from 之前，必须得到 no selection 而不是自动回退到旧聊天。

## 证据边界

内存实现验证语义，不证明持久化事务、加密、备份删除或向量索引。生产实验要加入数据库、row-level policy、并发写与 crash recovery。
