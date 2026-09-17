# Lab 08A — Intent、Journal 与 Receipt｜正常路径

## 实验目标

验证一次写动作先持久化 PREPARED，再由可查询远端 ledger 提交并记录 COMMITTED；参数摘要必须与 ActionIntent 一致，远端效果数为一。

## 环境与版本

Python 3.11–3.13，macOS/Linux、arm64/x86_64；无网络/API key。SUT 为 `EffectController`、`InMemoryEffectJournal`、`SimulatedRemoteLedger`。远端模型执行真实状态写入，但仅在当前进程内，因此证据不是外部 provider L5。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；确保 `PYTHONPATH=src`，不配置真实支付端点或密钥。

## 实验代码

固定 action `act-08` 将 `inv-2048` 标为 paid；canonical args 生成 SHA-256，idempotency key 为 `idem-act-08`。

```bash
PYTHONPATH=src uv run python examples/chapters/ch08_tool_runtime.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"invariant_holds":true,"observation":{"effect_count":1,"final_phase":"COMMITTED","first_phase":"COMMITTED","journal":["PREPARED","COMMITTED"],"receipt_id":"rcpt-1"},"passed":true,"scenario":"tool-runtime"}
```

## 调试断点

在 `EffectController.execute` 的 args digest、PREPARED append、remote apply 和 COMMITTED append 处停下；确认 journal 顺序先于远端调用。

## 验收标准

要求轨迹严格为两步、receipt 非空、effect_count=1。将 args 在 Intent 后改为其他 invoice，必须抛出 `intent_args_digest_mismatch` 且 journal/remote 均无效果。
