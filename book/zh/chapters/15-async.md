# Async Runtime：流式、并发、中断与取消

> **本章核心判断**：异步 Agent 需要处理长任务、流式响应、并行工具、取消和部分结果；这是一类运行时问题，不是 prompt 技巧。

上一章：Agent Loop：从 while 循环到可治理 Runtime。本章把前一章已经建立的能力进一步推进到 `Streaming`；下一章将进入：Human-in-the-Loop：把不可逆动作放进可恢复审批。

![Async Runtime：流式、并发、中断与取消：系统边界与组件关系](../../assets/diagrams/15-async-architecture.svg)

## 问题背景与学习目标

异步 Agent 需要处理长任务、流式响应、并行工具、取消和部分结果；这是一类运行时问题，不是 prompt 技巧。

在本章的 `Streaming` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“异步 Agent 需要处理长任务、流式响应、并行工具、取消和部分结果；这是一类运行时问题，不是 prompt 技巧。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `losing concurrent work must be cancelled or otherwise accounted for` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 15A` / `Lab 15B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Streaming

**定义。** Streaming 把模型 token、工具进度和 artifact 增量实时传给调用者，降低感知延迟，但不能提前宣告最终成功。

**系统责任。** 系统应区分 provisional event 与 committed event；UI 可以显示进度，状态机只有在 verifier 完成后进入 terminal success。

**失败边界。** 如果下游把流式文本当最终结果，后续失败/回滚会造成状态不一致。

### Cancellation

**定义。** Cancellation 是跨模型调用、工具、subagent 和队列传播的协作式停止协议。它需要 cancellation token/deadline，并定义已经发生的 effect 怎样处理。

**系统责任。** 纯计算可以立即停止；外部写入可能只能停止等待并进入 reconciliation。取消状态本身也应持久化。

**失败边界。** “HTTP client 断开 = 任务取消”在后台任务中通常不成立，也可能留下孤儿 effect。

### Parallel tools

**定义。** Parallel tools 在相互独立的调用上降低 wall‑clock latency，但要求明确 read/write set、资源配额和结果合并策略。

**系统责任。** 只读查询适合 fan‑out；对共享状态写入应序列化、加锁或使用事务/幂等。

**失败边界。** 盲目并行会产生 race、rate limit、重复写和上下文爆炸。

### Backpressure

**定义。** Backpressure 是下游处理能力不足时限制上游生成/并发的机制，包括 queue bound、 semaphore、rate limit 和 adaptive concurrency。

**系统责任。** Agent 平台应同时约束 model requests、 tool calls、 subagent 数量和 event stream， 避免局部快导致全局崩溃。

**失败边界。** 没有背压时，一个高 fan‑out plan 就可能耗尽连接、文件描述符或 provider quota。

## 原理与理论基础

### 系统不变量

> **Invariant**：losing concurrent work must be cancelled or otherwise accounted for

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `取消只停 UI 不停后端` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “取消只停 UI 不停后端”、“fan-out 不限流”、“流式 token 与工具事件混乱” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Streaming** 与 **Cancellation** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“取消只停 UI 不停后端”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Streaming 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Cancellation 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `任务 id 贯穿事件`、`部分结果标注状态` 以及对不变量 **losing concurrent work must be cancelled or otherwise accounted for** 的检查。

**What if。** 一旦“fan-out 不限流”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
L_{e2e}=\max(L_{parallel})+L_{serial}+L_{queue},\qquad Q_{t+1}=Q_t+in-out
$$

Async Agent 的性能问题首先是 critical path、队列和背压问题，而不是“多开几个协程”。

**可证伪假设。** bounded concurrency + backpressure 相比无限并发能降低尾延迟和资源雪崩。

**建议测量。** p50/p95/p99 latency、queue depth、cancel latency、backpressure events。

## 关键机制与执行流程

![Async Runtime：流式、并发、中断与取消：正常路径与故障恢复流程](../../assets/diagrams/15-async-flow.svg)

**Step 1 — 任务 id 贯穿事件。** `任务 id 贯穿事件` 是“Async Runtime：流式、并发、中断与取消”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Streaming` 是否仍满足 **losing concurrent work must be cancelled or otherwise accounted for**。

**Step 2 — 取消信号向工具传播。** `取消信号向工具传播` 是“Async Runtime：流式、并发、中断与取消”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Cancellation` 是否仍满足 **losing concurrent work must be cancelled or otherwise accounted for**。

