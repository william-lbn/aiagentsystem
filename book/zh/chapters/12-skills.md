# Skills、Procedural Memory 与可复用能力

> **本章核心判断**：Skill 是可复用过程知识，既可以是 prompt/recipe，也可以是工具组合、脚本或 workflow；它让 Agent 从一次性动作走向积累能力。

上一章：长期记忆：从聊天历史到可治理的用户状态。本章把前一章已经建立的能力进一步推进到 `Skill card`；下一章将进入：MCP：把外部工具与资源接成协议边界。

![Skills、Procedural Memory 与可复用能力：系统边界与组件关系](../../assets/diagrams/12-skills-architecture.svg)

## 问题背景与学习目标

Skill 是可复用过程知识，既可以是 prompt/recipe，也可以是工具组合、脚本或 workflow；它让 Agent 从一次性动作走向积累能力。

在本章的 `Skill card` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“Skill 是可复用过程知识，既可以是 prompt/recipe，也可以是工具组合、脚本或 workflow；它让 Agent 从一次性动作走向积累能力。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `a reusable skill packages procedure plus an explicit capability boundary` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 12A` / `Lab 12B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Skill card

**定义。** Skill card 是对一项可复用能力的机器可读说明，包含目标、触发条件、输入、步骤、依赖、风险和验收标准。

**系统责任。** 它位于 prompt 与 tool 之间：比单个函数更高层， 又比完整 Agent 更可组合。 Runtime 可按任务检索 skill，再加载必要工具。

**失败边界。** 如果 skill 只有自然语言“经验总结”而没有 precondition/verifier，会在新环境中被错误复用。

### Tool chain

**定义。** Tool chain 是完成一个能力所需的有序/有依赖的工具组合，例如查 schema→ 运行查询 → 生成图 → 验证 artifact。

**系统责任。** 稳定链路适合固化为 workflow/skill，而开放分支保留给 Agent 决策。每一步应声明输入/输出 contract。

**失败边界。** 把所有步骤都留给自由 tool selection 会增加回合数和错误表面；链路过度硬编码又会降低适应性。

### Precondition

**定义。** Precondition 是 skill 可以安全执行前必须成立的环境和状态条件，如文件存在、权限只读、分支干净或数据版本匹配。

**系统责任。** Runtime 在加载/执行 skill 前检查 precondition，失败时应返回“不可执行原因” 而不是让模型猜。

**失败边界。** 缺少前置检查会让原本正确的 skill 在错误环境里产生危险 effect。

### Verification

**定义。** Skill verification 是执行后对目标状态做独立检查，可以是测试、schema、文件 hash、 API query 或人工验收。

**系统责任。** Verifier 应尽量独立于生成该结果的 Agent，并产生结构化 evidence 供复用和回归。

**失败边界。** 如果 skill 自己输出“完成”就被视为 PASS，自我改进系统会迅速发生 reward hacking。

## 原理与理论基础

### 系统不变量

> **Invariant**：a reusable skill packages procedure plus an explicit capability boundary

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `skill 描述过宽导致误用` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “skill 描述过宽导致误用”、“旧版 skill 与工具 schema 不兼容”、“skill 成功标准缺失” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Skill card** 与 **Tool chain** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“skill 描述过宽导致误用”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Skill card 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Tool chain 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `skill 声明输入/输出/限制`、`失败样本反哺改进` 以及对不变量 **a reusable skill packages procedure plus an explicit capability boundary** 的检查。

**What if。** 一旦“旧版 skill 与工具 schema 不兼容”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
Skill=(Pre,Action,Post,Verifier,Version)
$$

Skill 是具有前置条件、动作、后置条件、验证器和版本的程序化能力，而不仅是 prompt 模板。

**可证伪假设。** 把 verifier/version 纳入 Skill contract 后，升级造成的 silent regression 会更早被检测。

**建议测量。** skill success、postcondition pass、version regression rate、reuse rate。

## 关键机制与执行流程

![Skills、Procedural Memory 与可复用能力：正常路径与故障恢复流程](../../assets/diagrams/12-skills-flow.svg)

**Step 1 — skill 声明输入/输出/限制。** `skill 声明输入/输出/限制` 是“Skills、Procedural Memory 与可复用能力”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Skill card` 是否仍满足 **a reusable skill packages procedure plus an explicit capability boundary**。

**Step 2 — 版本化 skill。** `版本化 skill` 是“Skills、Procedural Memory 与可复用能力”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Tool chain` 是否仍满足 **a reusable skill packages procedure plus an explicit capability boundary**。

