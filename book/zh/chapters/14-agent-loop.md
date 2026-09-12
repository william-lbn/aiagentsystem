# Agent Loop：从 while 循环到可治理 Runtime

> **本章核心判断**：最小 Agent loop 很简单，但生产 loop 必须处理停止条件、预算、工具结果、审批、重入和中断。

上一章：MCP：把外部工具与资源接成协议边界。本章把前一章已经建立的能力进一步推进到 `Loop`；下一章将进入：Async Runtime：流式、并发、中断与取消。

![Agent Loop：从 while 循环到可治理 Runtime：系统边界与组件关系](../../assets/diagrams/14-agent-loop-architecture.svg)

## 问题背景与学习目标

最小 Agent loop 很简单，但生产 loop 必须处理停止条件、预算、工具结果、审批、重入和中断。

在本章的 `Loop` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“最小 Agent loop 很简单，但生产 loop 必须处理停止条件、预算、工具结果、审批、重入和中断。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `the loop must have a deterministic stop condition and a finite budget` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 14A` / `Lab 14B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Loop

**定义。** Agent loop 是 observation→decision→action→new observation 的反复执行，不等于简单 while True；每轮必须受 budget、state machine 和 stop policy 约束。

**系统责任。** Runtime 应把每轮变成事件，允许 crash 后恢复、评测每个 step，并在 tool/action 之间插入 policy。

**失败边界。** 无限 loop、重复同一工具和无进展重试是最常见失败，需要 progress detector 和 hard budget。

### Stop condition

**定义。** Stop condition 是从“继续探索”转到 FINISHED/FAILED/NEEDS_INPUT 的可验证规则，可以来自 goal verifier、budget、不可解判断或用户中断。

**系统责任。** 高风险任务应要求外部 objective state，而不是只接受模型 final message。

**失败边界。** 没有 stop condition 会烧 token；过早 stop 则产生看似完整但未闭合的任务。

### Budget

**定义。** Budget 是 Runtime 对 token、model turns、tool calls、wall time、money 和风险动作数量设定的资源上限。

**系统责任。** Budget 可以分层：全任务 hard cap、节点 soft cap、特殊高价值步骤额外额度，并在接近上限时触发 compaction/replan。

**失败边界。** 如果预算只是成本告警而不是执行约束，Agent 在异常 loop 中仍可无限消耗资源。

### Replay

**定义。** Replay 用已有 trajectory/state 重新执行全部或部分决策，用于故障恢复、离线评测和版本回归。

**系统责任。** 对纯计算步骤可以 deterministic replay；对外部 effect 应读取历史 evidence 或使用 sandbox，不能无条件再次调用。

**失败边界。** 把 replay 和 retry 混淆会重复不可逆动作。

## 原理与理论基础

### 系统不变量

> **Invariant**：the loop must have a deterministic stop condition and a finite budget

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `没有停止条件` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “没有停止条件”、“错误结果继续喂给模型”、“模型循环调用同一工具” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Loop** 与 **Stop condition** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“没有停止条件”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Loop 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Stop condition 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `最大步数与 token budget`、`每轮都有 trace id` 以及对不变量 **the loop must have a deterministic stop condition and a finite budget** 的检查。

**What if。** 一旦“错误结果继续喂给模型”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
S_{t+1}=\delta(S_t,O_t,A_t),\qquad Stop\iff Goal\lor Budget\lor Risk\lor NoProgress
$$

成熟 Agent Loop 必须拥有停止语义；仅有 while-loop + tool call 无法约束 runaway、无进展和高风险状态。

**可证伪假设。** 加入 no-progress 与 budget stop rule 会显著降低 p99 tool-call 数，而不会按同比例损害 verified success。

**建议测量。** p99 tool calls、no-progress stops、budget exhaustions、verified success。

## 关键机制与执行流程

![Agent Loop：从 while 循环到可治理 Runtime：正常路径与故障恢复流程](../../assets/diagrams/14-agent-loop-flow.svg)

**Step 1 — 最大步数与 token budget。** `最大步数与 token budget` 是“Agent Loop：从 while 循环到可治理 Runtime”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Loop` 是否仍满足 **the loop must have a deterministic stop condition and a finite budget**。

**Step 2 — 空 action 立即失败。** `空 action 立即失败` 是“Agent Loop：从 while 循环到可治理 Runtime”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Stop condition` 是否仍满足 **the loop must have a deterministic stop condition and a finite budget**。

**Step 3 — 循环状态可 checkpoint。** `循环状态可 checkpoint` 把短暂执行状态转换为后续能够读取的证据。写入内容至少要能关联本次 run、前一状态与下一状态；对 crash-sensitive 数据，应明确写入完成的判据。若进程在写入期间终止，恢复代码必须能够区分“没有记录”“完整记录”和“损坏/不确定记录”，而不能把半写状态视作成功。

