# Tool Design：让模型拥有可用而可控的双手

> **本章核心判断**：工具是模型行动空间的系统调用层；工具设计要同时考虑可发现性、语义粒度、参数校验、风险等级和输出形状。

上一章：Agent State、Trajectory 与可调试性。本章把前一章已经建立的能力进一步推进到 `Affordance`；下一章将进入：Tool Runtime：调度、权限、超时、重试与副作用语义。

![Tool Design：让模型拥有可用而可控的双手：系统边界与组件关系](../../assets/diagrams/07-tool-design-architecture.svg)

## 问题背景与学习目标

工具是模型行动空间的系统调用层；工具设计要同时考虑可发现性、语义粒度、参数校验、风险等级和输出形状。

在本章的 `Affordance` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“工具是模型行动空间的系统调用层；工具设计要同时考虑可发现性、语义粒度、参数校验、风险等级和输出形状。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `a tool contract must state intent, typed arguments, risk, and idempotency` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 07A` / `Lab 07B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Affordance

**定义。** Tool affordance 是模型从工具描述中感知到的“可以做什么、什么时候该做、有什么代价与风险”。好的 affordance 比单纯函数名更接近人类操作说明。

**系统责任。** 描述应包含输入语义、返回信息、典型失败和何时不要使用；工具集合过大时还需要 discover/search，而不是把所有 schema 塞进 prompt。

**失败边界。** 模糊 affordance 会导致模型选错工具或在相似工具之间随机游走；过度暴露工具则增加 prompt injection 与权限面。

### Schema

**定义。** Tool schema 是参数结构的可执行契约，应该把类型、范围、枚举、互斥关系和必填项尽量前移到 Runtime validation。

**系统责任。** Schema 同时服务模型生成与服务器验证。对 ID、金额、时间等关键字段应使用领域类型或额外 verifier，而不是全部 string。

**失败边界。** Schema 太宽会把错误推到真实系统；schema 太窄则迫使模型用自然语言绕过。

### Risk level

**定义。** Risk level 描述工具调用可能造成的外部损失和可逆性，例如 read‑only、reversible write、high‑impact irreversible。

**系统责任。** Runtime 可以根据 risk 决定是否需要 approval、sandbox、短期凭据、二次验证或 effect journal。风险应绑定具体 action，而不是只给整个 Agent 一个“高/低风险”标签。

**失败边界。** 若低风险查询与支付/删除共享同一权限，任何 prompt injection 都能直接升级成高影响事件。

### Result shaping

**定义。** Result shaping 是把原始工具输出转换为模型真正需要的最小、结构化 observation，同时保留原始证据引用。

**系统责任。** 应裁剪无关字段、标记来源/时间、限制不可信文本，并让大对象通过 handle/file 引用而不是全部塞进 context。

**失败边界。** 过度摘要会删除关键错误信息；完全透传 HTML/日志会引入噪声和注入风险。

## 原理与理论基础

### 系统不变量

> **Invariant**：a tool contract must state intent, typed arguments, risk, and idempotency

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `万能 shell 暴露过大` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “万能 shell 暴露过大”、“工具描述像内部 API 文档”、“返回原始日志淹没模型” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Affordance** 与 **Schema** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“万能 shell 暴露过大”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Affordance 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Schema 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `工具元数据包含 risk/idempotent`、`错误分类可进入 eval` 以及对不变量 **a tool contract must state intent, typed arguments, risk, and idempotency** 的检查。

**What if。** 一旦“工具描述像内部 API 文档”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
R(tool)=Impact\times Irreversibility\times Uncertainty
$$

工具风险由影响范围、不可逆性和结果不确定性共同决定；权限和审批强度应跟随风险而不是跟随工具名称。

**可证伪假设。** 基于风险分级的审批/限权能在保持低风险任务自动化率的同时降低高风险 unsafe effect。

**建议测量。** high-risk approval coverage、unsafe-effect rate、approval latency、least-privilege coverage。

## 关键机制与执行流程

![Tool Design：让模型拥有可用而可控的双手：正常路径与故障恢复流程](../../assets/diagrams/07-tool-design-flow.svg)

**Step 1 — 工具元数据包含 risk/idempotent。** `工具元数据包含 risk/idempotent` 是“Tool Design：让模型拥有可用而可控的双手”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Affordance` 是否仍满足 **a tool contract must state intent, typed arguments, risk, and idempotency**。

**Step 2 — 参数用类型和 enum 约束。** `参数用类型和 enum 约束` 是“Tool Design：让模型拥有可用而可控的双手”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Schema` 是否仍满足 **a tool contract must state intent, typed arguments, risk, and idempotency**。

