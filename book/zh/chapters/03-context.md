# Context Engineering：把信息配置成受治理的运行时视图

> **本章核心判断**：Context 是 Runtime 在特定身份、状态与预算下构造的受治理视图，安全硬边界必须先于相关性优化。

> Context 不是聊天记录的别名，而是某一决策时刻对状态、证据、规则与能力的有损投影。本章事实窗口截至 **2026-09-11**，实验同时注入网页指令污染和跨租户记录。

![多来源信息经过信任、租户、时效与预算门后形成模型视图](../../assets/diagrams/03-context-architecture.svg)

## 问题背景与学习目标

模型看不到真实世界，只能看到 Runtime 配置给它的上下文。遗漏最新审批会让合法任务停滞；遗漏租户边界会造成数据泄漏；把网页内容放进 system channel 会把证据升级为指令；塞入全部历史又会挤掉当前目标。许多被归因于“模型不聪明”的失败，本质上是控制平面构造了错误视图。

本章把上下文组装定义为可审计的约束优化问题。读者将学会区分 instruction、state、evidence、memory 与 tool manifest；在 token 预算下保证强制记录；处理来源、租户、时效和不可信内容；并让压缩与缓存具有可失效、可追溯语义。

## 核心概念与系统直觉

### Context 是一次决策的物化视图

对时刻 $t$，上下文不是全局数据集 $D$，而是组装器产生的有序视图：

$$
C_t = Assemble(D_t, identity_t, policy_t, budget_t, task_t)
$$

同一条内容至少要携带 `record_id`、channel、source/provenance、tenant、freshness、authority、token cost 和生命周期。没有这些元数据，Runtime 无法判断它是否应进入当前决策。

### Channel 是能力，不只是排版

system/developer/user/evidence/history/tool result 在系统中具有不同权威。网页、邮件、代码注释和检索文档是**不可信数据**；即使它们写着“忽略之前的规则”，也不能被提升为指令 channel。安全目标不是让模型凭语义猜谁可信，而是让组装器在模型之前保持 data/instruction separation。

### 状态、记忆和上下文不是同一物

- **状态**是 Runtime 恢复所需的权威事实，如 phase、pending action 和版本；
- **记忆**是跨时段保留、可检索、可更新的信息资产；
- **上下文**是当前一步实际交给模型的有限视图；
- **轨迹**是事件序列，用于重放与评测。

把它们都塞进 messages，会失去所有权、更新语义与保留策略。

## 原理与理论基础

### 受约束的选择问题

令记录 $i$ 的 token 成本为 $c_i$，任务相关性、权威性、时效性与风险覆盖共同形成效用 $u_i$。可把可选记录选择近似为：

$$
\max_{x_i\in\{0,1\}} \sum_i u_i x_i,
\quad \text{s.t. }\sum_i c_i x_i\le B,
\quad x_j=1\ \forall j\in M,
\quad Trust(i)\land Tenant(i)
$$

$M$ 是必须出现的 policy/task 状态。真实效用不是独立可加的：两个片段可能冗余，也可能只有组合才有意义；所以教材实现采用可检查的启发式，而不声称求解了最优上下文。

### 信息瓶颈与位置效应

增加窗口大小不会消除选择问题。长输入会引入噪声、冲突与位置效应；工具结果还会随时间过期。上下文工程的目标不是最大化 token，而是在有限带宽中保留决策充分统计量，并显式记录被排除的内容和原因。

### 不变量

> **Invariant**：selected context must satisfy tenant and trust boundaries, retain mandatory state, and remain within budget

本章安全不变量为：

$$
Selected(i) \Rightarrow Tenant(i)=Tenant(run)
\land \neg(Untrusted(i)\land InstructionChannel(i))
$$

资源不变量为 $Tokens(C_t)\le B$；完备性要求所有 mandatory records 都被选入。如果强制记录本身超过预算，正确行为是失败并要求更大窗口或重构，而不是悄悄丢掉 policy。

## 关键机制与执行流程

![污染记录在模型调用前被隔离，剩余记录按预算和效用选择](../../assets/diagrams/03-context-flow.svg)

完整流水线包括：

1. 从请求、checkpoint、策略仓、检索器、工具观测和记忆仓读取候选记录；
2. 绑定 provenance、tenant、时间和内容类型，无法确定来源的记录降为不可信；
3. 在模型之前拒绝跨租户和不可信 instruction channel；
4. 先放入 mandatory policy/task/state，再在剩余预算中选择证据；
5. 去重、排序、标注引用和过期时间，生成 assembly manifest；
6. 模型调用后把实际使用的 manifest 摘要写入 trace；
7. 新观测到达或状态版本变化时，使相关缓存失效。

