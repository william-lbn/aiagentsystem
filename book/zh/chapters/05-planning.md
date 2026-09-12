# Planning、Workflow 与 Hybrid Control

> **本章核心判断**：复杂任务既需要模型规划，也需要确定性 workflow 执行；好的系统用 workflow 固化关键边界，用 Agent 处理开放问题。

上一章：Messages、Structured Output 与 ReAct 轨迹。本章把前一章已经建立的能力进一步推进到 `Plan graph`；下一章将进入：Agent State、Trajectory 与可调试性。

![Planning、Workflow 与 Hybrid Control：系统边界与组件关系](../../assets/diagrams/05-planning-architecture.svg)

## 问题背景与学习目标

复杂任务既需要模型规划，也需要确定性 workflow 执行；好的系统用 workflow 固化关键边界，用 Agent 处理开放问题。

在本章的 `Plan graph` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“复杂任务既需要模型规划，也需要确定性 workflow 执行；好的系统用 workflow 固化关键边界，用 Agent 处理开放问题。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `a workflow plan must make dependencies explicit and reject cycles` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 05A` / `Lab 05B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Plan graph

**定义。** Plan graph 把目标分解成具有依赖关系的节点，而不是一串承诺一定执行的自然语言步骤。节点应带前置条件、资源、完成判据和可替代路径。

**系统责任。** 图结构允许并行、局部重规划和显式阻塞；Runtime 可以只解锁前置条件满足的节点，并把 observation 写回图状态。

**失败边界。** 线性计划在工具失败、信息晚到或目标部分不可达时容易整体失效。计划质量应看约束满足和可执行性，不只看语言合理性。

### Deterministic nodes

**定义。** Deterministic node 是输入和规则足够明确、应该由普通软件完成的计划节点，如格式转换、schema check、权限验证、测试和数据库查询。

**系统责任。** 把这些节点固定下来可以缩小模型决策空间，降低成本，并提供稳定 verifier。Agent 只在需要开放判断的边界介入。

**失败边界。** 如果连确定性工作也反复调用模型，会增加随机错误、延迟和不可解释性；反之把开放任务硬编码会导致脆弱 workflow。

### Agentic nodes

**定义。** Agentic node 是状态空间或 action space 开放、无法预先枚举所有步骤的节点，如研究、诊断、代码修复和多源分析。

**系统责任。** 它应有清晰 goal、budget、allowed tools 和 exit criteria，而不是无限循环。执行中产生的新事实可以触发局部 replan。

**失败边界。** 没有 budget/stop criterion 的 Agentic node 容易产生探索发散；没有 verifier 则会把“模型说做完了”当成完成。

### Plan repair

**定义。** Plan repair 是根据真实 observation 修改尚未执行的计划， 而不是掩盖已经发生的 effect。 修复对象可以是节点、依赖、工具选择或目标范围。

**系统责任。** 修复前应分类失败：temporary tool failure、invalid assumption、constraint violation、unsolvable task 或 changed environment。不同原因对应 retry、replace、replan、 refuse。

**失败边界。** 盲目全量重规划会丢失已完成证据并重复副作用。局部 repair 必须读取 durable state。

## 原理与理论基础

### 系统不变量

> **Invariant**：a workflow plan must make dependencies explicit and reject cycles

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `模型无限重规划` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “模型无限重规划”、“workflow 太死无法适配异常”、“计划没有版本导致复盘困难” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Plan graph** 与 **Deterministic nodes** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“模型无限重规划”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Plan graph 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Deterministic nodes 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `把计划表示为 DAG`、`人工审批改变 plan state` 以及对不变量 **a workflow plan must make dependencies explicit and reject cycles** 的检查。

**What if。** 一旦“workflow 太死无法适配异常”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
P=(V,E,C,R),\qquad feasible(P)\iff\forall v\in V:\ constraints(v),resources(v)\ \mathrm{checkable}
$$

计划不只是步骤列表，还包含依赖、约束和资源；真正有价值的 planning 必须能识别不可解任务与失效工具。

**可证伪假设。** 在执行前增加显式 feasibility check，会降低 broken-tool/unsolvable 场景的无效调用，并提升 calibrated refusal。

**建议测量。** plan correctness、unsolvable detection、wasted tool calls、plan repair count。

## 关键机制与执行流程

![Planning、Workflow 与 Hybrid Control：正常路径与故障恢复流程](../../assets/diagrams/05-planning-flow.svg)

