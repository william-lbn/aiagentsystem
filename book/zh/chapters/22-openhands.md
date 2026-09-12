# OpenHands 与远程 Agent Server 架构

> **本章核心判断**：OpenHands 展示了从本地 coding demo 走向远程 workspace、事件流和 Agent Server 的产品化路径。

上一章：Codex、Pi 与 Claude Code 类 Harness 解剖。本章把前一章已经建立的能力进一步推进到 `Agent Server`；下一章将进入：Browser / Computer Use Agent：观察、动作与环境验证。

![OpenHands 与远程 Agent Server 架构：系统边界与组件关系](../../assets/diagrams/22-openhands-architecture.svg)

## 问题背景与学习目标

OpenHands 展示了从本地 coding demo 走向远程 workspace、事件流和 Agent Server 的产品化路径。

在本章的 `Agent Server` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“OpenHands 展示了从本地 coding demo 走向远程 workspace、事件流和 Agent Server 的产品化路径。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `remote agent servers need explicit conversation/workspace/event boundaries` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 22A` / `Lab 22B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Agent Server

**定义。** 把 run/session、agent lifecycle、events 与远程 workspace 暴露为服务接口的控制面， 而不是把所有逻辑塞进单个进程。

**系统责任。** Agent Server 负责创建/恢复任务、路由事件、维护租约与客户端连接，并把 agent 决策与执行基座解耦。

**失败边界。** 控制面没有持久状态或租约语义时，断线重连会重复启动任务；多客户端也可能同时驱动同一 workspace。

### Workspace

**定义。** 远程 Agent 实际读取文件、运行命令、访问浏览器或构建代码的执行基座。

**系统责任。** Workspace 应明确镜像/快照、网络、secret mount、CPU/内存/磁盘和销毁策略， 并产生可回收 artifact。

**失败边界。** 把 workspace 当成“远程 shell”会让权限、环境漂移和残留状态不可控；重建后也难以证明任务运行于同一基线。

### Events

**定义。** Agent Server 与 runtime 之间传递的类型化 action、observation、state change 和 lifecycle record。

**系统责任。** 事件流为 UI、replay、audit 和恢复提供共享事实；事件应有 run/sequence/correlation id，而不是只保存文本日志。

**失败边界。** 事件乱序、重复或缺少 sequence 时，客户端看到的状态可能与服务器不同；以 UI 最后一条消息判成功尤其危险。

### Remote execution

**定义。** 把 agent decision 与实际 tool/process 执行放在网络另一端，并通过租约、heartbeat、 timeout 和 observation 协调。

**系统责任。** 远程执行允许弹性资源与更强隔离，但必须把连接中断与任务中断分开，并支持重连后的状态查询。

**失败边界。** 网络超时无法证明命令未执行；若直接 retry，可能重复产生副作用，因此需要 idempotency 或 reconciliation。

## 原理与理论基础

### 系统不变量

> **Invariant**：remote agent servers need explicit conversation/workspace/event boundaries

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `server 进程挂掉丢任务` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “server 进程挂掉丢任务”、“workspace 泄漏跨用户文件”、“事件状态 RUNNING 卡死” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Agent Server** 与 **Workspace** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“server 进程挂掉丢任务”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Agent Server 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Workspace 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `API 与执行环境分离`、`server policy 独立配置` 以及对不变量 **remote agent servers need explicit conversation/workspace/event boundaries** 的检查。

**What if。** 一旦“workspace 泄漏跨用户文件”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
Lease=(workspace,run,t_{exp}),\qquad EventSeq_{n+1}>EventSeq_n
$$

Remote Agent Server 需要把连接状态与运行状态分离，并用 lease/event sequence 处理断线重连。

**可证伪假设。** 持久 run identity + monotonic event sequence 能在 reconnect 时降低重复执行。

**建议测量。** reconnect recovery、duplicate run rate、lease expiry errors、event-gap detection。

## 关键机制与执行流程

![OpenHands 与远程 Agent Server 架构：正常路径与故障恢复流程](../../assets/diagrams/22-openhands-flow.svg)

**Step 1 — API 与执行环境分离。** 这一阶段可能改变系统或外部环境，因此 `API 与执行环境分离` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **remote agent servers need explicit conversation/workspace/event boundaries**。

**Step 2 — workspace 生命周期明确。** `workspace 生命周期明确` 是“OpenHands 与远程 Agent Server 架构”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Workspace` 是否仍满足 **remote agent servers need explicit conversation/workspace/event boundaries**。

**Step 3 — 事件流可订阅。** `事件流可订阅` 是“OpenHands 与远程 Agent Server 架构”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Events` 是否仍满足 **remote agent servers need explicit conversation/workspace/event boundaries**。

