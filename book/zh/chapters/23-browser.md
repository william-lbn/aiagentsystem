# Browser / Computer Use Agent：观察、动作与环境验证

> **本章核心判断**：浏览器 Agent 的核心是 observation/action space 与 verifier，而不是“能不能点按钮”。

上一章：OpenHands 与远程 Agent Server 架构。本章把前一章已经建立的能力进一步推进到 `DOM observation`；下一章将进入：Data Agent：SQL、Python 与可审计分析。

![Browser / Computer Use Agent：观察、动作与环境验证：系统边界与组件关系](../../assets/diagrams/23-browser-architecture.svg)

## 问题背景与学习目标

浏览器 Agent 的核心是 observation/action space 与 verifier，而不是“能不能点按钮”。

在本章的 `DOM observation` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“浏览器 Agent 的核心是 observation/action space 与 verifier，而不是“能不能点按钮”。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `computer-use actions must be grounded in the current observation before execution` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 23A` / `Lab 23B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### DOM observation

**定义。** 从 DOM、accessibility tree 或结构化页面状态读取可定位元素与语义的 observation。

**系统责任。** 结构化 observation 降低视觉定位成本，并为 selector、role、text 等目标提供可验证引用；同时要处理动态 DOM 与 stale element。

**失败边界。** 仅依赖 DOM 会看不到 canvas、图像或视觉遮挡；长期持有旧 node id 又会在页面变化后点击错误对象。

### Screenshot

**定义。** 页面在某一时刻的像素级视觉证据，适合处理布局、canvas、验证码外的视觉状态和 DOM 不可见信息。

**系统责任。** Screenshot 与 DOM 互补，用于 visual grounding、前后状态比较和人工审查；应绑定 viewport、time 与 page state。

**失败边界。** 截图本身不提供可靠语义或 provenance；模型“看见按钮”不代表按钮可点击，更不能证明后端 effect 已提交。

### Action space

**定义。** 浏览器 Agent 被允许执行的 click/type/scroll/navigate/upload/download 等动作集合及其参数约束。

**系统责任。** Action space 应受域名、元素类型、敏感字段、下载/上传策略与审批规则限制，并让每次动作可关联 observation。

**失败边界。** 动作空间过宽会把 prompt injection 直接转化为真实权限；过窄则迫使模型用脆弱的坐标技巧绕过安全边界。

### Verifier

**定义。** 通过 DOM、URL、网络状态、下载 artifact 或业务 API 判断浏览器任务是否真正达成目标的确定性检查器。

**系统责任。** Verifier 负责把“模型说已完成”转换成可观察条件，例如订单状态、文件 hash、表单确认页或后台对象。

**失败边界。** 仅以页面出现“Success”或模型最终回答作为成功判据，可能被前端假象、缓存、错误 tab 或注入文本欺骗。

## 原理与理论基础

### 系统不变量

> **Invariant**：computer-use actions must be grounded in the current observation before execution

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `网页变动导致实验漂移` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “网页变动导致实验漂移”、“截图 OCR 当唯一证据”、“点击成功却业务未完成” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **DOM observation** 与 **Screenshot** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“网页变动导致实验漂移”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 DOM observation 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Screenshot 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `离线 DOM fixtures`、`verifier 独立于模型` 以及对不变量 **computer-use actions must be grounded in the current observation before execution** 的检查。

**What if。** 一旦“截图 OCR 当唯一证据”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
b_{t+1}=Update(b_t,DOM_t,Pixels_t,Action_t)
$$

Browser/Computer Use 是部分可观测控制问题；DOM、视觉、焦点、网络状态只是对真实页面状态的观测。

**可证伪假设。** 融合 DOM+vision 并在动作后做 verifier，比单一视觉/单一 DOM 更能降低 wrong-target 与 silent failure。

**建议测量。** grounding accuracy、action success、post-action verification、recovery steps。

## 关键机制与执行流程

![Browser / Computer Use Agent：观察、动作与环境验证：正常路径与故障恢复流程](../../assets/diagrams/23-browser-flow.svg)

**Step 1 — 离线 DOM fixtures。** `离线 DOM fixtures` 是“Browser / Computer Use Agent：观察、动作与环境验证”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `DOM observation` 是否仍满足 **computer-use actions must be grounded in the current observation before execution**。

**Step 2 — 动作序列保存。** 这一阶段可能改变系统或外部环境，因此 `动作序列保存` 不能只存在于模型文本中。runtime 在执行前绑定 `run_id/step_id` 与参数摘要，执行后记录结果或外部 observation；如果调用可能重复，必须同时定义幂等键或 reconciliation 依据。这里检查的核心是 **computer-use actions must be grounded in the current observation before execution**。

