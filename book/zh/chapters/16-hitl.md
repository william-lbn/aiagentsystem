# Human-in-the-Loop：把不可逆动作放进可恢复审批

> **本章核心判断**：HITL 不是弹窗，而是 durable pause：系统应保存待审批动作、上下文、证据和恢复点，审批后继续或终止。

上一章：Async Runtime：流式、并发、中断与取消。本章把前一章已经建立的能力进一步推进到 `Approval request`；下一章将进入：Sandbox 与权限：控制 Agent 的爆炸半径。

![Human-in-the-Loop：把不可逆动作放进可恢复审批：系统边界与组件关系](../../assets/diagrams/16-hitl-architecture.svg)

## 问题背景与学习目标

HITL 不是弹窗，而是 durable pause：系统应保存待审批动作、上下文、证据和恢复点，审批后继续或终止。

在本章的 `Approval request` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“HITL 不是弹窗，而是 durable pause：系统应保存待审批动作、上下文、证据和恢复点，审批后继续或终止。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `high-risk side effects cannot execute before a durable approval decision` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 16A` / `Lab 16B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Approval request

**定义。** Approval request 是 Runtime 在高风险 action 前生成的结构化决策对象，应包含拟执行动作、关键参数、影响范围、证据和超时。

**系统责任。** 审批人确认的应是具体 effect，而不是模糊的“允许 Agent 继续”。批准结果需要绑定 action hash/版本，防止批准后参数被模型修改。

**失败边界。** 如果审批只是一条聊天消息，无法证明批准了哪个具体动作，也难以审计。

### Interrupt

**定义。** Interrupt 是把运行中的状态机停在一个可恢复、可观察的等待点，而不是抛出异常后丢失上下文。

**系统责任。** 中断点应持久化 state、pending action 和 resume token，并释放不需要长期占用的资源。

**失败边界。** 不可恢复 interrupt 会让 HITL 变成“人一确认，任务从头再来”，容易重复副作用。

### Resume

**定义。** Resume 从持久化 interrupt state 继续执行，并重新验证时间敏感条件、权限和外部状态。

**系统责任。** 批准不是永久通行证；如果等待期间数据、价格或代码发生变化，应要求重新确认或重新 plan。

**失败边界。** 直接把旧内存对象继续跑会忽略进程重启和环境漂移。

### Audit

**定义。** HITL audit 记录谁在什么时间看到什么证据、批准/拒绝了哪个 action，以及之后真实发生了什么。

**系统责任。** 审计日志应与业务 effect ID 关联，并支持不可抵赖的身份和 retention policy。

**失败边界。** 只保存“用户点了确认”而没有 action 内容，无法满足事故调查与合规要求。

## 原理与理论基础

### 系统不变量

> **Invariant**：high-risk side effects cannot execute before a durable approval decision

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `审批只存在前端状态` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “审批只存在前端状态”、“审批后重新生成不同动作”、“拒绝后任务仍继续” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Approval request** 与 **Interrupt** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“审批只存在前端状态”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Approval request 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Interrupt 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `审批对象包含 tool+args+risk`、`审批写入审计日志` 以及对不变量 **high-risk side effects cannot execute before a durable approval decision** 的检查。

**What if。** 一旦“审批后重新生成不同动作”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
ValidApproval=Sig(run,action\_hash,state\_version,scope,expiry)
$$

HITL 的审批对象必须绑定具体 run、动作摘要、状态版本、权限范围和过期时间，而不是一句“批准继续”。

**可证伪假设。** state-bound approval 能减少 stale approval/TOCTOU 导致的越权执行。

**建议测量。** stale-approval rejection、approval replay block、approval latency、manual override rate。

## 关键机制与执行流程

![Human-in-the-Loop：把不可逆动作放进可恢复审批：正常路径与故障恢复流程](../../assets/diagrams/16-hitl-flow.svg)

