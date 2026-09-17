# Hybrid / Agentic RAG：让检索成为决策过程

> **本章命题**：Hybrid RAG 不是把 BM25 与向量分数相加；它是一个受治理的检索计划：选择检索器、隔离各自故障、保留 provenance、融合候选、判定证据是否充分，并在预算内继续、改写或停止。

上一章建立了单检索器的证据边界。本章讨论检索器组合和 Agentic control，同时严格区分“本地第二检索算法”与“真实 embedding 模型”。

![Hybrid RAG 的路由、隔离、融合与证据验证](../../assets/diagrams/10-hybrid-rag-architecture.svg)

## 问题背景与学习目标

Lexical retrieval 擅长精确 ID、错误码与专有名词；dense retrieval 擅长语义改写；SQL/graph 擅长结构化约束。混合系统希望互补，却会引入新故障：不同 score 不可比、adapter 返回越权 ID、重复候选被多算、reranker 抹掉来源、循环检索耗尽预算。

读完本章，读者应能：

- 把 retriever 当成有合同、有 authorized universe 的 adapter；
- 用 rank fusion 而非未经校准的原始 score 相加；
- 区分 query routing、query rewriting、multi-hop decomposition 和 evidence verification；
- 设计最大轮数、最大候选、token/latency/cost budget 与停止条件；
- 分别报告 retriever、fusion、reranker、generator 的消融结果。

## 核心概念与系统直觉

### Hybrid 是证据组合，不是分数拼盘

BM25、cosine、数据库概率和图路径成本的量纲不同。未经校准直接加权，会让某一路分数范围支配结果。Reciprocal Rank Fusion（RRF）只依赖名次，提供稳健基线；学习融合可更强，但需要代表性标注和漂移监控。

### Retriever Adapter 是安全边界

每个 adapter 返回 doc ID、rank、score、retriever/version 与 provenance。融合器只接受 authorized corpus 中的 ID；未知、跨租户或重复 ID 被拒绝并计入 error budget。不能因为“dense service 已经过滤”就跳过本地验证。

### Agentic Retrieval 是有限状态控制

模型可提出：检索、改写、拆问题、请求结构化查询或停止。但循环必须有 deterministic budget，证据充分性由可检查条件决定。Agent 不应通过不断换措辞掩盖 corpus 缺失。

### Reranker 不拥有事实

Cross-encoder/LLM reranker 只调整候选顺序，不提升文档 authority，也不应移除原始 retriever provenance。最终 claim 仍需指向 source span。

## 原理与理论基础

RRF 对文档 $d$ 的分数为：

$$
RRF(d)=\sum_{r\in R}\frac{1}{k+rank_r(d)}
$$

$k$ 控制头部名次的敏感度。未被某检索器召回的文档不贡献分数。RRF 的优点是无需让 BM25 与 cosine 共享量纲；局限是忽略 score margin 和 retriever reliability。

Agentic RAG 可写成预算受限策略：

$$
\pi(a_t\mid q,E_t,B_t),\quad
a_t\in\{retrieve_r,rewrite,decompose,verify,stop,abstain\}
$$

其中 Evidence Set $E_t$ 必须保留来源，Budget $B_t$ 单调递减。终止条件不是模型说“够了”，而是 coverage/contradiction/authority gate 达标或预算耗尽。

**不变量**：fusion must preserve retriever provenance and reject IDs outside the authorized corpus。

## 关键机制与执行流程

![混合检索器独立运行、合同校验并以 RRF 融合](../../assets/diagrams/10-hybrid-rag-flow.svg)

1. Policy 根据 query type 和成本选择 lexical、dense、SQL 或 graph 路径；
2. 各 adapter 在相同 subject scope 下独立执行，使用 deadline 与 bulkhead；
3. Validator 检查 ID universe、tenant、重复项、版本和返回上限；
4. Fusion 计算 RRF，并建立 `doc_id → retrievers` provenance；
5. 可选 reranker 只处理已授权候选；
6. Evidence gate 检查覆盖、权威、时效、冲突和引用 span；
7. 不充分时可改写/分解，直到 step/cost budget 到顶；之后 abstain；
8. Answer verifier 比较 claim 与实际 Evidence Set。