压缩必须输出“来源集合 + 摘要版本 + 覆盖范围 + 遗失风险”。摘要是衍生物，不应覆盖原始证据；对授权、金额、时间和否定词等高风险字段，最好保留结构化原值。

## 从原理到实现

### 先隔离，再排序

```python
for record in records:
    if record.tenant_id != tenant_id:
        excluded[record.record_id] = "tenant_mismatch"
    elif record.untrusted and record.channel in {"system", "developer", "user"}:
        excluded[record.record_id] = "untrusted_instruction_channel"
    elif record.token_cost <= 0:
        excluded[record.record_id] = "invalid_token_cost"
    else:
        candidates.append(record)
```

这段顺序很重要：安全过滤不能依赖相关性评分。恶意页面可以获得极高关键词相似度；如果先按相关性选 top-k 再过滤，污染记录仍可能挤掉合法证据。

### mandatory 与可选证据分开

```python
mandatory = sorted(
    (r for r in candidates if r.mandatory),
    key=lambda r: (-r.priority, r.record_id),
)
used = sum(r.token_cost for r in mandatory)
if used > budget:
    return ContextAssembly((), excluded, used, budget, False)

optional = sorted(
    (r for r in candidates if not r.mandatory),
    key=lambda r: (-(r.utility() / r.token_cost), -r.priority, r.record_id),
)
```

教材实现随后用稳定排序贪心选择，以便跨架构复现。生产版本可以使用学习排序或组合优化，但必须保留硬边界。关键断点设在 tenant/trust gate、mandatory budget 检查、排序 tie-break 和 manifest 生成处。

## 主流系统实现对照与源码阅读入口

