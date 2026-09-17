# Lab 02A — 三层严格解码一个工具决定｜正常路径

## 实验目标

验证工具候选必须依次通过 JSON 语法、判别联合 schema 和 capability/置信策略语义检查，合格的 `schedule_maintenance` 决定才会成为可调度意图。

## 环境与版本

Python `3.11–3.13`；macOS/Linux；`arm64/x86_64`；无网络、Docker 或 API key。实验使用标准库 `json` 与仓库 `StrictDecisionDecoder`，不宣称评估真实模型。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与输入

- 入口：`examples/chapters/ch02_model_substrate.py`
- 场景：`course_scenarios.py::model_substrate`
- SUT：`foundation_system.py::StrictDecisionDecoder`

输入声明 `kind=tool`、`tool=schedule_maintenance`、`service=payments-api`、整数 `window_minutes=30`、`confidence=0.94`；本地合同要求 `{service: str, window_minutes: int}` 且最低 confidence 0.70。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch02_model_substrate.py
```

## 实际验证输出

```json
{"effect_dispatched": true, "validation": {"accepted": true, "errors": [], "stage": "accepted"}}
```

## 调试断点

依次检查 `StrictDecisionDecoder.decode` 的 JSON parse、unknown fields、discriminator、参数集合/类型、tool capability 和 confidence policy。最后在场景的 `effect_dispatched` 赋值处确认它完全由 `accepted` 导出。

## 验收标准

`accepted=true`、`stage=accepted`、errors 为空，解析后的 `window_minutes` 仍为整数 30，stdout 为 `L1_MECHANISM`。若实现通过字符串 coercion 才成功，视为失败。

## 证据解释与上限

实验只证明本地 decoder 对固定合法 payload 的合同。真实 OpenAI/其他 provider 运行必须另外记录模型快照、请求 ID、schema、时间与原始 item，API key 只能从环境变量读取。

## 进阶实验

增加带 `schema_version` 的 `final|tool|abstain` 判别联合；建立旧版迁移策略，并测试未知 discriminator 默认拒绝。
