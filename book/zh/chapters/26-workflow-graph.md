# Graph Runtime：LangGraph / ADK / MAF 的共同抽象

> **本章命题**：Graph Runtime 的价值不是把流程画成图，而是把 state、node、edge、interrupt、checkpoint、effect 与 topology identity 变成可持久化和可验证的执行语义。Checkpoint 只证明保存了状态，不自动证明外部副作用 exactly-once。

前五章的专项 Agent 都需要长期编排。本章给出 provider-neutral graph 核心，并结合仓库已有的 LangGraph、Google ADK 和 Microsoft Agent Framework 跨进程证据，严格区分三者不同的 durability surface。

![Graph Runtime 的状态、节点、检查点、效果与验证平面](../../assets/diagrams/26-workflow-graph-architecture.svg)

## 问题背景与学习目标

隐式 `while` loop 容易把状态藏在 prompt 和调用栈中；图可以显式表达分支、并行、审批与恢复。然而，如果节点修改外部系统后进程崩溃，单纯恢复 checkpoint 仍可能重复 effect；如果部署了新图，却用旧 checkpoint 恢复，node index 甚至可能指向完全不同的动作。

读者应能定义 typed state、node contract、deterministic edge、interrupt/resume、checkpoint CAS、pending write、topology signature 和 effect journal；能比较 LangGraph、ADK、MAF 的不同持久化保证；能运行关闭/重开 SQLite 的恢复实验并阻断改变拓扑后的旧状态。

## 核心概念与系统直觉

**State** 是可序列化的权威运行数据；**node** 是从输入 state 到新 state/events 的执行单元；**edge** 决定下一节点；**interrupt** 在 durable point 暂停等待外部输入；**checkpointer** 保存 state/version；**effect protocol** 管理不可重算的外部动作。

节点“尽量纯”不是要求 Agent 不使用工具，而是把 effect 放在显式 adapter 中：写 intent，执行带 idempotency key 的 action，记录 receipt，必要时 reconcile。这样 replay node 时可识别哪些计算能重做，哪些动作必须查询外部世界。

Topology identity 将 graph definition、node version 与 schema version 纳入恢复条件。仅保存 `current_node=3` 极其脆弱；部署后节点顺序变化会让旧状态跳到错误动作。

## 原理与理论基础

纯状态转移可写为 (S_{t+1}=N_i(S_t))，边为 (i_{t+1}=E(S_{t+1}))。加入外部 effect 后，应拆成：

$$
(S_t,intent)\xrightarrow{commit}C_t,
\quad C_t\xrightarrow{effect}receipt,
\quad (C_t,receipt)\xrightarrow{reconcile}S_{t+1}.
$$

Crash 可以发生在三条箭头之间。没有 intent/receipt 时，checkpoint 无法区分“没执行”和“执行了但未记录”。

> **Invariant**: graph recovery binds persisted state version, topology identity and effect key; prompt memory is never a checkpoint.

同时恢复必须使用 CAS/版本检查，防止两个 worker 从同一 checkpoint 并发推进。Graph correctness 包含 safety（不走非法边、不重复危险 effect）和 liveness（在公平调度/有限重试下能到终态）。

## 关键机制与执行流程

![Graph Runtime 从 checkpoint、跨实例恢复到拓扑拒绝的流程](../../assets/diagrams/26-workflow-graph-flow.svg)

1. 编译 graph，计算 topology/schema signature，校验 unreachable/cycle/terminal；
2. 创建 run，写入初始 typed state、node pointer、version 和 signature；
3. node 读取 state，产生 state delta、events 和可选 effect intent；
4. checkpointer 以 expected version/CAS 提交，冲突者停止；
5. effect executor 使用稳定 effect key，保存 receipt 或 UNKNOWN；
6. interrupt 持久化待决 action 与 resume schema，然后释放 worker；
7. 新进程按 run/thread ID 读取 checkpoint，核验 signature 后继续；
8. verifier 只在终态条件和外部 observation 闭合时写 FINISHED。

