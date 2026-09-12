# Coding Agent 最小实现：读、改、测、验证

> **本章核心判断**：Coding Agent 是最适合学习 Agent Harness 的场景，因为读取、修改、测试和验证都有可执行证据。

上一章：Harness 与插件运行时：模型之外的系统能力如何组合。本章把前一章已经建立的能力进一步推进到 `Repo map`；下一章将进入：Codex、Pi 与 Claude Code 类 Harness 解剖。

![Coding Agent 最小实现：读、改、测、验证：系统边界与组件关系](../../assets/diagrams/20-coding-minimal-architecture.svg)

## 问题背景与学习目标

Coding Agent 是最适合学习 Agent Harness 的场景，因为读取、修改、测试和验证都有可执行证据。

在本章的 `Repo map` 场景中，真实 Agent 系统与普通“问答程序”的差异，在于一次任务会跨越模型、工具、状态、外部环境和人工治理边界。本章所有原理、代码与实验都围绕这些可验证问题展开。


**本章完成标准：**

- **机制理解**：能够解释“Coding Agent 是最适合学习 Agent Harness 的场景，因为读取、修改、测试和验证都有可执行证据。”，并指出它对应的确定性软件边界；
- **正确性判断**：能够针对 `a code change is complete only when an external verifier proves the requested behavior` 构造一个反例，说明证据不足时系统为什么不能继续乐观执行；
- **实验与迁移**：运行 `Lab 20A` / `Lab 20B`，分别说明 normal/fault 的 evidence level，并把同一机制映射到至少一个上游实现或协议。

## 核心概念与系统直觉

本节不把概念当作术语清单，而是回答三个工程问题：它**是什么**、在系统里**负责什么**、以及它失效时**会留下什么可观测证据**。

### Repo map

**定义。** Repo map 是对代码库结构、语言、构建入口、关键模块和依赖的任务相关压缩表示，帮助 Agent 在不读取所有文件的情况下建立导航模型。

**系统责任。** 生成 repo map 时应结合文件树、符号索引、测试和近期 diff；它是可刷新缓存而不是事实源。

**失败边界。** 过时 map 会让 Agent 编辑已移动代码；过大 map 又挤占 context。

### Patch

**定义。** Patch 是 Coding Agent 对仓库提出的最小可审查变更集，最好以 diff 表达并保留基线 commit。

**系统责任。** Runtime 应在 sandbox/worktree 中应用 patch，限制修改范围并记录每个文件 hash。

**失败边界。** 直接让 Agent 覆盖工作区且不保留 diff，会降低审查、回滚和 attribution 能力。

### Test

**定义。** Test 是对行为契约的可执行验证，不应只运行 Agent 自己新写的测试；需要现有回归、 目标测试和必要的静态检查。

**系统责任。** 测试选择可以由 Agent 建议，但最终 gate 应由 Runtime 固定执行，记录命令、版本和输出。

**失败边界。** 只运行“最相关测试”可能漏掉跨模块回归；只看 exit code 也可能忽略 skipped/xfail。

### Verifier

**定义。** Verifier 把“代码看起来合理”转换为可接受/拒绝的工程判断， 包括 tests、 lint、 typecheck、 build、security scan 和任务专用检查。

**系统责任。** 高级 verifier 可对 artifact 做黑盒行为测试或比较数据库/API 状态，且最好与生成 Agent 分离。

**失败边界。** 没有 verifier 的 Coding Agent 本质上只是高速代码生成器，不是可自治工程系统。

## 原理与理论基础

### 系统不变量

> **Invariant**：a code change is complete only when an external verifier proves the requested behavior

不变量与普通“最佳实践”不同：最佳实践可以因为场景变化而替换，不变量一旦被破坏，系统就失去本章希望保证的正确性。例如 `直接覆盖文件无 diff` 并不是一个 UI 问题，而是说明某个状态已经无法从证据中唯一判断。


### 故障模型

