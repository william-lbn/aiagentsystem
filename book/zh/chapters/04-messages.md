# Messages 与 Trajectory：Agent 的类型化事件语言

> **本章核心判断**：可恢复 Agent 的消息必须是带稳定身份和因果关系的类型化事件，不能退化为无约束的 role/content 字符串列表。

> 本章不把对话历史当作字符串数组，而把一次 Agent run 建模为带身份、因果与状态语义的 item ledger。事实窗口截至 **2026-09-11**。

![用户消息、工具调用、工具结果与最终响应通过稳定身份形成轨迹](../../assets/diagrams/04-messages-architecture.svg)

## 问题背景与学习目标

`[{role, content}]` 足以展示聊天，却不足以支撑并行工具、流式增量、崩溃恢复和审计。系统必须知道某个结果回答了哪一个调用、同一结果是否重复投递、最终响应产生时是否仍有未决调用，以及轨迹在序列化/反序列化后是否保持同一语义。

本章将建立 item algebra 与 append-only ledger；解释 message、tool call、tool result、event 和 state 的区别；保留 ReAct 的“行动—观察”价值而不依赖私有思维链；并通过 orphan tool result 证明因果身份断裂时系统不会推进。

## 核心概念与系统直觉

### 从 role 列表到判别联合

消息项可定义为判别联合：

$$
Item = UserMessage\;|\;AssistantMessage\;|\;ToolCall\;|\;ToolResult
$$

每个 item 有唯一 `item_id`；`ToolCall` 还产生稳定 `call_id` 和 tool name；`ToolResult` 必须引用同一个 `call_id` 与 name。`role` 只说明主体类别，不能替代 item kind 与因果身份。

### 轨迹是事件记录，不是当前状态

轨迹 $\tau=(i_1,\dots,i_n)$ 保存发生顺序；当前状态由 reducer 从轨迹派生。把状态字段反复写回历史 message，会造成多份真相。反之，只保存最终 state 又失去“为何到达这里”的证据。第 6 章将进一步讨论事件重放和 checkpoint。

### ReAct 的工程化解释