**Step 1 — 审批对象包含 tool+args+risk。** 这一阶段可能改变系统或外部环境，因此 `审批对象包含 tool+args+risk` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **high-risk side effects cannot execute before a durable approval decision**。

**Step 2 — checkpoint 在暂停前落盘。** `checkpoint 在暂停前落盘` 把短暂执行状态转换为后续能够读取的证据。写入内容至少要能关联本次 run、前一状态与下一状态；对 crash-sensitive 数据，应明确写入完成的判据。若进程在写入期间终止，恢复代码必须能够区分“没有记录”“完整记录”和“损坏/不确定记录”，而不能把半写状态视作成功。

**Step 3 — 拒绝路径是终态。** `拒绝路径是终态` 是“Human-in-the-Loop：把不可逆动作放进可恢复审批”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Resume` 是否仍满足 **high-risk side effects cannot execute before a durable approval decision**。

**Step 4 — 审批写入审计日志。** 这一阶段可能改变系统或外部环境，因此 `审批写入审计日志` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **high-risk side effects cannot execute before a durable approval decision**。

在本章的 `Approval request` 场景中，**最后一步 — 验证。** verifier 针对 `Audit` 检查本章不变量 **high-risk side effects cannot execute before a durable approval decision**。如果“审批只存在前端状态”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **审批对象包含 tool+args+risk → checkpoint 在暂停前落盘 → 拒绝路径是终态 → 审批写入审计日志** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“审批只存在前端状态”尤其要检查动作前后的证据是否足以闭合不变量 **high-risk side effects cannot execute before a durable approval decision**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Approval request` 有关的纯计算状态通常可以重算；一旦 `checkpoint 在暂停前落盘` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **high-risk side effects cannot execute before a durable approval decision**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Human-in-the-Loop：把不可逆动作放进可恢复审批')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('hitl', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def hitl(fault=False):
    effects = []

    @tool("Delete demo", risk="high", idempotent=True)
    def delete(id: int):
        effects.append(id)
        return {"deleted": id}

    reg = ToolRegistry(); reg.register(delete)
    rt = AgentRuntime(
        ScriptedModel([ModelDecision(tool="delete", args={"id": 1}), ModelDecision(final="deleted")]),
        reg,
        policy=PolicyEngine(approval_tools={"delete"}),
    )
    first = rt.run("delete demo")
    action_id = (first.get("pending_approval") or {}).get("action_id")
    if fault:
        condition = first["status"] == "WAITING_APPROVAL" and effects == [] and bool(action_id)
        return _ok("hitl", True,
                   {"before": first["status"], "action_id": action_id, "effect_count": 0},
                   "high-risk side effects cannot execute before a durable approval decision bound to the exact action",
                   condition)

    second = rt.run("ignored", resume=True, run_id=first["run_id"],
                    approval="approve", approval_action_id=action_id)
    condition = first["status"] == "WAITING_APPROVAL" and \
        second["status"] == "FINISHED" and effects == [1]
    return _ok("hitl", False,
               {"before": first["status"], "after": second["status"],
                "action_id": action_id, "effect_count": len(effects)},
               "high-risk side effects cannot execute before a durable approval decision bound to the exact action",
               condition)
