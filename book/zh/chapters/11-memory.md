# 长期记忆：从聊天历史到可治理的用户状态

> **本章命题**：Agent Memory 不是“把聊天切块放进向量库”，而是一个具有写入、读取、更新、冲突、遗忘、时间语义和访问控制的数据系统。Embedding 只是访问路径，不能成为权威状态。

前两章处理外部知识证据；本章处理跨会话延续的信息。核心问题不是“记得更多”，而是“在正确时间，以正确来源和权限，记住仍然成立的内容”。

![长期记忆的提议、治理、双时态存储与受控读取](../../assets/diagrams/11-memory-architecture.svg)

## 问题背景与学习目标

将完整聊天历史当 memory 会混合寒暄、猜测、敏感数据、过期偏好和模型生成内容。自动摘要又可能丢失否定、金额或身份。真正的长期记忆必须回答：谁提出、谁确认、何时有效、何时写入、覆盖谁、为何可见、何时删除。

本章目标：

- 区分 working state、episodic trace、semantic profile 与 procedural memory；
- 使用 valid time 与 transaction time 表达“事实何时成立”和“系统何时知道”；
- 以 source/authority/confidence/supersedes 管理更新，而非 last-write-wins；
- 在相同等级冲突时 abstain，而不是随机选一个；
- 设计 construction/read/generation 分阶段成本和质量指标。

## 核心概念与系统直觉

### State、History 与 Memory 不同

Run state 控制当前执行，history 记录发生过什么，memory 是经治理后供未来任务读取的信息资产。当前工具已提交属于 effect/state，不应通过“记忆说它完成了”来恢复。

### 写入是高风险决策

模型可提出 memory candidate，但写入需要 policy：允许哪些类型、是否要用户确认、PII 保留多久、来源最低 authority、多租户如何隔离。自动提取的高召回若带来错误事实，会长期污染后续决策。

### 双时态避免“覆盖历史”

Valid time 表示事实适用区间；recorded/transaction time 表示系统接收它的时间。用户 9 月 1 日开始偏好中文，9 月 10 日才被系统记录，这两个时间不能压成一个 `updated_at`。

### 遗忘是正确性机制

TTL、撤回、tombstone、权限变化和法规删除都要求 memory 失效。无限保留不是能力，而是隐私、成本与陈旧性风险。

## 原理与理论基础

记忆记录可表示为：

$$
m=(id,tenant,subject,key,value,source,authority,confidence,[v_f,v_t),t_r,supersedes)
$$

在查询时刻 $t$ 的合法集合：

$$
C_t=\{m\mid tenant(m)=tenant_q\land subject/key\ match\land v_f\le t<v_t\}
$$

解析顺序必须先硬过滤 tenant/subject/valid time，再比较 authority、confidence 与 recorded time。若最高等级记录值冲突且无 supersedes 关系，安全结果是 unresolved conflict。

**不变量**：memory reads must enforce tenant and valid time, retain provenance, and abstain on unresolved conflict。

Memory quality 不能只用最终回答准确率。至少拆成 write precision/recall、retrieval recall、conflict detection、freshness、deletion completeness、privacy leakage，以及 construction/retrieval/generation 三阶段资源成本。

## 关键机制与执行流程

![Memory candidate 经过政策门、双时态存储和冲突解析](../../assets/diagrams/11-memory-flow.svg)

1. 从用户明确陈述、可信系统事件或人工标注生成 candidate；
2. 分类为 preference、profile fact、episode、procedure 等；
3. 运行 consent、sensitivity、tenant、retention 与 authority policy；
4. 写入 immutable record，包含 valid/recorded time 与 source；
5. 更新通过新 record + supersedes/tombstone 表达，不原地抹除；
6. Query 先按 scope/time 过滤，再 rank/resolve；
7. 等级相同且值冲突时返回 conflict，请求澄清；
8. Context assembler 只投影本轮需要的最小 memory，并保留 memory ID。

## 从原理到实现

参考存储在 append 时验证身份、区间和 supersedes scope：

