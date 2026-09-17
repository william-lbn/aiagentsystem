# Multi-Agent 协作：分工、隔离、调度与成本

> **本章核心判断**：多 Agent 的价值不来自“角色数量”，而来自可验证的任务分解、受限信息投影、明确所有权、预算守恒和独立 join。若所有 worker 共享全量上下文与权限，再让 supervisor 用自然语言汇总，系统只是把单 Agent 的不确定性放大为并发的不确定性。

上一章解决远端 Agent 间的协议边界；本章解决一个目标被多个执行体共同推进时的控制面。下一篇将把这些轨迹放进 evaluation、benchmark、observability、安全与恢复体系。

![Multi-Agent 的任务图、权限、预算与验证边界](../../assets/diagrams/28-multi-agent-architecture.svg)

## 问题背景与学习目标

“researcher、coder、reviewer 轮流发言”不是系统架构。真正的多 Agent 协作必须回答：谁拥有哪个 work order？每个 worker 看到哪些输入、持有哪些能力？哪些任务可并行？预算在并发 claim 时会不会超卖？部分失败后怎样重试？最终输出由谁验证？发布 effect 会不会执行两次？

本章完成后，读者应能：

- 用任务 DAG、owner、capability、input projection 与 artifact contract 描述协作，而不是只写角色 prompt；
- 区分 manager-as-tools、handoff、deterministic workflow、blackboard 与市场式调度；
- 解释并行收益何时被通信、重复工作、冲突和验证成本抵消；
- 实现原子预算预留、依赖 frontier、owner/scope 检查与 exactly-once effect key；
- 设计能发现串谋、同源错误、上下文泄漏和 supervisor bottleneck 的评测。

## 核心概念与系统直觉

> **Invariant**：任何 work order 只有认证 identity 与 owner 相符、能力覆盖 required scope、依赖完成且原子预算预留成功时才能执行；最终 effect 还必须通过 exact-task-set join 并由稳定 key 去重。

**Work order 是最小可审计委派单元。** 它至少包含 task ID、owner、输入引用、输出 schema、依赖、required scope、最大成本、deadline 与 verifier。自然语言目标可以附带，但不能替代这些字段。

**Owner 表示责任归属，不是“谁先抢到”。** 一个任务可以由 scheduler 重新分配，但任何时刻只有一个有效 lease/owner。worker 的名称不构成身份；运行时必须用已认证 identity 检查 claim 和 completion。

**Context projection 是信息流控制。** Researcher 只需要 `source:policy`，Coder 只需要 `repo:workspace`。把完整用户历史、秘密、别的 worker scratchpad 全部广播，不仅增加 token，还扩大 prompt injection、隐私和错误耦合面。

**Frontier 是所有依赖已满足的 READY 任务集合。** 可并行不等于应该无限并行。scheduler 还需考虑预算、速率限制、资源冲突、风险与下游 join 的等待时间。

**Join 是独立状态转移。** 它不是 supervisor 写一段更顺的总结，而是检查 expected task set、完成状态、artifact digest、schema、冲突和业务 verifier 后，才允许产生最终 effect。

## 原理与理论基础

设任务图为有向无环图 $G=(V,E)$，任务 $i$ 的最大资源需求为 $c_i$，全局预算为 $B$。任一时刻的预留必须满足：

$$
\sum_{i\in Claimed\cup Completed} reserved_i \le B
$$

这项约束必须在原子 transaction 内检查和更新；先读取余额、后分别写入的并发实现会发生 budget oversubscription。

对 work order $w_i$，可执行条件为：

$$
Ready(i)\land Identity(a)=Owner(i)\land Scope(i)\subseteq Cap(a)
\land Budget(i)\land LeaseValid(i)
$$

完成条件则额外要求 artifact 满足 contract。全局完成不是“所有 worker 都说完成”，而是：

$$
Complete(run)=ExactTaskSet\land \bigwedge_i Verified(A_i)
\land JoinInvariant\land EffectReceipt
$$

多 Agent 是否值得，还需比较实际 makespan：

$$
T_{multi}\approx \max(T_{parallel})+T_{coord}+T_{join}+T_{conflict}+T_{verify}
$$