```


审批对象必须是不可变 action，而不是“这个 run 大概可以继续”。本实现用 `run_id + step + tool + args_hash` 生成 `action_id`；缺失、过期或不匹配的 approval 都 fail-closed。批准后不会再次询问模型生成新动作，而是执行 checkpoint 中保存的原始 pending effect。

| 恢复点 | 能否自动执行/重放 | 原因 |
|---|---|---|
| `WAITING_APPROVAL` | 否 | 尚无与 action 绑定的 durable approval |
| `APPROVED_PENDING_EFFECT` | 可以执行一次 pending intent | 批准已持久化，而 effect execution 尚未开始 |
| `EXECUTING_EFFECT` 后崩溃 | **禁止盲目重放** | 外部系统可能已经提交但本地 result 尚未落盘，必须转 `NEEDS_RECONCILIATION` |
| `COMMITTED` 已持久化 | 继续后续状态机 | effect outcome 已有本地证据；生产仍可按风险做独立 observation |

因此本章不声称跨系统 “exactly once”。没有分布式事务时，正确目标是让 ambiguous window 可检测、可停住、可 observation/reconcile。


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| LangGraph / LangChain HITL docs | `docs observed 2026-09-09` | interrupt/resume 依赖持久化 graph state。 | 以官方 docs/release/source tree 为准 | [官方来源](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) |
| OpenAI Agents SDK | `v0.22.0 @ 4df9ecf` | 从 Agent/Runner 入口追踪 tool loop、RunState、session、guardrail 与 tracing；特别对照 v0.22.0 对 replay state 与 failed/incomplete response 的 hardening。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/openai/openai-agents-python) |
| Microsoft Agent Framework checkpoints | `docs observed 2026-09-09` | checkpoint 捕获 executor states、pending messages/requests、shared state，用于 resume。 | 以官方 docs/release/source tree 为准 | [官方来源](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints) |

### 源码阅读方法

源码阅读以 **LangGraph / LangChain HITL docs** 为第一参照，并只追与“Human-in-the-Loop：把不可逆动作放进可恢复审批”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“审批只存在前端状态”、如何在“审批后重新生成不同动作”后恢复，以及如何让 `审批写入审计日志` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| LangGraph / LangChain HITL docs | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| OpenAI Agents SDK | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| Microsoft Agent Framework checkpoints | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Human-in-the-Loop：把不可逆动作放进可恢复审批”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Human-in-the-Loop：把不可逆动作放进可恢复审批”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 16A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch16_hitl.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::hitl`
- `examples/chapters/ch16_hitl.py::main`
- `src/agentlab/runtime.py::AgentRuntime.run`
- `src/agentlab/tools.py::ToolRegistry.execute`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "high-risk side effects cannot execute before a durable approval decision bound to the exact action", "invariant_holds": true, "observation": {"action_id": "d8bab1f8ef45cf1b89c11cb64669f3437c044378ac93897eb334db272360e56f", "after": "FINISHED", "before": "WAITING_APPROVAL", "effect_count": 1}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "hitl", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 16A](../../../labs/core/lab-16A-hitl.md)。

### Lab 16B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch16_hitl.py --fault
```

**本发布包实际输出：**

```json
{"contained": true, "evidence_level": "L3_CONTAINED", "evidence_meaning": "fault_detected_and_contained", "fault": true, "fault_injected": true, "invariant": "high-risk side effects cannot execute before a durable approval decision bound to the exact action", "invariant_holds": true, "observation": {"action_id": "1d168810edad2e7d8f42acffeabd0c7ff0eba4033c021daee6d32ba5461b2b5e", "attempt": "no approval", "before": "WAITING_APPROVAL", "effect_count": 0}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "hitl", "system_detected": true}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L3_CONTAINED**：被测组件检测并 fail-closed/约束了故障，但不声明已恢复业务结果。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 16B](../../../labs/core/lab-16B-hitl-fault.md)。

### 观察与证据


## 工程场景与系统设计

本章沿用第 14 章长任务场景，重点将 30 分钟审批 TTL 绑定到具体 action identity，并验证过期、拒绝和 crash-window 的 fail-closed 行为。


### 上线前必须补齐

- 围绕 **Human-in-the-Loop** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `人工审批是状态机，不是弹窗；审批必须持久化并绑定动作摘要。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **审批只存在前端状态**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **审批后重新生成不同动作**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **拒绝后任务仍继续**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `run p95 latency`
- `checkpoint fsync latency`
- `resume success rate`
- `cancellation tail latency`
- `approval wait time`
- `UNKNOWN reconciliation time`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Interrupt` 的生命周期时，要重新验证 **high-risk side effects cannot execute before a durable approval decision**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “审批只存在前端状态”、“审批后重新生成不同动作”、“拒绝后任务仍继续”：只有正常路径与对应 fault path 都保持 **high-risk side effects cannot execute before a durable approval decision**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- checkpoint 只能恢复已持久化状态，不能凭空知道外部副作用是否成功
- sandbox 限制本地执行边界，不自动限制所有网络/云权限
- HITL 提高安全性但增加延迟和运营成本
- 并发提升吞吐但放大竞态、预算和取消复杂度

