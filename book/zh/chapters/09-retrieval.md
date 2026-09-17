# RAG 基础：检索、证据与生成边界

> **本章命题**：检索不是“给模型找几段相似文本”，而是带访问控制、来源、时间和拒答语义的证据查询。相关性排序只能发生在合法候选集合内；生成答案不能提升证据本身的权威等级。

Tool 让 Agent 行动，Retrieval 让 Agent 基于外部证据判断。本章先建立单检索器的正确性边界，下一章再讨论混合检索、路由和 Agentic RAG。

![受治理检索先过滤安全边界，再计算相关性](../../assets/diagrams/09-retrieval-architecture.svg)

## 问题背景与学习目标

RAG 常被简化成 chunk → embedding → top-k → prompt。这条流水线遗漏了五个决定系统可信度的问题：谁有权读取文档、文档何时有效、查询是否需要关键词/语义/结构化约束、没有证据时能否拒答、答案如何回指原文。

本章完成标准是：

- 能推导 BM25 的 term frequency、document frequency 与长度归一化；
- 理解向量相似度不是事实置信度，也不能替代租户/ACL 过滤；
- 为每个 hit 保留 source URI、observed time、authority、score 与内容 digest；
- 把 no-evidence 作为正常结果，而不是强迫生成；
- 用 Recall@k、MRR/nDCG、citation precision 与安全泄漏率共同评价系统。

## 核心概念与系统直觉

### Corpus 是版本化数据产品

文档集合必须有 ingestion manifest：来源、抓取时间、解析器版本、chunk policy、ACL、tenant、内容 hash 和 tombstone。没有 manifest 的向量库无法回答“结果来自哪一版知识”。

### Chunk 是索引单元，不是语义真理

chunk 太小会丢失条件和否定，太大则降低定位精度并增加 token。标题、章节路径、表格结构和邻接关系应作为字段保留。对法律、财务、代码等领域，按句号机械切分通常不够。

### Query、Filter、Rank 是三件事

Filter 是硬约束：tenant、ACL、data class、有效时间；违反即排除。Rank 是合法集合内的软排序：BM25、dense similarity、authority 或 freshness。把它们加权成一个分数会允许“极相关的越权文档”获胜。

### Abstention 是能力

当 top score/coverage 不足、证据互相冲突或问题超出 corpus，系统应返回 `NO_EVIDENCE` 或请求澄清。无依据地“尽力回答”会把语言流畅度变成错误承诺。

## 原理与理论基础

BM25 对查询词 $q$ 和文档 $d$ 的典型形式为：

$$
score(d,q)=\sum_{t\in q} IDF(t)\frac{f(t,d)(k_1+1)}
{f(t,d)+k_1(1-b+b\frac{|d|}{avgdl})}
$$

它通过 IDF 提高稀有词权重，并以 $b$ 修正文档长度。BM25 是 lexical relevance 模型，不理解权限或事实正确性；这些必须在评分前后由系统处理。

离线 ranking 指标：

$$
Recall@k=\frac{|Relevant\cap Top_k|}{|Relevant|},\qquad
MRR=\frac{1}{|Q|}\sum_q\frac{1}{rank_q}
$$

nDCG 适合多级相关性，但 Agent 场景还要测 evidence coverage、answer support、freshness violation、cross-tenant exposure 和 abstention calibration。

**不变量**：retrieval must apply hard scope filters before scoring and return provenance with every hit。

## 关键机制与执行流程

![检索从版本化语料、硬过滤到可引用 observation](../../assets/diagrams/09-retrieval-flow.svg)

1. Ingestion 解析原文，生成稳定 doc/chunk ID 和 source digest；
2. 写入 tenant、ACL、authority、valid time、observed time 等元数据；
3. Query normalization 保留实体、否定、时间和字段约束；
4. 先执行 hard filter，形成 authorized candidate set；
5. BM25 在候选集内评分，稳定 tie-break；
6. 低于阈值或覆盖不足时 abstain；
7. 返回 hit + provenance，而非裸文本；
8. 生成器引用 hit ID，post-hoc verifier 检查 claim 是否有证据支持。