**Step 3 — 大输出转 artifact。** `大输出转 artifact` 是“Tool Design：让模型拥有可用而可控的双手”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Risk level` 是否仍满足 **a tool contract must state intent, typed arguments, risk, and idempotency**。

**Step 4 — 错误分类可进入 eval。** `错误分类可进入 eval` 是“Tool Design：让模型拥有可用而可控的双手”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Result shaping` 是否仍满足 **a tool contract must state intent, typed arguments, risk, and idempotency**。

在本章的 `Affordance` 场景中，**最后一步 — 验证。** verifier 针对 `Result shaping` 检查本章不变量 **a tool contract must state intent, typed arguments, risk, and idempotency**。如果“万能 shell 暴露过大”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **工具元数据包含 risk/idempotent → 参数用类型和 enum 约束 → 大输出转 artifact → 错误分类可进入 eval** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“万能 shell 暴露过大”尤其要检查动作前后的证据是否足以闭合不变量 **a tool contract must state intent, typed arguments, risk, and idempotency**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Affordance` 有关的纯计算状态通常可以重算；一旦 `参数用类型和 enum 约束` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **a tool contract must state intent, typed arguments, risk, and idempotency**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Tool Design：让模型拥有可用而可控的双手')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('tool-design', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def tool_design(fault=False):
 @tool('Fetch invoice by immutable identifier',risk='low',idempotent=True)
 def invoice(id:int)->dict:return {'id':id,'amount':42}
 reg=ToolRegistry(); reg.register(invoice); schema=reg.schema()[0]
 if fault: schema['description']='do things'
 quality=bool(schema['description']) and 'invoice' in schema['description'].lower() and schema['parameters']['required']==['id']
 return _ok('tool-design',fault,{'schema':schema},'a tool contract must state intent, typed arguments, risk, and idempotency', quality if not fault else not quality)
```


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| Anthropic: Writing effective tools for agents | `official engineering article` | 工具接口本身是 Agent 性能与安全的重要变量。 | 以官方 docs/release/source tree 为准 | [官方来源](https://www.anthropic.com/engineering/writing-tools-for-agents) |
| OpenAI Agents SDK | `v0.22.0 @ 4df9ecf` | 从 Agent/Runner 入口追踪 tool loop、RunState、session、guardrail 与 tracing；特别对照 v0.22.0 对 replay state 与 failed/incomplete response 的 hardening。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/openai/openai-agents-python) |
| Hugging Face smolagents | `source observed 2026-09-09` | CodeAgent 与 ToolCallingAgent 的轻量实现对照。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/huggingface/smolagents) |

### 源码阅读方法

源码阅读以 **Anthropic: Writing effective tools for agents** 为第一参照，并只追与“Tool Design：让模型拥有可用而可控的双手”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“万能 shell 暴露过大”、如何在“工具描述像内部 API 文档”后恢复，以及如何让 `错误分类可进入 eval` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| Anthropic: Writing effective tools for agents | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| OpenAI Agents SDK | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| Hugging Face smolagents | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Tool Design：让模型拥有可用而可控的双手”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Tool Design：让模型拥有可用而可控的双手”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 07A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch07_tool_design.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::tool_design`
- `examples/chapters/ch07_tool_design.py::main`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "a tool contract must state intent, typed arguments, risk, and idempotency", "invariant_holds": true, "observation": {"schema": {"description": "Fetch invoice by immutable identifier", "idempotent": true, "name": "invoice", "parameters": {"properties": {"id": {"type": "integer"}}, "required": ["id"], "type": "object"}, "risk": "low"}}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "tool-design", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 07A](../../../labs/core/lab-07A-tool-design.md)。

### Lab 07B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch07_tool_design.py --fault
```

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L2_DETECTED", "evidence_meaning": "fault_detected_but_not_containment_or_recovery", "fault": true, "fault_injected": true, "invariant": "a tool contract must state intent, typed arguments, risk, and idempotency", "invariant_holds": false, "observation": {"schema": {"description": "do things", "idempotent": true, "name": "invoice", "parameters": {"properties": {"id": {"type": "integer"}}, "required": ["id"], "type": "object"}, "risk": "low"}}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "tool-design", "system_detected": true}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L2_DETECTED**：被测组件检测到了故障，但没有证明 containment/recovery。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 07B](../../../labs/core/lab-07B-tool-design-fault.md)。

### 观察与证据


## 工程场景与系统设计

**教学工程设计输入（不是公开云厂商性能数据）：** 客户支持 Agent 需要从 200 万条知识文档和用户历史中选择证据，再调用受控业务 API。设计输入：100 QPS、检索 p95 150 ms、每次最多 8 个证据块、写工具全部要求幂等键。


