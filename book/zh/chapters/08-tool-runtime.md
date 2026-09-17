# Tool Runtime：调度、权限、超时、重试与副作用语义

> **本章命题**：Tool Runtime 的首要任务不是“把函数调通”，而是在进程、网络或服务随时失效时，仍不把未知效果误判为失败并盲目重试。正确核心是 Intent、Effect Journal、幂等身份、UNKNOWN 和 reconciliation。

上一章定义了工具 ABI；本章把一次获准动作推进到真实外部效果，并给出崩溃与响应丢失时的恢复语义。

![Tool Runtime 的授权、执行、效果与对账边界](../../assets/diagrams/08-tool-runtime-architecture.svg)

## 问题背景与学习目标

远程写请求存在一个不可消除的时间窗：服务端已经提交，客户端却在收到响应前超时。若 Runtime 把 timeout 当成“未执行”并重试，支付、发信、建单或删除可能重复发生；若一律不重试，又会把真正未到达的请求永久丢失。这个问题不是更强模型可以推理解决的，因为模型看不到远端事实。

本章要求读者能够：

- 明确区分 `PREPARED/COMMITTED/NOT_APPLIED/UNKNOWN`；
- 在工具调用前持久化 canonical Intent，而不是事后补日志；
- 判断何时可 retry、何时必须 reconcile、何时需要 compensate；
- 用 action ID、idempotency key、args digest 与 receipt 连接本地和远端；
- 设计取消、deadline、bulkhead 与权限 scope，而不混淆 transport 和 effect。

## 核心概念与系统直觉

### Timeout 是观测缺失

Timeout 只说明调用方在 deadline 前没有收到可接受响应。它不证明远端未接收、未开始或未提交。因此写工具的 timeout 默认进入 UNKNOWN，而非 FAILED。

### 幂等键属于业务操作

重用 HTTP request ID 不一定防止重复业务效果。稳定 key 必须绑定 canonical action identity；服务端 ledger 对同一 key 返回同一 receipt，且需要定义 key 的保留窗口、作用域和参数冲突行为。

### Reconciliation 重新观察权威系统

对账不是“再调用一次写接口”，而是查询能够回答 effect 是否存在的权威账本。查询结果将 UNKNOWN 收敛到 COMMITTED 或 NOT_APPLIED。没有查询面时，系统只能暂停、升级人工或执行领域特定恢复流程。

### Compensation 不是回滚

外部世界通常不支持数据库式原子回滚。补偿是一项新的、有权限、有风险的动作，例如退款不是删除原支付。它需要自己的 Intent、receipt 和 verifier。

## 原理与理论基础

对一个 action $a$，本地知识状态为：

$$
K(a)\in\{PREPARED,COMMITTED,NOT\_APPLIED,UNKNOWN\}
$$

安全转移包括：

$$
PREPARED\rightarrow\{COMMITTED,NOT\_APPLIED,UNKNOWN\}
$$

$$
UNKNOWN\xrightarrow{reconcile}\{COMMITTED,NOT\_APPLIED\}
$$

不允许从 COMMITTED 返回 PREPARED，也不允许 UNKNOWN 在无新证据时直接标成 NOT_APPLIED。可重试条件应表达为：

$$
Retry(a) \iff K(a)=NOT\_APPLIED \lor (Idempotent(a)\land KeyValid(a))
$$

**不变量**：an ambiguous remote write must enter UNKNOWN and be reconciled before retry。

这与“exactly once delivery”不同。网络通常只能给 at-least-once 或 at-most-once 传递；业务层通过稳定身份、去重 ledger 和对账获得“单一可观察效果”。

## 关键机制与执行流程

![响应丢失后从 UNKNOWN 经权威 ledger 对账恢复](../../assets/diagrams/08-tool-runtime-flow.svg)

执行链如下：

1. 校验 args，并生成 `action_id`、`args_sha256`、`idempotency_key`；
2. 以 durable append 保存 PREPARED，确保崩溃恢复时知道“可能即将发生什么”；
3. 取得仅适用于该对象/动作的短期凭据并调用远端；
4. 收到可信 receipt，写 COMMITTED；明确拒绝且能证明未应用，写 NOT_APPLIED；
5. 连接断开、deadline、响应解析失败等模糊结果写 UNKNOWN；
6. reconciliation worker 查询远端 ledger，将 UNKNOWN 收敛；
7. verifier 检查业务后置条件，必要时创建新的 compensation action。