现代模型 API、[OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)、[LangGraph](https://github.com/langchain-ai/langgraph)、[Google ADK](https://github.com/google/adk-python) 都提供某种 session/state/context 便利设施，但命名并不统一。阅读源码时要逐一追问：谁拥有权威状态？模型调用前哪一层决定 messages？tool result 是否原样回灌？checkpoint 恢复后是否重新验证 tenant/policy？压缩结果何时失效？

[Agent Memory as a System](https://arxiv.org/abs/2606.06448) 强调记忆不仅是存储与检索，还涉及形成、演化、治理和使用。对 Context Engineering 的启示是：读取记忆同样是一次有权限、有来源、有时间语义的数据访问，不能把向量相似度当授权。

| 项目 | 本章源码入口 | 核查重点 |
|---|---|---|
| OpenAI Agents SDK | session、run context、model input | state 与实际 model input 的映射位置 |
| LangGraph | state schema、checkpointer、interrupt | 恢复后 context 是否重新组装与鉴权 |
| Google ADK | session、event、runner | session 所有权、artifact 与 event 生命周期 |
| AgentLab ContextAssembler | record metadata 与 manifest | tenant/trust 硬过滤是否先于相关性排序 |

## 设计方案与方法对比

| 方法 | 可控性 | 主要收益 | 主要缺陷 |
|---|---:|---|---|
| 全历史拼接 | 低 | 简单、少基础设施 | 膨胀、污染、位置效应 |
| 固定窗口截断 | 中 | 成本可预测 | 可能截掉当前关键状态 |
| 检索 top-k | 中 | 扩展到大语料 | 相似不等于可信或新鲜 |
| 结构化分层组装 | 高 | 硬边界与证据清晰 | 元数据和治理成本高 |
| 学习型 context policy | 潜力高 | 适应任务分布 | 难解释、需防策略漂移 |

推荐基线是“结构化硬过滤 + 可解释排序 + 可选学习 reranker”。任何学习组件都不能决定租户隔离或把数据升级成指令。

## 可复现实验

### 实验环境

Python `>=3.11,<3.14`，macOS/Linux，支持 `arm64/x86_64`；无网络、无 API key。fixture 含 policy、当前任务、trace、runbook、旧历史；故障路径再加入网页注入和另一个租户的记录。token cost 是固定测试值，不冒充具体 tokenizer 计数。

### Lab 03A — 受预算约束的合法视图

```bash
PYTHONPATH=src python3 examples/chapters/ch03_context.py
```

实际输出应选择 `policy/task/trace/runbook`，使用 86/90 tokens，并以 `token_budget` 排除 `old-chat`。验收要求 mandatory 记录存在、预算不超限且 manifest 可解释。[Lab 03A](../../../labs/core/lab-03A-context.md)

### Lab 03B — 注入与跨租户双故障

```bash
PYTHONPATH=src python3 examples/chapters/ch03_context.py --fault
```

实际输出必须分别给出 `web-injection: untrusted_instruction_channel` 与 `other-tenant: tenant_mismatch`，两者均不在 selected，证据为 `L3_CONTAINED`。关键断点是 `ContextAssembler.assemble` 的前两个 gate。[Lab 03B](../../../labs/core/lab-03B-context-fault.md)

## 工程场景与系统设计

事故诊断 Agent 至少需要：当前 incident 目标、写操作策略、最近 trace、版本匹配的 runbook、工具能力和上一步未完成动作。网页搜索结果只能作为 evidence；另一个租户的相似事故即使相关也不得进入。工具执行后，新的 trace 会改变 freshness，旧的 context cache 必须按 state/policy/source version 联合失效。

Context manifest 应记录 selected/excluded record IDs、原因、source digest、版本、token budget 与实际 provider token usage。敏感正文可脱敏或外部保存，但元数据要足以复盘“模型当时看到了什么”。

## 故障模型、失败模式与排错

| 失败 | 机制 | 诊断 |
|---|---|---|
| 指令污染 | 不可信数据进入高权威 channel | 检查 source→channel 映射与 manifest |
| 跨租户泄漏 | 检索过滤在 rerank 后或未绑定身份 | 比较 run tenant 与每条记录 tenant |
| 陈旧状态 | cache key 缺 state/policy version | 重建失效链与 freshness |
| 关键事实丢失 | mandatory 未单独预算 | 检查 excluded reason 与 token 分配 |
| 摘要扭曲 | 衍生摘要覆盖原始证据 | 对照 source digest 与高风险字段 |

排错时不要只保存最终 prompt；还要保存候选集合、排除原因和排序分数。否则无法区分检索没找到、组装器丢掉、还是模型忽略了证据。

## 性能、可靠性与工程化

指标应覆盖 retrieval recall、context precision、mandatory coverage、cross-tenant rejection、untrusted-channel rejection、freshness violation、assembly latency、实际 token 和单位 verified task 成本。降低 token 不是孤立目标：若节省 20% 输入却使工具重试增加，端到端成本可能更高。

可靠性测试应包括边界预算、同分稳定排序、空检索、冲突 policy、多语言注入、超长工具返回、状态更新后的缓存失效和摘要回溯。线上抽样重放必须脱敏并固定 source versions。

## 技术边界与设计取舍

本章效用函数是教学启发式，不代表相关性的普适真值；固定 token cost 也不等同于 provider tokenizer。实验能够证明 tenant/trust/budget 控制流，却不能证明模型一定使用了所选证据，更不能证明对所有 prompt injection 鲁棒。

严格隔离会降低“利用一切信息”的表面能力，但它控制了数据泄漏和权限升级。必须通过拒绝率、人工升级率与任务成功率共同选择策略，而不是只优化单一 benchmark。

## 前沿研究与演进方向

长时程 Harness 研究正在把上下文问题从单次 prompt 扩展到跨任务状态管理。[Long-Horizon Agent Benchmark](https://arxiv.org/abs/2608.01964) 指向长期执行中环境、状态和验证的系统性挑战；记忆系统研究则进一步关注何时写、何时忘、如何治理以及如何评价记忆对策略的因果贡献。

开放问题包括：怎样学习 context policy 又不越过硬权限；怎样为摘要定义可量化的 loss budget；怎样在百万级工具/资源空间中联合检索能力与证据；怎样评价模型“没有使用”某条上下文；怎样使跨 Agent 传递的上下文保持来源、身份和授权链。

### 深度审计与研究证据链：上下文视图

本章把 source metadata、选择 manifest 和模型实际输入分成三个可审计对象。记忆/长时程论文说明研究方向，框架源码帮助定位组装边界，而注入/跨租户实验直接检验本地过滤器；它并不外推为对未知攻击的通用防御率。

## 本章总结与进阶实践

Context Engineering 的本质是构造受治理的决策视图。先做 trust/tenant 硬过滤，再保证 mandatory 状态，最后在预算中优化证据；每次组装都应产生可审计 manifest。

进阶实践可加入冲突检测：当两个同权威 policy 对同一动作给出矛盾规则时，组装器不选择其一，而是返回 `POLICY_CONFLICT` 并阻止模型调用；再用 property-based test 验证任意输入顺序下结果稳定。

### 思考题与实践

1. 为什么最大 context window 不能消除 Context Engineering？
2. 相关性、权威性、时效性与租户边界为何不能压成一个相似度分数？
3. mandatory context 超预算时，为何不应静默截断？
4. 如何证明摘要没有篡改金额、否定词和审批状态？
5. 设计一个同时测量任务质量与泄漏风险的 context ablation。

参考答案见[附录 G：第三章参考答案](../appendix-g-part1-solutions.html#part1-solutions-ch03)。
