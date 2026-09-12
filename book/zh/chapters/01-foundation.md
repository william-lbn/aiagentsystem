# AI Agent Systems：从模型调用到可运行系统

> **本章核心判断**：从“模型回复”走向“系统运行”的第一步，是把 Agent 视为模型、上下文、工具、状态、证据和治理共同组成的运行系统。

全书起点：本章从 `Agent vs Workflow` 建立 Agent 系统的基本边界，并把模型、上下文、工具、状态、证据与治理放入同一运行视角；下一章将进入：模型基座：Token、结构化生成、工具调用与推理接口。

![AI Agent Systems：从模型调用到可运行系统：系统边界与组件关系](../../assets/diagrams/01-foundation-architecture.svg)

## 问题背景与学习目标

从“模型回复”走向“系统运行”的第一步，是把 Agent 视为模型、上下文、工具、状态、证据和治理共同组成的运行系统。

在本章的 `Agent vs Workflow` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“从“模型回复”走向“系统运行”的第一步，是把 Agent 视为模型、上下文、工具、状态、证据和治理共同组成的运行系统。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `model decision is not a side effect; runtime owns execution evidence` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 01A` / `Lab 01B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Agent vs Workflow

**定义。** Agent 是在运行时根据 observation 选择下一步动作的决策主体；Workflow 则把允许的状态转移预先编码在图或状态机中。两者不是强弱关系，而是“决策自由度由模型拥有多少”的区别。

**系统责任。** 在生产系统里通常采用 Hybrid Control：开放性高的节点交给 Agent，合规、支付、 发布、删除等节点交给确定性 workflow。边界应能在 trace 中看到，而不是只写在 prompt 里。

**失败边界。** 如果把所有流程都交给 Agent，会把业务不变量变成概率事件；如果把所有节点都固定，又失去开放任务适应性。可观测量应包括 agentic‑node 比例、人工接管率和 plan repair 次数。

### Context/Tool/Runtime

**定义。** Context 是模型当前可见的信息集合，Tool 是模型可请求的能力描述，Runtime 是真正执行、持久化、限权和验证这些请求的软件层。模型只能“提出调用”，不能直接拥有外部世界事实。

**系统责任。** Context 决定模型知道什么，Tool schema 决定模型能提出什么，Runtime policy 决定系统最终允许什么。三者分层后，模型升级不会自动改变权限边界。

**失败边界。** 最常见的架构错误是把 API key、 重试、 超时和成功判定藏在 Tool wrapper 或 prompt 中。运行时必须记录 intent、actual call、observation 和 terminal status。

### Trajectory evidence

**定义。** Trajectory 是一次 run 中按因果顺序排列的决策、工具调用、observation、状态变化和验证事件；evidence 是其中足以证明某个状态转移成立的可复核材料。

**系统责任。** 一个高质量 trajectory 既服务调试，也服务 evaluation、incident review 和 replay。 关键不是“日志很多”，而是每个 effect 都能关联 run_id、step_id、输入摘要和外部 observation。

**失败边界。** 只保存最终 answer 会丢失因果链；只保存 chain‑of‑thought 也不能证明真实外部状态。应优先保存结构化事件和可重建证据，而不是依赖模型自述。

### Harness boundary

**定义。** Harness 是模型与真实计算环境之间的系统外壳：它组合 tool、workspace、sandbox、 context compaction、subagent、approval 和 verifier，并定义哪些责任不能交给模型。

**系统责任。** 好的 harness 会把概率性推理限制在候选决策，把文件写入、命令执行、网络、权限和恢复交给确定性组件。不同模型可以替换，但 harness 的状态语义和审计接口保持稳定。

**失败边界。** 如果 harness 只是一个 while‑loop 加几个工具函数，长时任务会在 context 膨胀、 并发、取消、崩溃恢复和权限方面迅速失控。

## 原理与理论基础

### 系统不变量

> **Invariant**：model decision is not a side effect; runtime owns execution evidence

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `误把 tool_call 当作任务成功` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。

