# 模型基座：概率生成、结构化决策与工具调用边界

> **本章核心判断**：模型原生输出属于概率分布；只有通过语法、模式、语义与授权门的候选，才能成为可持久化的系统意图。

> 本章把模型视为不确定的决策部件，而不是可信执行器。事实窗口截至 **2026-09-11**；Core Lab 不调用任何模型服务，真实 OpenAI 调用应使用环境变量 `OPENAI_API_KEY`，不得把密钥写入代码、日志、fixture 或提交历史。

![模型候选输出必须依次通过语法、模式与语义安全门](../../assets/diagrams/02-model-substrate-architecture.svg)

## 问题背景与学习目标

大模型的原生接口是条件概率分布，不是类型安全的 RPC。即使服务端承诺结构化输出，也只能缩小“输出长什么样”的空间，不能证明工具存在、用户有权限、参数符合业务语义或副作用可重试。真正的 Agent 工程从这条边界开始。

本章要求读者理解 token 化、采样、上下文限制与 tool call 的关系；实现 syntax → schema → semantic 三层解码；区分可公开的决策证据与不应依赖的私有思维链；并用错误 JSON 类型证明不合法动作不会到达执行器。

## 核心概念与系统直觉

### 序列分布，而非事实数据库

自回归模型近似：

$$
p_\theta(y\mid x)=\prod_{i=1}^{n}p_\theta(y_i\mid x,y_{<i})
$$

token 是模型的离散计算单位，不等同于词、字符或业务字段。温度、top-p、随机种子和服务端实现会改变采样轨迹；即使温度为 0，也不应把跨版本、跨硬件、并行推理视为字节级确定。稳定系统因此验证**不变量与后置条件**，而不是期待复现完全相同的自然语言。

### Context window 不等于有效工作记忆

最大上下文长度只是接口容量上限。有效上下文还受位置、干扰、检索召回、指令冲突、token 化与任务结构影响。向窗口塞入更多材料可能提高覆盖，也可能降低相关证据的可辨识度。第 3 章将把上下文选择建模为受约束的信息配置问题。

### Structured output 是语法设施，不是授权设施

一个工具决定至少经历三层：

- **语法层**：字节能否解析为 JSON/typed item；
- **模式层**：discriminator、必填字段、额外字段、类型与取值域是否正确；
- **语义层**：工具是否在当前 capability set 中，参数对象是否属于当前租户，风险策略和预算是否允许。

通过前一层不蕴含后一层。尤其要拒绝静默类型转换：把字符串 `"30"` 自动转为整数 `30` 看似友好，却会隐藏提供方漂移和契约破坏。

### Tool call 是提议，不是调用

模型生成的 tool name 与 arguments 是候选意图。Runtime 需要重新查表、规范化、授权和落日志后才能调度。工具结果还必须与 call identity 关联；模型最终声称“已完成”也必须由外部 verifier 证实。

## 原理与理论基础

### 校准、选择性预测与弃权

模型信心并不天然校准，单个 `confidence=0.94` 不是 94% 成功保证。生产策略应基于离线/在线评测构建风险阈值，并允许系统弃权、询问或升级人工。选择性预测可写为：只在风险估计 $\hat r(x,a)\le \tau$ 时自动执行；高风险动作即使置信度高也仍需确定性授权。

### 类型系统只能描述可表达的约束

JSON Schema 可以表达字段、类型、枚举和局部关系，却很难单独表达“工单属于当前租户”“维护窗口与现网变更冻结不冲突”“此次动作已被正确审批”。因此 schema validator 与 policy engine 必须分层，错误也应标出发生在哪一层。

### 推理接口边界

