# Agent State、Trajectory 与可调试性

> **本章核心判断**：没有显式状态，就没有可靠调试；状态不是聊天历史，而是任务、资源、证据、预算和风险的统一视图。

上一章：Planning、Workflow 与 Hybrid Control。本章把前一章已经建立的能力进一步推进到 `Run state`；下一章将进入：Tool Design：让模型拥有可用而可控的双手。

![Agent State、Trajectory 与可调试性：系统边界与组件关系](../../assets/diagrams/06-state-architecture.svg)

## 问题背景与学习目标

没有显式状态，就没有可靠调试；状态不是聊天历史，而是任务、资源、证据、预算和风险的统一视图。

在本章的 `Run state` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“没有显式状态，就没有可靠调试；状态不是聊天历史，而是任务、资源、证据、预算和风险的统一视图。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `state transitions must be explicit, monotonic where terminal, and auditable` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 06A` / `Lab 06B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Run state

**定义。** Run state 是一次 Agent 任务的权威执行状态，至少包含目标、当前阶段、已完成节点、 pending actions、budget、approval 和 effect/evidence 引用。

**系统责任。** 它应由 Runtime 持久化并版本化，模型只能读取或提出更新，不能靠对话历史隐式维持。状态迁移最好有显式枚举和合法边。

**失败边界。** 如果 state 只存在 prompt 中，进程重启、compaction 或并发请求都会破坏一致性。

### Checkpoint

**定义。** Checkpoint 是在某个可恢复边界保存的状态一致性切面，使新进程可以从那里继续，而不需要重放全部历史。

**系统责任。** 高质量 checkpoint 要么原子写入，要么带版本/校验使半写可检测；同时记录与外部 effect 的关系，避免恢复后重复执行。

**失败边界。** Checkpoint 频率太低会扩大重算/RPO，太高会增加 I/O 和序列化成本；应由任务价值和恢复窗口决定。

### Session tree

**定义。** Session tree 表示主任务、分支、subagent 和重试之间的父子关系。它比平铺 message history 更能表达并行与回滚语义。

**系统责任。** 每个 branch 应有独立 context/state，同时共享明确的 immutable input 或 blackboard；merge 时需要冲突规则。

**失败边界。** 如果所有 subagent 共写同一会话，会发生上下文污染、覆盖状态和难以归责的 tool call。

### Time travel

**定义。** Time travel 是从历史 checkpoint 派生新的执行分支，用于调试、评测或尝试不同策略； 它不是把外部世界真正回滚到过去。

**系统责任。** Runtime 必须区分 replayable internal state 与已经发生的 external effect。调试分支应默认禁止真实写操作或使用 sandbox/shadow environment。

**失败边界。** 如果把“回到旧 checkpoint”误当成外部事务回滚，可能重复邮件、支付或部署。

## 原理与理论基础

### 系统不变量

> **Invariant**：state transitions must be explicit, monotonic where terminal, and auditable

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `状态只在内存中` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “状态只在内存中”、“checkpoint 写一半损坏”、“分支会话互相污染” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Run state** 与 **Checkpoint** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“状态只在内存中”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Run state 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Checkpoint 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `状态对象显式建模`、`断点观察 state diff` 以及对不变量 **state transitions must be explicit, monotonic where terminal, and auditable** 的检查。

**What if。** 一旦“checkpoint 写一半损坏”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
\hat S_k=Checkpoint(E_{\le k}),\qquad S_n=Fold(\hat S_k,E_{k+1:n})
$$

长时 Agent 的状态不能等同于上下文窗口。Checkpoint 提供一致恢复切面，event/trajectory 提供之后的确定性重建依据。

**可证伪假设。** 在相同故障注入下，外部化 state + checkpoint 的系统比 chat-only resume 更接近无故障执行结果。

**建议测量。** resume equivalence、replayed steps、lost-state rate、checkpoint recovery latency。

## 关键机制与执行流程

![Agent State、Trajectory 与可调试性：正常路径与故障恢复流程](../../assets/diagrams/06-state-flow.svg)

**Step 1 — 状态对象显式建模。** `状态对象显式建模` 是“Agent State、Trajectory 与可调试性”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Run state` 是否仍满足 **state transitions must be explicit, monotonic where terminal, and auditable**。

**Step 2 — 关键转换写 checkpoint。** 这一阶段可能改变系统或外部环境，因此 `关键转换写 checkpoint` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **state transitions must be explicit, monotonic where terminal, and auditable**。

**Step 3 — 每个 artifact 有引用。** `每个 artifact 有引用` 是“Agent State、Trajectory 与可调试性”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Session tree` 是否仍满足 **state transitions must be explicit, monotonic where terminal, and auditable**。