**Step 4 — 每轮都有 trace id。** `每轮都有 trace id` 把短暂执行状态转换为后续能够读取的证据。写入内容至少要能关联本次 run、前一状态与下一状态；对 crash-sensitive 数据，应明确写入完成的判据。若进程在写入期间终止，恢复代码必须能够区分“没有记录”“完整记录”和“损坏/不确定记录”，而不能把半写状态视作成功。

在本章的 `Loop` 场景中，**最后一步 — 验证。** verifier 针对 `Replay` 检查本章不变量 **the loop must have a deterministic stop condition and a finite budget**。如果“没有停止条件”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **最大步数与 token budget → 空 action 立即失败 → 循环状态可 checkpoint → 每轮都有 trace id** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“没有停止条件”尤其要检查动作前后的证据是否足以闭合不变量 **the loop must have a deterministic stop condition and a finite budget**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Loop` 有关的纯计算状态通常可以重算；一旦 `空 action 立即失败` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **the loop must have a deterministic stop condition and a finite budget**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Agent Loop：从 while 循环到可治理 Runtime')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('agent-loop', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def agent_loop(fault=False):
 @tool('echo')
 def echo(text:str):return text
 reg=ToolRegistry(); reg.register(echo)
 decisions=[ModelDecision(tool='echo',args={'text':'evidence'}),ModelDecision(final='done')]
 runtime=AgentRuntime(ScriptedModel(decisions),reg)
 if fault: runtime.budget.max_steps=1
 out=runtime.run('run')
 return _ok('agent-loop',fault,{'status':out['status'],'model_calls':out['budget']['model_calls'],'tool_calls':out['budget']['tool_calls']},'the loop must have a deterministic stop condition and a finite budget', out['status']=='FINISHED' if not fault else out['status']=='BUDGET_EXCEEDED')
```


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| OpenAI Agents SDK | `v0.22.0 @ 4df9ecf` | 从 Agent/Runner 入口追踪 tool loop、RunState、session、guardrail 与 tracing；特别对照 v0.22.0 对 replay state 与 failed/incomplete response 的 hardening。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/openai/openai-agents-python) |
| Google Agent Development Kit | `v2.1.0 @ 6d15e19` | 比较 LlmAgent 与 Sequential/Parallel/Loop/graph workflow，把 session、sandbox、telemetry/evaluation 放在同一 runtime 视角下。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/google/adk-python) |
| LangGraph | `langgraph==1.2.11 @ 644815f` | 从 StateGraph/CompiledGraph 与 checkpointer 语义入手，观察 node/edge/state/pending writes 如何支持 interrupt、resume 与 fault tolerance。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/langchain-ai/langgraph) |

### 源码阅读方法

源码阅读以 **OpenAI Agents SDK** 为第一参照，并只追与“Agent Loop：从 while 循环到可治理 Runtime”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“没有停止条件”、如何在“错误结果继续喂给模型”后恢复，以及如何让 `每轮都有 trace id` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| OpenAI Agents SDK | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| Google Agent Development Kit | 状态/工作流抽象成熟，适合长任务与治理 | 框架状态不能自动解决外部副作用不确定性 | 企业 workflow、HITL、durable orchestration |
| LangGraph | 状态/工作流抽象成熟，适合长任务与治理 | 框架状态不能自动解决外部副作用不确定性 | 企业 workflow、HITL、durable orchestration |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Agent Loop：从 while 循环到可治理 Runtime”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Agent Loop：从 while 循环到可治理 Runtime”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 14A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch14_agent_loop.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::agent_loop`
- `examples/chapters/ch14_agent_loop.py::main`
- `src/agentlab/runtime.py::AgentRuntime.run`
- `src/agentlab/tools.py::ToolRegistry.execute`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "the loop must have a deterministic stop condition and a finite budget", "invariant_holds": true, "observation": {"model_calls": 2, "status": "FINISHED", "tool_calls": 1}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "agent-loop", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 14A](../../../labs/core/lab-14A-agent-loop.md)。

### Lab 14B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch14_agent_loop.py --fault
```

**本发布包实际输出：**