取消信号只取消仍可取消的本地等待；若远端可能已提交，取消后仍需对账。用户点击“停止”不等于外部世界自动回滚。

## 从原理到实现

`EffectController` 先核对 Intent 中的参数摘要，再持久化 PREPARED：

```python
def execute(self, intent, args, *, lose_reply=False):
    if sha256_json(args) != intent.args_sha256:
        raise ValueError("intent_args_digest_mismatch")
    self.journal.append(EffectRecord(EffectPhase.PREPARED, intent.action_id))
    try:
        receipt = self.remote.apply(intent, args, lose_reply=lose_reply)
    except TimeoutError as exc:
        record = EffectRecord(EffectPhase.UNKNOWN, intent.action_id, reason=str(exc))
    else:
        record = EffectRecord(EffectPhase.COMMITTED, intent.action_id, receipt=receipt)
    self.journal.append(record)
    return record
```

对账只接受当前状态为 UNKNOWN 的 action：

```python
def reconcile(self, intent):
    current = self.journal.latest(intent.action_id)
    if current is None or current.phase is not EffectPhase.UNKNOWN:
        raise ValueError("reconcile_requires_unknown")
    receipt = self.remote.lookup(intent.idempotency_key)
    phase = EffectPhase.COMMITTED if receipt else EffectPhase.NOT_APPLIED
    record = EffectRecord(phase, intent.action_id, receipt=receipt)
    self.journal.append(record)
    return record
```

故障实验的 remote ledger 确实先提交一条效果，再故意丢失 reply；它不是直接抛出一个发生在调用前的 mock exception。因此实验能够验证最危险的 “commit succeeded, acknowledgement lost” 窗口。

## 主流系统实现对照与源码阅读入口

| 系统层 | 常见机制 | 仍由应用决定的事项 |
|---|---|---|
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | tool loop、sessions、HITL、tracing | 业务幂等键、外部 receipt、对账接口 |
| Workflow/graph runtime | retry policy、checkpoint、interrupt | retry 是否会重复副作用；checkpoint 与外部 effect 的一致性 |
| 云任务队列 | visibility timeout、delivery attempts、dead letter | consumer 的 dedupe ledger 与业务提交边界 |
| MCP tool server | tool request/result transport | server 是否实现 effect identity、查询与 compensation |

不要把框架的“节点重放”误解为业务动作可重放。若节点内部调用支付 API，恢复引擎必须知道 effect phase，否则 deterministic replay 反而会稳定地产生重复效果。

## 设计方案与方法对比

| 方法 | 能回答的问题 | 不能保证 |
|---|---|---|
| 客户端重试 | 瞬时失败后再次发送 | 远端没有第一次提交 |
| 服务端幂等 ledger | 同 key 不新增效果 | 参数摘要正确、key 不碰撞 |
| Outbox/Inbox | 本地事务与消息发布协调 | 第三方 API 有可查询 receipt |
| Saga/补偿 | 跨服务失败后的业务修复 | 回到历史上完全相同状态 |
| 人工对账 | 处理无机器证据的例外 | 高吞吐、低延迟自动恢复 |

生产设计通常组合使用：Intent journal + idempotent endpoint + reconciliation query + verifier；任何单项都不足以覆盖全部窗口。

## 可复现实验

### 实验环境

本实验仅用 Python 标准库和 AgentLab，支持 arm64/x86_64，无网络、无 API key。SUT 是 `InMemoryEffectJournal`、`SimulatedRemoteLedger` 与 `EffectController`；remote 是可查询的确定性外部系统模型，不冒充真实云服务。

### Lab 08A：可确认提交

```bash
PYTHONPATH=src uv run python examples/chapters/ch08_tool_runtime.py
```

实际轨迹为 `PREPARED → COMMITTED`，`effect_count=1`，receipt 为 `rcpt-1`，证据等级 `L1_MECHANISM`。

### Lab 08B：提交后丢失响应

```bash
PYTHONPATH=src uv run python examples/chapters/ch08_tool_runtime.py --fault
```

实际轨迹为 `PREPARED → UNKNOWN → COMMITTED`；第一次观测是 UNKNOWN，对账命中远端 ledger，最终 `effect_count=1`，故为 `L4_RECOVERED`。这证明本地故障模型的恢复语义，不证明任意 SaaS 都提供可对账 API。完整实验见 [Lab 08A](../../../labs/core/lab-08A-tool-runtime.md) 与 [Lab 08B](../../../labs/core/lab-08B-tool-runtime-fault.md)。

