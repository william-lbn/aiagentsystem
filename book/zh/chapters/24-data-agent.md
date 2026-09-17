# Data Agent：SQL、Python 与可审计分析

> **本章命题**：Data Agent 的可信单位不是一段自然语言答案，而是从问题语义、数据版本、查询计划、受限执行、结果 artifact 到独立校验的可重放分析。只读权限必须由数据库/沙箱强制，而不是靠 prompt 约定。

Browser Agent 操作外部界面，本章转向数据系统。我们用真实 SQLite 文件、query-only connection 和 authorizer 执行查询与故障注入；下一章把相同证据思想扩展为 Research Agent。

![Data Agent 的语义层、查询层、执行层与证据层](../../assets/diagrams/24-data-agent-architecture.svg)

## 问题背景与学习目标

“帮我分析收入下降原因”同时包含语义歧义、权限风险和统计陷阱：收入是含税还是不含税，时间按订单还是结算，取消单是否排除，查询是否扫全表，缺失值怎样处理，模型是否把相关性写成因果性。即使 SQL 正确，数据 snapshot 改变也会让结果不可复现。

读者应能设计 semantic contract、read-only execution、row/byte/time budget、query plan 检查、结果 digest、统计 verifier 和 provenance；理解 SQL 生成只是 proposal；能够运行只读查询并证明 `DELETE` 在数据库层被拒绝且原表未变化。

## 核心概念与系统直觉

**Semantic layer** 把业务指标映射为字段、过滤条件、时间与粒度；**planner** 生成 SQL/Python 候选；**execution boundary** 控制连接、schema、资源和函数；**artifact** 保存 SQL、参数、plan、rows/hash；**verifier** 检查行数、单位、约束和交叉计算。

Read-only 不是 `sql.lower().startswith("select")`。CTE、触发器、扩展函数、多语句和方言都会击穿词法判断。权限应由数据库角色、只读 transaction、SQLite authorizer 或隔离副本强制。Python 分析还需要进程/容器 sandbox、包白名单、资源限制和无默认网络。

结果可审计也不等于结论正确。数据库能证明返回了哪些行，不能证明业务定义、样本选择或因果解释合理；这些属于 semantic/statistical verification。

## 原理与理论基础

一次分析可以表示为：

$$
A=(Q,S,D_v,P,X,R,V),
$$

其中 (Q) 是问题，(S) 是语义定义，(D_v) 是数据版本，(P) 是 query/program，(X) 是受限执行环境，(R) 是结果 artifact，(V) 是 verifier。可信结论要求每一条 claim 都能追到这个链，而不是只保存最后回答。

> **Invariant**: a data agent has read-only authority by construction and binds every reported value to query, plan, data version, result and verifier.

权限与正确性是正交的：只读 SQL 仍可能算错；统计正确的 SQL 若可修改生产库仍不安全。因此评估至少拆成 execution safety、semantic correctness、numerical correctness 和 explanation faithfulness。

## 关键机制与执行流程

![Data Agent 从语义解析到只读执行和复核的流程](../../assets/diagrams/24-data-agent-flow.svg)

1. 解析问题中的指标、维度、时间窗、时区、币种与排除规则；
2. 读取 schema catalog 和允许数据集，不把任意表结构塞进 prompt；
3. 模型产生参数化 SQL/分析 plan，静态检查表、列、函数和估算成本；
4. 在只读连接/副本执行，设置 statement timeout、row/byte limit；
5. 保存 canonical SQL、参数、query plan、dataset snapshot 与 result digest；
6. verifier 做行数/范围/守恒/重复计算，必要时用第二条查询交叉验证；
7. 报告区分 observation、推断、统计不确定性和未覆盖范围；
8. 若需要写回，创建独立 write workflow，经 action-bound approval 执行。

流式返回大量行时，`LIMIT` 不是完整资源控制；聚合、join 或排序可能在输出前已经消耗大量资源。应同时使用数据库 workload policy 和物理隔离。

## 从原理到实现

`ReadOnlyDataAgent` 以 `mode=ro` 打开 SQLite，启用 `query_only`，再用 authorizer 拒绝 mutation/DDL/attach。执行前保存 query plan，结果有行数上限与 canonical digest：

```python
agent = ReadOnlyDataAgent(database, max_rows=10)
result = agent.execute(
    "select status,sum(amount) as total "
    "from invoices group by status order by status"
)
assert result.rows == (("open", 100), ("paid", 10))
assert result.plan
assert len(result.digest) == 64
```

故障路径不是“发现字符串含 delete 就假装阻止”，而是真正把语句交给受限数据库接口并断言原数据保持：

```python
try:
    agent.execute("delete from invoices")
except QueryRejected:
    pass
agent.close()

with sqlite3.connect(database) as verifier:
    assert verifier.execute("select count(*) from invoices").fetchone()[0] == 3
```

代码位于 `src/agentlab/specialized_system.py`。实验覆盖真实 DB authorization 和查询计划，但不覆盖企业 warehouse 方言、RBAC、行列级权限或 Python sandbox。

## 主流系统实现对照与源码阅读入口

| 实现路径 | 优势 | 审计重点 |
|---|---|---|
| 数据库原生只读角色/副本 | 强权限边界、可利用 optimizer | role、row/column policy、snapshot、statement budget |
| Semantic layer + SQL Agent | 业务指标一致性较高 | metric version、join path、time/currency semantics |
| Notebook/Python Agent | 表达力强 | code sandbox、package/data/network capability、artifact |
| OpenAI Responses/Agents + function tool | 可把 query contract 暴露为 typed tool | 模型只提 proposal，host 仍做 policy 与 verifier |
| 本章 SQLite 引擎 | 轻量、跨平台、可故障注入 | claim ceiling 不外推到云 warehouse |