```json
{"contained": true, "evidence_level": "L3_CONTAINED", "evidence_meaning": "fault_detected_and_contained", "fault": true, "fault_injected": true, "invariant": "the loop must have a deterministic stop condition and a finite budget", "invariant_holds": true, "observation": {"model_calls": 1, "status": "BUDGET_EXCEEDED", "tool_calls": 1}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "agent-loop", "system_detected": true}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L3_CONTAINED**：被测组件检测并 fail-closed/约束了故障，但不声明已恢复业务结果。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 14B](../../../labs/core/lab-14B-agent-loop-fault.md)。

### 观察与证据


## 工程场景与系统设计

**教学工程设计输入（不是公开云厂商性能数据）：** 长任务 Agent 可能运行 30 分钟并跨越人工审批，进程或节点可以重启。设计输入：RPO=一次已确认状态变化，resume 成功率目标 99.9%，高风险动作审批 TTL 30 分钟。


### 上线前必须补齐

- 围绕 **Agent Loop** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `循环必须有预算、停止条件、状态推进和失败出口。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **没有停止条件**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **错误结果继续喂给模型**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **模型循环调用同一工具**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `run p95 latency`
- `checkpoint fsync latency`
- `resume success rate`
- `cancellation tail latency`
- `approval wait time`
- `UNKNOWN reconciliation time`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Stop condition` 的生命周期时，要重新验证 **the loop must have a deterministic stop condition and a finite budget**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “没有停止条件”、“错误结果继续喂给模型”、“模型循环调用同一工具”：只有正常路径与对应 fault path 都保持 **the loop must have a deterministic stop condition and a finite budget**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- checkpoint 只能恢复已持久化状态，不能凭空知道外部副作用是否成功
- sandbox 限制本地执行边界，不自动限制所有网络/云权限
- HITL 提高安全性但增加延迟和运营成本
- 并发提升吞吐但放大竞态、预算和取消复杂度

选择方案时要回到本章边界：如果业务不能接受“没有停止条件”，就必须为 `Loop` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Stop condition` 决策交给模型，但要用 `每轮都有 trace id` 保持结果可验证。**OpenAI Agents SDK** 与 **Google Agent Development Kit** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

Agent loop 只是控制骨架。没有预算、终止条件、tool outcome 状态和 durable transition 的循环，在异常时会退化为不可解释的 while-loop；可靠性来自状态机约束，而不是多循环几次。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)**：提出 reasoning/action 交错轨迹，连接语言推理与外部环境动作。
- **[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)**（v0.22.0 @ 4df9ecf）：Agent/Runner/Tools/Handoffs/Guardrails/Sessions/HITL/Tracing；0.22.0 包含 runtime hardening。
- **[Google Agent Development Kit](https://github.com/google/adk-python)**（v2.1.0 @ 6d15e19）：Agent、workflow、sandbox、telemetry、evaluation/deployment 参考实现。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- OpenAI: The next evolution of the Agents SDK（2026‑04‑15）：model‑native harness, sandbox, long‑horizon tasks and subagents。
- LongHorizon‑Harness（arXiv 2608.01964; observed 2026‑09‑10）：context, planning, state, long‑running harness。

**本章吸收的变化。** Agent loop 的核心是状态推进与停止条件；无限 while 只是实现形式。 Budget、 no‑progress 和 risk 必须可由 Runtime 强制。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Loop`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **the loop must have a deterministic stop condition and a finite budget** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“没有停止条件”和“错误结果继续喂给模型”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **Agent Loop** 的可验证性。Anthropic managed agents 和 long-running harness 研究显示，loop 外的 initializer/evaluator/progress artifact 与模型一样重要。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Loop` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“没有停止条件”与“错误结果继续喂给模型”同时发生时，**OpenAI Agents SDK** 与 **Google Agent Development Kit** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Stop condition` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“模型循环调用同一工具”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：Agent Loop

本章重新审计后的核心结论是：**循环必须有预算、停止条件、状态推进和失败出口。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[Semantic Transactions for Tool-Using LLM Agents](https://arxiv.org/abs/2606.17573)**：把不可逆工具副作用抽象成语义事务，支撑 UNKNOWN、staging 与 validation 讨论。
- **[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)**：提供 Agent/Runner/Tools/HITL/Tracing/Sessions 的公开实现边界。
- **[Microsoft Agent Framework Checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)**：把 checkpoint 定义为 workflow resume 所需的 executor state、pending messages/requests 与 shared state。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。OpenAI Runner、LangGraph graph executor、AgentLab loop 可以比较 SDK 托管和自研 loop。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证 Agent Loop 在 normal/fault 两条路径下是否进入可解释状态；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**the loop must have a deterministic stop condition and a finite budget**；
2. `Loop` 必须是可观察软件边界，而不是 prompt 约定；
3. `最大步数与 token budget` 与 `每轮都有 trace id` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 没有停止条件
- 错误结果继续喂给模型
- 模型循环调用同一工具

### 思考题与实践

- **Why：** 为什么 `Loop` 不能只靠模型“记住”？
- **What if：** 如果在 `最大步数与 token budget` 与 `每轮都有 trace id` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch14_agent_loop.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **Async Runtime：流式、并发、中断与取消**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
