# Lab 18A — Checkpoint 与 Journal：单调持久化｜正常路径

## 实验目标

真实写入两版 checkpoint 和两条 hash-chain journal，验证版本单调、最终状态可加载、journal 完整。

## 环境与版本

- Python 3.11–3.13；本机临时文件系统；
- `JsonCheckpointStore` 与 `EffectJournal`；
- 无远端 effect/API key；证据上限 `L1_MECHANISM`。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch18_checkpoint_journal.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"observation":{"journal_records":2,"journal_valid":true,"loaded_step":2,"loaded_version":2,"stale_write_error":null,"versions":[1,2]},"passed":true,"scenario":"checkpoint"}
```

## 调试断点

在 expected-version 比较、temp file write、file/parent fsync、atomic replace、journal previous hash 与 reload 处观察。

## 验收标准

`versions=[1,2]`、加载 step/version 均为 2、两条 journal 且 chain valid。不得写成远端 exactly-once。