## 从原理到实现

为了让离线 lab 不伪装成 neural embedding，本书明确使用第二种真实但非神经的算法：字符三元组 cosine。类名和 docstring 都声明其身份：

```python
class CharacterNgramIndex:
    """A deterministic second retriever, explicitly not a neural embedding model."""

    def rank(self, query: str, *, tenant_id: str) -> list[str]:
        query_vector = character_ngrams(query)
        scored = [
            (doc.doc_id, cosine(query_vector, self.vectors[doc.doc_id]))
            for doc in self.documents
            if doc.tenant_id == tenant_id
        ]
        return [doc_id for doc_id, score in sorted(scored, key=...) if score > 0]
```

融合器把 adapter 视为不可信输入：

```python
for retriever, ranking in rankings.items():
    seen = set()
    for rank, doc_id in enumerate(ranking, 1):
        if doc_id in seen:
            rejected[f"{retriever}:{rank}:{doc_id}"] = "duplicate_in_ranking"
            continue
        if doc_id not in allowed_ids:
            rejected[f"{retriever}:{rank}:{doc_id}"] = "unknown_or_forbidden_document"
            continue
        scores[doc_id] += 1.0 / (k + rank)
        provenance[doc_id].append(retriever)
```

这个边界允许故障注入一个高排名 `foreign-secret`，并验证它没有进入融合结果。

## 主流系统实现对照与源码阅读入口

