# Lab 16A — HITL：绑定动作的持久审批｜正常路径

## 实验目标

真实写入 checkpoint/journal，暂停高风险工具，使用准确 `action_id` 恢复，并验证 effect 只发生一次。

## 环境与版本

- Python 3.11–3.13；本机临时文件 store；
- `AgentRuntime` + `JsonCheckpointStore` + `EffectJournal`；
- 无网络/API key；证据上限 `L1_MECHANISM`。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch16_hitl.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"observation":{"action_bound":true,"after":"FINISHED","before":"WAITING_APPROVAL","effect_count":1,"provided_action_matches":true,"state_version":6},"passed":true,"scenario":"hitl"}
```

## 调试断点

检查 pending approval 的 action ID、resume 时 ID 比较、工具入口前 policy gate、effect journal 与最终 checkpoint version。

## 验收标准

先暂停后完成，`action_bound=true`、`effect_count=1`。本实验不证明 OAuth principal、签名或多人审批。
