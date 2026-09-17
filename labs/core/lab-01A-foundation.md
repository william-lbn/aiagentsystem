# Lab 01A — action-bound approval 与可验证副作用｜正常路径

## 实验目标

系统级验证不变量：**模型提议不是外部效果；只有绑定当前 action 的授权才能使 Runtime 提交一次效果，并由 receipt 验证。**

被测对象（SUT）是 `AgentRuntime + PolicyEngine + ToolRegistry + JsonCheckpointStore + EffectJournal` 的真实组合，不是打印预设答案。输入为事故 `INC-2048`，动作是轮换 `payments-api` 凭据。

## 环境与版本

- Python `3.11–3.13`；macOS 13+/Ubuntu 22.04+；`arm64` 或 `x86_64`；建议 2 CPU/4 GiB。
- 依赖由 `uv.lock` 固定；Core Lab 无网络、无 Docker、无 API key。
- 运行产生隔离临时 checkpoint/journal，不读取或修改真实凭据系统。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与输入

- 入口：`examples/chapters/ch01_foundation.py`
- 场景：`src/agentlab/course_scenarios.py::foundation`
- 执行内核：`src/agentlab/runtime.py::AgentRuntime.run`
- 审批与效果：`src/agentlab/security.py`、`src/agentlab/journal.py`

`ScriptedModel` 只固定候选动作，使控制实验可重复；`rotate_credential` 是确实被 Runtime 调用并写入独立 `effects` oracle 的函数。正常路径先得到 `WAITING_APPROVAL`，再以该 run 的 `action_id` 恢复。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch01_foundation.py
```

## 实际验证输出

```json
{"approval_bound": true, "effect_count": 1, "first_status": "WAITING_APPROVAL", "receipt_verified": true, "resume_status": "FINISHED"}
```

完整 stdout 还应给出 `passed=true`、`invariant_holds=true` 与 `evidence_level=L1_MECHANISM`。

## 调试断点

1. `course_scenarios.py::foundation`：检查 pending action 与提供的 action 是否相同；
2. `runtime.py::AgentRuntime.run`：观察 intent 先于工具执行被 checkpoint；
3. `security.py` 的审批校验：确认不是仅检查 `approved=true`；
4. `tools.py::ToolRegistry.execute` 与 journal commit：确认一次效果对应一份 receipt。

## 验收标准

进程退出码为 0；第一次运行状态为 `WAITING_APPROVAL`；恢复后为 `FINISHED`；`approval_bound=true`；独立 oracle 只观察到 1 次效果且 receipt 的 service/ticket/effect 三字段精确匹配。

## 证据解释与上限

这是 **L1_MECHANISM**：证明本仓库确定性场景的正常机制。它没有调用真实 secret manager，不测模型质量、跨主机一致性或云 IAM。不得写成“生产凭据轮换已验证”。

## 进阶实验

在审批后、执行前修改规范化参数；把审批绑定扩展为 `(run_id, action_id, args_sha256, expires_at)`，证明参数变化或过期时间到达都会产生新审批，而不是复用旧布尔值。
