# Lab 10A — BM25、字符三元组与 RRF｜正常路径

## 实验目标

真实执行两个不同检索算法，使用 RRF 融合并保留 `doc_id → retrievers` provenance。字符三元组 cosine 是确定性 lexical-shape baseline，明确不是 neural embedding。

## 环境与版本

Python 3.11–3.13，无网络/GPU/API key。SUT：`BM25Index`、`CharacterNgramIndex`、`reciprocal_rank_fusion`。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；两路索引都由固定语料在进程内重建。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch10_hybrid_rag.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"invariant_holds":true,"observation":{"fused":[["runbook",0.03278689],["approval",0.01612903],["retrieval",0.01587302]],"provenance":{"approval":["char_ngram"],"retrieval":["char_ngram"],"runbook":["bm25","char_ngram"]},"rankings":{"bm25":["runbook"],"char_ngram":["runbook","approval","retrieval"]},"rejected":{}},"passed":true,"scenario":"hybrid-rag"}
```

## 调试断点

断点放在每路 ranking、allowed universe 和 fusion accumulator；检查 provenance 只在文档通过 gate 后写入。

## 验收标准

要求 runbook top-1，并同时来自两路；分数严格由 `1/(60+rank)` 累加。交换 adapter 顺序不应改变最终稳定排序。

## 扩展到真实小模型

可将第二路替换为锁定 revision 的小型多语 embedding 模型，但要记录权重 SHA-256、量化、pooling、max length、CPU/GPU 和完整依赖；新增 dense-only/hybrid 消融，不得把本 lab 的字符算法称作 embedding 结果。
