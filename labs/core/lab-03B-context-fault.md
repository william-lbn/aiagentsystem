# Lab 03B — 网页指令污染与跨租户记录双故障｜故障注入

## 实验目标

同时注入两类高风险 context fault：不可信网页内容被标成 system channel，以及 tenant-b 记录进入 tenant-a 候选集。要求两者在评分前被隔离。

## 环境与版本

Python `3.11–3.13`；macOS/Linux；`arm64/x86_64`；无网络、Docker 与 API key。恶意 URL 使用 `.invalid` fixture，不发出网络请求。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与故障模型

入口 `examples/chapters/ch03_context.py --fault`。`web-injection` 的 priority 很高且文本要求绕过审批；`other-tenant` 也具有高优先级。这样可证明安全边界不是靠低相关性偶然排除。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch03_context.py --fault
```

## 实际验证输出

```json
{"excluded": {"old-chat": "token_budget", "other-tenant": "tenant_mismatch", "web-injection": "untrusted_instruction_channel"}, "selected": ["policy", "task", "trace", "runbook"], "used_tokens": 86}
```

## 调试断点

在 `ContextAssembler.assemble` 的 tenant 与 untrusted-channel 分支停下；确认两个恶意记录从未进入 utility 排序；在模型调用边界确认 selected 中不存在其 ID。

## 验收标准

两条故障均被独立 reason code 检测，selected 集保持合法，预算不超限；完整结果必须为 `system_detected=true/contained=true/invariant_holds=true/L3_CONTAINED`。

## 证据解释与上限

这是两种已知元数据故障的 L3 containment，不是通用 prompt-injection 防御证明。若来源元数据本身被伪造，还需内容隔离、授权和工具层防线。

## 进阶实验

让恶意文本进入合法 evidence channel，证明它可以作为数据被引用但不能改变工具权限；再模拟 provenance 缺失，要求记录默认降为 untrusted 而非继承 system 权威。