对于并行 fan-out/fan-in，还要定义 reducer 是否交换/结合、partial failure 怎样表示、pending writes 如何提交。把多个分支结果直接覆盖同一 dict key 会使 replay 顺序影响结果。

## 从原理到实现

`DurableGraph` 用 SQLite 保存 graph signature、node index、version 和 state；`apply` 节点把稳定 effect key 写入唯一键表。正常路径在两个节点后关闭实例，再由新实例恢复：

```python
nodes = ("collect", "approve", "apply", "verify")
first = DurableGraph(db_path, nodes)
first.start("run-26", {"history": []})
state = first.step("run-26", expected_version=1)
state = first.step("run-26", expected_version=state["version"])
first.close()

second = DurableGraph(db_path, nodes)
while state["node"] != "FINISHED":
    state = second.step("run-26", expected_version=state["version"])
assert second.effect_count("run-26") == 1
```

故障路径用改变后的图恢复同一 run，必须在执行 effect 前拒绝：

```python
changed = DurableGraph(db_path, ("collect", "apply", "verify"))
try:
    changed.resume("run-26")
except GraphRecoveryError as exc:
    assert str(exc) == "graph_signature_mismatch"
assert changed.effect_count("run-26") == 0
```

这是实际 SQLite close/reopen，而不是内存集合假装 checkpoint。实现仍是线性教学图；没有分布式锁、parallel superstep、graph migration 或外部 API exactly-once。

## 主流系统实现对照与源码阅读入口

| 框架与本仓库锁定实验 | 实际跨进程边界 | 本项目已证明 | 明确未证明 |
|---|---|---|---|
| LangGraph `1.2.11` + SQLite checkpointer `3.1.1` | 首进程在 `interrupt` 停止，新进程以同一 `thread_id` 和 resume 输入继续 | checkpoint、approve/reject 分支、replay 前缀与 effect counter | 分布式 DB failover、任意 graph migration、外部 exactly-once |
| Google ADK `2.1.0` + `DatabaseSessionService` | 新进程从同一 SQLite 读取 session state/event 并写决定 | session/event 数据库持久性 | 恢复 instruction pointer、模型/任意工具 exactly-once |
| Microsoft Agent Framework Core `1.13.0` + `FileCheckpointStorage` | 第一进程在 superstep 后退出，第二进程先拒绝变更 topology，再以原图恢复 | checkpoint lineage、拓扑约束、单机文件恢复、effect once | 分布式存储、graph migration、所有 integration |
| 本章 `DurableGraph` | 关闭并重开 SQLite | version/signature/effect key 最小机制 | 上游框架行为与生产 durability |

对应机器证据位于 `evidence/l5/langgraph-durable-restart/`、`google-adk-session-restart/` 与 `maf-checkpoint-restart/`。三组证据不可相互替代：ADK session persistence 不能被写成 instruction-pointer resume，单机 file checkpoint 也不是跨 host store。

## 设计方案与方法对比

| 控制方式 | 优势 | 局限 | 适用场景 |
|---|---|---|---|
| 隐式 Agent loop | 自适应、代码少 | 恢复/分支难审计 | 短任务 |
| 静态 DAG | 可预测、易优化 | 难表达动态回环 | ETL/固定 workflow |
| 状态图 + 条件边 | 动态性与治理平衡 | schema/checkpoint 复杂 | 长任务、HITL |
| 外部 workflow engine + Agent node | durability/运维成熟 | 双状态机与适配成本 | 高可靠生产系统 |

图越细，可观测性越好但状态/迁移成本越高；图越粗，node 内部又会退化成不可见的 Agent loop。合理边界通常按 side effect、审批、长等待和可独立重试点划分。

## 可复现实验

### Lab 26A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch26_workflow_graph.py
```

实际输出为 `process_boundary=close_reopen_sqlite`、完整 history、`final_node=FINISHED`、`effect_count=1`，证据等级 `L1_MECHANISM`。验收要求恢复后从 checkpoint 继续而非重建内存。详见 [Lab 26A](../../../labs/core/lab-26A-workflow-graph.md)。

### Lab 26B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch26_workflow_graph.py --fault
```