**Step 3 — skill 调用写入 trace。** 这一阶段可能改变系统或外部环境，因此 `skill 调用写入 trace` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **a reusable skill packages procedure plus an explicit capability boundary**。

**Step 4 — 失败样本反哺改进。** `失败样本反哺改进` 是“Skills、Procedural Memory 与可复用能力”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Verification` 是否仍满足 **a reusable skill packages procedure plus an explicit capability boundary**。

在本章的 `Skill card` 场景中，**最后一步 — 验证。** verifier 针对 `Verification` 检查本章不变量 **a reusable skill packages procedure plus an explicit capability boundary**。如果“skill 描述过宽导致误用”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **skill 声明输入/输出/限制 → 版本化 skill → skill 调用写入 trace → 失败样本反哺改进** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“skill 描述过宽导致误用”尤其要检查动作前后的证据是否足以闭合不变量 **a reusable skill packages procedure plus an explicit capability boundary**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Skill card` 有关的纯计算状态通常可以重算；一旦 `版本化 skill` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **a reusable skill packages procedure plus an explicit capability boundary**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Skills、Procedural Memory 与可复用能力')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('skills', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def skills(fault=False):
 skill={'name':'incident','steps':['collect evidence','form hypothesis','verify','report'],'permissions':['read_logs']}
 if fault: skill['permissions'].append('delete_database')
 safe=set(skill['permissions']) <= {'read_logs','read_metrics'}
 return _ok('skills',fault,skill,'a reusable skill packages procedure plus an explicit capability boundary', safe if not fault else not safe)
```


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| Pi Coding Agent | `@earendil-works/pi-coding-agent 0.85.1` | 把 session tree、branching、compaction、extensions/skills 看成极简 coding harness 的核心；同时注意 2026 年包名迁移到 @earendil-works。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/earendil-works/pi) |
| DeepSeek Harness | `@deepseek-ai/dsh 0.1.2-rc.1 reproducibility pin` | 先读 docs/architecture.md，再看 service/dependency/lifecycle；关注 Cordis context、service 注入与 plugin 可逆 effect，而不是只看 UI。 | `docs/architecture.md`<br>`docs/user/develop/framework/service.md` | [官方来源](https://github.com/deepseek-ai/deepseek-harness) |
| OpenAI Agents SDK | `v0.22.0 @ 4df9ecf` | 从 Agent/Runner 入口追踪 tool loop、RunState、session、guardrail 与 tracing；特别对照 v0.22.0 对 replay state 与 failed/incomplete response 的 hardening。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/openai/openai-agents-python) |

### 源码阅读方法

源码阅读以 **Pi Coding Agent** 为第一参照，并只追与“Skills、Procedural Memory 与可复用能力”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“skill 描述过宽导致误用”、如何在“旧版 skill 与工具 schema 不兼容”后恢复，以及如何让 `失败样本反哺改进` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| Pi Coding Agent | 贴近 coding/长期执行 harness，工作区和工具边界更真实 | 依赖更重或迭代快，升级需锁版本做回归 | Coding Agent、Harness 源码学习 |
| DeepSeek Harness | 贴近 coding/长期执行 harness，工作区和工具边界更真实 | 依赖更重或迭代快，升级需锁版本做回归 | Coding Agent、Harness 源码学习 |
| OpenAI Agents SDK | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Skills、Procedural Memory 与可复用能力”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Skills、Procedural Memory 与可复用能力”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 12A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch12_skills.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::skills`
- `examples/chapters/ch12_skills.py::main`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "a reusable skill packages procedure plus an explicit capability boundary", "invariant_holds": true, "observation": {"name": "incident", "permissions": ["read_logs"], "steps": ["collect evidence", "form hypothesis", "verify", "report"]}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "skills", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 12A](../../../labs/core/lab-12A-skills.md)。