**Step 4 — server policy 独立配置。** `server policy 独立配置` 是“OpenHands 与远程 Agent Server 架构”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Remote execution` 是否仍满足 **remote agent servers need explicit conversation/workspace/event boundaries**。

在本章的 `Agent Server` 场景中，**最后一步 — 验证。** verifier 针对 `Remote execution` 检查本章不变量 **remote agent servers need explicit conversation/workspace/event boundaries**。如果“server 进程挂掉丢任务”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **API 与执行环境分离 → workspace 生命周期明确 → 事件流可订阅 → server policy 独立配置** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“server 进程挂掉丢任务”尤其要检查动作前后的证据是否足以闭合不变量 **remote agent servers need explicit conversation/workspace/event boundaries**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Agent Server` 有关的纯计算状态通常可以重算；一旦 `workspace 生命周期明确` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **remote agent servers need explicit conversation/workspace/event boundaries**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='OpenHands 与远程 Agent Server 架构')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('openhands', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def openhands(fault=False):
 events=[('conversation.created','c1'),('workspace.attached','w1'),('tool.started','shell'),('tool.finished','0')]
 if fault: events=events[:-1]
 finished=any(t=='tool.finished' for t,_ in events)
 return _ok('openhands',fault,{'events':events,'finished':finished},'remote agent servers need explicit conversation/workspace/event boundaries',finished if not fault else not finished)
```


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| OpenHands Software Agent SDK | `v1.24.0 @ fdc2bdf` | 围绕 Conversation、Agent、Tool、Workspace、Event 与 Agent Server 阅读，理解远程 workspace、interrupt、metrics/resume 的服务边界。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/OpenHands/software-agent-sdk) |
| OpenHands SDK architecture | `docs observed 2026-09-09` | Software Agent SDK / Agent Server / applications 分层。 | 以官方 docs/release/source tree 为准 | [官方来源](https://docs.openhands.dev/sdk/arch/overview) |
| SWE-bench | `benchmark source observed 2026-09-09` | 真实 GitHub issue + repository snapshot + Docker/test verifier。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/swe-bench/SWE-bench) |

### 源码阅读方法

源码阅读以 **OpenHands Software Agent SDK** 为第一参照，并只追与“OpenHands 与远程 Agent Server 架构”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“server 进程挂掉丢任务”、如何在“workspace 泄漏跨用户文件”后恢复，以及如何让 `server policy 独立配置` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| OpenHands Software Agent SDK | 贴近 coding/长期执行 harness，工作区和工具边界更真实 | 依赖更重或迭代快，升级需锁版本做回归 | Coding Agent、Harness 源码学习 |
| OpenHands SDK architecture | 贴近 coding/长期执行 harness，工作区和工具边界更真实 | 依赖更重或迭代快，升级需锁版本做回归 | Coding Agent、Harness 源码学习 |
| SWE-bench | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“OpenHands 与远程 Agent Server 架构”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“OpenHands 与远程 Agent Server 架构”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 22A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch22_openhands.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::openhands`
- `examples/chapters/ch22_openhands.py::main`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "remote agent servers need explicit conversation/workspace/event boundaries", "invariant_holds": true, "observation": {"events": [["conversation.created", "c1"], ["workspace.attached", "w1"], ["tool.started", "shell"], ["tool.finished", "0"]], "finished": true}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "openhands", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 22A](../../../labs/core/lab-22A-openhands.md)。