本章优先把 “直接覆盖文件无 diff”、“测试失败仍报告成功”、“上下文忽略错误日志” 作为可证伪故障，而不是泛化地枚举所有异常。对涉及外部 effect 的失败，判定顺序固定为“最后 durable state → effect 是否可能发生 → 现有 observation 是否足够决定下一步”；证据不足时停在 UNKNOWN/显式失败。

### Why / What if / Trade-off

本章真正的设计取舍不是“使用更强模型还是写更多规则”，而是确定 **Repo map** 与 **Patch** 分别应该由概率性决策还是确定性软件拥有。模型可以帮助识别候选路径，但它不会自动消除“直接覆盖文件无 diff”这类系统失败；该失败必须由 runtime 的 schema、状态机、权限或 verifier 显式约束。

如果把 Repo map 完全交给模型，系统会把不可验证的语言判断混入执行事实；如果把 Patch 全部硬编码为固定 workflow，又会失去开放任务所需的适应性。更稳健的边界是：让模型负责提出候选决策，让软件负责 `search/read/edit/shell 四工具`、`失败进入下一轮 context` 以及对不变量 **a code change is complete only when an external verifier proves the requested behavior** 的检查。

**What if。** 一旦“测试失败仍报告成功”发生，系统首先需要判断现有证据是否足够决定下一状态；证据不足时应停在显式失败或待协调状态，而不是让模型用自然语言补全事实。这个边界决定了本章方案是否具有可恢复性，而不只是演示效果。


### 形式化模型与可证伪假设

$$
AcceptPatch\iff Tests\land StaticChecks\land Scope\land DiffReview
$$

Coding Agent 的完成条件应是经验证的仓库 artifact，而不是模型“认为已经改好”。

**可证伪假设。** 将测试、静态检查、scope 和 diff review 作为接受门禁会降低 plausible-but-wrong patch。

**建议测量。** test pass、scope violations、rework rate、verified patch rate。

## 关键机制与执行流程

![Coding Agent 最小实现：读、改、测、验证：正常路径与故障恢复流程](../../assets/diagrams/20-coding-minimal-flow.svg)

**Step 1 — search/read/edit/shell 四工具。** `search/read/edit/shell 四工具` 是“Coding Agent 最小实现：读、改、测、验证”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Repo map` 是否仍满足 **a code change is complete only when an external verifier proves the requested behavior**。

**Step 2 — patch 产物可审计。** `patch 产物可审计` 是“Coding Agent 最小实现：读、改、测、验证”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Patch` 是否仍满足 **a code change is complete only when an external verifier proves the requested behavior**。

**Step 3 — 测试 stdout 保存。** `测试 stdout 保存` 把短暂执行状态转换为后续能够读取的证据。写入内容至少要能关联本次 run、前一状态与下一状态；对 crash-sensitive 数据，应明确写入完成的判据。若进程在写入期间终止，恢复代码必须能够区分“没有记录”“完整记录”和“损坏/不确定记录”，而不能把半写状态视作成功。

**Step 4 — 失败进入下一轮 context。** `失败进入下一轮 context` 是“Coding Agent 最小实现：读、改、测、验证”的一次显式状态转移。输入和输出都必须可序列化并关联 `run_id/step_id`；一旦该步骤失败，后继步骤只能依据已记录状态继续。关键观察点是 `Verifier` 是否仍满足 **a code change is complete only when an external verifier proves the requested behavior**。

在本章的 `Repo map` 场景中，**最后一步 — 验证。** verifier 针对 `Verifier` 检查本章不变量 **a code change is complete only when an external verifier proves the requested behavior**。如果“直接覆盖文件无 diff”使现有 artifact/外部状态不足以证明成功，结果必须停在显式失败或 UNKNOWN；只有 observation 能闭合状态转移时，流程才允许进入 FINISHED。

### 数据流与控制流

本章的数据/控制链按 **search/read/edit/shell 四工具 → patch 产物可审计 → 测试 stdout 保存 → 失败进入下一轮 context** 推进。调试时不要只看最终 answer，应确认每一阶段的输入来源、状态版本和 observation；对“直接覆盖文件无 diff”尤其要检查动作前后的证据是否足以闭合不变量 **a code change is complete only when an external verifier proves the requested behavior**。


