# Lab 28A — Multi-Agent 协作：分工、隔离、调度与成本｜正常路径

## 实验目标

用真实 SQLite 状态执行三节点协作 DAG：`research` 与 `patch` 同时进入 frontier，`verify` 等待二者完成；每个 owner 只得到自己的 input reference 与 scope；全局预算原子预留；join 生成一次幂等发布 receipt；关闭并重开后状态不丢失。

## 可证伪假设与不变量

假设：显式 work order、依赖、owner、scope、input projection、预算和 effect key 足以使控制面在无模型条件下可重复验证。

不变量：**multi-agent execution requires explicit ownership, least-privilege context, budget conservation and verified join semantics**。

任一情形均判失败：`verify` 提前 READY；Researcher 看见 repo reference；预算预留超过 9；重复 join 使 effect count 增加；重开后状态不是 COMPLETED。

## 环境与版本

- OS：macOS 13+/Ubuntu 22.04+/WSL2；x86_64/arm64；
- Python：3.11–3.13；SQLite 来自 Python 标准库；
- 资源：2 核、4 GiB 足够；不需要模型、网络、Docker 或 API key；
- 模型 worker 属于可选上层，本实验专门隔离 scheduler/control-plane 正确性。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与被测任务图

| task | owner | required scope | max cost | input refs | depends on |
|---|---|---|---:|---|---|
| research | researcher | `sources.read` | 3 | `source:policy` | — |
| patch | coder | `repository.write` | 4 | `repo:workspace` | — |
| verify | reviewer | `artifacts.verify` | 2 | 两个 artifact 引用 | research, patch |

总预算正好为 9，使遗漏预留或重复扣费立即可见。

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch28_multi_agent.py
```

代码分为三层：入口是 `examples/chapters/ch28_multi_agent.py`，场景编排在 `course_scenarios.multi_agent`，持久调度核心为 `MultiAgentCoordinator`。正常路径 claim/complete 两个前置任务，确认新 frontier 只有 `verify`，再验证并重复调用 join，最后关闭/重开数据库。

## 实际验证输出（本发布源码 QA 生成）

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "multi-agent execution requires explicit ownership, least-privilege context, budget conservation and verified join semantics", "invariant_holds": true, "observation": {"context_projection": {"coder": ["repo:workspace"], "researcher": ["source:policy"]}, "effect_count": 1, "idempotent_replay": true, "initial_frontier": ["patch", "research"], "join_frontier": ["verify"], "receipt_sha256": "5ef6a7600f9ca38383075155f46ecb4ee1b4ec118225e8ed9a4de7f280e9ff85", "snapshot": {"budget_limit": 9, "budget_reserved": 9, "status": "COMPLETED", "tasks": {"patch": "COMPLETED", "research": "COMPLETED", "verify": "COMPLETED"}}}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "multi-agent", "system_detected": false}
```

## 调试断点与观察量

1. `MultiAgentCoordinator.ready`：观察 dependency anti-join；
2. `claim` 的 `begin immediate`：owner/scope/dependency/budget 与 update 必须在同一事务；
3. `complete`：只有当前 owner 且状态 CLAIMED 才能写 artifact digest；
4. `join`：expected task set、全部 digest 和 effect unique key；
5. `run_snapshot`：重开后的 budget/status/task states。

## 验收标准

PASS 当且仅当：退出码 0；初始 frontier 为 patch/research；join frontier 只有 verify；context projection 互斥；预算 `9/9`；全部任务 COMPLETED；重复 join 后 effect count 仍为 1；`passed=true`。

证据等级 **L1_MECHANISM** 仅覆盖调度正常路径，不表示 worker 的自然语言/代码 artifact 在真实任务上正确。

## 扩展实验

- 将预算改为 6，先 claim research，再 claim patch，应得到 `run_budget_exceeded`；
- 在 research 完成前 claim verify，应得到 dependency incomplete；
- 更换 expected task set，join 应得到 `join_task_set_mismatch`；
- 给每个 worker 接入本地小模型或 OpenAI provider，但保持相同 work order、预算和 verifier，对比单 Agent 基线；
- 用线程/多进程同时 claim，保存每次 transaction 结果，检查没有 budget oversubscription。

## 结果解释与声明边界

本实验真实执行 durability、事务和唯一约束，worker artifact 则是确定性 fixture。它不会伪造“多个大模型已协作”，也不报告未运行的质量提升；模型层实验必须另存 provider/model、prompt、seed/采样、token/tool cost 和 evaluator 输出。