### 上线前必须补齐

- 围绕 **工具契约设计** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `工具契约必须声明意图、参数、风险、幂等性和可观察结果。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **万能 shell 暴露过大**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **工具描述像内部 API 文档**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **返回原始日志淹没模型**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `tool/retrieval p50,p95 latency`
- `tool error/UNKNOWN rate`
- `recall@k / evidence coverage`
- `memory hit/conflict rate`
- `payload bytes / turn`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Schema` 的生命周期时，要重新验证 **a tool contract must state intent, typed arguments, risk, and idempotency**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “万能 shell 暴露过大”、“工具描述像内部 API 文档”、“返回原始日志淹没模型”：只有正常路径与对应 fault path 都保持 **a tool contract must state intent, typed arguments, risk, and idempotency**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- 检索只能返回可索引/可访问的数据，不自动保证事实完整性
- 工具 schema 无法消除外部系统自身的不一致
- 长期记忆会过期、冲突或包含敏感信息，必须治理
- 协议标准化互操作，不替代业务授权与审计

选择方案时要回到本章边界：如果业务不能接受“万能 shell 暴露过大”，就必须为 `Affordance` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Schema` 决策交给模型，但要用 `错误分类可进入 eval` 保持结果可验证。**Anthropic: Writing effective tools for agents** 与 **OpenAI Agents SDK** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

良好的 Tool schema 能减少误调用，但不能独自解决授权、竞态或未知提交结果。写工具必须额外定义身份、权限、幂等键、超时后的 outcome 语义与可观察的 post-condition。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)**：探索模型学习何时调用外部工具以及如何把工具结果纳入后续预测。
- **[Anthropic: Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)**（official engineering article）：工具接口本身是 Agent 性能与安全的重要变量。
- **[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)**（v0.22.0 @ 4df9ecf）：Agent/Runner/Tools/Handoffs/Guardrails/Sessions/HITL/Tracing；0.22.0 包含 runtime hardening。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- MCP 2026‑07‑28 Specification（2026‑07‑28 GA）：stateless protocol core, MRTR, header routing, cache hints and auth hardening。
- NIST AI 800‑5: Security Considerations for AI Agents（published 2026‑05‑18）：agent security threats, mitigations, assessment and adoption barriers。

**本章吸收的变化。** 工具设计的关键不是函数数量，而是把 capability、schema、风险与结果证据做成模型可用、Runtime 可控的边界。高风险工具应自动触发更强 policy/approval/verifier。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Affordance`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **a tool contract must state intent, typed arguments, risk, and idempotency** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“万能 shell 暴露过大”和“工具描述像内部 API 文档”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **工具契约设计** 的可验证性。Anthropic Writing Effective Tools 强调工具接口质量会直接影响 Agent 行为；这与本章 schema/risk/idempotency 不变量一致。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Affordance` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“万能 shell 暴露过大”与“工具描述像内部 API 文档”同时发生时，**Anthropic: Writing effective tools for agents** 与 **OpenAI Agents SDK** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Schema` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“返回原始日志淹没模型”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：工具契约设计

本章重新审计后的核心结论是：**工具契约必须声明意图、参数、风险、幂等性和可观察结果。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[Semantic Transactions for Tool-Using LLM Agents](https://arxiv.org/abs/2606.17573)**：把不可逆工具副作用抽象成语义事务，支撑 UNKNOWN、staging 与 validation 讨论。
- **[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)**：提供 Agent/Runner/Tools/HITL/Tracing/Sessions 的公开实现边界。
- **[Microsoft Agent Framework Checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)**：把 checkpoint 定义为 workflow resume 所需的 executor state、pending messages/requests 与 shared state。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。OpenAI tools、MCP tools、smolagents Tool、ADK tools 可以对照 schema 表达力和运行时治理能力。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证工具契约设计的 schema、证据或记忆边界；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**a tool contract must state intent, typed arguments, risk, and idempotency**；
2. `Affordance` 必须是可观察软件边界，而不是 prompt 约定；
3. `工具元数据包含 risk/idempotent` 与 `错误分类可进入 eval` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 万能 shell 暴露过大
- 工具描述像内部 API 文档
- 返回原始日志淹没模型

### 思考题与实践

- **Why：** 为什么 `Affordance` 不能只靠模型“记住”？
- **What if：** 如果在 `工具元数据包含 risk/idempotent` 与 `错误分类可进入 eval` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch07_tool_design.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **Tool Runtime：调度、权限、超时、重试与副作用语义**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
