# Lab 16B — HITL：陈旧审批拒绝｜故障注入

## 实验目标

用错误 action ID 恢复已暂停运行，验证陈旧/替换审批无法执行受控 effect。

## 环境与版本

- Python 3.11–3.13；本机 durable fixture；
- 确定性 clock；无网络/API key；
- 预期 `L3_CONTAINED`。

## 环境准备

```bash
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch16_hitl.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"observation":{"action_bound":true,"after":"WAITING_APPROVAL","before":"WAITING_APPROVAL","effect_count":0,"provided_action_matches":false,"state_version":2},"passed":true,"scenario":"hitl"}
```

## 调试断点

在 resume 的 `approval_action_id` 比较处断点；确认 tool function 未进入、journal 无新 effect、checkpoint 仍在等待状态。

## 验收标准

`provided_action_matches=false`、前后均 `WAITING_APPROVAL`、`effect_count=0`、`contained=true`。