| 路线 | 机制 | 审计重点 |
|---|---|---|
| [RAG](https://arxiv.org/abs/2005.11401) | 参数/非参数记忆联合生成 | 研究任务与生产权限/时态边界不同 |
| [DPR](https://arxiv.org/abs/2004.04906) | dense bi-encoder retrieval | negative sampling、domain shift、index/model version |
| [RRF](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) | 基于名次的稳健融合 | authorized universe、重复 ID、k 与 candidate depth |
| Agentic/Graph RAG 实现 | query routing、decomposition、迭代检索 | 循环预算、状态持久化、模型共偏差 |

托管 vector/file-search 服务可降低基础设施负担，但应用仍要保留 corpus/version、subject scope、query、returned IDs、citations 和 usage。若 API 不暴露某层分数，不应伪造或推测。

## 设计方案与方法对比

| 方案 | 需要的标注 | 优势 | 主要风险 |
|---|---:|---|---|
| RRF | 无 | 简单稳健、分数无关 | 忽略 margin/可靠性 |
| 归一化加权分数 | 少量校准 | 可表达 retriever 权重 | 分布漂移后失真 |
| 学习排序 | 大量 query-doc labels | 可优化业务指标 | 过拟合、解释与治理成本 |
| LLM rerank | 可零样本 | 语义/指令理解强 | 成本、注入、共偏差 |

RRF 应作为强基线。只有在 held-out eval 明确提升且安全 slice 不退化时，才引入更复杂融合。

## 可复现实验

### 实验环境

Python 3.11–3.13；无网络/模型/API key。两路检索均真实执行：BM25 与字符 n-gram cosine；后者是 lexical-shape baseline，不称为 embedding。核心代码在 `knowledge_system.py`，入口为 `ch10_hybrid_rag.py`。

### Lab 10A：双检索器 RRF

```bash
PYTHONPATH=src uv run python examples/chapters/ch10_hybrid_rag.py
```

实际结果：BM25 仅召回 `runbook`；char-ngram 顺序为 `runbook, approval, retrieval`；融合 top-1 为 `runbook`，其 provenance 同时包含两路检索器，等级 `L1_MECHANISM`。

### Lab 10B：损坏 adapter 注入未知 ID

```bash
PYTHONPATH=src uv run python examples/chapters/ch10_hybrid_rag.py --fault
```

第二路把 `foreign-secret` 放在 rank 1。融合器实际返回 `char_ngram:1:foreign-secret → unknown_or_forbidden_document`，最终 ranking 不含该 ID，证据等级 `L3_CONTAINED`。详见 [Lab 10A](../../../labs/core/lab-10A-hybrid-rag.md) 与 [Lab 10B](../../../labs/core/lab-10B-hybrid-rag-fault.md)。

### 关键断点与验收标准

**关键断点**：保留每路原始 ranking、authorized document universe、RRF accumulator 和 provenance map，不允许 adapter 的未知 ID 进入融合。**验收标准**：正常实际输出的 top-1 必须由两路共同支持；故障输出必须将 `foreign-secret` 列入 rejected、不给予分数或 provenance，且合法排名稳定。

## 工程场景与系统设计

面向生产支持 Agent，可先用 query classifier 判断：ticket/error code 走 BM25，用户自然语言走 dense，两者不确定时并行；涉及账户状态则必须追加结构化查询。每路有独立 deadline，迟到结果不阻塞全部请求；但融合 manifest 要记录哪些 retriever 超时，避免把降级结果误称为完整检索。

多跳问题应显式维护 subquery 与已用证据，防止模型重复检索同一内容。停止条件可以是：每个必要 claim 至少一个高 authority span、无未解决冲突、候选增益低于阈值，或预算用尽。

## 故障模型、失败模式与排错

- **未知 ID**：adapter/索引版本不一致或越权，融合前拒绝；
- **重复 ID**：同一路重复不应多次加分；
- **迟到 retriever**：记录 timeout 与降级模式，不伪装成全量结果；
- **query drift**：多轮改写偏离原任务，比较每轮 query 与 constraint manifest；
- **reranker 注入**：候选正文是 data，不能改变 system policy；
- **循环无增益**：跟踪 unique evidence gain，达到阈值后停止。

## 性能、可靠性与工程化

分解 latency：route、每路 retrieval、validation、fusion、rerank、evidence gate。质量按 retriever ablation 报告，并给出 oracle labels、样本数、置信区间。成本不仅是 token，还包括索引查询、GPU rerank、外部 API 与重复检索。

并行能降低尾延迟，但会提高资源峰值；可用 hedging、early-exit 和 query-dependent routing。所有 cache key 都需包含 authorized scope 与 index/model version。融合结果需要 deterministic tie-break，确保 replay 和跨主机证据一致。

## 技术边界与设计取舍

本章第二检索器不是语义 embedding，故不能宣称验证了 neural hybrid RAG；这是刻意的证据诚实。读者若接入本地小 embedding 模型，可选冻结 revision 的轻量多语模型，并记录权重哈希、量化和 pooling；若使用 OpenAI embeddings/file search，同样只从环境读取 key 并保存脱敏 provider evidence。

真实模型实验至少比较 BM25-only、dense-only、RRF、reranker 四组，并对正常查询、无解查询、跨租户攻击、过期文档和多语言分别报告。没有这些 slice，平均 Recall 提升不足以上线。

## 前沿研究与演进方向

下一代 RAG 趋向 retrieval planning：模型决定访问哪类索引、是否继续、如何验证，同时系统以形式化预算和治理门限制约策略。多模态、时态、代码与数据库检索将共存，关键不再是单一 embedding，而是跨证据类型的身份、冲突与 completion semantics。

### 深度审计与研究证据链：算法互补不能跨越治理边界

RRF 提供无需分数校准的组合基础；Agentic RAG 增加策略自适应；本章的授权 ID universe 和 adapter rejection 属于系统安全层。任何检索算法的论文分数都不能证明跨租户隔离，离线故障包含也不能证明真实 embedding 质量。

## 本章总结与进阶实践

Hybrid RAG 的价值来自多路证据互补；其可靠性来自 adapter 合同、provenance、budget 和 evidence gate。把两个列表相加只是开始，不是系统完成。

进阶问题：

1. 为什么 BM25 与 cosine 原始分数不宜直接相加？
2. 融合器为什么还要验证 doc ID，而不能信任 adapter？
3. 怎样定义多轮检索的 evidence gain？
4. reranker 应保留哪些上游 provenance？
5. 如何设计 dense-only 与 hybrid 的安全消融？

参考答案见[附录 H：第二篇问题参考答案](../appendix-h-part2-solutions.html#part2-solutions-ch10)。