### Lab 22B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch22_openhands.py --fault
```

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L2_ORACLE_ONLY", "evidence_meaning": "external_oracle_observed_bad_outcome_only", "fault": true, "fault_injected": true, "invariant": "remote agent servers need explicit conversation/workspace/event boundaries", "invariant_holds": false, "observation": {"events": [["conversation.created", "c1"], ["workspace.attached", "w1"], ["tool.started", "shell"]], "finished": false}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "openhands", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L2_ORACLE_ONLY**：独立 oracle 观察到故障，但被测系统没有证明检测/约束/恢复。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 22B](../../../labs/core/lab-22B-openhands-fault.md)。

### 观察与证据


## 工程场景与系统设计

本章沿用第 20 章工程 Agent 负载，重点讨论远程 Agent Server 的 workspace 隔离、会话所有权与 2 CPU/4 GiB 资源上限。


### 上线前必须补齐

- 围绕 **OpenHands 与远程 Agent Server** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `远程 Agent 需要 conversation、workspace、event 和 server API 边界。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **server 进程挂掉丢任务**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **workspace 泄漏跨用户文件**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **事件状态 RUNNING 卡死**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `task success rate`
- `verifier pass rate`
- `tool steps/task`
- `workspace/sandbox violations`
- `artifact correctness`
- `wall-clock/cost per task`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Workspace` 的生命周期时，要重新验证 **remote agent servers need explicit conversation/workspace/event boundaries**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “server 进程挂掉丢任务”、“workspace 泄漏跨用户文件”、“事件状态 RUNNING 卡死”：只有正常路径与对应 fault path 都保持 **remote agent servers need explicit conversation/workspace/event boundaries**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- coding/browser/data/research agent 的 verifier 都依赖真实环境可观测性
- 远程 workspace 和 browser 状态可能漂移，不能只依赖模型记忆
- 自动修改代码或数据必须区分只读、可逆和不可逆动作
- benchmark 成功不能直接外推到组织私有环境

选择方案时要回到本章边界：如果业务不能接受“server 进程挂掉丢任务”，就必须为 `Agent Server` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Workspace` 决策交给模型，但要用 `server policy 独立配置` 保持结果可验证。**OpenHands Software Agent SDK** 与 **OpenHands SDK architecture** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

远程 Agent Server 能提供隔离与并行度，但也引入会话持久化、凭据托管和远程执行攻击面。生产部署需要把 sandbox、session ownership、artifact provenance 与网络出口策略同时纳入控制面。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)**：提出 reasoning/action 交错轨迹，连接语言推理与外部环境动作。
- **[Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)**：探索模型学习何时调用外部工具以及如何把工具结果纳入后续预测。
- **[OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)**（v1.24.0 @ fdc2bdf）：agents、tools、conversations、workspaces、events，支持 Agent Server。
- **[OpenHands SDK architecture](https://docs.openhands.dev/sdk/arch/overview)**（docs observed 2026-09-09）：Software Agent SDK / Agent Server / applications 分层。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- OpenHands Software Agent SDK（v1.24.0 @ fdc2bdf）：公开展示 Agent、workspace、event/runtime 等边界，适合对照远程执行服务的责任划分。
- OpenHands SDK architecture（docs observed 2026‑09‑09）：提供远程/本地 Agent 执行架构、event 与 workspace 设计的公开文档证据。

**本章吸收的变化。** Remote Agent Server 需要租约与有序事件来区分客户端断线、agent 运行和 workspace 生命周期。网络连接本身不能成为任务事实源。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Agent Server`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **remote agent servers need explicit conversation/workspace/event boundaries** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“server 进程挂掉丢任务”和“workspace 泄漏跨用户文件”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **OpenHands 与远程 Agent Server** 的可验证性。OpenHands Software Agent SDK 把 SDK、Agent Server、应用分层，适合讲 workspace 与远程执行。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Agent Server` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“server 进程挂掉丢任务”与“workspace 泄漏跨用户文件”同时发生时，**OpenHands Software Agent SDK** 与 **OpenHands SDK architecture** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Workspace` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“事件状态 RUNNING 卡死”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：OpenHands 与远程 Agent Server

本章重新审计后的核心结论是：**远程 Agent 需要 conversation、workspace、event 和 server API 边界。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[SWE-bench](https://github.com/swe-bench/SWE-bench)**：真实 GitHub issue + repo snapshot + test verifier，是 coding agent 评估基础。
- **[AIDev](https://arxiv.org/abs/2602.09185)**：以大规模 agent-authored PR 数据展示 coding agent 的真实软件工程影响。
- **[OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)**：提供 Conversation/Workspace/Event/Agent Server 公开边界。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。OpenHands SDK、Codex CLI、Pi 可比较本地 terminal harness 与远程 server harness。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证 OpenHands 与远程 Agent Server 的 workspace、verifier、artifact 或协作状态；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**remote agent servers need explicit conversation/workspace/event boundaries**；
2. `Agent Server` 必须是可观察软件边界，而不是 prompt 约定；
3. `API 与执行环境分离` 与 `server policy 独立配置` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- server 进程挂掉丢任务
- workspace 泄漏跨用户文件
- 事件状态 RUNNING 卡死

### 思考题与实践

- **Why：** 为什么 `Agent Server` 不能只靠模型“记住”？
- **What if：** 如果在 `API 与执行环境分离` 与 `server policy 独立配置` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch22_openhands.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **Browser / Computer Use Agent：观察、动作与环境验证**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