```python
def append(self, record):
    if record.memory_id in self._records:
        raise ValueError("duplicate_memory_id")
    if record.valid_to is not None and parse_utc(record.valid_to) <= parse_utc(record.valid_from):
        raise ValueError("invalid_valid_interval")
    if record.supersedes is not None:
        previous = self._records.get(record.supersedes)
        if previous is None:
            raise ValueError("superseded_memory_missing")
        if (previous.tenant_id, previous.subject, previous.key) != (
            record.tenant_id, record.subject, record.key
        ):
            raise ValueError("supersedes_scope_mismatch")
    self._records[record.memory_id] = record
```

读取不是 last-write-wins：

```python
ordered = sorted(
    candidates,
    key=lambda r: (-r.authority, -r.confidence, -parse_utc(r.recorded_at).timestamp(), r.memory_id),
)
if equal_rank(ordered[0], ordered[1]) and ordered[0].value != ordered[1].value:
    return MemoryResolution(None, candidate_ids, conflict_quarantine)
return MemoryResolution(ordered[0] if ordered else None, candidate_ids, quarantined)
```

lab 的 fault path 同时注入同租户等等级矛盾记录和跨租户记录，实际 resolver 选择 abstain 并给出不同 quarantine reason。

## 主流系统实现对照与源码阅读入口