**Step 4 — 断点观察 state diff。** `断点观察 state diff` 负责形成后续决策的输入。需要同时保存来源、版本/时间与必要的关联标识，避免把“当前看到的数据”误当成永远有效的事实。进入下一阶段前，对结构、权限和来源做最小验证，使 `Time travel` 的状态能够在 trace 中被复现。

在本章的 `Run state` 场景中，**最后一步 — 验证。** verifier 针对 `Time travel` 检查本章不变量 **state transitions must be explicit, monotonic where terminal, and auditable**。如果“状态只在内存中”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **状态对象显式建模 → 关键转换写 checkpoint → 每个 artifact 有引用 → 断点观察 state diff** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“状态只在内存中”尤其要检查动作前后的证据是否足以闭合不变量 **state transitions must be explicit, monotonic where terminal, and auditable**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Run state` 有关的纯计算状态通常可以重算；一旦 `关键转换写 checkpoint` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **state transitions must be explicit, monotonic where terminal, and auditable**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Agent State、Trajectory 与可调试性')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('state', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def state(fault=False):
 allowed={'RECEIVED':{'RUNNING'},'RUNNING':{'WAITING_TOOL','FINISHED','FAILED'},'WAITING_TOOL':{'RUNNING','FAILED'},'FINISHED':set(),'FAILED':set()}
 path=['RECEIVED','RUNNING','WAITING_TOOL','RUNNING','FINISHED'] if not fault else ['RECEIVED','FINISHED']
 valid=all(b in allowed.get(a,set()) for a,b in zip(path,path[1:]))
 return _ok('state',fault,{'path':path,'valid':valid},'state transitions must be explicit, monotonic where terminal, and auditable', valid if not fault else not valid)
```


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| LangGraph | `langgraph==1.2.11 @ 644815f` | 从 StateGraph/CompiledGraph 与 checkpointer 语义入手，观察 node/edge/state/pending writes 如何支持 interrupt、resume 与 fault tolerance。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/langchain-ai/langgraph) |
| Microsoft Agent Framework checkpoints | `docs observed 2026-09-09` | checkpoint 捕获 executor states、pending messages/requests、shared state，用于 resume。 | 以官方 docs/release/source tree 为准 | [官方来源](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints) |
| Pi Coding Agent | `@earendil-works/pi-coding-agent 0.85.1` | 把 session tree、branching、compaction、extensions/skills 看成极简 coding harness 的核心；同时注意 2026 年包名迁移到 @earendil-works。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/earendil-works/pi) |

### 源码阅读方法

源码阅读以 **LangGraph** 为第一参照，并只追与“Agent State、Trajectory 与可调试性”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“状态只在内存中”、如何在“checkpoint 写一半损坏”后恢复，以及如何让 `断点观察 state diff` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| LangGraph | 状态/工作流抽象成熟，适合长任务与治理 | 框架状态不能自动解决外部副作用不确定性 | 企业 workflow、HITL、durable orchestration |
| Microsoft Agent Framework checkpoints | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| Pi Coding Agent | 贴近 coding/长期执行 harness，工作区和工具边界更真实 | 依赖更重或迭代快，升级需锁版本做回归 | Coding Agent、Harness 源码学习 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Agent State、Trajectory 与可调试性”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Agent State、Trajectory 与可调试性”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 06A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch06_state.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::state`
- `examples/chapters/ch06_state.py::main`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "state transitions must be explicit, monotonic where terminal, and auditable", "invariant_holds": true, "observation": {"path": ["RECEIVED", "RUNNING", "WAITING_TOOL", "RUNNING", "FINISHED"], "valid": true}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "state", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 06A](../../../labs/core/lab-06A-state.md)。

### Lab 06B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch06_state.py --fault
```

**本发布包实际输出：**