当协调、冲突和验证成本大于被并行化的关键路径，多 Agent 反而更慢、更贵。增加角色数量不是单调改进。

## 关键机制与执行流程

![Multi-Agent 从任务图到幂等发布的执行与拒绝路径](../../assets/diagrams/28-multi-agent-flow.svg)

1. **编译任务图**：验证 task ID 唯一、依赖存在且无环，固定 expected task set；
2. **投影上下文**：为每个 work order 生成最小 `input_refs`，秘密由运行时按能力临时取用；
3. **计算 frontier**：只有依赖全部 COMPLETED 的 READY task 可 claim；
4. **原子 claim**：在同一 transaction 中检查 owner、scope、status、依赖和预算并写入 CLAIMED；
5. **提交 artifact**：completion 必须来自 owner，写入 canonical digest；失败任务不得伪装成空 artifact；
6. **验证 join**：expected task set 完全一致、所有 artifact 可用、冲突已处理，才创建发布 receipt；
7. **幂等 effect**：`(run_id,effect_key)` 唯一，恢复或重复 join 不增加 effect count。

Scheduler 决定“何时/谁可执行”，模型决定“如何解决开放子问题”。把权限、预算或完成性留给模型自述，会让不可验证判断进入控制面。

## 从原理到实现

本章使用三个有真实依赖的 work order：研究和修改可并行，验证必须等待两者：

```python
orders = (
    WorkOrder("research", "researcher", "sources.read", 3, ("source:policy",)),
    WorkOrder("patch", "coder", "repository.write", 4, ("repo:workspace",)),
    WorkOrder(
        "verify",
        "reviewer",
        "artifacts.verify",
        2,
        ("artifact:research", "artifact:patch"),
        ("research", "patch"),
    ),
)
coordinator.create_run("run-28", budget_limit=9, orders=orders)
assert coordinator.ready("run-28") == ("patch", "research")
```

`claim` 在 SQLite `BEGIN IMMEDIATE` 中完成检查和预算预留，错误 owner 即使持有同名 scope 也不能取得 work order：

```python
research = coordinator.claim(
    "run-28",
    "research",
    agent="researcher",
    scopes={"sources.read"},
)
assert research["input_refs"] == ("source:policy",)

receipt = coordinator.join(
    "run-28",
    expected_tasks=("research", "patch", "verify"),
    effect_key="publish-28",
)
```

实现位于 `src/agentlab/coordination_system.py`。它使用真实 SQLite durability 与唯一约束，但 worker 的语义输出是固定 fixture；因此实验能够证明调度不变量，不能证明某个 LLM 的研究、代码或协作质量。

## 主流系统实现对照与源码阅读入口