**Step 3 — 并发受 quota 控制。** `并发受 quota 控制` 是“Async Runtime：流式、并发、中断与取消”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Parallel tools` 是否仍满足 **losing concurrent work must be cancelled or otherwise accounted for**。

**Step 4 — 部分结果标注状态。** `部分结果标注状态` 是“Async Runtime：流式、并发、中断与取消”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Backpressure` 是否仍满足 **losing concurrent work must be cancelled or otherwise accounted for**。

在本章的 `Streaming` 场景中，**最后一步 — 验证。** verifier 针对 `Backpressure` 检查本章不变量 **losing concurrent work must be cancelled or otherwise accounted for**。如果“取消只停 UI 不停后端”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **任务 id 贯穿事件 → 取消信号向工具传播 → 并发受 quota 控制 → 部分结果标注状态** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“取消只停 UI 不停后端”尤其要检查动作前后的证据是否足以闭合不变量 **losing concurrent work must be cancelled or otherwise accounted for**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Streaming` 有关的纯计算状态通常可以重算；一旦 `取消信号向工具传播` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **losing concurrent work must be cancelled or otherwise accounted for**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Async Runtime：流式、并发、中断与取消')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('async', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def async_runtime(fault=False):
 winner,cancelled=asyncio.run(_race(fault))
 clean=all(cancelled) if cancelled else True
 return _ok('async',fault,{'winner':winner,'pending_cancelled':cancelled},'losing concurrent work must be cancelled or otherwise accounted for', clean if not fault else not clean)
```


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| LangGraph | `langgraph==1.2.11 @ 644815f` | 从 StateGraph/CompiledGraph 与 checkpointer 语义入手，观察 node/edge/state/pending writes 如何支持 interrupt、resume 与 fault tolerance。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/langchain-ai/langgraph) |
| Google Agent Development Kit | `v2.1.0 @ 6d15e19` | 比较 LlmAgent 与 Sequential/Parallel/Loop/graph workflow，把 session、sandbox、telemetry/evaluation 放在同一 runtime 视角下。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/google/adk-python) |
| OpenHands Software Agent SDK | `v1.24.0 @ fdc2bdf` | 围绕 Conversation、Agent、Tool、Workspace、Event 与 Agent Server 阅读，理解远程 workspace、interrupt、metrics/resume 的服务边界。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/OpenHands/software-agent-sdk) |

### 源码阅读方法

源码阅读以 **LangGraph** 为第一参照，并只追与“Async Runtime：流式、并发、中断与取消”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“取消只停 UI 不停后端”、如何在“fan-out 不限流”后恢复，以及如何让 `部分结果标注状态` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| LangGraph | 状态/工作流抽象成熟，适合长任务与治理 | 框架状态不能自动解决外部副作用不确定性 | 企业 workflow、HITL、durable orchestration |
| Google Agent Development Kit | 状态/工作流抽象成熟，适合长任务与治理 | 框架状态不能自动解决外部副作用不确定性 | 企业 workflow、HITL、durable orchestration |
| OpenHands Software Agent SDK | 贴近 coding/长期执行 harness，工作区和工具边界更真实 | 依赖更重或迭代快，升级需锁版本做回归 | Coding Agent、Harness 源码学习 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Async Runtime：流式、并发、中断与取消”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Async Runtime：流式、并发、中断与取消”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 15A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch15_async.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::async_runtime`
- `examples/chapters/ch15_async.py::main`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "losing concurrent work must be cancelled or otherwise accounted for", "invariant_holds": true, "observation": {"pending_cancelled": [true], "winner": "fast"}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "async", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 15A](../../../labs/core/lab-15A-async.md)。

### Lab 15B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch15_async.py --fault
```

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L2_ORACLE_ONLY", "evidence_meaning": "external_oracle_observed_bad_outcome_only", "fault": true, "fault_injected": true, "invariant": "losing concurrent work must be cancelled or otherwise accounted for", "invariant_holds": false, "observation": {"pending_cancelled": [false], "winner": "fast"}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "async", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L2_ORACLE_ONLY**：独立 oracle 观察到故障，但被测系统没有证明检测/约束/恢复。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 15B](../../../labs/core/lab-15B-async-fault.md)。

### 观察与证据


## 工程场景与系统设计

本章沿用第 14 章长任务场景，重点分析流式/并发时取消、背压和 restart 对 30 分钟任务的影响；99.9% resume 仍是设计目标而非本仓库实测。


### 上线前必须补齐