源码阅读应追到连接创建、credential scope、authorizer/RBAC、timeout、result serialization 和 audit hook。只读 prompt 与隐藏 system message 都不是安全边界。

## 设计方案与方法对比

| 方案 | 表达力 | 风险面 | 推荐控制 |
|---|---:|---:|---|
| 模板化参数查询 | 低 | 低 | 参数类型与结果 schema |
| 受约束 Text-to-SQL | 中 | 中 | catalog allowlist、只读连接、plan/budget |
| 任意 SQL | 高 | 高 | 隔离副本、严格 RBAC、人工审批 |
| SQL + Python | 最高 | 最高 | 容器、包/网络限制、artifact verifier |

先用最小表达力满足任务。许多 dashboard 问答不需要任意 Python；给 Agent 更多能力会增加 prompt injection、数据外传和不可复现分析的空间。

## 可复现实验

### Lab 24A — 正常路径

```bash
PYTHONPATH=src python examples/chapters/ch24_data_agent.py
```

实际输出包含两行聚合结果 `open=100`、`paid=10`，query plan 为 `SCAN invoices USING INDEX invoices_status`，并给出 result digest；证据等级为 `L1_MECHANISM`。详见 [Lab 24A](../../../labs/core/lab-24A-data-agent.md)。

### Lab 24B — 故障注入

```bash
PYTHONPATH=src python examples/chapters/ch24_data_agent.py --fault
```

实际输出为 `error=QueryRejected`、`verified_row_count=3`、`L3_CONTAINED`。关键断点是 SQLite authorizer 和独立 verifier connection；验收不能只看 exception。详见 [Lab 24B](../../../labs/core/lab-24B-data-agent-fault.md)。

**实验语义边界。** 真实执行和拒绝均发生在 SQLite；没有模型生成 SQL，也没有声称查询回答质量。模型接入后必须把 invalid SQL、semantic error 和 unsafe proposal 分开统计。

## 工程场景与系统设计

销售分析 Agent 应把“净收入”绑定到经过治理的 metric ID/version，使用只读 warehouse service account，只暴露允许 schema。结果 artifact 包含 SQL、参数、snapshot/time travel ID、plan、row count、digest 和 verifier。自然语言报告引用 artifact 中的字段，不能生成不存在的数值。

对于小型本地模型，可先让它在有限 catalog 上选择模板和参数；能力更强的 OpenAI 模型可生成候选 SQL，但仍按[附录 A](../appendix-a-environment.md)接入，key 不进入仓库，SQL 不因模型来源而免检。

## 故障模型、失败模式与排错

- **业务语义错**：核对 metric/时间/时区/币种/取消单定义；
- **越权查询或写入**：检查 DB role、authorizer、schema/row policy，而非 prompt；
- **资源耗尽**：审查 query plan、扫描量、join cardinality、timeout 与 concurrency；
- **结果截断被当完整**：artifact 显式记录 `truncated` 和总量估计；
- **Python 外传数据**：默认无网络、最小 mount、短期 credential 与输出扫描；
- **因果过度解释**：报告标记 observation/correlation/hypothesis，不能把相关性写成原因。

排错从数据版本和 SQL artifact 开始；如果无法重放同一数据 snapshot，答案本身就缺乏可复核性。

## 性能、可靠性与工程化

应记录 query success、semantic accuracy、numerical tolerance、unsafe proposal rate、DB-denied rate、rows/bytes scanned、queue/execute latency、cache hit、result truncation 和人工复核率。Latency 优化必须区分模型时间与数据库时间。

缓存键至少包含 normalized query、parameters、metric/catalog version、data snapshot 与 principal scope；只按自然语言问题缓存会跨用户或跨数据版本泄露/错用结果。

## 技术边界与设计取舍

SQLite authorizer 是强于字符串规则的真实边界，但不是所有 warehouse 的替代品。生产系统需要验证具体方言、存储过程、UDF、外部表和 time-travel 语义。敏感数据还需要脱敏、最小行列权限、用途限制和审计。

自动生成图表或结论前，必须保证单位和聚合粒度明确。更漂亮的报告不能弥补错误 denominator、selection bias 或未控制混杂变量。

## 前沿研究与演进方向

研究方向包括带语义约束的 Text-to-SQL、查询计划反馈、自纠错而不扩大权限、可验证数据分析、隐私保护 Agent、因果推断 guardrail，以及把 query/result provenance 与自然语言 claim 自动对齐。

### 深度审计与研究证据链

截至 2026-09-11，本章的可运行证据是 SQLite 查询、授权拒绝和独立行数复核。任何企业 warehouse、真实数据集或模型准确率结论需要单独的数据许可、版本锁、评测集和原始输出；本书不制造这些数字。

## 本章总结与进阶实践

Data Agent 的可信性来自“权限由系统限制、数值可重放、语义可审计、结论不过度外推”。SQL 只是证据链中的一环。

进阶问题（答案见[附录 J](../appendix-j-part4-solutions.html#ch24)）：

1. 为什么 `startswith("select")` 不是只读安全边界？
2. query plan 和 result digest 分别提供什么证据？
3. 如何防止截断结果被报告成完整总体？
4. Text-to-SQL 的 semantic error 应怎样评测？
5. 在允许 Python 分析时还需增加哪些隔离和复现字段？
