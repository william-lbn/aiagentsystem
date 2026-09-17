# Lab 01B — 过期审批的 fail-closed｜故障注入

## 实验目标

反事实验证：当恢复请求携带 `stale-action-id` 时，被测 Runtime 必须检测 action identity 不匹配、保持等待态并产生 **0 次副作用**。

## 环境与版本

与 Lab 01A 相同：Python `3.11–3.13`，macOS/Linux，`arm64/x86_64`；无网络、Docker 与 API key；临时目录隔离 checkpoint/journal。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与故障模型

入口 `examples/chapters/ch01_foundation.py` 以 `--fault` 进入同一 `foundation` 场景。系统仍注册真实 `rotate_credential` 工具并走正常恢复 API；唯一自变量是把 pending action ID 替换为 `stale-action-id`。故障不是脚本提前 return，也不是 mock 出一个错误响应。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch01_foundation.py --fault
```

## 实际验证输出

```json
{"approval_bound": false, "effect_count": 0, "first_status": "WAITING_APPROVAL", "receipt_verified": false, "resume_status": "WAITING_APPROVAL"}
```

完整 stdout 应同时包含 `system_detected=true`、`contained=true`、`invariant_holds=true`、`evidence_level=L3_CONTAINED`。

## 调试断点

- 在 `foundation` 中记录 pending 与 supplied action；
- 在 Runtime 审批分支确认比较发生在工具调用之前；
- 在 `rotate_credential` 首行设断点：本实验中该断点**不得命中**；
- 结束时检查 effects 长度与 checkpoint phase。

## 验收标准

只有同时满足以下条件才 PASS：故障确实注入；系统而非外部 oracle 检测到不匹配；状态仍为 `WAITING_APPROVAL`；工具断点未命中；`effect_count=0`。仅出现异常或退出码 0 都不充分。

## 证据解释与上限

这是 **L3_CONTAINED**：检测并约束过期审批，但没有恢复业务目标，因此不是 L4。测试的是单机 Runtime 合同，不证明跨服务授权链或分布式 fencing。

## 进阶实验

分别注入正确 action ID/错误 run ID、正确身份/已过期批准、相同 action/不同参数摘要；制作二维矩阵，要求仅精确绑定且未过期的一格允许效果。
