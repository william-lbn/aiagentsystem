# Lab 40B — Capstone：权限、审批、唯一副作用与独立验证｜故障注入

## 实验目标

在 provider 已提交 effect 后丢失响应。本地持久化 `UNKNOWN`，进入 `RECONCILING`，按同一 key 查询远端并修复 receipt；最终 effect count 仍为 1，trace 与 verifier 收敛到 `COMPLETED`。

## 可证伪假设与故障位置

故障精准位于远端 transaction commit 与本地确认之间。把 timeout 当失败会重复 effect；把 timeout 当成功会隐藏未提交。唯一安全的中间状态是 UNKNOWN，且恢复必须依赖 provider observation。

## 环境与版本

与 Lab 40A 相同。故障路径真实写入两个 SQLite 数据库并执行 reconcile，不是预先写好的状态列表。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
orchestrator = CapstoneOrchestrator(workdir)
approval = orchestrator.demonstration_approval("run-capstone")
result = orchestrator.run("run-capstone", approval=approval, lose_ack=True)
assert "UNKNOWN" in result["path"] and "RECONCILING" in result["path"]
assert result["path"][-1] == "COMPLETED"
assert result["effect_count"] == 1 and result["recovery_used"]
orchestrator.close()
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch40_capstone.py --fault
```

## 实际验证输出（本发布源码执行所得）

```json
{"path":["RECEIVED","TRIAGED","PLANNED","WAITING_APPROVAL","EXECUTING","UNKNOWN","RECONCILING","VERIFYING","COMPLETED"],"capability_allowed":true,"approval_bound":true,"effect_count":1,"recovery_used":true,"trace_verified":true,"verified":true,"system_detected":true,"contained":true,"recovered":true,"evidence_level":"L4_RECOVERED"}
```

## 调试断点

- provider commit 后的 `lose_ack`；
- local UNKNOWN 的 durable write；
- reconcile 使用的 key/operation/args identity；
- completion 前 effect count、receipt 与 hash chain verifier。

## 验收标准

退出码 0；路径包含 UNKNOWN/RECONCILING 且最后 COMPLETED；远端 effect 恰为 1；`recovered=true`、`evidence_level=L4_RECOVERED`。若 provider 没有权威查询接口，实验必须停在 UNKNOWN，不能伪称恢复。

## 反例与进阶注入

- provider 实际未提交，reconcile 证明 absent 后才允许同 key 重试；
- reconcile 完成而本地写回前再次崩溃，重启仍须幂等收敛；
- 篡改 event chain，verifier 应转为 `QUARANTINED` 而不是完成。
