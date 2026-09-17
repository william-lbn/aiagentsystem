# Lab 02B — 字符串冒充整数的契约故障｜故障注入

## 实验目标

验证可解析 JSON 仍可能违反类型合同；`"window_minutes":"30"` 必须在 schema 层被检测并阻断，不能静默转换后调度。

## 环境与版本

Python `3.11–3.13`；macOS/Linux；`arm64/x86_64`；无网络、Docker 与 API key。与 02A 使用完全相同的 decoder 和合同。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与故障模型

运行 `examples/chapters/ch02_model_substrate.py --fault`。唯一自变量是把 `window_minutes` 从 JSON number 变为 JSON string；JSON 语法仍合法，工具名也存在，因此可以确认错误由 schema/type gate 捕获。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch02_model_substrate.py --fault
```

## 实际验证输出

```json
{"effect_dispatched": false, "validation": {"accepted": false, "errors": ["argument_type:window_minutes:expected_int"], "stage": "schema"}}
```

## 调试断点

在 `StrictDecisionDecoder._is_type` 检查 value 的实际类型；在 schema 错误返回处确认尚未进入 semantic/dispatch；在执行边界设断点，故障路径不得命中。

## 验收标准

reason code 精确为 `argument_type:window_minutes:expected_int`，stage 为 `schema`，`effect_dispatched=false`；完整结果为 `system_detected=true/contained=true/L3_CONTAINED`。

## 证据解释与上限

L3 只说明此类类型漂移被本地组件约束。它不证明所有业务语义正确：合法字符串 `payments-api` 仍可能指向错误租户或环境。

## 进阶实验

追加 `true` 冒充整数、未知字段、NaN/极值、未知工具和低于阈值的 confidence；要求分别落到 schema 或 semantic 层，并保持零调度。