### Lab 12B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch12_skills.py --fault
```

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L2_DETECTED", "evidence_meaning": "fault_detected_but_not_containment_or_recovery", "fault": true, "fault_injected": true, "invariant": "a reusable skill packages procedure plus an explicit capability boundary", "invariant_holds": false, "observation": {"name": "incident", "permissions": ["read_logs", "delete_database"], "steps": ["collect evidence", "form hypothesis", "verify", "report"]}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "skills", "system_detected": true}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L2_DETECTED**：被测组件检测到了故障，但没有证明 containment/recovery。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 12B](../../../labs/core/lab-12B-skills-fault.md)。

### 观察与证据


## 工程场景与系统设计

本章复用第 7 章“客户支持 Agent”教学负载，重点检查可复用 skill 是否越过业务 API 的权限和幂等边界。


### 上线前必须补齐

- 围绕 **Skills 与过程记忆** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `Skill 是过程、资源和权限边界的组合，不只是 prompt 片段。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **skill 描述过宽导致误用**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **旧版 skill 与工具 schema 不兼容**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **skill 成功标准缺失**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `tool/retrieval p50,p95 latency`
- `tool error/UNKNOWN rate`
- `recall@k / evidence coverage`
- `memory hit/conflict rate`
- `payload bytes / turn`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Tool chain` 的生命周期时，要重新验证 **a reusable skill packages procedure plus an explicit capability boundary**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “skill 描述过宽导致误用”、“旧版 skill 与工具 schema 不兼容”、“skill 成功标准缺失”：只有正常路径与对应 fault path 都保持 **a reusable skill packages procedure plus an explicit capability boundary**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- 检索只能返回可索引/可访问的数据，不自动保证事实完整性
- 工具 schema 无法消除外部系统自身的不一致
- 长期记忆会过期、冲突或包含敏感信息，必须治理
- 协议标准化互操作，不替代业务授权与审计

选择方案时要回到本章边界：如果业务不能接受“skill 描述过宽导致误用”，就必须为 `Skill card` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Tool chain` 决策交给模型，但要用 `失败样本反哺改进` 保持结果可验证。**Pi Coding Agent** 与 **DeepSeek Harness** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

Skill 是可复用能力包，不应成为绕过 Runtime policy 的隐式代码通道。技能加载、版本、依赖、权限和来源都需要显式治理；来自未知来源的技能即使能运行，也不能自动获得高风险工具权限。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[Voyager: An Open-Ended Embodied Agent with Large Language Models](https://arxiv.org/abs/2305.16291)**：自动课程、技能库和迭代 prompting 的 embodied agent。
- **[Pi Coding Agent](https://github.com/earendil-works/pi)**（@earendil-works/pi-coding-agent 0.85.1）：极简 terminal coding harness；extensions、skills、sessions、branching/compaction；旧 @mariozechner 包已弃用。
- **[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)**（@deepseek-ai/dsh 0.1.2-rc.1 reproducibility pin）：Developer preview；Everything is a Plugin，基于 Cordis context/service/lifecycle。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- Anthropic: Writing effective tools for agents（official engineering article）：强调工具描述、输入边界与模型可用性应共同设计，工具质量直接影响 Agent 的决策空间。
- OpenAI: The next evolution of the Agents SDK（2026‑04‑15）：model‑native harness, sandbox, long‑horizon tasks and subagents。

**本章吸收的变化。** Skill/Procedural Memory 应把前置条件、动作、后置条件和 verifier 封装成可版本化能力，而不只是 prompt 片段。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Skill card`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **a reusable skill packages procedure plus an explicit capability boundary** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“skill 描述过宽导致误用”和“旧版 skill 与工具 schema 不兼容”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **Skills 与过程记忆** 的可验证性。Anthropic Agent Skills 把技能组织成文件夹和脚本资源；这与本章 procedural memory/capability boundary 对齐。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Skill card` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“skill 描述过宽导致误用”与“旧版 skill 与工具 schema 不兼容”同时发生时，**Pi Coding Agent** 与 **DeepSeek Harness** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Tool chain` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“skill 成功标准缺失”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：Skills 与过程记忆

本章重新审计后的核心结论是：**Skill 是过程、资源和权限边界的组合，不只是 prompt 片段。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[Memora](https://arxiv.org/abs/2604.20006)**：强调长期记忆不仅要 recall，也要遗忘过期事实。
- **[Mem2ActBench](https://arxiv.org/abs/2601.19935)**：把记忆是否能主动用于工具参数 grounding 作为评测目标。
- **[LongMemEval-V2](https://arxiv.org/abs/2605.12493)**：把 web-agent 经验轨迹转成长期记忆评测，暴露 latency/quality 取舍。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。Claude Skills、DeepSeek Harness plugins、Pi extensions 可比较技能封装和生命周期。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证 Skills 与过程记忆的 schema、证据或记忆边界；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**a reusable skill packages procedure plus an explicit capability boundary**；
2. `Skill card` 必须是可观察软件边界，而不是 prompt 约定；
3. `skill 声明输入/输出/限制` 与 `失败样本反哺改进` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- skill 描述过宽导致误用
- 旧版 skill 与工具 schema 不兼容
- skill 成功标准缺失

### 思考题与实践

- **Why：** 为什么 `Skill card` 不能只靠模型“记住”？
- **What if：** 如果在 `skill 声明输入/输出/限制` 与 `失败样本反哺改进` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch12_skills.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **MCP：把外部工具与资源接成协议边界**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