- 围绕 **异步 Runtime** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `并发工具和流式输出必须处理取消、孤儿任务和尾部延迟。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **取消只停 UI 不停后端**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **fan-out 不限流**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **流式 token 与工具事件混乱**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `run p95 latency`
- `checkpoint fsync latency`
- `resume success rate`
- `cancellation tail latency`
- `approval wait time`
- `UNKNOWN reconciliation time`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Cancellation` 的生命周期时，要重新验证 **losing concurrent work must be cancelled or otherwise accounted for**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “取消只停 UI 不停后端”、“fan-out 不限流”、“流式 token 与工具事件混乱”：只有正常路径与对应 fault path 都保持 **losing concurrent work must be cancelled or otherwise accounted for**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- checkpoint 只能恢复已持久化状态，不能凭空知道外部副作用是否成功
- sandbox 限制本地执行边界，不自动限制所有网络/云权限
- HITL 提高安全性但增加延迟和运营成本
- 并发提升吞吐但放大竞态、预算和取消复杂度

选择方案时要回到本章边界：如果业务不能接受“取消只停 UI 不停后端”，就必须为 `Streaming` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Cancellation` 决策交给模型，但要用 `部分结果标注状态` 保持结果可验证。**LangGraph** 与 **Google Agent Development Kit** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

异步和流式提高吞吐，却把取消、重复交付和进程崩溃窗口暴露得更明显。收到 cancel 或 transport timeout 不能推导远端 effect 未发生；跨边界写操作仍需 idempotency 或 reconciliation。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[Language Agent Tree Search](https://proceedings.mlr.press/v235/zhou24r.html)**：ICML 2024；把 tree search、环境反馈、反思和值函数组合到 Agent 决策。
- **[LangGraph](https://github.com/langchain-ai/langgraph)**（langgraph==1.2.11 @ 644815f）：状态图、durable execution、checkpointer、HITL、pending writes/fault tolerance。
- **[Google Agent Development Kit](https://github.com/google/adk-python)**（v2.1.0 @ 6d15e19）：Agent、workflow、sandbox、telemetry、evaluation/deployment 参考实现。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- OpenAI: The next evolution of the Agents SDK（2026‑04‑15）：model‑native harness, sandbox, long‑horizon tasks and subagents。
- Anthropic: Patterns and problems in emerging multiagent systems（2026‑08‑13）： multi‑agent interaction risks, institutions, scale and oversight。

**本章吸收的变化。** 异步 Agent 不是“全部并发”。需要依赖图、取消传播和 backpressure；真正收益来自独立步骤并行，而非盲目 fan‑out。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Streaming`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **losing concurrent work must be cancelled or otherwise accounted for** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“取消只停 UI 不停后端”和“fan-out 不限流”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **异步 Runtime** 的可验证性。Long-running agent harness 与 LangGraph/MAF superstep 都暴露了异步任务的调度和持久化成本。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Streaming` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“取消只停 UI 不停后端”与“fan-out 不限流”同时发生时，**LangGraph** 与 **Google Agent Development Kit** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Cancellation` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“流式 token 与工具事件混乱”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：异步 Runtime

本章重新审计后的核心结论是：**并发工具和流式输出必须处理取消、孤儿任务和尾部延迟。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[Semantic Transactions for Tool-Using LLM Agents](https://arxiv.org/abs/2606.17573)**：把不可逆工具副作用抽象成语义事务，支撑 UNKNOWN、staging 与 validation 讨论。
- **[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)**：提供 Agent/Runner/Tools/HITL/Tracing/Sessions 的公开实现边界。
- **[Microsoft Agent Framework Checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)**：把 checkpoint 定义为 workflow resume 所需的 executor state、pending messages/requests 与 shared state。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。LangGraph streaming/interrupt、ADK parallel agent、MAF concurrent workflow 可对照并发控制。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证异步 Runtime 在 normal/fault 两条路径下是否进入可解释状态；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**losing concurrent work must be cancelled or otherwise accounted for**；
2. `Streaming` 必须是可观察软件边界，而不是 prompt 约定；
3. `任务 id 贯穿事件` 与 `部分结果标注状态` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 取消只停 UI 不停后端
- fan-out 不限流
- 流式 token 与工具事件混乱

### 思考题与实践

- **Why：** 为什么 `Streaming` 不能只靠模型“记住”？
- **What if：** 如果在 `任务 id 贯穿事件` 与 `部分结果标注状态` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch15_async.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **Human-in-the-Loop：把不可逆动作放进可恢复审批**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
