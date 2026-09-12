# Post-training 与 Agent 能力塑形

> **本章核心判断**：Agent 不只靠 prompt；SFT、distillation、RL 和 tool-use training 可以改变模型对工具、计划和错误的行为。

上一章：部署工程：Docker、本地开发与 CI 验证。本章把前一章已经建立的能力进一步推进到 `Dataset`；下一章将进入：多模态、语音、机器人与实时 Agent。

![Post-training 与 Agent 能力塑形：系统边界与组件关系](../../assets/diagrams/37-post-training-architecture.svg)

## 问题背景与学习目标

Agent 不只靠 prompt；SFT、distillation、RL 和 tool-use training 可以改变模型对工具、计划和错误的行为。

在本章的 `Dataset` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“Agent 不只靠 prompt；SFT、distillation、RL 和 tool-use training 可以改变模型对工具、计划和错误的行为。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `post-training evaluation must prevent task leakage between training and held-out evaluation` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 37A` / `Lab 37B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Dataset

**定义。** 用于 SFT/RL/偏好训练的任务、输入、轨迹、verifier 与 outcome 集合，质量比“对话数量”更重要。

**系统责任。** Agent dataset 要保存环境版本和行为结果，区分 expert demonstration、失败轨迹、纠正和 synthetic data。

**失败边界。** 仅收集漂亮最终回答会训练出会叙述但不会执行的模型；数据泄漏 benchmark 还会虚增能力。

### Trajectory

**定义。** 训练时包含 observation、reasoning/decision、tool call、environment feedback 和最终 outcome 的序列。

**系统责任。** Trajectory 让 credit assignment 可以定位工具选择与恢复步骤；敏感 CoT 可用结构化 action/state 替代直接存储。

**失败边界。** 长轨迹只给最终 reward 会让训练信号极稀疏；错误中间 observation 若未标注会强化坏策略。

### SFT

**定义。** 用高质量示范最大化目标行为 token/动作似然，适合学习格式、工具语法和稳定策略先验。

**系统责任。** SFT 是行为初始化而非完整优化：示范应覆盖拒绝、恢复和坏工具，而不只是成功路径。

**失败边界。** 过度模仿固定 harness 会降低新环境适应性；示范本身有错误时会被高置信复制。

### RL/Preference

**定义。** 依据环境 reward、verifier 或人类/模型偏好进一步优化长期策略。

**系统责任。** Agentic RL 的关键是可交互环境、可靠 reward 与 credit assignment；应同时惩罚成本、风险和无效工具调用。

**失败边界。** reward 可被 hack，偏好 judge 也会偏置；若训练环境过窄，策略会学到 benchmark exploit 而非通用能力。

## 原理与理论基础

### 系统不变量

> **Invariant**：post-training evaluation must prevent task leakage between training and held-out evaluation

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `用生成数据自我强化幻觉` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “用生成数据自我强化幻觉”、“只看训练 loss 不看任务成功”、“训练数据泄漏 benchmark” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Dataset** 与 **Trajectory** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“用生成数据自我强化幻觉”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Dataset 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Trajectory 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `保存成功/失败轨迹`、`训练后用独立 eval 防回归` 以及对不变量 **post-training evaluation must prevent task leakage between training and held-out evaluation** 的检查。

**What if。** 一旦“只看训练 loss 不看任务成功”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
J(\pi)=\mathbb{E}[R_{task}-\lambda_c C-\lambda_r Risk+\sum_t\alpha_t r_t]
$$

Agentic post-training 同时受任务奖励、成本、风险与长时信用分配影响，环境和 verifier 的质量决定训练上限。

**可证伪假设。** 在长时工具任务中，turn-aware/process credit 相比只用终局 reward 能提高学习稳定性。

**建议测量。** sample efficiency、credit variance、tool-use success、risk-adjusted return。

## 关键机制与执行流程

![Post-training 与 Agent 能力塑形：正常路径与故障恢复流程](../../assets/diagrams/37-post-training-flow.svg)

**Step 1 — 保存成功/失败轨迹。** `保存成功/失败轨迹` 把短暂执行状态转换为后续能够读取的证据。写入内容至少要能关联本次 run、前一状态与下一状态；对 crash-sensitive 数据，应明确写入完成的判据。若进程在写入期间终止，恢复代码必须能够区分“没有记录”“完整记录”和“损坏/不确定记录”，而不能把半写状态视作成功。

**Step 2 — 数据含工具调用和 verifier。** 这一阶段可能改变系统或外部环境，因此 `数据含工具调用和 verifier` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **post-training evaluation must prevent task leakage between training and held-out evaluation**。