[ReAct](https://arxiv.org/abs/2210.03629) 的核心贡献是把推理与环境行动交错，使新观察能修正后续步骤；这不意味着系统必须记录或暴露完整私有思维链。可审计系统应保存任务输入摘要、选定动作、结构化理由码、工具调用、观测、策略版本和 verifier 结果。隐藏推理可以变化，公共决策契约必须稳定。

本章不变量是：

> **Invariant**：a model-generated decision must pass syntax, schema, semantic, and authorization gates before dispatch

$$
Dispatch(d) \Rightarrow Parse(d)\land Schema(d)\land Semantic(d)\land Authorized(d)
$$

## 关键机制与执行流程

![错误类型在模式层被拒绝，合格决定仍需进入授权层](../../assets/diagrams/02-model-substrate-flow.svg)

推荐处理链：保留原始响应引用 → 解析 provider item → 检查 discriminator → 严格校验 schema → 解析领域对象 → capability/policy 判定 → 生成稳定 action intent → 调度。每一层产生机器可聚合的 reason code，避免所有失败都退化成 `invalid output`。

流式输出尤其不能边接收参数边执行。只有工具调用 item 完整、校验结束并被持久化后，执行面才能看到它。并行工具调用则要分别分配 call identity、独立授权和关联返回，不能把一批调用共享为一个布尔批准。

## 从原理到实现

### 严格的判别联合

```python
decoder = StrictDecisionDecoder(
    {"schedule_maintenance": {"service": str, "window_minutes": int}},
    min_confidence=0.70,
)
result = decoder.decode(payload)

if not result.accepted:
    audit(stage=result.stage, reason_codes=result.errors)
else:
    authorize_then_dispatch(result.decision)
```

实现中的 `kind` 是 discriminator：`final` 不能携带工具字段，`tool` 必须有对象参数；未知顶层字段和未知参数均拒绝。Python 中 `bool` 是 `int` 的子类，但 JSON 边界显式拒绝 `true` 充当整数，这是领域契约比语言便利规则更严格的例子。

### 故障输入不是 mock exception

```python
bad_payload = """{
  "kind": "tool",
  "tool": "schedule_maintenance",
  "arguments": {"service": "payments-api", "window_minutes": "30"},
  "confidence": 0.94
}"""

result = decoder.decode(bad_payload)
assert result.stage == "schema"
assert result.errors == ("argument_type:window_minutes:expected_int",)
assert result.accepted is False
```

关键断点设在 JSON parse、字段集合比较、参数类型检查、工具可用性检查和调度调用之前。实验 oracle 同时观察 `effect_dispatched=false`，防止验证器虽然报错、执行器却已旁路执行。

## 主流系统实现对照与源码阅读入口

[OpenAI Responses API 官方参考](https://developers.openai.com/api/reference/cli/resources/responses/methods/create) 把输入/输出表示为 items，支持自定义函数工具、结构化文本格式、并行工具调用以及与前序 response/conversation 的关联。它给出了提供方协议，但应用仍负责业务授权、工具执行和结果验证。[OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) 在更高层提供 agent loop、tool、guardrail、handoff、session 与 trace；阅读时应区分“SDK 帮你编排什么”和“你的环境保证了什么”。

其他框架也会提供 schema 生成或 typed tool 便利层。审计重点不在装饰器语法，而在：是否拒绝额外字段、是否会自动 coercion、provider schema 与本地函数签名如何保持一致、模型版本升级后 contract test 是否运行、校验失败是否可能触发 fallback 工具。

| 项目 | 本章源码入口 | 核查重点 |
|---|---|---|
| OpenAI Responses API | response input/output items 与 function tools | provider item 何时完整、usage/response identity 如何保留 |
| OpenAI Agents SDK | model/tool adapter 与 function schema | SDK 校验与应用授权的责任分界 |
| AgentLab StrictDecisionDecoder | syntax/schema/semantic gate | 拒绝 coercion、未知字段和缺失 capability |

## 设计方案与方法对比

| 输出策略 | 优点 | 主要风险 | 建议用途 |
|---|---|---|---|
| 自由文本后正则解析 | 接入快 | 歧义、注入、难演进 | 仅展示性文本 |
| JSON mode | 语法更稳定 | 未必符合领域 schema | 中间结构草案 |
| 严格 schema/tool item | 类型契约清晰 | 仍缺语义与授权 | 工具提议边界 |
| 有限状态/枚举决策 | 最易验证 | 表达能力较低 | 高风险控制节点 |

类型越严格，修复与版本迁移成本越显式；但这正是可治理系统需要付出的成本。容忍性解析适合人机界面，不适合副作用边界。

## 可复现实验

### 实验环境

Python `>=3.11,<3.14`，仅标准库和仓库代码；macOS/Linux、`arm64/x86_64` 均可。不需要 OpenAI key。若自行连接真实 OpenAI API，只从进程环境读取 `OPENAI_API_KEY`，并把 provider 模型快照、请求 ID、schema 摘要和运行时间记录为外部证据；不要提交 `.env`。

### Lab 02A — 合格的工具决定

```bash
PYTHONPATH=src python3 examples/chapters/ch02_model_substrate.py
```

实际输出应包含 `validation.accepted=true`、`stage=accepted` 与 `effect_dispatched=true`。验收标准是精确合同被接受，而非模型文本相似。[Lab 02A](../../../labs/core/lab-02A-model-substrate.md)

### Lab 02B — 字符串冒充整数

```bash
PYTHONPATH=src python3 examples/chapters/ch02_model_substrate.py --fault
```

实际输出必须出现 `argument_type:window_minutes:expected_int`，并保持 `effect_dispatched=false`、`evidence_level=L3_CONTAINED`。关键断点是 `StrictDecisionDecoder._is_type` 与返回前的 stage 选择。[Lab 02B](../../../labs/core/lab-02B-model-substrate-fault.md)

## 工程场景与系统设计

维护调度系统不应让模型直接写日历或集群。模型可以从事故上下文提出 `{service, window_minutes}`；领域层再补全服务 ID、时区、冻结窗口、租户和风险级别；策略层决定自动、人工审批或拒绝；执行层使用幂等键创建变更；验证层查询变更记录。由此，即使更换模型提供方，行动协议仍保持稳定。

模型升级需要 shadow evaluation：把同一代表性输入送给候选版本，只比较结构化决策、拒绝率、工具选择和风险后置条件，不执行候选写操作。上线用 canary 与回滚门，不能以几个对话样例替代分布评测。

## 故障模型、失败模式与排错

| 症状 | 根因候选 | 排错证据 |
|---|---|---|
| JSON 可解析但被拒 | 字段/类型/枚举漂移 | 原始 item、schema version、reason code |
| 工具名不存在 | provider hallucination 或目录不同步 | capability manifest 与工具注册摘要 |
| 参数合法却越权 | schema 只做形状校验 | identity、tenant、policy decision |
| 流式调用执行两次 | 未等 item 完整或 call identity 不稳 | stream event 序列与 journal |
| 高置信错误 | 信心未校准或分布漂移 | 分桶可靠性图与任务切片 |

解析失败后不要把原文本再次交给同一个模型无限“修 JSON”。应限制修复次数、保留原始与修复后的差异，并在高风险动作上拒绝自动修复语义字段。

## 性能、可靠性与工程化

应测量首 token 延迟、完整 decision 延迟、校验耗时、schema rejection rate、semantic rejection rate、tool-selection accuracy、abstention precision、每个 verified task 的 token/成本。并行生成可以降延迟，却会增加冲突、费用和选择偏差；推测执行仅适合可撤销纯读，不能越过授权提前做写操作。

可靠性来自 contract test 与分层故障，而不是单一平均成功率。每次 provider/model/schema 变更都应重放边界 corpus：截断 JSON、额外字段、Unicode、极值、布尔冒充整数、未知工具、跨租户对象和高风险参数。

## 技术边界与设计取舍

Core Lab 使用固定 payload，证明本地解码器的可重复语义，不评估任何真实模型生成这些 payload 的概率。官方 API 文档说明接口能力，不证明本仓库已进行外部请求；只有带运行时间、版本、请求摘要和可核验输出的 integration evidence 才能作此声明。

严格解码也不能发现所有语义欺骗。例如 `service="payments-api"` 类型正确，却可能指向错误环境；这需要目录解析、身份绑定和策略检查。不要把一个 validator 塑造成万能安全层。

## 前沿研究与演进方向

[Toolformer](https://arxiv.org/abs/2302.04761) 奠定了模型学习工具选择的研究路径；后续问题已转向大规模动态工具空间、工具检索、错误反馈、不可解任务识别和跨模态行动。到 2026 年，评测也开始主动引入损坏与多余工具，而不是假设工具目录永远正确。

开放问题包括：如何在 schema 演进时保持长期 run 可恢复；如何校准“调用/弃权”而非仅校准答案；如何验证模型对工具描述中的恶意内容保持指令隔离；如何让 provider-native structured output、MCP schema 和应用领域类型共享一个可审计的源，而不产生三套漂移合同。

### 深度审计与研究证据链：模型接口

官方 Responses 参考只支持“该接口具有这些 item/tool 字段”的文档事实；Toolformer/ReAct 支持模型工具使用的研究背景；Core Lab 的真实输出只支持 decoder 合同。三者分别对应 API、研究与本地机制层，不能合并成“真实模型端到端可靠”的强结论。

## 本章总结与进阶实践

模型输出是概率生成物，tool call 是候选意图，strict schema 是必要但不充分的边界。一个可执行决定必须经过语法、模式、语义与授权四道门，并留下足以重建选择过程的公共证据。

进阶实践：扩展 decoder 支持带版本的 discriminated union；加入 `schema_version`、取值上下界与 canonical arguments hash；建立旧版本迁移测试，并证明未知新字段默认 fail-closed。

### 思考题与实践

1. 为什么 temperature=0 仍不应被视为跨环境确定性保证？
2. JSON Schema 能证明什么，不能证明什么？
3. 设计一次 provider schema 与本地函数签名漂移的 contract test。
4. 为什么不应以私有思维链作为生产审计日志？应保存哪些替代证据？
5. 真实 OpenAI 实验怎样记录证据，才不与离线 Core Lab 混淆？

参考答案见[附录 G：第二章参考答案](../appendix-g-part1-solutions.html#part1-solutions-ch02)。
