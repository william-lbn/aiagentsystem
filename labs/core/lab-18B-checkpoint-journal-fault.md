# Lab 18B — Checkpoint 与 Journal：陈旧写冲突｜故障注入

## 实验目标

在 version 2 已提交后，用 version 1 发起 stale write，验证 CAS 显式拒绝且新状态未被覆盖。

## 环境与版本

- Python 3.11–3.13；本机临时文件系统；
- 真实 CAS 与 reload；无 API key；
- 预期 `L3_CONTAINED`。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch18_checkpoint_journal.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"observation":{"journal_records":2,"journal_valid":true,"loaded_step":2,"loaded_version":2,"stale_write_error":"CheckpointConflictError","versions":[1,2]},"passed":true,"scenario":"checkpoint"}
```

## 调试断点

在 `current_version != expected_version` 处断点；异常后重新从磁盘加载，而不是信任内存对象。

## 验收标准

必须观察 `CheckpointConflictError`，reload 仍为 step 2/version 2，journal 保持有效；故障被包含但无业务恢复声明。