### 持久化点与崩溃窗口

本章需要持久化的内容取决于动作可逆性。与 `Repo map` 有关的纯计算状态通常可以重算；一旦 `patch 产物可审计` 可能产生昂贵、外部或不可逆效果，就必须在动作前后建立可区分的证据边界。对于本章不变量 **a code change is complete only when an external verifier proves the requested behavior**，恢复时最重要的问题是：最后一个已知状态是什么、动作是否可能已经发生、现有 observation 能否唯一决定 retry/continue/compensate。


## 从原理到实现


### 完整实验入口

```python
from __future__ import annotations
import argparse
from agentlab.course_scenarios import run_scenario

def main() -> int:
 p=argparse.ArgumentParser(description='Coding Agent 最小实现：读、改、测、验证')
 p.add_argument("--fault", action="store_true", help="inject the chapter-specific failure path")
 args=p.parse_args()
 result=run_scenario('coding-minimal', fault=args.fault)
 print(result.as_json())
 return 0 if result.passed else 2

if __name__ == "__main__":
 raise SystemExit(main())
```

### 核心机制实现

```python
def coding_minimal(fault=False):
 root=Path(tempfile.mkdtemp(prefix='agentlab-code-')); f=root/'calc.py'; f.write_text('def add(a,b):\n return a-b\n',encoding='utf-8')
 original=f.read_text(); patched=original.replace('return a-b','return a+b' if not fault else 'return a*b'); f.write_text(patched)
 ns={}; exec(f.read_text(),ns); got=ns['add'](2,3); expected=5
 return _ok('coding-minimal',fault,{'file':str(f),'result':got,'diff':patched.strip()},'a code change is complete only when an external verifier proves the requested behavior',got==expected if not fault else got!=expected)
```


### 简化假设与不能省略的机制


## 主流系统实现对照与源码阅读入口