| 来源/系统 | 重要观察 | 工程核查点 |
|---|---|---|
| [Agent Memory: Characterization and System Implications](https://arxiv.org/abs/2606.06448) | 以系统视角拆解多类 memory，并分阶段分析成本 | construction/read/generation 成本、freshness 与规模效应 |
| [Memory for AI Agents Survey](https://arxiv.org/abs/2603.07670) | 扩展 memory taxonomy 与开放问题 | 记忆形成、演化、治理与可信性 |
| Mem0/Letta 等开源系统 | 抽取、存储、检索与更新的具体抽象 | source、tenant、deletion、conflict 和版本迁移 |
| 框架 session/memory API | 便捷保存 message/state | session history 是否被误称为长期权威记忆 |

论文或产品列表不能替代 source reading。应沿 write proposal → persistence schema → retrieval filter → update/delete → context projection 阅读，并检查敏感信息生命周期。

## 设计方案与方法对比

| 方案 | 优势 | 主要缺陷 | 适用场景 |
|---|---|---|---|
| 全量 transcript | 简单、可审计原文 | 成本高、噪声与隐私大 | 短期会话归档 |
| 摘要 memory | token 小 | 丢失与幻觉、难更新 | 低风险背景 |
| typed fact store | 冲突/时间可治理 | schema 与写策略成本 | 用户偏好、业务 profile |
| episodic vector store | 相似经历召回 | 权威与时态弱 | 辅助案例检索 |
| knowledge graph | 关系、演化明确 | 构建维护复杂 | 高价值实体关系 |

通常采用分层组合，而非一种存储包打天下。对高风险事实，应读取权威业务系统，memory 只保存引用或缓存。

## 可复现实验

### 实验环境

Python 标准库、无网络/API key。SUT 为 `TemporalMemoryStore`，固定 UTC 时间与 tenant；测试覆盖重复 ID、时间区间、supersedes scope、authority 排序、跨租户隔离和等等级冲突。

### Lab 11A：可信偏好读取

```bash
PYTHONPATH=src uv run python examples/chapters/ch11_memory.py
```

实际结果选择 `mem-zh`，value 为 `zh-CN`，候选和 quarantine 均可见，证据等级 `L1_MECHANISM`。

### Lab 11B：冲突与跨租户污染

```bash
PYTHONPATH=src uv run python examples/chapters/ch11_memory.py --fault
```

实际结果 `selected=null`；`mem-zh/mem-conflict` 标为 `unresolved_equal_rank_conflict`，`mem-foreign` 标为 `tenant_mismatch`。系统没有把任何值投影到上下文，因此为 `L3_CONTAINED`。详见 [Lab 11A](../../../labs/core/lab-11A-memory.md) 与 [Lab 11B](../../../labs/core/lab-11B-memory-fault.md)。

### 关键断点与验收标准

**关键断点**：在 UTC 解析、tenant/subject/key 范围过滤、valid-time、authority/confidence 排序、supersedes 与冲突裁决处跟踪 identity。**验收标准**：无冲突时实际输出必须返回稳定 memory ID 与值；同等级异值必须 abstain，跨租户记忆必须隔离，任一污染值都不得投影给模型。

## 工程场景与系统设计

客服 Agent 可记住用户语言偏好，但不应从一次模型推断永久写入健康、财务或身份属性。明确用户设置拥有最高 authority；CRM 同步次之；模型抽取只是 proposal。每次回答可回显“我依据哪条 memory”，并提供纠正/删除入口。

Memory 服务要支持 tenant partition、subject access request、retention policy、legal hold、tombstone propagation 和 backup deletion。向量索引是派生层；删除时必须验证 raw store、index、cache、checkpoint 与分析副本。

## 故障模型、失败模式与排错

- **模型把推测写成事实**：检查 source type 和 write policy；
- **偏好已经改变却仍读旧值**：比较 valid time、supersedes 链和 index lag；
- **跨用户召回**：tenant/subject filter 应先于 similarity；
- **摘要丢失否定**：保留原 record/source，关键字段结构化；
- **删除不完整**：逐层验证 store/index/cache/backup 的 deletion receipt；
- **冲突被最近写入掩盖**：禁用无条件 last-write-wins，显式标记 unresolved。

## 性能、可靠性与工程化

系统指标分三段：construction queue/latency/cost、retrieval latency/hit/conflict、generation token/quality；治理指标包括 stale-read、cross-tenant exposure、delete SLA、consent coverage。研究显示复杂 memory 往往把大量成本放在写入构建阶段，因此不能只优化查询 p95。

可以异步 consolidation，但用户刚刚确认的关键更新要满足 read-your-writes。冷热分层和 compaction 不得抹去 provenance 或未解决冲突。模型/抽取器升级应重新跑 write precision 和 conflict regression，而非直接重写全部历史。

## 技术边界与设计取舍

本章 store 是内存参考实现，不具备数据库事务、加密、分布式索引或法规删除证明；它验证的是双时态、范围与冲突语义。真实系统至少需要持久化数据库、行级租户策略、审计、备份策略和故障恢复测试。

使用小模型进行 memory extraction 时，可本地部署轻量 instruct 模型，但输出只能成为候选；记录权重 revision、hash、量化、prompt/schema 和人工 gold labels。使用 OpenAI 时通过环境变量读取 key，保存脱敏 response/request identity，绝不把原始 PII、secret 或私有 transcript 提交到公开证据包。

## 前沿研究与演进方向

Memory 正从检索功能演化为 agent-native data management：自动形成、动态演化、冲突与遗忘、多模态、多 Agent 共享和策略学习。重要研究缺口包括时态一致性、错误记忆的级联影响、删除可验证性、memory poisoning 与 fleet-scale 成本。

### 深度审计与研究证据链：Embedding 是索引，不是权威

2026 年系统研究将 memory 拆为形成、读取和生成阶段，并显示设计选择会转移而非消除成本。本章将这一观察落实为双时态记录和冲突拒答。小型离线 store 不冒充对论文十个系统的复现实验，也不把产品能力列表当成已验证结论。

## 本章总结与进阶实践

长期记忆的目标不是最大化保存，而是最小化未来决策所需、仍然有效且可追溯的信息。写错一条持久事实可能比一次回答错误更危险。

进阶问题：

1. valid time 与 recorded time 分别解决什么问题？
2. 为什么模型抽取应是 candidate 而不是直接事实？
3. 等等级记录冲突时，为什么 abstain 优于最近写入覆盖？
4. 删除一条 memory 需要验证哪些派生层？
5. 如何分别评估 construction、retrieval 和 generation？

参考答案见[附录 H：第二篇问题参考答案](../appendix-h-part2-solutions.html#part2-solutions-ch11)。
