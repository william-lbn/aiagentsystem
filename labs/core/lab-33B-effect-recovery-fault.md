# Lab 33B — 副作用恢复：COMMITTED、NOT_APPLIED 与 UNKNOWN｜故障注入

## 实验目标

精确注入“远端已提交、本地确认丢失”的经典崩溃窗口。runtime 只能写 `UNKNOWN`，关闭并重开本地 coordinator 后必须查询远端 durable state，修复为 `COMMITTED`；随后重复 execute 仍不能二次扣款。

## 可证伪假设与故障位置

故障发生在 `remote.apply()` 返回之后、本地 receipt commit 之前。把 timeout 当 `NOT_APPLIED` 会重复 effect；把它当 `COMMITTED` 又可能掩盖真实未提交。唯一安全结论是 UNKNOWN，随后 observation/reconciliation。

## 环境与版本

与 Lab 33A 相同。实验真实关闭并重开本地 SQLite 连接，证明恢复不依赖进程内变量；远端数据库保持独立 durable state。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
try:
    coordinator.execute("charge-33", "charge_cents", 4200, lose_ack=True)
except EffectOutcomeUnknown:
    assert coordinator.status("charge-33") == "UNKNOWN"
coordinator.close()

reopened = EffectCoordinator(local_db, remote)
assert reopened.reconcile("charge-33") == "COMMITTED"
receipt = reopened.execute("charge-33", "charge_cents", 4200)
assert remote.count("charge-33") == 1
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch33_effect_recovery.py --fault
```

## 实际验证输出（本发布源码执行所得）

```json
{"reported_before_reconcile":"UNKNOWN","reconciled":"COMMITTED","receipt":"rcpt_046c902140291034","remote_effect_count":1,"system_detected":true,"contained":true,"recovered":true,"evidence_level":"L4_RECOVERED"}
```

## 调试断点

- remote transaction commit 后立刻注入 `lose_ack`；
- 本地 `UNKNOWN` durable write；
- 关闭/重开后 `remote.lookup(key)`；
- reconcile 写回 receipt；
- 最后重放确认 remote count 仍为 1。

## 验收标准

退出码 0；reconcile 前为 UNKNOWN、之后为 COMMITTED；receipt 非空；远端 count 恰为 1；`recovered=true`、`evidence_level=L4_RECOVERED`。只有“检测到 timeout”不够；必须证明重启后通过外部 observation 恢复且无重复 effect。

## 反例与进阶注入

- 让远端实际未提交，reconcile 应得到 `NOT_COMMITTED`，随后才可重试；
- 重用同 key 但改变 amount，必须拒绝；
- 在 reconcile 后、本地修复前再次 crash，下一次恢复仍应收敛；
- provider 无查询 API 时进入人工处置，不能用模型推测 effect 状态。