对 web 内容，retrieved text 必须保持 untrusted data 身份；网页中的“忽略之前指令”不能进入 system channel。

## 从原理到实现

`BM25Index` 使用实际公式而不是固定 ranking fixture：

```python
def _score(self, query, doc_id):
    counts = Counter(self.tokens[doc_id])
    score = 0.0
    for term in query:
        if not counts[term]:
            continue
        idf = math.log(1.0 + (n - self.df[term] + 0.5) / (self.df[term] + 0.5))
        tf = counts[term]
        denom = tf + self.k1 * (
            1 - self.b + self.b * self.lengths[doc_id] / self.avgdl
        )
        score += idf * (tf * (self.k1 + 1)) / denom
    return score
```

安全关键点在循环的顺序：tenant mismatch 在 `_score` 前被排除。

```python
for doc in self.documents:
    if doc.tenant_id != tenant_id:
        excluded[doc.doc_id] = "tenant_mismatch"
        continue
    score = self._score(terms, doc.doc_id)
    if score < min_score:
        excluded[doc.doc_id] = "below_score_threshold"
        continue
    scored.append(SearchHit(...))
```

返回值同时包含 `hits`、`excluded` 与 `abstained`。这使“为什么没检到”也成为可调试证据，而不是只暴露 top-k。

## 主流系统实现对照与源码阅读入口