| 系统/模式 | 控制语义 | 应重点审计的公开机制 | 本章证据边界 |
|---|---|---|---|
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | manager-as-tools、handoff、Python orchestration | 谁拥有最终回复、handoff input filter、session、approval、trace | 已有 SDK durable run evidence；本章未宣称云模型协作分数 |
| [Google ADK](https://github.com/google/adk-python) | LLM Agent 与 Sequential/Parallel/Loop/custom workflow | session/event、shared state、workflow agent、remote boundary | 已有 pinned session/event L5；需单独评测任务语义 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | StateGraph、subgraph、checkpoint、interrupt | reducer、pending writes、subgraph namespace、resume | 已有 graph resume L5；不是权限/预算证明 |
| [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | agents、workflow、executor/superstep | edge、checkpoint、concurrency、hosting/replay | 已有 scoped checkpoint evidence；版本不可混用 |
| [A2A](https://github.com/a2aproject/A2A) | 跨进程任务协议 | discovery、Task/Event/Artifact、auth hook | 解决互操作，不替代本地 scheduler 与业务 join |

OpenAI Agents SDK 的官方文档明确区分 manager 调用 agent-as-tool 与 handoff：前者由 manager 保持会话和最终答案所有权，后者由 specialist 接管。这个差异会改变 history、guardrail、approval 和用户可见责任链，不能只当两种 prompt 写法。

## 设计方案与方法对比

| 模式 | 最适合 | 主要风险 | 必须存在的控制 |
|---|---|---|---|
| Manager / agents-as-tools | 汇总多个 bounded specialist 输出 | manager bottleneck、遗漏冲突 | structured outputs、per-tool budget、final verifier |
| Handoff | 路由后由专家直接负责用户交互 | context/authority 随控制权漂移 | input filter、目标白名单、handoff audit |
| Deterministic DAG | 合规、数据管道、发布流程 | 灵活性较低、图迁移复杂 | checkpoint、schema/version、effect journal |
| Blackboard | 多方迭代共享中间事实 | 脏写、错误级联、秘密扩散 | typed record、ACL、version/CAS、provenance |
| Debate / critic | 高价值、可验证判断 | 同源模型相关错误、成本倍增 | 独立证据、角色隔离、外部 judge |
| Market / auction | 大规模异构 worker 分配 | 报价操纵、质量难比较 | identity、escrow/budget、reputation、objective verifier |

架构选择首先看 ownership 与失败代价。若一个确定性程序就能可靠完成，不应为了“更 agentic”拆成多个模型；若子任务真正独立、需要不同工具/权限/模型且可分别验证，多 Agent 才可能产生净收益。

## 可复现实验

### Lab 28A — 持久调度、最小上下文与幂等 join

```bash
PYTHONPATH=src python examples/chapters/ch28_multi_agent.py
```

**实际输出。** 本发布源码的关键结果如下：

```json
{"initial_frontier":["patch","research"],"join_frontier":["verify"],"context_projection":{"coder":["repo:workspace"],"researcher":["source:policy"]},"snapshot":{"status":"COMPLETED","budget_limit":9,"budget_reserved":9},"effect_count":1,"idempotent_replay":true,"evidence_level":"L1_MECHANISM"}
```

实验真实写入 SQLite、关闭并重开，重复执行 join 后 effect count 仍为 1。完整环境、关键断点和验收见 [Lab 28A](../../../labs/core/lab-28A-multi-agent.md)。

**关键断点与验收。** 在 `claim()` 的 owner/scope/预算检查后、`complete()` 写入 artifact digest 后，以及 `join()` 创建 effect receipt 前分别停下：前两个任务完成后 frontier 必须严格等于 `("verify",)`；重开数据库后预算预留仍为 9；同一 `effect_key` 连续 join 两次仍只有一条 receipt。任一条件不成立，都说明实验没有证明依赖门控、durability 或幂等发布中的至少一项。

### Lab 28B — 所有权混淆故障注入

```bash
PYTHONPATH=src python examples/chapters/ch28_multi_agent.py --fault
```

故障让 `coder` 携带 `sources.read` 尝试 claim `researcher` 的任务；scope 看似足够，但 identity/owner 不匹配：

```json
{"rejected":"work_order_owner_mismatch","snapshot":{"status":"RUNNING","budget_reserved":0,"tasks":{"patch":"READY","research":"READY","verify":"READY"}},"effect_count":0,"evidence_level":"L3_CONTAINED"}
```

事务 rollback 后预算未扣、任务未 claim、发布 effect 为零，因此证据是 L3 containment。完整步骤见 [Lab 28B](../../../labs/core/lab-28B-multi-agent-fault.md)。

**实验语义边界。** 该实验不调用模型，也不声称三个模型真的并行工作；它执行的是多 Agent 系统最容易被 demo 隐藏的控制面。模型质量需在第 29–30 章的固定任务、预算和 verifier 下另测。

## 工程场景与系统设计

以“研究政策变化并修改合规代码”为例，Researcher 得到锁定官方来源和只读网络，Coder 得到独立 worktree 与测试命令，Reviewer 只读取两类 artifact 和验收规则。两个前置任务同时进入 frontier，但各自 secret、工具和上下文互不可见；Reviewer 未完成前，publish task 不存在可执行路径。

小型开源模型适合分类、抽取、轻量 reviewer 或离线回归，可通过附录 A 的本地 OpenAI-compatible endpoint 使用；高难研究/代码任务可选更强本地模型或 OpenAI Responses/Agents SDK。教程不硬编码“最新模型名”，运行时从环境变量选择 provider/model，key 不进入 prompt、SQLite、artifact 或 trace。

## 故障模型、失败模式与排错

- **所有权混淆**：认证 identity 与 owner 不同即拒绝，不允许“有 scope 就代做”；
- **预算超卖**：claim 的检查与预留必须原子化，拒绝读后写竞态；
- **依赖绕过**：frontier 由 durable status 计算，不相信 worker 自报“前置已完成”；
- **上下文串线**：输入只用 typed reference，artifact/secret 按任务 ACL 解引用；
- **重复 completion**：任务状态与 lease/version 共同检查，旧 worker 不能覆盖新 owner；
- **虚假共识**：同源模型多次赞成不等于独立证据，verifier 读取 artifact 和环境事实；
- **Join 漏项**：固定 expected task set，禁止只对“已返回的那些结果”求和；
- **发布重放**：稳定 effect key 与 receipt 唯一约束，恢复后先查询再重试。

排错顺序是任务图/版本 → owner/lease → scope/input projection → budget ledger → artifact digest → join decision → effect receipt。先读最终聊天会掩盖控制面错误。

## 性能、可靠性与工程化

应同时记录成功率、verified task completion、critical-path latency、token/tool/currency cost、fan-out、queue time、duplicate work、conflict rate、join rejection、context bytes、secret exposure attempts 和 human escalation。只报告总 token 或 wall time无法解释并行是否有效。

并行度上限应由关键路径、provider rate limit、workspace 资源和预算共同决定。可先对任务图做静态上界，再用运行时 semaphore/queue 限制；高风险 effect task 通常串行并设置 approval。任务 artifact 采用 content-addressed store，scheduler 只保存引用和 digest，避免把大输出复制进每个 Agent 的 context。

## 技术边界与设计取舍

Core Lab 是单进程 SQLite，没有真实 lease timeout、分布式共识、消息队列或 worker crash。`BEGIN IMMEDIATE` 足以证明单数据库内的预算原子性，不代表跨数据库全局预算。输入引用只是 namespace 演示，不是操作系统 sandbox 或云 IAM。

更复杂的“自治社会”还会引入声誉、协商、动态拓扑和涌现行为，但复杂度不能替代可证伪目标。生产默认应从最少 Agent、最少权限和最短图开始，只有固定评测显示质量/延迟收益超过协调成本时才增加节点。

## 前沿研究与演进方向

重要问题包括：动态 team formation 如何保持授权链；基于能力/成本/风险的 scheduler 如何避免选择偏差；多个同源基础模型的相关错误如何估计；Agent 间 communication topology 怎样影响信息压缩与错误传播；如何用 causal attribution 判断哪个 worker 真正贡献了改进。

多 Agent benchmark 也必须从“角色表演”转向机制测量：在相同模型调用预算下比较单 Agent 与团队；改变拓扑但保持工具/数据不变；注入恶意 worker、陈旧 artifact、预算竞态和部分失败；用独立环境 verifier 衡量结果，而不是让 supervisor 自评。

### 深度审计与研究证据链

本章框架对照截止 2026-09-11，并引用仓库 SOURCE_LOCK 中的版本。Core Lab 的任务、成本和 artifact 是公开 deterministic fixture；任何 OpenAI、ADK、LangGraph、MAF 或 A2A 的额外能力只在对应 pinned upstream evidence 范围内成立。未执行真实模型团队实验，所以不报告质量提升百分比或 benchmark 排名。

## 本章总结与进阶实践

Multi-Agent 的本质是“带权限和预算的并行状态机”，不是多个 persona。一个可信团队需要 work order、owner、context projection、frontier、atomic reservation、artifact contract、verified join 与 idempotent effect；模型只在这些边界内提供概率性能力。

进阶问题（答案见[附录 K](../appendix-k-part5-solutions.html#ch28)）：

1. 为什么给 Coder 增加 `sources.read` scope 仍不应允许它 claim Researcher 的任务？
2. 多 Agent 在什么条件下必然比单 Agent 更慢？
3. 如何证明 context projection 没有遗漏必要信息又没有泄露其他任务数据？
4. 为什么多数投票不能消除多个同源模型的相关错误？
5. 怎样把本章 L1/L3 调度实验升级为真实模型团队的可复现实验？
