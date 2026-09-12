# Checkpoint、Journal 与可恢复执行

> **本章核心判断**：Checkpoint 保存“现在在哪里”，Journal 保存“发生过什么”。二者结合才能解释崩溃后的恢复路径。

上一章：Sandbox 与权限：控制 Agent 的爆炸半径。本章把前一章已经建立的能力进一步推进到 `Snapshot`；下一章将进入：Harness 与插件运行时：模型之外的系统能力如何组合。

![Checkpoint、Journal 与可恢复执行：系统边界与组件关系](../../assets/diagrams/18-checkpoint-journal-architecture.svg)

## 问题背景与学习目标

Checkpoint 保存“现在在哪里”，Journal 保存“发生过什么”。二者结合才能解释崩溃后的恢复路径。

在本章的 `Snapshot` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“Checkpoint 保存“现在在哪里”，Journal 保存“发生过什么”。二者结合才能解释崩溃后的恢复路径。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `a checkpoint must be atomic and corruption must fail visibly` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 18A` / `Lab 18B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Snapshot

**定义。** Snapshot 是某时刻完整或足以恢复的状态映像，适合快速启动；它回答“现在状态是什么”。

**系统责任。** Snapshot 应带 schema/version/checksum，并与 event position 绑定；大状态可做增量或 copy‑on‑write。

**失败边界。** 只有 snapshot 没有事件历史时，很难解释状态为什么变成这样，也不利于审计。

### Event log

**定义。** Event log 按顺序记录导致状态变化的事实，回答“发生了什么”。它可以支持 replay、审计和重建派生状态。

**系统责任。** 事件应尽量 immutable，并拥有 sequence/id、actor、payload hash 和 causal link；不能把可变业务表当事件日志替代。

**失败边界。** 日志缺口或乱序会破坏 replay；因此需要 contiguous acknowledgement 或 gap detection。

### Atomic write

**定义。** Atomic write 保证 checkpoint/journal 更新不会暴露半写状态。实现可以依赖数据库事务、write‑temp+fsync+rename 或 WAL。

**系统责任。** 关键是定义 durable point：进程崩溃后哪些字节/记录一定存在，以及 ack 何时可以发送。

**失败边界。** “write() 返回成功”不一定等于持久化完成；对关键恢复状态应明确 fsync/commit 语义。

### Hash chain

**定义。** Hash chain 把事件内容与前一事件 hash 连接，用于检测离线篡改、缺失或重排；它提供完整性证据而不是保密。

**系统责任。** 可以按 segment 封存并把 root hash 写入独立存储/签名系统，以降低同一攻击者同时修改全部证据的风险。

**失败边界。** Hash chain 不能证明事件本身真实，只能证明记录之后没有悄悄改变；仍需可信 observation。

## 原理与理论基础

### 系统不变量

> **Invariant**：a checkpoint must be atomic and corruption must fail visibly

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `只做 checkpoint 不记 effect` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “只做 checkpoint 不记 effect”、“写一半 checkpoint 损坏”、“崩溃后不知道请求是否发出” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Snapshot** 与 **Event log** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“只做 checkpoint 不记 effect”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Snapshot 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Event log 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `先写 intent 再执行 effect`、`恢复时重放到一致状态` 以及对不变量 **a checkpoint must be atomic and corruption must fail visibly** 的检查。

**What if。** 一旦“写一半 checkpoint 损坏”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
S_n=Fold(S_0,E_1,\ldots,E_n),\qquad Checkpoint_k=Snapshot(S_k,seq=k)
$$

Checkpoint 加速恢复，Journal/Event Log 提供因果历史；两者需要 sequence/integrity 约束才能识别截断与半写。

**可证伪假设。** 带 CRC/sequence 的 journal + checkpoint 能检测 silent truncation，并保持 crash recovery 的状态等价性。

**建议测量。** recovery equivalence、corruption detection、replay length、RPO/RTO。

## 关键机制与执行流程

![Checkpoint、Journal 与可恢复执行：正常路径与故障恢复流程](../../assets/diagrams/18-checkpoint-journal-flow.svg)

**Step 1 — 先写 intent 再执行 effect。** 这一阶段可能改变系统或外部环境，因此 `先写 intent 再执行 effect` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **a checkpoint must be atomic and corruption must fail visibly**。

**Step 2 — checkpoint 原子替换。** `checkpoint 原子替换` 把短暂执行状态转换为后续能够读取的证据。写入内容至少要能关联本次 run、前一状态与下一状态；对 crash-sensitive 数据，应明确写入完成的判据。若进程在写入期间终止，恢复代码必须能够区分“没有记录”“完整记录”和“损坏/不确定记录”，而不能把半写状态视作成功。

**Step 3 — journal fsync/hash。** `journal fsync/hash` 把短暂执行状态转换为后续能够读取的证据。写入内容至少要能关联本次 run、前一状态与下一状态；对 crash-sensitive 数据，应明确写入完成的判据。若进程在写入期间终止，恢复代码必须能够区分“没有记录”“完整记录”和“损坏/不确定记录”，而不能把半写状态视作成功。