**Step 3 — 环境 reset 明确。** `环境 reset 明确` 是“Browser / Computer Use Agent：观察、动作与环境验证”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Action space` 是否仍满足 **computer-use actions must be grounded in the current observation before execution**。

**Step 4 — verifier 独立于模型。** `verifier 独立于模型` 是“Browser / Computer Use Agent：观察、动作与环境验证”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Verifier` 是否仍满足 **computer-use actions must be grounded in the current observation before execution**。

在本章的 `DOM observation` 场景中，**最后一步 — 验证。** verifier 针对 `Verifier` 检查本章不变量 **computer-use actions must be grounded in the current observation before execution**。如果“网页变动导致实验漂移”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **离线 DOM fixtures → 动作序列保存 → 环境 reset 明确 → verifier 独立于模型** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“网页变动导致实验漂移”尤其要检查动作前后的证据是否足以闭合不变量 **computer-use actions must be grounded in the current observation before execution**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `DOM observation` 有关的纯计算状态通常可以重算；一旦 `动作序列保存` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **computer-use actions must be grounded in the current observation before execution**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Browser / Computer Use Agent：观察、动作与环境验证')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('browser', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def browser(fault=False):
 html='<button id="approve">Approve</button><div id="status">WAITING</div>'
 observation={'buttons':re.findall(r'<button id="([^"]+)">([^<]+)</button>',html),'status':'WAITING'}
 action={'type':'click','target':'approve' if not fault else 'missing'}
 targets={x[0] for x in observation['buttons']}; valid=action['target'] in targets
 return _ok('browser',fault,{'observation':observation,'action':action,'valid_target':valid},'computer-use actions must be grounded in the current observation before execution',valid if not fault else not valid)
```


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| OSWorld | `benchmark source observed 2026-09-09` | 真实计算机环境的 observation/action/evaluator。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/xlang-ai/OSWorld) |
| Anthropic: Building Effective Agents | `official engineering article` | 从简单、可组合的 workflow/agent 模式开始。 | 以官方 docs/release/source tree 为准 | [官方来源](https://www.anthropic.com/engineering/building-effective-agents) |
| OpenHands SDK architecture | `docs observed 2026-09-09` | Software Agent SDK / Agent Server / applications 分层。 | 以官方 docs/release/source tree 为准 | [官方来源](https://docs.openhands.dev/sdk/arch/overview) |

### 源码阅读方法

源码阅读以 **OSWorld** 为第一参照，并只追与“Browser / Computer Use Agent：观察、动作与环境验证”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“网页变动导致实验漂移”、如何在“截图 OCR 当唯一证据”后恢复，以及如何让 `verifier 独立于模型` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| OSWorld | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| Anthropic: Building Effective Agents | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| OpenHands SDK architecture | 贴近 coding/长期执行 harness，工作区和工具边界更真实 | 依赖更重或迭代快，升级需锁版本做回归 | Coding Agent、Harness 源码学习 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Browser / Computer Use Agent：观察、动作与环境验证”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Browser / Computer Use Agent：观察、动作与环境验证”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 23A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch23_browser.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::browser`
- `examples/chapters/ch23_browser.py::main`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "computer-use actions must be grounded in the current observation before execution", "invariant_holds": true, "observation": {"action": {"target": "approve", "type": "click"}, "observation": {"buttons": [["approve", "Approve"]], "status": "WAITING"}, "valid_target": true}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "browser", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 23A](../../../labs/core/lab-23A-browser.md)。

### Lab 23B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch23_browser.py --fault
```

**本发布包实际输出：**

```json
{"contained": true, "evidence_level": "L3_CONTAINED", "evidence_meaning": "fault_detected_and_contained", "fault": true, "fault_injected": true, "invariant": "computer-use actions must be grounded in the current observation before execution", "invariant_holds": true, "observation": {"action": {"target": "missing", "type": "click"}, "observation": {"buttons": [["approve", "Approve"]], "status": "WAITING"}, "valid_target": false}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "browser", "system_detected": true}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L3_CONTAINED**：被测组件检测并 fail-closed/约束了故障，但不声明已恢复业务结果。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 23B](../../../labs/core/lab-23B-browser-fault.md)。

### 观察与证据


## 工程场景与系统设计

本章沿用第 20 章工程 Agent 负载，重点把浏览器动作的 20 分钟 timeout、外网写禁令与页面 post-condition verifier 联系起来。


### 上线前必须补齐

