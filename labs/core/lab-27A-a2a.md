# Lab 27A — A2A 与 Multi-Agent 互操作｜正常路径

## 实验目标

执行“wire contract 校验 → task-bound delegation → durable task lifecycle → artifact digest → 关闭/重开恢复”的完整路径。实验要证明协议消息合法和调用有权是两个独立条件，并验证 `SUBMITTED → WORKING → COMPLETED` 只能通过受控状态迁移发生。

## 可证伪假设与不变量

假设：若 grant 同时绑定 principal、delegate、task、scope、时间窗和 nonce，并且 Task 使用版本化持久状态机，则合法调用可在重启后恢复到同一 artifact digest。

不变量：**A2A interoperability requires protocol validation plus task-bound authorization and durable lifecycle evidence**。

若数据库重开后状态/digest 不一致，事件顺序缺失，或未验证 grant 就创建 Task，本实验失败。

## 环境与版本

- OS：macOS 13+/Ubuntu 22.04+/WSL2；x86_64 与 arm64 均可；
- Python：3.11–3.13；仅使用标准库 SQLite/HMAC 与本仓库 AgentLab；
- CPU/Memory：2 核、4 GiB 足够；
- 外部依赖：无网络、无 Docker、无浏览器、无 API key；
- 官方 SDK 的跨进程互操作不在本 Core Lab 伪装执行，见独立 L5 evidence pack。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与真实机制

- 入口：`examples/chapters/ch27_a2a.py`；
- 场景：`src/agentlab/course_scenarios.py::a2a`；
- wire subset：`src/agentlab/protocols.py`；
- 委派/任务内核：`src/agentlab/coordination_system.py::DelegationAuthority` 与 `A2ATaskLedger`。

Grant 用 canonical JSON 做 HMAC-SHA256；Task/Event/Artifact 写入真实临时 SQLite。HMAC secret 是公开 fixture，只用于验证绑定机制，不代表生产身份方案。

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch27_a2a.py
```

运行时依次：构造并验证 A2A 1.0 Card/Task 子集；签发含 `artifact.publish` 的 grant；在授权后写 `SUBMITTED`；以 expected version 进入 `WORKING`；写 artifact/digest 与 `COMPLETED`；关闭数据库；新实例重开并比较 snapshot/event log。

## 实际验证输出（本发布源码 QA 生成）

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "A2A interoperability requires protocol validation plus task-bound authorization and durable lifecycle evidence", "invariant_holds": true, "observation": {"events": ["task.submitted", "task.status", "task.artifact", "task.status"], "grant": {"delegate": "researcher", "scopes": ["artifact.publish", "evidence.read"], "task_id": "task-27"}, "protocol_errors": [], "protocol_valid": true, "reopened": true, "task": {"artifact_digest": "3a979031ea40ae788654bd7815172fe710853aa4dbb1c43861ff309b6602688a", "context_id": "ctx-27", "delegate": "researcher", "state": "TASK_STATE_COMPLETED", "task_id": "task-27", "version": 3}}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "a2a", "system_detected": false}
```

## 调试断点与观察量

1. `DelegationAuthority.verify`：检查 constant-time signature、delegate/task/scope/time；
2. `A2ATaskLedger.submit`：授权检查应在 `BEGIN IMMEDIATE`/insert 之前；
3. `A2ATaskLedger.transition`：观察 expected version 与允许边；
4. `A2ATaskLedger.complete`：确认 digest 与终态在同一 commit；
5. `course_scenarios.a2a` 重开处：旧 connection 已关闭，snapshot 仍一致。

可额外用 SQLite CLI 查询 `a2a_tasks` 和 `a2a_events`，但不要修改 fixture 后仍引用上面的 digest 作为自己的输出。

## 验收标准

PASS 当且仅当：退出码 0；`protocol_valid=true`；事件严格为 submit/status/artifact/status；终态 `TASK_STATE_COMPLETED`、version 3、digest 为 64 位十六进制；`reopened=true`；整体 `passed=true`。

证据等级是 **L1_MECHANISM**：它证明本地机制正常路径被执行，不证明远程 A2A server、认证系统或外部 Agent 质量。

## 扩展实验

- 在 WORKING 后关闭进程，再重开完成，记录恢复点；
- 对旧 expected version 重放 transition，应得到 `task_version_conflict`；
- 用相同 idempotency key 重发同 task，应返回同一 snapshot；用该 key 指向另一 task 应失败；
- 将 store 替换为 PostgreSQL 时，重新证明 transaction isolation 与唯一约束；
- 运行 `experiments/l5` 的官方 SDK 实验，比较 Core wire helper 与官方 generated types，不得合并两类证据标签。

## 结果解释与声明边界

本实验没有模型调用。它真实验证协议子集、HMAC 字段绑定、SQLite durability 与 artifact digest；不验证 OAuth/mTLS、跨语言 binding、streaming/cancel/push、分布式一致性或 benchmark 成绩。