**Step 3 — 小模型先蒸馏规则任务。** `小模型先蒸馏规则任务` 是“Post-training 与 Agent 能力塑形”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `SFT` 是否仍满足 **post-training evaluation must prevent task leakage between training and held-out evaluation**。

**Step 4 — 训练后用独立 eval 防回归。** `训练后用独立 eval 防回归` 是“Post-training 与 Agent 能力塑形”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `RL/Preference` 是否仍满足 **post-training evaluation must prevent task leakage between training and held-out evaluation**。

在本章的 `Dataset` 场景中，**最后一步 — 验证。** verifier 针对 `RL/Preference` 检查本章不变量 **post-training evaluation must prevent task leakage between training and held-out evaluation**。如果“用生成数据自我强化幻觉”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **保存成功/失败轨迹 → 数据含工具调用和 verifier → 小模型先蒸馏规则任务 → 训练后用独立 eval 防回归** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“用生成数据自我强化幻觉”尤其要检查动作前后的证据是否足以闭合不变量 **post-training evaluation must prevent task leakage between training and held-out evaluation**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Dataset` 有关的纯计算状态通常可以重算；一旦 `数据含工具调用和 verifier` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **post-training evaluation must prevent task leakage between training and held-out evaluation**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Post-training 与 Agent 能力塑形')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('post-training', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def post_training(fault=False):
 samples=[{'task':'t1','split':'train','trajectory':'good'},{'task':'t2','split':'eval','trajectory':'bad'}]
 if fault: samples.append({'task':'t2','split':'train','trajectory':'copied eval'})
 train={x['task'] for x in samples if x['split']=='train'}; ev={x['task'] for x in samples if x['split']=='eval'}; leak=bool(train&ev)
 return _ok('post-training',fault,{'samples':samples,'leakage':sorted(train&ev)},'post-training evaluation must prevent task leakage between training and held-out evaluation',not leak if not fault else leak)
```


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| bojieli/ai-agent-book | `main; 10 chapters / 109 experiments observed 2026-09-09` | 对标开源教材：正文、实验 ledger、PDF/EPUB、多语言。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/bojieli/ai-agent-book) |
| OpenAI MLE-bench | `2024 benchmark` | 75 个 Kaggle-style ML engineering competitions。 | 以官方 docs/release/source tree 为准 | [官方来源](https://openai.com/index/mle-bench/) |
| OpenAI PaperBench | `2025 benchmark` | 论文复现任务与细粒度 rubric/grader。 | 以官方 docs/release/source tree 为准 | [官方来源](https://openai.com/index/paperbench/) |

### 源码阅读方法

源码阅读以 **bojieli/ai-agent-book** 为第一参照，并只追与“Post-training 与 Agent 能力塑形”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“用生成数据自我强化幻觉”、如何在“只看训练 loss 不看任务成功”后恢复，以及如何让 `训练后用独立 eval 防回归` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| bojieli/ai-agent-book | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| OpenAI MLE-bench | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| OpenAI PaperBench | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Post-training 与 Agent 能力塑形”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Post-training 与 Agent 能力塑形”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 37A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch37_post_training.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::post_training`
- `examples/chapters/ch37_post_training.py::main`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "post-training evaluation must prevent task leakage between training and held-out evaluation", "invariant_holds": true, "observation": {"leakage": [], "samples": [{"split": "train", "task": "t1", "trajectory": "good"}, {"split": "eval", "task": "t2", "trajectory": "bad"}]}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "post-training", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 37A](../../../labs/core/lab-37A-post-training.md)。

### Lab 37B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch37_post_training.py --fault
```

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L2_ORACLE_ONLY", "evidence_meaning": "external_oracle_observed_bad_outcome_only", "fault": true, "fault_injected": true, "invariant": "post-training evaluation must prevent task leakage between training and held-out evaluation", "invariant_holds": false, "observation": {"leakage": ["t2"], "samples": [{"split": "train", "task": "t1", "trajectory": "good"}, {"split": "eval", "task": "t2", "trajectory": "bad"}, {"split": "train", "task": "t2", "trajectory": "copied eval"}]}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "post-training", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L2_ORACLE_ONLY**：独立 oracle 观察到故障，但被测系统没有证明检测/约束/恢复。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 37B](../../../labs/core/lab-37B-post-training-fault.md)。

### 观察与证据


## 工程场景与系统设计

本章沿用第 35 章多租户 API 场景，重点说明训练/微调产物如何经过独立 eval 和回滚 gate 后才能影响 30 个租户。


### 上线前必须补齐

- 围绕 **Post-training** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `训练改变能力分布，必须通过独立 eval gate 防止 tool use/security 回归。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **用生成数据自我强化幻觉**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **只看训练 loss 不看任务成功**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **训练数据泄漏 benchmark**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `API p95/p99`
- `tenant isolation violations`
- `queue depth`
- `RPO/RTO rehearsal`
- `deployment rollback time`
- `cost per tenant/run`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Trajectory` 的生命周期时，要重新验证 **post-training evaluation must prevent task leakage between training and held-out evaluation**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “用生成数据自我强化幻觉”、“只看训练 loss 不看任务成功”、“训练数据泄漏 benchmark”：只有正常路径与对应 fault path 都保持 **post-training evaluation must prevent task leakage between training and held-out evaluation**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- 教学服务不等于生产认证系统，HA、secret broker、审计保留等需额外实现
- 多租户必须在存储/缓存/日志/队列每层强制 tenant boundary
- 部署成功不代表恢复成功，需定期做故障演练
- post-training 会改变行为分布，必须用独立 eval gate 防回归

选择方案时要回到本章边界：如果业务不能接受“用生成数据自我强化幻觉”，就必须为 `Dataset` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Trajectory` 决策交给模型，但要用 `训练后用独立 eval 防回归` 保持结果可验证。**bojieli/ai-agent-book** 与 **OpenAI MLE-bench** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

Post-training 可以塑造工具使用策略，却不能训练出不存在的权限或事务保证。训练数据中的成功轨迹、环境版本与 verifier 偏差会被模型学习，因此数据 provenance 和独立 evaluation 是能力提升的前提。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761)**：探索模型学习何时调用外部工具以及如何把工具结果纳入后续预测。
- **[Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)**：通过外部反馈与语言化反思把失败经验写入后续尝试。
- **[bojieli/ai-agent-book](https://github.com/bojieli/ai-agent-book)**（main; 10 chapters / 109 experiments observed 2026-09-09）：对标开源教材：正文、实验 ledger、PDF/EPUB、多语言。
- **[OpenAI MLE-bench](https://openai.com/index/mle-bench/)**（2024 benchmark）：75 个 Kaggle-style ML engineering competitions。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- ToolVerse: Massive Environments and Long‑Horizon Tasks for Agentic RL（arXiv 2607.15660; 2026‑07‑17）：agentic RL, ~400 MCPs, ~4500 tools, long‑horizon credit assignment。
- OpenAI: Research acceleration —the view inside OpenAI（2026‑09‑06）：parallel coding agents, research task horizons, human intervention and research velocity。

**本章吸收的变化。** Agentic post‑training 把优化对象从最终答案扩展到长轨迹决策。环境、 verifier 和 credit assignment 与模型本身同等重要。这些研究/规范的价值不在于替换本章原理， 而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Dataset`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **post-training evaluation must prevent task leakage between training and held-out evaluation** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“用生成数据自我强化幻觉”和“只看训练 loss 不看任务成功”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **Post-training** 的可验证性。Toolformer、RL/tool-use training 与近期 agent post-training 工作说明，模型能力塑形不能替代 Runtime 约束。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Dataset` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“用生成数据自我强化幻觉”与“只看训练 loss 不看任务成功”同时发生时，**bojieli/ai-agent-book** 与 **OpenAI MLE-bench** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Trajectory` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“训练数据泄漏 benchmark”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：Post-training

本章重新审计后的核心结论是：**训练改变能力分布，必须通过独立 eval gate 防止 tool use/security 回归。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[PaperBench](https://openai.com/index/paperbench/)**：把论文复现拆成细粒度可评分任务，强调 rubric/grader。
- **[AgentDojo](https://arxiv.org/abs/2406.13352)**：用不可信工具返回内容测试 prompt injection 攻防。
- **[Agent Security Bench](https://arxiv.org/abs/2410.02644)**：覆盖多工具、多场景、多攻击/防御的 Agent 安全评测。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。OpenAI/DeepSeek/TRL/verl 等训练栈可作为能力塑形对照，核心仍是实验边界。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证 Post-training 的观测、评测、安全或生产控制面不变量；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**post-training evaluation must prevent task leakage between training and held-out evaluation**；
2. `Dataset` 必须是可观察软件边界，而不是 prompt 约定；
3. `保存成功/失败轨迹` 与 `训练后用独立 eval 防回归` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 用生成数据自我强化幻觉
- 只看训练 loss 不看任务成功
- 训练数据泄漏 benchmark

### 思考题与实践

- **Why：** 为什么 `Dataset` 不能只靠模型“记住”？
- **What if：** 如果在 `保存成功/失败轨迹` 与 `训练后用独立 eval 防回归` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch37_post_training.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **多模态、语音、机器人与实时 Agent**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
