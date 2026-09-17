# Lab 28B — Multi-Agent 协作：分工、隔离、调度与成本｜故障注入

## 实验目标

注入 confused-deputy 式所有权错误：Coder 同时携带自己的 `repository.write` 和 Researcher 所需的 `sources.read`，尝试 claim `research`。验证系统不会把“有能力”误判成“拥有该 work order”，且事务 rollback 后预算、任务与 effect 均未改变。

## 可证伪假设与故障位置

假设：identity/owner 与 capability/scope 必须同时成立。只检查 scope 的 scheduler 会允许权限较大的 worker 横向接管任务，破坏责任链和上下文隔离。

故障位置在 `MultiAgentCoordinator.claim`；预期错误为 `work_order_owner_mismatch`，发生在预算预留和状态更新之前。

## 环境与版本

与 Lab 28A 相同：Python 3.11–3.13、标准库 SQLite、本仓库 AgentLab；无模型、网络、Docker 或 API key。先运行 28A 建立正常基线。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

入口为 `examples/chapters/ch28_multi_agent.py`，场景在 `course_scenarios.multi_agent`，持久调度实现为 `coordination_system.MultiAgentCoordinator`。

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch28_multi_agent.py --fault
```

注意这不是“scope 不足”测试：Coder 被故意赋予 `sources.read`，从而确认系统确实检查 owner。异常由场景捕获后，独立读取 run snapshot 与 effect count。

## 实际验证输出（本发布源码 QA 生成）

```json
{"contained": true, "evidence_level": "L3_CONTAINED", "evidence_meaning": "fault_detected_and_contained", "fault": true, "fault_injected": true, "invariant": "multi-agent execution requires explicit ownership, least-privilege context, budget conservation and verified join semantics", "invariant_holds": true, "observation": {"effect_count": 0, "initial_frontier": ["patch", "research"], "rejected": "work_order_owner_mismatch", "snapshot": {"budget_limit": 9, "budget_reserved": 0, "status": "RUNNING", "tasks": {"patch": "READY", "research": "READY", "verify": "READY"}}}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "multi-agent", "system_detected": true}
```

## 调试断点

- `claim` 读取 work order 后的 owner 比较；
- exception handler 前的 SQLite transaction；
- rollback 后 `run_snapshot` 的 `budget_reserved`；
- `effect_count`，确认没有提前发布；
- `_ok` 的 evidence classification，确认场景已列入 contained faults。

## 验收标准

PASS 当且仅当：退出码 0；错误为 `work_order_owner_mismatch`；三项任务仍为 READY；预算预留为 0；effect count 为 0；`system_detected=true`、`contained=true`、`evidence_level=L3_CONTAINED`。

L3 表示所有权故障被被测 scheduler 主动阻断；不表示任务随后被重新调度、业务已经恢复或分布式 worker lease 已验证。

## 反例与进阶注入

- 用正确 owner 但删除 required scope，应得到 `work_order_scope_missing`；
- 并发 claim 使预算可能超过上限，确认只有一个事务成功；
- 在依赖未完成时 claim reviewer，确认 frontier 检查阻断；
- 让旧 owner 在任务重新分配后提交 completion，加入 lease/version 后验证拒绝；
- 让两个模型产出表面一致但引用同一错误来源的 artifact，证明多数投票不是独立 verifier。

## 结果解释与声明边界

观察重点是拒绝后的持久状态没有变化，而不只是捕获了异常。实验覆盖单 SQLite scheduler 的 owner/scope 分离；生产系统还需 authenticated worker identity、lease/fencing token、跨租户 ACL、消息重放防护与真实 artifact verifier。