| 研究/系统 | 核心贡献 | 不能直接外推的结论 |
|---|---|---|
| [BM25 系统综述](https://dl.acm.org/doi/10.1561/1500000019) | 概率相关性、TF/IDF、长度归一化 | 不包含现代租户与提示注入治理 |
| [Dense Passage Retrieval](https://arxiv.org/abs/2004.04906) | 学习 query/passage 表示用于开放域检索 | 相似度不是 authority 或访问权 |
| [RAG](https://arxiv.org/abs/2005.11401) | 参数模型与非参数知识联合生成 | 论文任务指标不等于生产证据链 |
| OpenAI file search / 向量存储类服务 | 托管 ingestion、search 与引用便利 | 数据治理、删除、评测和最终 claim 仍由应用负责 |

阅读任何检索 SDK 时，应从 ingestion identity 追到 filter execution、ranking、result metadata 与 deletion semantics；只看 `search(query)` 示例无法判断生产边界。

## 设计方案与方法对比

| 检索方法 | 强项 | 弱项 | 典型用途 |
|---|---|---|---|
| BM25 | 精确术语、ID、可解释 | 同义改写召回弱 | 工单号、错误码、规范术语 |
| Dense retriever | 语义近邻 | 模型/域漂移、难解释 | 自然语言知识问答 |
| Metadata/SQL | 硬约束、精确 | 非结构化语义弱 | 时间、租户、状态、金额 |
| Knowledge graph | 关系与路径 | 构建治理成本高 | 实体关系、多跳约束 |

工程上常先用 metadata 缩小合法集合，再 lexical/dense ranking；过滤不是 reranking feature。

## 可复现实验

### 实验环境

核心 lab 使用 Python 标准库，语料在进程内构建；无网络、无 embedding 模型、无 API key。SUT 为真实 BM25 计算、tenant gate、threshold 与 provenance report。环境准备：

```bash
uv sync --locked --all-groups --no-install-project
```

### Lab 09A：带来源的 runbook 检索

```bash
PYTHONPATH=src uv run python examples/chapters/ch09_retrieval.py
```

实际 top-1 为 `runbook`，score `9.952768`，source 为 `kb://runbooks/checkpoint-recovery`；无关文档以 `below_score_threshold` 明确排除。该结果是固定 corpus 上的 L1 机制证据，不是通用检索质量声明。

### Lab 09B：高相关跨租户注入

```bash
PYTHONPATH=src uv run python examples/chapters/ch09_retrieval.py --fault
```

注入文档含更多 query 词并诱导忽略审批，但 tenant 为 B。实际报告 `poison: tenant_mismatch`，top-1 仍为 A 租户 runbook，故为 `L3_CONTAINED`。完整实验见 [Lab 09A](../../../labs/core/lab-09A-retrieval.md) 与 [Lab 09B](../../../labs/core/lab-09B-retrieval-fault.md)。

### 关键断点与验收标准

**关键断点**：在 tenant/ACL 硬过滤、DF/IDF 构建、长度归一化、score threshold 和 provenance 组装处记录中间值。**验收标准**：正常实际输出必须返回正确 top-1 与 source URI；高相关跨租户文档必须在评分前被拒绝并留下 `tenant_mismatch`，空命中则明确 abstain。

## 工程场景与系统设计

生产知识库至少分离四个平面：raw object store 保留原文；metadata catalog 管理身份/ACL/时间；index 提供可重建访问路径；evaluation set 保存 query、relevance judgment 和安全攻击。索引不是权威存储，删除/权限变化必须由 catalog 驱动并验证索引传播。

对 200 万文档、100 QPS 的系统，先按 tenant/ACL/time 过滤，再做两阶段检索。cache key 必须包含 corpus version、subject scope 和 query normalization version；否则缓存可能跨租户泄漏或返回撤权前内容。

## 故障模型、失败模式与排错

- **解析丢否定/表格头**：回到 raw source 对比 chunk，不能只调 embedding。
- **ACL 更新未传播**：比较 catalog version、index version 与 query filter trace。
- **无证据仍回答**：检查 threshold、coverage 和 generator 的 abstention contract。
- **旧文档压过新规范**：time/authority 是独立字段，不应只靠相似度。
- **引用存在但不支持 claim**：citation presence 不等于 entailment，需要 claim-evidence verifier。
- **跨语言召回下降**：分别测 query language、document language 与 tokenizer/model。

## 性能、可靠性与工程化

在线指标包括 candidate count、filter latency、ranking latency、top-k score distribution、no-evidence rate、cache hit 和 index freshness lag；质量指标按业务 slice 报 Recall@k/nDCG、citation precision、unsupported-claim rate 与 leakage rate。单一全局平均会掩盖小租户、冷门语言和新文档退化。

索引发布采用 immutable version + alias 切换；新索引先 replay golden queries，再 shadow 流量。灾难恢复要求能从 raw + manifest 重建，而不是备份一个无法解释的向量库快照。

## 技术边界与设计取舍

本章 tokenizer 对中文按单字、英文按词，适合解释 BM25 机制，不代表最佳中文生产分词；三文档 corpus 也不能支持质量外推。要升级证据，应引入公开或脱敏真实 corpus、人工 relevance labels、攻击集和跨版本统计区间。

若选用小型本地 embedding/reranker，应记录模型仓库、文件 SHA-256、revision、量化、pooling、max length 与硬件；若使用 OpenAI embedding/file-search，key 只经环境变量传入，并保存脱敏 request ID、index/vector-store identity、usage 和检索结果，不能提交 secret 或私有文档。

## 前沿研究与演进方向

检索研究正在从静态 top-k 转向多阶段、结构化、时态、多模态和 query-adaptive retrieval。Agent 场景额外要求知道“何时不检索、何时继续检索、何时证据足够”。前沿问题不只是 recall，而是受预算与治理约束的 evidence acquisition policy。

### 深度审计与研究证据链：相似不代表可用

BM25/DPR/RAG 分别提供 lexical、dense 与生成结合的研究基础；本章额外加入 tenant-first filter、provenance 和 abstention。离线小语料实验只能证明实现逻辑和故障包含，不能引用论文分数或托管服务能力冒充本项目结果。

## 本章总结与进阶实践

可靠 RAG 的第一产物不是答案，而是一个经授权、可追溯、可拒绝的 Evidence Set。生成器只能消费它，不能修复其权限和时效缺陷。

进阶问题：

1. 为什么 tenant/ACL 必须在 ranking 前执行？
2. BM25 的长度归一化在哪些文档类型上可能伤害召回？
3. citation precision 与 Recall@k 为什么要同时测？
4. 如何为 no-evidence 选择阈值并校准？
5. index 为什么应视为可重建访问路径而非权威数据？

参考答案见[附录 H：第二篇问题参考答案](../appendix-h-part2-solutions.html#part2-solutions-ch09)。
