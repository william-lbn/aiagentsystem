# Lab 08B — 提交后响应丢失与对账恢复｜故障注入

## 实验目标

`SimulatedRemoteLedger.apply` 先把 effect 写入 idempotency ledger，然后抛出 `reply_lost_after_remote_commit`。这与“调用前直接抛 timeout”不同：副作用确实发生，盲重试可能重复。

## 环境与版本

与 Lab 08A 相同：Python 3.11–3.13，macOS/Linux、arm64/x86_64，无网络/API key。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；故障由 `SimulatedRemoteLedger` 在真实落账后确定性注入，不依赖网络随机性。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch08_tool_runtime.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L4_RECOVERED","fault":true,"invariant_holds":true,"observation":{"effect_count":1,"final_phase":"COMMITTED","first_phase":"UNKNOWN","journal":["PREPARED","UNKNOWN","COMMITTED"],"receipt_id":"rcpt-1"},"oracle_detected":true,"passed":true,"recovered":true,"scenario":"tool-runtime","system_detected":true}
```

## 验收标准

- 故障后第一状态必须是 UNKNOWN，不能伪写 FAILED/NOT_APPLIED；
- reconciliation 通过同一 idempotency key 查询 receipt；
- 最终 COMMITTED，effect_count 仍为 1；
- Journal 必须保留三步历史。

满足检测、包含并恢复，因此为 L4。若只停在 UNKNOWN 则是 L3；若测试看到 timeout 但 Runtime 标为 FAILED，则不满足不变量。

## 调试断点

在 `remote.apply` 抛错前检查 ledger 已有记录；在 `reconcile` 检查它调用 lookup 而非再次 apply。可扩展 NOT_APPLIED 分支、延迟可见 ledger、幂等 key 参数冲突与人工 exception queue。

## Claim ceiling

这是确定性外部系统模型，不证明真实支付/云 API 的一致性。L5 升级需要 disposable provider sandbox、真实断流、真实查询 receipt 和脱敏服务端证据。
