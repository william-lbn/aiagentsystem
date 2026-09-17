# Lab 14B — 有界 Agent Loop：重复轨迹｜故障注入

## 实验目标

注入持续重复的同一动作和 observation，验证 Runtime 能检测无进展并在总步数预算之前停止。

## 环境与版本

- Python 3.11–3.13；macOS/Linux；ARM64/x86_64；
- 无网络/API key；真实循环和摘要计算；
- 预期证据 `L3_CONTAINED`，不声称恢复任务结果。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch14_agent_loop.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"observation":{"event_types":["decision","observation","decision","observation","decision","observation","stop"],"status":"NO_PROGRESS","steps":3,"stop_reason":"no_progress","verified":false},"passed":true,"scenario":"agent-loop"}
```

## 调试断点

观察三轮 `progress_digest` 相同，第三次后 `same_observation > 2`，Runtime 追加 `stop` 而不再调用决策器。

## 验收标准

`status=NO_PROGRESS`、`steps=3`、`contained=true`、`verified=false`；不得把 containment 写成任务成功或自动恢复。