实际输出为 `error=graph_signature_mismatch`、history 停在 `collect,approve`、`effect_count=0`、`L3_CONTAINED`。关键断点在 `resume` 的 topology signature 检查。详见 [Lab 26B](../../../labs/core/lab-26B-workflow-graph-fault.md)。

**实验语义边界。** Core Lab 证明本书最小图机制；三个 pinned upstream 实验才是相应框架的范围受限 L5 行为证据。它们都不证明生产 exactly-once 或任意版本迁移。

## 工程场景与系统设计

一个发布 Agent 可用 `collect → analyze → approve → apply → verify` 图：前三个节点纯计算/等待，`apply` 通过 effect journal 调用部署系统，`verify` 查询真实 rollout。若 apply receipt 丢失，run 进入 UNKNOWN 并按 deployment ID reconciliation；不能从 checkpoint 中 `node=apply` 推断未执行。

模型可在 analyze 节点使用[附录 A](../appendix-a-environment.md)的本地/OpenAI provider，但 routing 结果先解码为 enum，edge 不直接匹配自由文本。Checkpoint 禁止保存 API key；外部 tool 使用短期 scoped credential。

## 故障模型、失败模式与排错

- **checkpoint 有、effect 无证据**：进入 UNKNOWN，查询外部系统；
- **旧图恢复新部署**：校验 topology/node/schema signature，提供显式 migration；
- **并发 worker 双推进**：version/CAS + lease/fencing token；
- **interrupt 仅在内存**：先持久化 pending action 与 resume schema；
- **replay 重复 effect**：稳定 effect key、intent/receipt 与 reconciliation；
- **reducer 非确定**：测试交换/结合性，记录分支输入顺序。

排错从 run ID 的 checkpoint version/signature 开始，然后检查 pending write/effect journal 和外部 observation，最后才看 node prompt。

## 性能、可靠性与工程化

应测 node latency/attempt、checkpoint commit latency、resume success、CAS conflict、interrupt age、UNKNOWN duration、effect duplicate suppression、branch coverage 和 state size。Graph 可视化不能替代这些 runtime 指标。

大 state 不应每步整块复制；可用增量 event + 周期 snapshot，但恢复必须验证 hash chain 和 schema。压缩/GC 不能删除仍被 active run、审计或 migration 引用的 checkpoint。

## 技术边界与设计取舍

本章实现是单机 SQLite 线性图；生产环境还需存储高可用、worker fencing、backpressure、定时器、dead-letter、schema migration 和跨服务 trace。是否采用框架取决于 workload，不应为了“Agent 化”把简单事务拆成复杂图。

框架的 durable marketing term 必须落到具体对象：session、event、state、instruction pointer、pending write 还是 external effect。没有这个拆分，比较 LangGraph/ADK/MAF 会产生错误等价。

## 前沿研究与演进方向

前沿方向包括可验证 graph migration、动态生成但可静态审计的 workflow、基于类型/效果系统的 Agent node、跨框架 checkpoint interchange、语义事务、模型驱动 recovery policy 以及对长程 liveness 的形式验证。

### 深度审计与研究证据链

截至 2026-09-11，本章使用项目归档的三组真实上游跨进程证据，但每组 claim ceiling 独立记录。没有运行的 provider、分布式存储、网络分区和外部 API effect 不因框架名称而自动获得证据。

## 本章总结与进阶实践

Graph Runtime 的本质是显式状态和恢复协议。Checkpoint 是恢复输入，不是业务完成证明；topology identity 与 effect evidence 缺一不可。

进阶问题（答案见[附录 J](../appendix-j-part4-solutions.html#ch26)）：

1. 为什么 checkpoint 不能证明 external effect exactly-once？
2. topology signature 应覆盖哪些内容？
3. interrupt 与普通函数 return 的语义差异是什么？
4. 并行 graph reducer 需要满足哪些代数性质？
5. 为什么 LangGraph、ADK、MAF 的现有 L5 证据不能互换？