```json
{"contained": true, "evidence_level": "L3_CONTAINED", "evidence_meaning": "fault_detected_and_contained", "fault": true, "fault_injected": true, "invariant": "state transitions must be explicit, monotonic where terminal, and auditable", "invariant_holds": true, "observation": {"path": ["RECEIVED", "FINISHED"], "valid": false}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "state", "system_detected": true}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L3_CONTAINED**：被测组件检测并 fail-closed/约束了故障，但不声明已恢复业务结果。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 06B](../../../labs/core/lab-06B-state-fault.md)。

### 观察与证据


## 工程场景与系统设计

本章沿用第 1 章“研发助手”教学负载，重点验证会话状态、trajectory 和并发 run 隔离；这些数字仍是工程设计输入，不是 benchmark 实测。


### 上线前必须补齐

- 围绕 **状态、轨迹与调试** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `Agent 状态必须显式转移，terminal state 不应被自然语言覆盖。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **状态只在内存中**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **checkpoint 写一半损坏**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **分支会话互相污染**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `task success rate`
- `structured-decision parse failure`
- `context tokens / turn`
- `model turns / task`
- `trajectory completeness`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Checkpoint` 的生命周期时，要重新验证 **state transitions must be explicit, monotonic where terminal, and auditable**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “状态只在内存中”、“checkpoint 写一半损坏”、“分支会话互相污染”：只有正常路径与对应 fault path 都保持 **state transitions must be explicit, monotonic where terminal, and auditable**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- 模型输出仍然是概率性决策，不能提供传统事务语义
- 没有外部 verifier 时，最终答案不能等同于客观成功
- 上下文窗口不是无限数据库，历史必须被选择与压缩
- 模型能力升级会改变最佳 harness 假设，因此边界要可替换

选择方案时要回到本章边界：如果业务不能接受“状态只在内存中”，就必须为 `Run state` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Checkpoint` 决策交给模型，但要用 `断点观察 state diff` 保持结果可验证。**LangGraph** 与 **Microsoft Agent Framework checkpoints** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

Agent state 是执行视图，不应被误认为外部世界的权威状态。对远端资源、支付、部署等副作用，恢复时必须重新 observation/reconcile；仅恢复本地 checkpoint 不能证明外部动作未发生或只发生一次。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)**：提出 reasoning/action 交错轨迹，连接语言推理与外部环境动作。
- **[LangGraph](https://github.com/langchain-ai/langgraph)**（langgraph==1.2.11 @ 644815f）：状态图、durable execution、checkpointer、HITL、pending writes/fault tolerance。
- **[Microsoft Agent Framework checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)**（docs observed 2026-09-09）：checkpoint 捕获 executor states、pending messages/requests、shared state，用于 resume。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- LongHorizon‑Harness（arXiv 2608.01964; observed 2026‑09‑10）：context, planning, state, long‑running harness。
- Agent Memory: Characterization and System Implications of Stateful Long‑Horizon Workloads（arXiv 2606.06448; 2026‑06‑04）：memory system cost, write/read path, freshness‑latency tradeoffs。

**本章吸收的变化。** 可恢复状态应由 checkpoint 与其后的事件共同重建；session/trajectory 不能只存在于模型上下文。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、 更长时或更高风险的环境中检验。

### Research Gap

围绕 `Run state`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **state transitions must be explicit, monotonic where terminal, and auditable** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“状态只在内存中”和“checkpoint 写一半损坏”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **状态、轨迹与调试** 的可验证性。AgentBench 与长程 Agent 研究共同表明：最终答案不足以解释任务行为，trajectory 是一等证据。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Run state` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“状态只在内存中”与“checkpoint 写一半损坏”同时发生时，**LangGraph** 与 **Microsoft Agent Framework checkpoints** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Checkpoint` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“分支会话互相污染”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：状态、轨迹与调试

本章重新审计后的核心结论是：**Agent 状态必须显式转移，terminal state 不应被自然语言覆盖。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[ReAct](https://arxiv.org/abs/2210.03629)**：reasoning/action 交错轨迹让模型决策可被放进 trajectory，而不是隐藏在最终回答里。
- **[Toolformer](https://arxiv.org/abs/2302.04761)**：说明模型可学习工具调用，但工程系统仍要在模型外做 schema 与权限验证。
- **[Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)**：强调先从简单可组合的 workflow/agent 模式出发。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。LangGraph checkpoint、OpenAI RunState 和 MAF checkpoint 都可对照状态持久化边界。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证状态、轨迹与调试的输入、消息和状态是否能被显式记录；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**state transitions must be explicit, monotonic where terminal, and auditable**；
2. `Run state` 必须是可观察软件边界，而不是 prompt 约定；
3. `状态对象显式建模` 与 `断点观察 state diff` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 状态只在内存中
- checkpoint 写一半损坏
- 分支会话互相污染

### 思考题与实践

- **Why：** 为什么 `Run state` 不能只靠模型“记住”？
- **What if：** 如果在 `状态对象显式建模` 与 `断点观察 state diff` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch06_state.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **Tool Design：让模型拥有可用而可控的双手**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
