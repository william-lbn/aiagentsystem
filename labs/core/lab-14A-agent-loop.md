# Lab 14A — 有界 Agent Loop｜正常路径

## 实验目标

真实执行“决策—动作—观察—完成提案—外部验证”闭环，证明模型式 `finish` 只有通过 verifier 才进入 `FINISHED`。

## 环境与版本

- Python 3.11–3.13；macOS/Linux；ARM64/x86_64；
- 代码：`src/agentlab/runtime_system.py::GovernedLoop`；
- 无网络、容器或 API key；证据上限 `L1_MECHANISM`。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch14_agent_loop.py
```

决策器先返回 `act(inspect)`，观察器产生带 digest 的新证据，第二轮才返回 `finish`；verifier 检查事件中确有新证据。

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"observation":{"event_types":["decision","observation","decision"],"status":"FINISHED","steps":2,"stop_reason":"goal_verified","verified":true},"passed":true,"scenario":"agent-loop"}
```

## 调试断点

在 `GovernedLoop.run` 的 decision append、observation digest 与 `verify(tuple(events))` 处停下；确认 `finish` 之前状态仍不是成功。

## 验收标准

退出码 0，`steps=2`、`verified=true`、`status=FINISHED`。这不证明任何真实模型质量，只证明 Runtime 的完成门禁。
