# Lab 04B — Orphan Tool Result 因果断裂｜故障注入

## 实验目标

注入引用 `call-404` 的工具结果；要求 ledger 检测 orphan、拒绝追加、保留合法 `call-7` 的 pending 状态，并阻止错误观测影响最终回答。

## 环境与版本

Python `3.11–3.13`；macOS/Linux；`arm64/x86_64`；无网络、Docker 或 API key。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与故障模型

入口 `examples/chapters/ch04_messages.py --fault`。前两项与 Lab 04A 相同；第三项 tool name 正确但 call ID 改成不存在的 `call-404`，用于隔离 identity 因素。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch04_messages.py --fault
```

## 实际验证输出

```json
{"accepted": [true, true, false], "errors": ["orphan_or_duplicate_tool_result"], "ledger_size": 2, "pending_calls": ["call-7"], "trajectory_sha256": "3537151ff45a487e"}
```

## 调试断点

在 `_pending` lookup 处确认 `call-404` 不存在；在 ledger append 行设断点并确认故障 item 不进入；结尾确认 pending `call-7` 没有被错误消费。

## 验收标准

必须同时看到明确 reason code、append 第三项为 false、ledger 长度仍为 2、合法 pending 保留，以及 `system_detected=true/contained=true/L3_CONTAINED`。

## 证据解释与上限

L3 表示孤儿结果在本地边界被约束；没有恢复缺失的合法结果，因此不是 L4。实验未覆盖跨进程重复投递与消息代理重排序。

## 进阶实验

分别注入重复 item ID、重复 call ID、正确 call/错误 tool name 和 pending 未清时的 final；要求 reason code 可区分且任何拒绝均不改变 digest。