**Step 1 — 把计划表示为 DAG。** `把计划表示为 DAG` 是“Planning、Workflow 与 Hybrid Control”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Plan graph` 是否仍满足 **a workflow plan must make dependencies explicit and reject cycles**。

**Step 2 — 节点执行可重试。** 这一阶段可能改变系统或外部环境，因此 `节点执行可重试` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **a workflow plan must make dependencies explicit and reject cycles**。

**Step 3 — 失败节点进入 repair。** `失败节点进入 repair` 是“Planning、Workflow 与 Hybrid Control”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Agentic nodes` 是否仍满足 **a workflow plan must make dependencies explicit and reject cycles**。

**Step 4 — 人工审批改变 plan state。** 这一阶段可能改变系统或外部环境，因此 `人工审批改变 plan state` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **a workflow plan must make dependencies explicit and reject cycles**。

在本章的 `Plan graph` 场景中，**最后一步 — 验证。** verifier 针对 `Plan repair` 检查本章不变量 **a workflow plan must make dependencies explicit and reject cycles**。如果“模型无限重规划”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **把计划表示为 DAG → 节点执行可重试 → 失败节点进入 repair → 人工审批改变 plan state** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“模型无限重规划”尤其要检查动作前后的证据是否足以闭合不变量 **a workflow plan must make dependencies explicit and reject cycles**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Plan graph` 有关的纯计算状态通常可以重算；一旦 `节点执行可重试` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **a workflow plan must make dependencies explicit and reject cycles**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Planning、Workflow 与 Hybrid Control')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('planning', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def planning(fault=False):
 edges={'collect':['diagnose'],'diagnose':['propose'],'propose':['verify'],'verify':[]}
 if fault: edges['verify']=['collect']
 visiting=set(); done=set(); cycle=False
 def dfs(n):
 nonlocal cycle
 if n in visiting: cycle=True; return
 if n in done:return
 visiting.add(n)
 for m in edges[n]: dfs(m)
 visiting.remove(n); done.add(n)
 dfs('collect')
 return _ok('planning',fault,{'cycle':cycle,'nodes':list(edges)},'a workflow plan must make dependencies explicit and reject cycles', (not cycle) if not fault else cycle)
```


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| LangGraph | `langgraph==1.2.11 @ 644815f` | 从 StateGraph/CompiledGraph 与 checkpointer 语义入手，观察 node/edge/state/pending writes 如何支持 interrupt、resume 与 fault tolerance。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/langchain-ai/langgraph) |
| Microsoft Agent Framework | `Python 1.13.0` | 从 Workflow executor/superstep/checkpoint 语义入手，对照 pending messages、requests/responses 与 shared state 的持久化边界。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/microsoft/agent-framework) |
| Google Agent Development Kit | `v2.1.0 @ 6d15e19` | 比较 LlmAgent 与 Sequential/Parallel/Loop/graph workflow，把 session、sandbox、telemetry/evaluation 放在同一 runtime 视角下。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/google/adk-python) |

### 源码阅读方法

源码阅读以 **LangGraph** 为第一参照，并只追与“Planning、Workflow 与 Hybrid Control”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“模型无限重规划”、如何在“workflow 太死无法适配异常”后恢复，以及如何让 `人工审批改变 plan state` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| LangGraph | 状态/工作流抽象成熟，适合长任务与治理 | 框架状态不能自动解决外部副作用不确定性 | 企业 workflow、HITL、durable orchestration |
| Microsoft Agent Framework | 状态/工作流抽象成熟，适合长任务与治理 | 框架状态不能自动解决外部副作用不确定性 | 企业 workflow、HITL、durable orchestration |
| Google Agent Development Kit | 状态/工作流抽象成熟，适合长任务与治理 | 框架状态不能自动解决外部副作用不确定性 | 企业 workflow、HITL、durable orchestration |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Planning、Workflow 与 Hybrid Control”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Planning、Workflow 与 Hybrid Control”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 05A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch05_planning.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::planning`
- `examples/chapters/ch05_planning.py::main`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "a workflow plan must make dependencies explicit and reject cycles", "invariant_holds": true, "observation": {"cycle": false, "nodes": ["collect", "diagnose", "propose", "verify"]}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "planning", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 05A](../../../labs/core/lab-05A-planning.md)。

### Lab 05B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch05_planning.py --fault
```

**本发布包实际输出：**