[ReAct](https://arxiv.org/abs/2210.03629) 把推理和行动交错，使环境观察能改变后续策略。工程实现应重点保留可观察边界：选择了哪个动作、参数为何被策略允许、环境返回什么、后置条件是否成立。模型内部隐藏推理不是稳定 API，也不是完成证明。

## 原理与理论基础

### 因果匹配与线性化

令 $Pending(\tau)$ 为已出现但尚未匹配结果的 call IDs。接受工具结果 $r$ 的前提为：

$$
Accept(r,\tau) \Leftrightarrow r.call\_id\in Pending(\tau)
\land r.name=Call(r.call\_id).name
$$

一个 call 只能完成一次；重复或孤儿结果均拒绝。若允许并行调用，结果的物理到达顺序可以变化，但每个结果仍必须关联调用。需要确定性重放时，可在原始到达序列之外保存逻辑序号或调度屏障。

### Append-only 与不变性

已接受 item 不应原地修改。修正通过追加 superseding/correction event 表达，从而使 digest 和审计可解释。append-only 不自动等于防篡改；还需要内容摘要、访问控制、保留策略和外部锚定。

### 最终响应门

> **Invariant**：every tool result must match exactly one unresolved call identity, and a normal final response requires an empty pending set

当 `Pending(τ) ≠ ∅` 时，普通最终 assistant message 不应被接受，因为仍存在未解析的外部动作。取消、超时或人工接管也必须先产生明确的终止事件，不能悄悄遗忘 pending call。

## 关键机制与执行流程

![正常调用按 call identity 闭合，孤儿结果被拒绝且 ledger 不变](../../assets/diagrams/04-messages-flow.svg)

正常轨迹为 user message → assistant tool call → matching tool result → assistant message。每次 append 都先校验 item ID、kind 与 actor，再更新 pending/completed 索引。只有校验成功才同时追加 ledger 并改变索引，避免“日志写入失败但内存状态已推进”。

流式 provider event 应在适配层组装成完整 canonical item：文本 delta 可以增量展示，工具参数 delta 只能缓存；当结束事件确认后才解码和持久化。provider response ID 应作为 provenance 保留，但本地 `item_id/call_id` 不应完全依赖提供方生命周期。

## 从原理到实现

### 原子地接受一个结果

```python
elif item.kind == "tool_result":
    if item.actor != "tool" or not item.call_id:
        errors.append("invalid_tool_result")
    elif item.call_id not in self._pending:
        errors.append("orphan_or_duplicate_tool_result")
    elif item.name != self._pending[item.call_id]:
        errors.append("tool_result_name_mismatch")

if not errors:
    self.items.append(item)
    self._item_ids.add(item.item_id)
```

先验证、后改变 ledger，是最小事务边界。生产实现还要把 ledger 与 pending 索引放入同一数据库事务或从 ledger 重建索引。

### 故障路径保持原状态

```python
ledger.append(MessageItem(
    "m2", "assistant_tool_call", "assistant",
    {"ticket_id": "INC-2048"}, "call-7", "read_ticket",
))
before = len(ledger.items)
result = ledger.append(MessageItem(
    "m3", "tool_result", "tool",
    {"status": "OPEN"}, "call-404", "read_ticket",
))

assert result.errors == ("orphan_or_duplicate_tool_result",)
assert len(ledger.items) == before
assert result.pending_calls == ("call-7",)
```

关键断点位于 duplicate item 检查、pending lookup、name match 和 final-with-pending gate。调试时同时观察 ledger 长度与 pending 集合，不能只看返回错误。

## 主流系统实现对照与源码阅读入口

[OpenAI Responses API](https://developers.openai.com/api/reference/cli/resources/responses/methods/create) 使用 input/output items 表达 message、function call 等结构，并支持 conversation 或 `previous_response_id` 关联；应用若需要跨提供方重放，仍应定义自己的 canonical envelope。[OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) 的 run items、handoff 与 trace 提供了更高层语义。

[LangGraph](https://github.com/langchain-ai/langgraph)、[Google ADK](https://github.com/google/adk-python) 与 [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) 都有 event/message/state 表示。源码阅读应从序列化模型入手：unknown item 怎样处理、tool result 如何关联、并行结果怎样排序、恢复后 provider ID 是否仍有效、schema version 是否写入持久层。

| 项目 | 本章源码入口 | 核查重点 |
|---|---|---|
| OpenAI Responses API | input/output item 类型 | function call/result identity 与增量完成边界 |
| OpenAI Agents SDK | run items、handoff、trace | SDK item 与 provider item 如何映射 |
| LangGraph / ADK / MAF | message、event、state serializer | 并行结果、未知类型与版本迁移 |
| AgentLab MessageLedger | append/pending/completed/digest | orphan、duplicate、name mismatch 是否原子拒绝 |

## 设计方案与方法对比

| 表示 | 优点 | 不足 |
|---|---|---|
| role/content 列表 | 直观、兼容聊天 | 因果与工具语义弱 |
| provider-native items | 能利用原生特性 | 跨提供方迁移受限 |
| canonical envelope + adapter | 可重放、可治理 | 需要维护映射与版本 |
| 事件日志 + 派生视图 | 审计与恢复最强 | 存储、迁移、隐私成本高 |

推荐持久层保存 canonical items 与必要 provider provenance；调用时由 adapter 生成提供方格式。不要把 provider SDK 对象直接 pickle 作为长期 checkpoint。

## 可复现实验

### 实验环境

Python `>=3.11,<3.14`，无网络、无 API key，macOS/Linux 与 `arm64/x86_64` 均可。实验运行真实 `MessageLedger.append`，不是字符串比较脚本；SHA-256 截断值只用于显示，完整 digest 仍由 ledger 计算。

### Lab 04A — 闭合工具轨迹

```bash
PYTHONPATH=src python3 examples/chapters/ch04_messages.py
```

实际输出为四次 append 全部接受、`ledger_size=4`、`pending_calls=[]`，并产生稳定 trajectory digest。验收要求工具结果与 `call-7/read_ticket` 精确匹配。[Lab 04A](../../../labs/core/lab-04A-messages.md)

### Lab 04B — 孤儿结果

```bash
PYTHONPATH=src python3 examples/chapters/ch04_messages.py --fault
```

实际输出应包含 `orphan_or_duplicate_tool_result`、`ledger_size=2`、`pending_calls=[call-7]`、`L3_CONTAINED`。验收要求错误结果没有进入 ledger，合法调用也没有被错误完成。[Lab 04B](../../../labs/core/lab-04B-messages-fault.md)

## 工程场景与系统设计

事故查询场景中，同一轮可能并发读取工单、监控和部署状态。每个调用需要独立 call ID；结果到达后由 fan-in 节点按 identity 合并，而不是按数组位置配对。若用户取消，只取消尚未提交的调用，并追加 cancel outcome；已经提交的外部副作用进入对账路径。

canonical envelope 至少应包括 schema version、run/turn/item/call identity、actor、kind、时间、payload、provenance、sensitivity 和 content digest。日志展示层可脱敏，但不能改变用于重放的结构语义。

## 故障模型、失败模式与排错

| 失败模式 | 后果 | 防线 |
|---|---|---|
| orphan result | 错误观测进入当前推理 | pending identity gate |
| duplicate result | 重复推进或重复计费 | completed-call set / idempotency |
| tool name mismatch | 结果被解释成错误类型 | call name binding |
| final with pending calls | 虚假完成 | terminal gate |
| stream 截断 | 半个 JSON 被执行 | 完整 item 边界 |
| schema 演进未迁移 | 老 run 无法恢复 | versioned decoder 与 migration |

排错顺序：按 run/sequence 重建 canonical ledger；验证 item/call 唯一性；对照 provider event；计算 digest；最后再检查模型为何选择该调用。自然语言 transcript 只能辅助，不能替代结构化轨迹。

## 性能、可靠性与工程化

追踪 append latency、pending age、orphan/duplicate rate、stream assembly failure、ledger bytes per run、replay duration 和 schema migration failure。大 payload 应内容寻址并外置，ledger 保存 digest 与授权引用；但外置对象生命周期必须长于可恢复窗口。

批量写入可提高吞吐，却扩大崩溃时未持久化窗口。高风险 intent 应优先同步持久化；低风险文本 delta 可以异步聚合。索引是可重建派生物，权威事件必须有明确持久化顺序。

## 技术边界与设计取舍

教材 ledger 是单进程内存实现，证明身份关联和 fail-closed 语义，不提供多写者一致性、加密、长期保留或隐私删除。SHA-256 digest 能检测内容变化，但没有签名和可信时间戳就不能证明是谁写入。

保存更多轨迹提高可调试性，也增加隐私、成本与攻击面。生产策略应最小化敏感正文，保留结构化 reason code 与哈希引用，并按数据分类实施 TTL 和访问审计。

## 前沿研究与演进方向

Agent 研究正在从最终答案转向 trajectory-level evaluation：不仅问是否成功，还问调用是否必要、顺序是否合理、是否越权、遇到不可解任务是否停止。[Agent Planning Benchmark](https://arxiv.org/abs/2606.04874) 中的损坏/多余工具正需要这种轨迹诊断。

开放问题包括：跨 provider/cross-agent 的通用 item algebra；流式、并行与重试下的因果一致性；如何在隐私删除后仍保持审计证明；如何评价同样完成任务但成本与风险不同的多条轨迹；如何让 trace 既足够解释又不暴露敏感推理。

### 深度审计与研究证据链：类型化轨迹

ReAct 提供行动—观察交错的研究依据，provider/framework item 模型提供工程对照，MessageLedger 的 append 结果和 digest 提供本地可证伪事实。因果关联被验证，不等于日志已获得签名、防篡改存储或跨进程一致性。

## 本章总结与进阶实践

消息不是字符串容器，而是 Agent 与模型、工具、用户之间的类型化事件语言。稳定 item/call identity、append-only 轨迹和 final gate 是并行、恢复与审计的共同基础。

进阶实践：加入两个并行工具调用，让结果逆序到达；证明 ledger 接受二者但 reducer 仍能生成确定的派生视图。随后重复投递一个结果，确认 ledger digest 与状态均不改变。

### 思考题与实践

1. `role=tool` 为什么不足以关联工具结果？
2. provider response ID 与本地 canonical item ID 各自解决什么问题？
3. 流式工具参数何时可以进入执行器？
4. append-only 是否天然防篡改？还缺哪些机制？
5. 在不保存私有思维链时，怎样构建足够的轨迹证据？

参考答案见[附录 G：第四章参考答案](../appendix-g-part1-solutions.html#part1-solutions-ch04)。