选择方案时要回到本章边界：如果业务不能接受“审批只存在前端状态”，就必须为 `Approval request` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Interrupt` 决策交给模型，但要用 `审批写入审计日志` 保持结果可验证。**LangGraph / LangChain HITL docs** 与 **OpenAI Agents SDK** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

HITL 的安全性来自“批准具体动作”，而不是批准一个模糊的 run。审批必须绑定不可变 action identity、参数摘要和有效期；外部 effect 进入不确定窗口后，即使审批存在也不能盲目重放。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses](https://arxiv.org/abs/2406.13352)**：以工具返回内容中的 prompt injection 测试 Agent 安全边界。
- **[LangGraph / LangChain HITL docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)**（docs observed 2026-09-09）：interrupt/resume 依赖持久化 graph state。
- **[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)**（v0.22.0 @ 4df9ecf）：Agent/Runner/Tools/Handoffs/Guardrails/Sessions/HITL/Tracing；0.22.0 包含 runtime hardening。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- NIST Agent Identity and Authorization Concept Paper（published 2026‑02‑05）：agent identity, delegated authority, authentication and authorization。
- OpenAI Agents SDK v0.22.2（v0.22.2 @ 83c737f; 2026‑09‑09）：latest observed Python Agents SDK release。

**本章吸收的变化。** HITL 的安全性来自“批准什么”可验证，而不是界面上有一个确认按钮。 resume 前还要检查 state 是否变化。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Approval request`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **high-risk side effects cannot execute before a durable approval decision** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“审批只存在前端状态”和“审批后重新生成不同动作”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **Human-in-the-Loop** 的可验证性。OpenAI Agents SDK 与 LangGraph HITL 都要求 paused state/resume；Anthropic containment 指出审批疲劳需要最小权限和沙箱配合。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Approval request` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“审批只存在前端状态”与“审批后重新生成不同动作”同时发生时，**LangGraph / LangChain HITL docs** 与 **OpenAI Agents SDK** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Interrupt` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“拒绝后任务仍继续”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：Human-in-the-Loop

本章重新审计后的核心结论是：**人工审批是状态机，不是弹窗；审批必须持久化并绑定动作摘要。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[Semantic Transactions for Tool-Using LLM Agents](https://arxiv.org/abs/2606.17573)**：把不可逆工具副作用抽象成语义事务，支撑 UNKNOWN、staging 与 validation 讨论。
- **[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)**：提供 Agent/Runner/Tools/HITL/Tracing/Sessions 的公开实现边界。
- **[Microsoft Agent Framework Checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)**：把 checkpoint 定义为 workflow resume 所需的 executor state、pending messages/requests 与 shared state。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。OpenAI approval tools、LangGraph interrupt、MAF checkpoint 是主流对照。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证 Human-in-the-Loop 在 normal/fault 两条路径下是否进入可解释状态；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**high-risk side effects cannot execute before a durable approval decision**；
2. `Approval request` 必须是可观察软件边界，而不是 prompt 约定；
3. `审批对象包含 tool+args+risk` 与 `审批写入审计日志` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 审批只存在前端状态
- 审批后重新生成不同动作
- 拒绝后任务仍继续

### 思考题与实践

- **Why：** 为什么 `Approval request` 不能只靠模型“记住”？
- **What if：** 如果在 `审批对象包含 tool+args+risk` 与 `审批写入审计日志` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch16_hitl.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **Sandbox 与权限：控制 Agent 的爆炸半径**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