```json
{"contained": true, "evidence_level": "L3_CONTAINED", "evidence_meaning": "fault_detected_and_contained", "fault": true, "fault_injected": true, "invariant": "a workflow plan must make dependencies explicit and reject cycles", "invariant_holds": true, "observation": {"cycle": true, "nodes": ["collect", "diagnose", "propose", "verify"]}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "planning", "system_detected": true}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L3_CONTAINED**：被测组件检测并 fail-closed/约束了故障，但不声明已恢复业务结果。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 05B](../../../labs/core/lab-05B-planning-fault.md)。

### 观察与证据


## 工程场景与系统设计

本章沿用第 1 章“研发助手”教学负载，重点约束 planner 在最多 12 回合内终止，并把写动作审批视为硬边界而不是规划建议。


### 上线前必须补齐

- 围绕 **规划与混合控制** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `计划必须显式依赖、可检查环路，并允许 Runtime 拒绝危险路径。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **模型无限重规划**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **workflow 太死无法适配异常**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **计划没有版本导致复盘困难**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `task success rate`
- `structured-decision parse failure`
- `context tokens / turn`
- `model turns / task`
- `trajectory completeness`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Deterministic nodes` 的生命周期时，要重新验证 **a workflow plan must make dependencies explicit and reject cycles**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “模型无限重规划”、“workflow 太死无法适配异常”、“计划没有版本导致复盘困难”：只有正常路径与对应 fault path 都保持 **a workflow plan must make dependencies explicit and reject cycles**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- 模型输出仍然是概率性决策，不能提供传统事务语义
- 没有外部 verifier 时，最终答案不能等同于客观成功
- 上下文窗口不是无限数据库，历史必须被选择与压缩
- 模型能力升级会改变最佳 harness 假设，因此边界要可替换

选择方案时要回到本章边界：如果业务不能接受“模型无限重规划”，就必须为 `Plan graph` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Deterministic nodes` 决策交给模型，但要用 `人工审批改变 plan state` 保持结果可验证。**LangGraph** 与 **Microsoft Agent Framework** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

Planner 可以优化动作顺序，却不能替代权限检查、幂等性和运行时恢复。开放式规划如果缺少动作白名单、预算、终止条件和 verifier，计划越复杂，累积错误与副作用风险越高。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://proceedings.neurips.cc/paper_files/paper/2023/hash/271db9922b8d1f4dd7aaef84ed5ac703-Abstract-Conference.html)**：把单路径推理扩展为可搜索的 thought tree，支持 lookahead/backtracking。
- **[Language Agent Tree Search](https://proceedings.mlr.press/v235/zhou24r.html)**：ICML 2024；把 tree search、环境反馈、反思和值函数组合到 Agent 决策。
- **[LangGraph](https://github.com/langchain-ai/langgraph)**（langgraph==1.2.11 @ 644815f）：状态图、durable execution、checkpointer、HITL、pending writes/fault tolerance。
- **[Microsoft Agent Framework](https://github.com/microsoft/agent-framework)**（Python 1.13.0）：Agents、Workflows、Memory、Tools、Skills、Security、Hosting、Observability。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- Agent Planning Benchmark (APB)（arXiv 2606.04874; 2026‑06‑03）：planning diagnostics, tool noise, broken tools, unsolvable tasks。

**本章吸收的变化。** 可执行 plan 不是自然语言清单，而是带依赖、约束与完成条件的图。APB 类研究提示规划错误应与执行错误分离诊断。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Plan graph`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **a workflow plan must make dependencies explicit and reject cycles** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“模型无限重规划”和“workflow 太死无法适配异常”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **规划与混合控制** 的可验证性。Tree of Thoughts、LATS 与 Reflexion 都强化了搜索/反馈，但它们不自动解决生产中的权限和副作用问题。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Plan graph` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“模型无限重规划”与“workflow 太死无法适配异常”同时发生时，**LangGraph** 与 **Microsoft Agent Framework** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Deterministic nodes` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“计划没有版本导致复盘困难”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：规划与混合控制

本章重新审计后的核心结论是：**计划必须显式依赖、可检查环路，并允许 Runtime 拒绝危险路径。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[ReAct](https://arxiv.org/abs/2210.03629)**：reasoning/action 交错轨迹让模型决策可被放进 trajectory，而不是隐藏在最终回答里。
- **[Toolformer](https://arxiv.org/abs/2302.04761)**：说明模型可学习工具调用，但工程系统仍要在模型外做 schema 与权限验证。
- **[Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)**：强调先从简单可组合的 workflow/agent 模式出发。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。LangGraph 的 graph state、ADK Sequential/Parallel/Loop Agents、MAF workflow 可作为三类工程化规划实现。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证规划与混合控制的输入、消息和状态是否能被显式记录；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**a workflow plan must make dependencies explicit and reject cycles**；
2. `Plan graph` 必须是可观察软件边界，而不是 prompt 约定；
3. `把计划表示为 DAG` 与 `人工审批改变 plan state` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 模型无限重规划
- workflow 太死无法适配异常
- 计划没有版本导致复盘困难

### 思考题与实践

- **Why：** 为什么 `Plan graph` 不能只靠模型“记住”？
- **What if：** 如果在 `把计划表示为 DAG` 与 `人工审批改变 plan state` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch05_planning.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **Agent State、Trajectory 与可调试性**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