- 围绕 **Browser / Computer Use** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `Browser Agent 的 observation/action 必须来自真实 DOM/截图/可访问树和环境验证。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **网页变动导致实验漂移**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **截图 OCR 当唯一证据**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **点击成功却业务未完成**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `task success rate`
- `verifier pass rate`
- `tool steps/task`
- `workspace/sandbox violations`
- `artifact correctness`
- `wall-clock/cost per task`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Screenshot` 的生命周期时，要重新验证 **computer-use actions must be grounded in the current observation before execution**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “网页变动导致实验漂移”、“截图 OCR 当唯一证据”、“点击成功却业务未完成”：只有正常路径与对应 fault path 都保持 **computer-use actions must be grounded in the current observation before execution**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- coding/browser/data/research agent 的 verifier 都依赖真实环境可观测性
- 远程 workspace 和 browser 状态可能漂移，不能只依赖模型记忆
- 自动修改代码或数据必须区分只读、可逆和不可逆动作
- benchmark 成功不能直接外推到组织私有环境

选择方案时要回到本章边界：如果业务不能接受“网页变动导致实验漂移”，就必须为 `DOM observation` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Screenshot` 决策交给模型，但要用 `verifier 独立于模型` 保持结果可验证。**OSWorld** 与 **Anthropic: Building Effective Agents** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

Browser/Computer Use 的视觉动作天然存在页面漂移和不可重放性。DOM/截图只能作为观察证据；支付、提交、删除等动作需要更强的 post-condition verification，不能靠“点击成功”推断业务完成。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[AgentBench: Evaluating LLMs as Agents](https://arxiv.org/abs/2308.03688)**：多环境 Agent benchmark，推动从答案评估转向交互任务评估。
- **[AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses](https://arxiv.org/abs/2406.13352)**：以工具返回内容中的 prompt injection 测试 Agent 安全边界。
- **[OSWorld](https://github.com/xlang-ai/OSWorld)**（benchmark source observed 2026-09-09）：真实计算机环境的 observation/action/evaluator。
- **[Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)**（official engineering article）：从简单、可组合的 workflow/agent 模式开始。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- OSWorld2.0: Benchmarking Computer Use Agents on Long‑Horizon Real‑World Tasks（arXiv 2606.29537; 2026‑06‑28）：long‑horizon computer use, hidden state, cross‑source reasoning, safety。
- OpenAI Computer‑Using Agent（2025‑01‑23; observed 2026-09-11）：computer‑use action space, OSWorld/WebArena/WebVoyager baseline and safety。
- OpenAI: Equipping the Responses API with a computer environment（2026‑03‑11）： computer environments, intermediate files, network access, timeouts and retries。 本章吸收的变化。 Browser/Computer‑use 是部分可观察环境：DOM 与像素提供不同 observation，Agent 必须维护对页面真实状态的 belief，并用 environment verifier 闭合任务。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

**本章吸收的变化。**

### Research Gap

围绕 `DOM observation`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **computer-use actions must be grounded in the current observation before execution** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“网页变动导致实验漂移”和“截图 OCR 当唯一证据”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **Browser / Computer Use** 的可验证性。OSWorld 与 BrowserGym 把浏览器/桌面任务转为 environment + evaluator，而不是只看最终回答。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `DOM observation` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“网页变动导致实验漂移”与“截图 OCR 当唯一证据”同时发生时，**OSWorld** 与 **Anthropic: Building Effective Agents** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Screenshot` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“点击成功却业务未完成”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：Browser / Computer Use

本章重新审计后的核心结论是：**Browser Agent 的 observation/action 必须来自真实 DOM/截图/可访问树和环境验证。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[SWE-bench](https://github.com/swe-bench/SWE-bench)**：真实 GitHub issue + repo snapshot + test verifier，是 coding agent 评估基础。
- **[AIDev](https://arxiv.org/abs/2602.09185)**：以大规模 agent-authored PR 数据展示 coding agent 的真实软件工程影响。
- **[OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)**：提供 Conversation/Workspace/Event/Agent Server 公开边界。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。browser-use、OSWorld、BrowserGym/OpenHands browser tools 可作对照。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证 Browser / Computer Use 的 workspace、verifier、artifact 或协作状态；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**computer-use actions must be grounded in the current observation before execution**；
2. `DOM observation` 必须是可观察软件边界，而不是 prompt 约定；
3. `离线 DOM fixtures` 与 `verifier 独立于模型` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 网页变动导致实验漂移
- 截图 OCR 当唯一证据
- 点击成功却业务未完成

### 思考题与实践

- **Why：** 为什么 `DOM observation` 不能只靠模型“记住”？
- **What if：** 如果在 `离线 DOM fixtures` 与 `verifier 独立于模型` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch23_browser.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **Data Agent：SQL、Python 与可审计分析**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