**Step 4 — 恢复时重放到一致状态。** `恢复时重放到一致状态` 是“Checkpoint、Journal 与可恢复执行”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Hash chain` 是否仍满足 **a checkpoint must be atomic and corruption must fail visibly**。

在本章的 `Snapshot` 场景中，**最后一步 — 验证。** verifier 针对 `Hash chain` 检查本章不变量 **a checkpoint must be atomic and corruption must fail visibly**。如果“只做 checkpoint 不记 effect”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **先写 intent 再执行 effect → checkpoint 原子替换 → journal fsync/hash → 恢复时重放到一致状态** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“只做 checkpoint 不记 effect”尤其要检查动作前后的证据是否足以闭合不变量 **a checkpoint must be atomic and corruption must fail visibly**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Snapshot` 有关的纯计算状态通常可以重算；一旦 `checkpoint 原子替换` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **a checkpoint must be atomic and corruption must fail visibly**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Checkpoint、Journal 与可恢复执行')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('checkpoint', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def checkpoint(fault=False):
 d=Path(tempfile.mkdtemp(prefix='agentlab-cp-')); p=d/'checkpoint.json'; store=JsonCheckpointStore(p); store.save('r1',{'status':'RUNNING','step':2})
 if fault: p.write_text('{broken',encoding='utf-8')
 try: loaded=store.load(); ok=loaded['state']['step']==2
 except Exception as e: loaded={'error':type(e).__name__}; ok=False
 return _ok('checkpoint',fault,{'loaded':loaded},'a checkpoint must be atomic and corruption must fail visibly',ok if not fault else not ok)
```

这一版的 durable primitive 同时修了两个旧边界。`JsonCheckpointStore` 按 `run_id` 建立独立 snapshot，版本单调递增并支持 expected-version CAS；写入顺序是 temp file → `fsync(file)` → atomic replace → `fsync(parent directory)`，并以进程锁串行化本机 writer。`EffectJournal` 每次 append 前重新读取并验证完整 hash chain；已有 malformed/tampered history 时直接 `JournalCorruptionError`，绝不在损坏历史上继续追加。

这些机制只覆盖单机文件语义：它们**不是**跨主机 consensus、lease/fencing 或数据库 WAL。多实例生产部署应替换为具有明确并发、持久化与故障模型的外部 store。


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| LangGraph | `langgraph==1.2.11 @ 644815f` | 从 StateGraph/CompiledGraph 与 checkpointer 语义入手，观察 node/edge/state/pending writes 如何支持 interrupt、resume 与 fault tolerance。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/langchain-ai/langgraph) |
| Microsoft Agent Framework checkpoints | `docs observed 2026-09-09` | checkpoint 捕获 executor states、pending messages/requests、shared state，用于 resume。 | 以官方 docs/release/source tree 为准 | [官方来源](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints) |
| Pi Coding Agent | `@earendil-works/pi-coding-agent 0.85.1` | 把 session tree、branching、compaction、extensions/skills 看成极简 coding harness 的核心；同时注意 2026 年包名迁移到 @earendil-works。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/earendil-works/pi) |

### 源码阅读方法

源码阅读以 **LangGraph** 为第一参照，并只追与“Checkpoint、Journal 与可恢复执行”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“只做 checkpoint 不记 effect”、如何在“写一半 checkpoint 损坏”后恢复，以及如何让 `恢复时重放到一致状态` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| LangGraph | 状态/工作流抽象成熟，适合长任务与治理 | 框架状态不能自动解决外部副作用不确定性 | 企业 workflow、HITL、durable orchestration |
| Microsoft Agent Framework checkpoints | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| Pi Coding Agent | 贴近 coding/长期执行 harness，工作区和工具边界更真实 | 依赖更重或迭代快，升级需锁版本做回归 | Coding Agent、Harness 源码学习 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Checkpoint、Journal 与可恢复执行”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Checkpoint、Journal 与可恢复执行”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 18A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch18_checkpoint_journal.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::checkpoint`
- `examples/chapters/ch18_checkpoint_journal.py::main`
- `src/agentlab/runtime.py::AgentRuntime.run`
- `src/agentlab/tools.py::ToolRegistry.execute`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "a checkpoint must be atomic and corruption must fail visibly", "invariant_holds": true, "observation": {"loaded": {"run_id": "r1", "state": {"status": "RUNNING", "step": 2}, "version": 1}}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "checkpoint", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 18A](../../../labs/core/lab-18A-checkpoint-journal.md)。

### Lab 18B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch18_checkpoint_journal.py --fault
```

**本发布包实际输出：**

```json
{"contained": true, "evidence_level": "L3_CONTAINED", "evidence_meaning": "fault_detected_and_contained", "fault": true, "fault_injected": true, "invariant": "a checkpoint must be atomic and corruption must fail visibly", "invariant_holds": true, "observation": {"loaded": {"error": "CheckpointCorruptionError"}}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "checkpoint", "system_detected": true}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L3_CONTAINED**：被测组件检测并 fail-closed/约束了故障，但不声明已恢复业务结果。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 18B](../../../labs/core/lab-18B-checkpoint-journal-fault.md)。

### 观察与证据


## 工程场景与系统设计