| 项目 | 本书锁定版本/状态 | 应阅读的机制 | 已核验源码/文档入口 | 官方来源 |
|---|---|---|---|---|
| SWE-bench | `benchmark source observed 2026-09-09` | 真实 GitHub issue + repository snapshot + Docker/test verifier。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/swe-bench/SWE-bench) |
| Pi Coding Agent | `@earendil-works/pi-coding-agent 0.85.1` | 把 session tree、branching、compaction、extensions/skills 看成极简 coding harness 的核心；同时注意 2026 年包名迁移到 @earendil-works。 | 以官方 docs/release/source tree 为准 | [官方来源](https://github.com/earendil-works/pi) |
| OpenAI Codex CLI | `0.139.0 historical reproducibility pin` | 从 Rust CLI 的 sandbox/approval/config 入口分析“模型建议动作”和“本地执行权限”如何分离；不要推断公开源码之外的托管服务。 | `codex-rs/utils/cli/src/shared_options.rs`<br>`codex-rs/core/config.schema.json` | [官方来源](https://github.com/openai/codex) |

### 源码阅读方法

源码阅读以 **SWE-bench** 为第一参照，并只追与“Coding Agent 最小实现：读、改、测、验证”直接相关的公开执行链：入口 → durable/session state → 权限或协议边界 → verifier/trace。若上游没有公开某个服务端组件，本章不根据客户端现象反推其内部 scheduler、queue 或 policy engine。


### 工业实现为什么更复杂


对本章最值得关注的工程增量是：如何避免“直接覆盖文件无 diff”、如何在“测试失败仍报告成功”后恢复，以及如何让 `失败进入下一轮 context` 的结果能够进入 tracing/evaluation。只有这些机制都能落到公开类型、函数或协议消息上，才算真正完成源码对照。

## 设计方案与方法对比

| 方案 | 核心优势 | 主要局限 | 更适合的约束 |
|---|---|---|---|
| 最小自研 AgentLab | 机制透明、可断点、无网络即可故障注入 | 生态/模型能力有限 | 教学、研究原型、回归基线 |
| SWE-bench | 官方/主流实现提供成熟抽象与生态 | 抽象会隐藏部分底层机制，需要源码/trace 反推 | 生产集成与方案对照 |
| Pi Coding Agent | 贴近 coding/长期执行 harness，工作区和工具边界更真实 | 依赖更重或迭代快，升级需锁版本做回归 | Coding Agent、Harness 源码学习 |
| OpenAI Codex CLI | 贴近 coding/长期执行 harness，工作区和工具边界更真实 | 依赖更重或迭代快，升级需锁版本做回归 | Coding Agent、Harness 源码学习 |


## 可复现实验

本章两个 Core Lab 都直接执行仓库内的确定性代码；它们证明的是“Coding Agent 最小实现：读、改、测、验证”对应的本地机制与 fault oracle，而不是外部 provider 或真实云环境。第三方实现只在 `labs/upstream/` 按独立 L5 互操作证据记录，未实际执行时必须保持 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

### 实验环境

统一 Python/OS/离线复现约束、安装步骤与工具链版本集中维护在[附录 A](../appendix-a-environment.md)。本章只增加与“Coding Agent 最小实现：读、改、测、验证”直接相关的 normal/fault 双轨验证；若需要真实云、浏览器、GPU 或第三方 provider，则在对应 upstream lab 中单独标记 `NOT_RUN_EXTERNAL`，不把未运行结果计入核心实验。

### Lab 20A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch20_coding_minimal.py
```

**关键断点：**
- `src/agentlab/course_scenarios.py::coding_minimal`
- `examples/chapters/ch20_coding_minimal.py::main`

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "a code change is complete only when an external verifier proves the requested behavior", "invariant_holds": true, "observation": {"diff": "def add(a,b):\n    return a+b", "file": "/tmp/agentlab-code-wgsx1zqq/calc.py", "result": 5}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "coding-minimal", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=false`、`invariant_holds=true`；这只证明确定性 fixture 的正常机制断言。完整手册：[Lab 20A](../../../labs/core/lab-20A-coding-minimal.md)。

### Lab 20B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch20_coding_minimal.py --fault
```

**本发布包实际输出：**

```json
{"contained": false, "evidence_level": "L2_ORACLE_ONLY", "evidence_meaning": "external_oracle_observed_bad_outcome_only", "fault": true, "fault_injected": true, "invariant": "a code change is complete only when an external verifier proves the requested behavior", "invariant_holds": false, "observation": {"diff": "def add(a,b):\n    return a*b", "file": "/tmp/agentlab-code-er4h9kkl/calc.py", "result": 6}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "coding-minimal", "system_detected": false}
```

PASS：退出码 0，`passed=true`、`fault=true`、`oracle_detected=true`。本章故障实验为 **L2_ORACLE_ONLY**：独立 oracle 观察到故障，但被测系统没有证明检测/约束/恢复。 `passed=true` 本身只表示实验 oracle 得到预期观察。完整手册：[Lab 20B](../../../labs/core/lab-20B-coding-minimal-fault.md)。

### 观察与证据


## 工程场景与系统设计

**教学工程设计输入（不是公开云厂商性能数据）：** 工程 Agent 在隔离 workspace 中完成真实任务并由外部测试/数据库/浏览器状态验证。设计输入：20 个并行 workspace、每任务 2 CPU/4 GiB、执行超时 20 分钟、禁止默认外网写操作。


### 上线前必须补齐

- 围绕 **最小 Coding Agent** 建立可审计状态字段与最小权限；
- 为本章相关动作记录 run_id、step_id、输入摘要与 observation；
- 对 `代码修改只有通过外部测试/verifier 才算完成。` 这一边界建立自动化验收；
- 为本章主要故障窗口配置 trace、日志和恢复 runbook；
- 上线前把教学 fixture 替换为真实 provider/tool/workspace，并重新执行 normal/fault 两条路径。

## 故障模型、失败模式与排错

本章至少主动测试以下失败：

- **直接覆盖文件无 diff**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **测试失败仍报告成功**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。
- **上下文忽略错误日志**：先确认最后 durable state，再检查是否已经产生外部效果；不要先重试。


## 性能、可靠性与工程化

### 应采集指标

- `task success rate`
- `verifier pass rate`
- `tool steps/task`
- `workspace/sandbox violations`
- `artifact correctness`
- `wall-clock/cost per task`


### 优化顺序


任何优化都必须重新运行 Lab A/B。尤其当优化改变 `Patch` 的生命周期时，要重新验证 **a code change is complete only when an external verifier proves the requested behavior**；否则平均延迟下降可能以更大的 stale state、重复副作用或取消失效为代价。

### 可靠性工程

本章可靠性 gate 直接针对 “直接覆盖文件无 diff”、“测试失败仍报告成功”、“上下文忽略错误日志”：只有正常路径与对应 fault path 都保持 **a code change is complete only when an external verifier proves the requested behavior**，优化或功能扩展才可接受。是否达到 detection、containment 或 recovery 以实验的 `evidence_level` 字段为准。


## 技术边界与设计取舍
本章方案有明确边界：

- coding/browser/data/research agent 的 verifier 都依赖真实环境可观测性
- 远程 workspace 和 browser 状态可能漂移，不能只依赖模型记忆
- 自动修改代码或数据必须区分只读、可逆和不可逆动作
- benchmark 成功不能直接外推到组织私有环境

选择方案时要回到本章边界：如果业务不能接受“直接覆盖文件无 diff”，就必须为 `Repo map` 增加更强的确定性约束；如果主要任务是开放式探索，则可以把更多 `Patch` 决策交给模型，但要用 `失败进入下一轮 context` 保持结果可验证。**SWE-bench** 与 **Pi Coding Agent** 的差异也应放在这些约束下理解，而不是抽象成通用框架排名。

最小 Coding Agent 适合解释读改测闭环，但不能代表开放仓库上的生产能力。真实场景还需要 workspace 隔离、依赖安全、增量验证、测试污染控制和对不可逆外部操作的审批。

## 前沿研究与演进方向

当前研究和工业演进已经从“模型能否调用工具”推进到“怎样让长期、状态化、具有副作用的 Agent 可评估、可恢复、可治理”。与本章直接相关的资料：

- **[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)**：提出 reasoning/action 交错轨迹，连接语言推理与外部环境动作。
- **[SWE-bench](https://github.com/swe-bench/SWE-bench)**（benchmark source observed 2026-09-09）：真实 GitHub issue + repository snapshot + Docker/test verifier。
- **[Pi Coding Agent](https://github.com/earendil-works/pi)**（@earendil-works/pi-coding-agent 0.85.1）：极简 terminal coding harness；extensions、skills、sessions、branching/compaction；旧 @mariozechner 包已弃用。


### 截至 2026-09-11 的研究更新

本节只记录会改变本章系统结论的研究或官方规范更新；实验仍使用仓库锁定版本，避免把“最新观察版本”与“可复现实验版本”混为一谈。
- OpenAI: Separating signal from noise in coding evaluations （2026‑07‑08）：benchmark validity, broken tasks and coding‑agent evaluation design。
- SWE‑bench（benchmark source observed 2026‑09‑09）：以真实仓库 issue/patch/test 为单位评估代码修改能力，同时也提醒我们最终 patch 必须回到可执行测试验证。

**本章吸收的变化。** Coding Agent 的“完成”必须落在仓库 diff 与可执行 verifier 上。最小闭环是 read→plan→patch→test→inspect，而不是生成代码文本。这些研究/规范的价值不在于替换本章原理，而在于把上述假设放进更真实、更长时或更高风险的环境中检验。

### Research Gap

围绕 `Repo map`，当前缺口不是“再增加一个 Agent API”，而是怎样把 **a code change is complete only when an external verifier proves the requested behavior** 从局部实现经验升级为跨模型、跨 runtime 可验证的系统属性。现有工业实现已经能够提供 tool loop、session、graph、plugin 或 workspace 等抽象，但在“直接覆盖文件无 diff”和“测试失败仍报告成功”同时出现时，证据格式、恢复语义和评测方法仍缺少统一答案。

本章的研究更新不追求论文数量，而关注一个问题：现有工作是否真正推进了 **最小 Coding Agent** 的可验证性。SWE-bench 证明真实 GitHub issue 需要 repo snapshot 和测试验证；AIDev 显示 coding agent 已进入真实 PR 生态。 因此，本章会把论文结论放回不变量、失败窗口和实验断言中，而不是把研究当作参考文献列表。

### Open Problems

1. 如何把 `Repo map` 的正确性拆成可组合的局部不变量，并在不同 Agent runtime 中复用 verifier？
2. 当“直接覆盖文件无 diff”与“测试失败仍报告成功”同时发生时，**SWE-bench** 与 **Pi Coding Agent** 的公开抽象分别能保存哪些证据，哪些状态仍需要外部 reconciliation？
3. 如果模型能力显著提高，围绕 `Patch` 的哪些 harness 机制仍属于系统必要条件，哪些只是当前模型能力下的临时补丁？
4. 如何构造一个既保护真实业务数据、又能复现“上下文忽略错误日志”的公开 benchmark，使研究结果可以被第三方验证？


### 深度审计与研究证据链：最小 Coding Agent

本章重新审计后的核心结论是：**代码修改只有通过外部测试/verifier 才算完成。** 这句话只有在代码、实验、开源源码和研究证据四个层面同时成立时才有教学价值。仅靠定义或 API 示例无法证明它，因为 Agent Systems 的风险通常发生在模型决策与外部环境之间的缝隙里。

**与本章最相关的近期/基础研究与官方资料：**

- **[SWE-bench](https://github.com/swe-bench/SWE-bench)**：真实 GitHub issue + repo snapshot + test verifier，是 coding agent 评估基础。
- **[AIDev](https://arxiv.org/abs/2602.09185)**：以大规模 agent-authored PR 数据展示 coding agent 的真实软件工程影响。
- **[OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)**：提供 Conversation/Workspace/Event/Agent Server 公开边界。

这些资料与本章的关系不是“引用背书”，而是帮助读者识别设计边界。mini-SWE-agent、Pi、Codex CLI、OpenHands 可逐层对照极简到生产 harness。 读者阅读源码时应主动寻找四个对象：输入如何进入系统、状态在哪里持久化、动作由谁执行、失败后谁负责恢复。

**实验语义边界。** 本章实验验证最小 Coding Agent 的 workspace、verifier、artifact 或协作状态；证据等级定义与解释规则统一见附录 A，且 `passed=true` 不得跨级推导 containment/recovery。


## 本章总结与进阶实践

### 核心结论

1. 本章不变量是：**a code change is complete only when an external verifier proves the requested behavior**；
2. `Repo map` 必须是可观察软件边界，而不是 prompt 约定；
3. `search/read/edit/shell 四工具` 与 `失败进入下一轮 context` 之间必须有状态和证据连接；
4. 模型提出动作不等于系统已经执行，更不等于任务成功；
5. 正常路径只能证明功能，故障路径才能暴露恢复语义；
6. 开源实现的核心价值在于理解真实约束，不是复制 API；
7. 性能优化必须与可靠性/安全不变量一起重新验证；
8. 技术边界和未解决问题是高级系统设计的一部分。

### 常见误区

- 直接覆盖文件无 diff
- 测试失败仍报告成功
- 上下文忽略错误日志

### 思考题与实践

- **Why：** 为什么 `Repo map` 不能只靠模型“记住”？
- **What if：** 如果在 `search/read/edit/shell 四工具` 与 `失败进入下一轮 context` 之间 crash，当前证据足够恢复吗？
- **Programming：** 修改 `examples/chapters/ch20_coding_minimal.py` 或对应 scenario，让系统新增一种错误类型，但仍保持 invariant。
- **Engineering：** 把 Lab B 的故障改成 timeout/duplicate/crash 中另一种，写出状态机和恢复步骤。
- **Research：** 选择本章一个 Open Problem，阅读两篇相互不同的方法，给出你自己的实验设计和 falsifiable hypothesis。

下一章进入 **Codex、Pi 与 Claude Code 类 Harness 解剖**，它将复用本章已经建立的状态/证据边界，而不是重新从 API 使用开始。