在本章的 `Agent vs Workflow` 场景中，可以把一次 Agent 操作抽象为状态转移：`S_t --decision--> I_t --policy--> E_t --observation--> S_(t+1)`。其中 `I_t` 是意图（intent），`E_t` 是实际执行或环境变化。模型可以影响 `decision`，但 `policy`、持久化点与 success verifier 必须位于模型之外。这样才能区分“模型认为成功”和“系统已经证明成功”。

### 故障模型

本章优先把 “误把 tool_call 当作任务成功”、“只保存最终回答，无法复盘”、“把生产权限直接放入 prompt” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Agent vs Workflow** 与 **Context/Tool/Runtime** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“误把 tool_call 当作任务成功”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Agent vs Workflow 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Context/Tool/Runtime 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `构造 messages`、`记录 trace` 以及对不变量 **model decision is not a side effect; runtime owns execution evidence** 的检查。

**What if。** 一旦“只保存最终回答，无法复盘”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
S_{t+1}=F(S_t,O_t,D_t,A_t,E_t,G_t)
$$

把模型 decision、Runtime action、外部 effect、evidence 与 governance 分开，是整本书的总系统模型。模型可以提出 $D_t$，但只有 policy 允许的 $A_t$ 才能执行；$E_t$ 必须通过 observation 回到可恢复状态。

**可证伪假设。** 若把 `tool_call` 直接当成 success，则在 timeout/partial execution 场景中，false-finish rate 会显著高于由外部 verifier 判定 success 的系统。

**建议测量。** false-finish rate、unknown-outcome rate、verified success rate、human intervention rate。

## 关键机制与执行流程

![AI Agent Systems：从模型调用到可运行系统：正常路径与故障恢复流程](../../assets/diagrams/01-foundation-flow.svg)

**Step 1 — 构造 messages。** `构造 messages` 负责形成后续决策的输入。需要同时保存来源、版本/时间与必要的关联标识，避免把“当前看到的数据”误当成永远有效的事实。进入下一阶段前，对结构、权限和来源做最小验证，使 `Agent vs Workflow` 的状态能够在 trace 中被复现。

**Step 2 — 执行工具调用。** 这一阶段可能改变系统或外部环境，因此 `执行工具调用` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **model decision is not a side effect; runtime owns execution evidence**。

**Step 3 — 写入 checkpoint。** 这一阶段可能改变系统或外部环境，因此 `写入 checkpoint` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **model decision is not a side effect; runtime owns execution evidence**。

**Step 4 — 记录 trace。** `记录 trace` 把短暂执行状态转换为后续能够读取的证据。写入内容至少要能关联本次 run、前一状态与下一状态；对 crash-sensitive 数据，应明确写入完成的判据。若进程在写入期间终止，恢复代码必须能够区分“没有记录”“完整记录”和“损坏/不确定记录”，而不能把半写状态视作成功。

在本章的 `Agent vs Workflow` 场景中，**最后一步 — 验证。** verifier 针对 `Harness boundary` 检查本章不变量 **model decision is not a side effect; runtime owns execution evidence**。如果“误把 tool_call 当作任务成功”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **构造 messages → 执行工具调用 → 写入 checkpoint → 记录 trace** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“误把 tool_call 当作任务成功”尤其要检查动作前后的证据是否足以闭合不变量 **model decision is not a side effect; runtime owns execution evidence**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Agent vs Workflow` 有关的纯计算状态通常可以重算；一旦 `执行工具调用` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **model decision is not a side effect; runtime owns execution evidence**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='AI Agent Systems：从模型调用到可运行系统')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('foundation', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def foundation(fault=False):
    @tool("Add two integers")
    def add(a: int, b: int) -> int:
        return a + b

    reg = ToolRegistry(); reg.register(add)
    decisions = [ModelDecision(tool="add", args={"a": 7, "b": 5}), ModelDecision(final="12")]
    if fault:
        decisions = [ModelDecision(tool="missing", args={}), ModelDecision(final="unreachable")]

    out = AgentRuntime(ScriptedModel(decisions), reg).run("7+5?")
    condition = (out["status"] == "FINISHED" and out["answer"] == "12") if not fault \
        else (out["status"] == "TOOL_NOT_APPLIED" and out["answer"] is None)
    return _ok("foundation", fault,
               {"status": out["status"], "answer": out["answer"]},
               "model decision is not a side effect; runtime owns execution evidence",
               condition)
```


