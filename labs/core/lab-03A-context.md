# Lab 03A — 受信任、租户与预算约束的 Context Assembly｜正常路径

## 实验目标

验证组装器在 90-token 教学预算内强制保留 policy/task，按效用选择当前 trace/runbook，并以明确原因丢弃低价值旧历史。

## 环境与版本

Python `3.11–3.13`；macOS/Linux；`arm64/x86_64`；无网络、Docker 或 API key。固定 token cost 用于跨主机确定性实验，不等同于任一 provider tokenizer。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与输入

入口 `examples/chapters/ch03_context.py`，SUT 为 `foundation_system.py::ContextAssembler`。候选记录包括 `policy(18, mandatory)`、`task(16, mandatory)`、`trace(24)`、`runbook(28)` 和 `old-chat(30)`，每条携带 channel/source/tenant/freshness/authority。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch03_context.py
```

## 实际验证输出

```json
{"budget": 90, "excluded": {"old-chat": "token_budget"}, "selected": ["policy", "task", "trace", "runbook"], "used_tokens": 86}
```

## 调试断点

在 tenant/trust 预过滤、mandatory cost、utility/token 排序和 optional admission 处检查候选；在 manifest 生成处确认 excluded reason 未丢失。

## 验收标准

mandatory 全部存在，used tokens 不超过 90，选择顺序稳定，`old-chat` 因预算排除，`invariant_holds=true/L1_MECHANISM`。

## 证据解释与上限

本实验证明组装控制流，不证明选择结果是全局最优，也不证明模型一定使用了 trace/runbook。固定成本不应被报告为 OpenAI token 数。

## 进阶实验

把 mandatory 总成本设为 91，要求组装器整体失败而不是丢 policy；再设计一个可以证明优于贪心的反例，比较 ILP 与启发式但保留相同安全 gate。