本章沿用第 14 章长任务场景，重点把“一次已确认状态变化”的 RPO 解释为本地 durable state，而不是远端 effect exactly-once 保证。


### 上线前必须补齐

- 围绕 **Checkpoint 与 Journal** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `checkpoint 记录状态，journal 记录事件；二者不能混淆，也不能证明外部副作用必然 exactly-once。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **只做 checkpoint 不记 effect**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **写一半 checkpoint 损坏**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **崩溃后不知道请求是否发出**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `run p95 latency`
- `checkpoint fsync latency`
- `resume success rate`
- `cancellation tail latency`
- `approval wait time`
- `UNKNOWN reconciliation time`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Event log` 的生命周期时，要重新验证 **a checkpoint must be atomic and corruption must fail visibly**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “只做 checkpoint 不记 effect”、“写一半 checkpoint 损坏”、“崩溃后不知道请求是否发出”：只有正常路径与对应 fault path 都保持 **a checkpoint must be atomic and corruption must fail visibly**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- checkpoint 只能恢复已持久化状态，不能凭空知道外部副作用是否成功
- sandbox 限制本地执行边界，不自动限制所有网络/云权限
- HITL 提高安全性但增加延迟和运营成本
- 并发提升吞吐但放大竞态、预算和取消复杂度

选择方案时要回到本章边界：如果业务不能接受“只做 checkpoint 不记 effect”，就必须为 `Snapshot` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Event log` 决策交给模型，但要用 `恢复时重放到一致状态` 保持结果可验证。**LangGraph** 与 **Microsoft Agent Framework checkpoints** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

Checkpoint 解决本地执行状态恢复，Journal 提供追加式证据；二者都不能单独证明远端副作用 exactly-once。持久化链损坏应 fail-closed，恢复到 EXECUTING/UNKNOWN effect 时应先观察外部状态再决定补偿或重试。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)**：提出 reasoning/action 交错轨迹，连接语言推理与外部环境动作。
- **[Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)**：探索模型学习何时调用外部工具以及如何把工具结果纳入后续预测。
- **[LangGraph](https://github.com/langchain-ai/langgraph)**（langgraph==1.2.11 @ 644815f）：状态图、durable execution、checkpointer、HITL、pending writes/fault tolerance。
- **[Microsoft Agent Framework checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)**（docs observed 2026-09-09）：checkpoint 捕获 executor states、pending messages/requests、shared state，用于 resume。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- Semantic Transactions for Tool‑Using LLM Agents（arXiv 2606.17573; observed 2026‑09‑10）：tool‑runtime, checkpoint/journal, effect‑recovery。
- LongHorizon‑Harness（arXiv 2608.01964; observed 2026‑09‑10）：context, planning, state, long‑running harness。

**本章吸收的变化。** Event log 提供可解释历史， checkpoint 缩短恢复； 二者要有 sequence/version， 才能处理 partial write、duplicate 和 corruption。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Snapshot`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **a checkpoint must be atomic and corruption must fail visibly** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“只做 checkpoint 不记 effect”和“写一半 checkpoint 损坏”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **Checkpoint 与 Journal** 的可验证性。Semantic Transactions 与分布式系统 exactly-once 经验都支持本章结论：可靠性来自持久化意图、幂等键和 reconciliation。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Snapshot` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“只做 checkpoint 不记 effect”与“写一半 checkpoint 损坏”同时发生时，**LangGraph** 与 **Microsoft Agent Framework checkpoints** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Event log` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“崩溃后不知道请求是否发出”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：Checkpoint 与 Journal

本章重新审计后的核心结论是：**checkpoint 记录状态，journal 记录事件；二者不能混淆，也不能证明外部副作用必然 exactly-once。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[Semantic Transactions for Tool-Using LLM Agents](https://arxiv.org/abs/2606.17573)**：把不可逆工具副作用抽象成语义事务，支撑 UNKNOWN、staging 与 validation 讨论。
- **[OpenAI Agents SDK](https://github.com/openai/openai-agents-python)**：提供 Agent/Runner/Tools/HITL/Tracing/Sessions 的公开实现边界。
- **[Microsoft Agent Framework Checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)**：把 checkpoint 定义为 workflow resume 所需的 executor state、pending messages/requests 与 shared state。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。LangGraph checkpointer、MAF checkpoint、OpenAI durable integrations、AgentLab EffectJournal 可形成对照。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证 Checkpoint 与 Journal 在 normal/fault 两条路径下是否进入可解释状态；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**a checkpoint must be atomic and corruption must fail visibly**；
2. `Snapshot` 必须是可观察软件边界，而不是 prompt 约定；
3. `先写 intent 再执行 effect` 与 `恢复时重放到一致状态` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 只做 checkpoint 不记 effect
- 写一半 checkpoint 损坏
- 崩溃后不知道请求是否发出

### 思考题与实践

- **Why：** 为什么 `Snapshot` 不能只靠模型“记住”？
- **What if：** 如果在 `先写 intent 再执行 effect` 与 `恢复时重放到一致状态` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch18_checkpoint_journal.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **Harness 与插件运行时：模型之外的系统能力如何组合**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