这里故意把 unknown tool 设为 `NOT_APPLIED`，Runtime 随即进入终止态 `TOOL_NOT_APPLIED`。这条路径的验收条件不是“某条 tool message 里出现 NOT_APPLIED”，而是**系统级状态不能继续走到 FINISHED**；因此第二个 scripted `final="unreachable"` 永远不应被消费。这一修改封闭了旧版 Lab 01B 的 false-positive。


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| bojieli/ai-agent-book | `main; 10 chapters / 109 experiments observed 2026-09-09` | 对标开源教材：正文、实验 ledger、PDF/EPUB、多语言。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/bojieli/ai-agent-book) |
| OpenAI Agents SDK | `v0.22.0 @ 4df9ecf` | 从 Agent/Runner 入口追踪 tool loop、RunState、session、guardrail 与 tracing；特别对照 v0.22.0 对 replay state 与 failed/incomplete response 的 hardening。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/openai/openai-agents-python) |
| Anthropic: Building Effective Agents | `official engineering article` | 从简单、可组合的 workflow/agent 模式开始。 | 以官方 docs/release/source tree 为准 | [官方来源](https://www.anthropic.com/engineering/building-effective-agents) |

### 源码阅读方法

源码阅读以 **bojieli/ai-agent-book** 为第一参照，并只追与“AI Agent Systems：从模型调用到可运行系统”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“误把 tool_call 当作任务成功”、如何在“只保存最终回答，无法复盘”后恢复，以及如何让 `记录 trace` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| bojieli/ai-agent-book | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| OpenAI Agents SDK | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| Anthropic: Building Effective Agents | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“AI Agent Systems：从模型调用到可运行系统”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“AI Agent Systems：从模型调用到可运行系统”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 01A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch01_foundation.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::foundation`
- `examples/chapters/ch01_foundation.py::main`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "model decision is not a side effect; runtime owns execution evidence", "invariant_holds": true, "observation": {"answer": "12", "status": "FINISHED", "steps": 1}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "foundation", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 01A](../../../labs/core/lab-01A-foundation.md)。

### Lab 01B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch01_foundation.py --fault
```

**本发布包实际输出：**

```json
{"contained": true, "evidence_level": "L3_CONTAINED", "evidence_meaning": "fault_detected_and_contained", "fault": true, "fault_injected": true, "invariant": "model decision is not a side effect; runtime owns execution evidence", "invariant_holds": true, "observation": {"answer": null, "status": "TOOL_NOT_APPLIED", "steps": 1}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "foundation", "system_detected": true}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L3_CONTAINED**：被测组件检测并 fail-closed/约束了故障，但不声明已恢复业务结果。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 01B](../../../labs/core/lab-01B-foundation-fault.md)。

### 观察与证据


## 工程场景与系统设计

**教学工程设计输入（不是公开云厂商性能数据）：** 研发助手需要读取 issue、检索 runbook、调用只读工具并给出修复建议；写操作必须进入审批。设计输入：50 并发会话、单任务最多 12 个模型回合、只读工具 p95 500 ms。


### 上线前必须补齐

- 围绕 **Agent 系统边界** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `模型回复不是系统完成；tool_call 只是候选动作，证据与状态由 Runtime 负责。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **误把 tool_call 当作任务成功**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **只保存最终回答，无法复盘**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **把生产权限直接放入 prompt**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `task success rate`
- `structured-decision parse failure`
- `context tokens / turn`
- `model turns / task`
- `trajectory completeness`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Context/Tool/Runtime` 的生命周期时，要重新验证 **model decision is not a side effect; runtime owns execution evidence**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “误把 tool_call 当作任务成功”、“只保存最终回答，无法复盘”、“把生产权限直接放入 prompt”：只有正常路径与对应 fault path 都保持 **model decision is not a side effect; runtime owns execution evidence**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- 模型输出仍然是概率性决策，不能提供传统事务语义
- 没有外部 verifier 时，最终答案不能等同于客观成功
- 上下文窗口不是无限数据库，历史必须被选择与压缩
- 模型能力升级会改变最佳 harness 假设，因此边界要可替换

选择方案时要回到本章边界：如果业务不能接受“误把 tool_call 当作任务成功”，就必须为 `Agent vs Workflow` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Context/Tool/Runtime` 决策交给模型，但要用 `记录 trace` 保持结果可验证。**bojieli/ai-agent-book** 与 **OpenAI Agents SDK** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

本章只建立 Agent 系统的最小边界：模型输出不等于已发生的外部事实，tool result 也不等于跨系统事务提交。若系统无法观测真实副作用、无法识别调用主体或无法给高风险动作建立审批边界，就应降低自动化权限，而不是继续扩大 Agent 自主性。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)**：提出 reasoning/action 交错轨迹，连接语言推理与外部环境动作。
- **[Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)**：探索模型学习何时调用外部工具以及如何把工具结果纳入后续预测。
- **[bojieli/ai-agent-book](https://github.com/bojieli/ai-agent-book)**（main; 10 chapters / 109 experiments observed 2026-09-09）：对标开源教材：正文、实验 ledger、PDF/EPUB、多语言。
- **[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)**（v0.22.0 @ 4df9ecf）：Agent/Runner/Tools/Handoffs/Guardrails/Sessions/HITL/Tracing；0.22.0 包含 runtime hardening。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- OpenAI: The next evolution of the Agents SDK（2026‑04‑15）：model‑native harness, sandbox, long‑horizon tasks and subagents。
- NIST AI 800‑5: Security Considerations for AI Agents（published 2026‑05‑18）：agent security threats, mitigations, assessment and adoption barriers。

**本章吸收的变化。** 把模型 decision、Runtime action、外部 effect、evidence 与 governance 分开，是整本书的总系统模型。模型可以提出 Dt，但只有 policy 允许的 At 才能执行；Et 必须通过 observation 回到可恢复状态。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Agent vs Workflow`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **model decision is not a side effect; runtime owns execution evidence** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“误把 tool_call 当作任务成功”和“只保存最终回答，无法复盘”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **Agent 系统边界** 的可验证性。ReAct 与 Anthropic Building Effective Agents 都提醒我们：Agent 的关键不在“更像人思考”，而在把 reasoning/action 轨迹外化为可审计过程。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Agent vs Workflow` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“误把 tool_call 当作任务成功”与“只保存最终回答，无法复盘”同时发生时，**bojieli/ai-agent-book** 与 **OpenAI Agents SDK** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Context/Tool/Runtime` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“把生产权限直接放入 prompt”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：Agent 系统边界

本章重新审计后的核心结论是：**模型回复不是系统完成；tool_call 只是候选动作，证据与状态由 Runtime 负责。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[ReAct](https://arxiv.org/abs/2210.03629)**：reasoning/action 交错轨迹让模型决策可被放进 trajectory，而不是隐藏在最终回答里。
- **[Toolformer](https://arxiv.org/abs/2302.04761)**：说明模型可学习工具调用，但工程系统仍要在模型外做 schema 与权限验证。
- **[Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)**：强调先从简单可组合的 workflow/agent 模式出发。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。OpenAI Agents SDK 的 Runner 与 ai-agent-book 的实验轨道适合对照：它们把模型、工具与状态边界显式化，但不替代业务侧 verifier。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证 Agent 系统边界的输入、消息和状态是否能被显式记录；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**model decision is not a side effect; runtime owns execution evidence**；
2. `Agent vs Workflow` 必须是可观察软件边界，而不是 prompt 约定；
3. `构造 messages` 与 `记录 trace` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 误把 tool_call 当作任务成功
- 只保存最终回答，无法复盘
- 把生产权限直接放入 prompt

### 思考题与实践

- **Why：** 为什么 `Agent vs Workflow` 不能只靠模型“记住”？
- **What if：** 如果在 `构造 messages` 与 `记录 trace` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch01_foundation.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **模型基座：Token、结构化生成、工具调用与推理接口**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