### 关键断点与验收标准

**关键断点**：在 intent 摘要校验、`PREPARED` 持久化、远端 apply、`UNKNOWN` 记录和 reconciliation lookup 处观察，核对 journal 先于外部调用。**验收标准**：正常路径实际输出为一次 effect 和可查 receipt；丢回复后必须经 `UNKNOWN` 对账收敛，不得盲目重试，且 `effect_count=1`。

## 工程场景与系统设计

以支付提交为例，ActionIntent 应绑定付款对象、金额、币种、收款方、租户、审批版本和参数摘要。调用方在 PREPARED 后崩溃，恢复 worker 不能重新问模型“要不要再付一次”，而应以 idempotency key 查询支付方。若已提交则导入 receipt；若明确不存在才允许重新发送；若提供方不能回答则进入人工 exception queue。

调度层还需要每工具 concurrency limit、tenant quota、deadline budget、circuit breaker 和 bulkhead。读服务拥塞不能耗尽高风险写动作的对账 worker；reconciliation 通常应有独立优先级。

## 故障模型、失败模式与排错

- **发送前崩溃**：只有 PREPARED，无网络尝试证据；仍应查询或根据 transport evidence 判定。
- **提交后丢响应**：必须 UNKNOWN，最忌自动重试。
- **receipt 写盘前崩溃**：外部已提交，本地仍 PREPARED；按 action/key 对账。
- **key 重用但参数变化**：远端应拒绝并报告 digest conflict。
- **取消竞态**：取消到达时远端已提交，最终状态仍可为 COMMITTED。
- **对账读到副本延迟**：NOT_FOUND 不等于 NOT_APPLIED，需要 consistency/settling-window 合同。

排错时先画出时间线，逐条标明事实来源；不要用日志行顺序替代跨系统 happens-before。

## 性能、可靠性与工程化

关键指标包括：UNKNOWN rate、UNKNOWN age、reconciliation success/latency、duplicate-effect rate、idempotency conflict、receipt coverage、compensation rate、tool concurrency saturation 和 deadline exhaustion。最危险的指标不是普通 5xx，而是长时间未收敛的 UNKNOWN。

Journal 应 append-only、可索引并定期 compact，但 compaction 不能删除未终结 action。对账任务可批量化并指数退避；高价值动作可更积极查询。凭据和敏感 args 不写明文，日志保存 digest、对象引用和最小诊断字段。

## 技术边界与设计取舍

本章实验的远端 ledger 在同一进程中，因此没有真实网络、跨区域复制和第三方一致性延迟；证据上限是机制级 L4，而不是外部互操作 L5。真实验证要在 disposable sandbox/provider 上强制切断响应通道，再从真实 API 查询 receipt，并保存脱敏服务端证据。

使用 OpenAI 或本地模型只影响“何时提出工具调用”，不改变 effect protocol。模型 API key 必须来自环境变量；工具服务凭据应是另一个短期、最小权限 secret，二者不得混用或出现在 trace 中。

## 前沿研究与演进方向

长时 Agent 把传统分布式事务问题带回应用层：semantic transactions、可验证 effect receipts、跨工具 compensation planning 和 policy-aware replay 都是活跃方向。前沿系统需要同时建模模型不确定性与环境不确定性；仅增加 reasoning token 无法判断一个不可见的远端提交。

### 深度审计与研究证据链：恢复是新增证据，不是再推理一次

本章的结论建立在经典失败窗口、可执行状态机和真实提交后响应丢失注入上。框架源码只能证明它提供 checkpoint/retry 接口；只有远端 ledger 或业务 verifier 才能证明效果。将两者混写会夸大 durable execution 的能力。

## 本章总结与进阶实践

安全 Tool Runtime 将 timeout 解释为知识状态，而非业务状态。UNKNOWN 是诚实而必要的中间态；对账使它收敛，盲重试只会扩大风险。

进阶问题：

1. 为什么 TCP 连接断开不能证明请求未提交？
2. idempotency key 应绑定哪些字段，保留多久？
3. NOT_FOUND 在最终一致系统中为什么不等于 NOT_APPLIED？
4. 用户取消后为什么仍要运行 reconciliation？
5. compensation 与数据库 rollback 的语义差异是什么？

参考答案见[附录 H：第二篇问题参考答案](../appendix-h-part2-solutions.html#part2-solutions-ch08)。
