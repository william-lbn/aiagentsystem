# Lab 09A — BM25、来源与拒答边界｜正常路径

## 实验目标

在固定语料上真实计算 BM25，验证 runbook 进入 top-1，每个 hit 带 source URI/observed metadata，并让低分文档显式进入 excluded report。

## 环境与版本

Python 3.11–3.13；无网络、embedding 或 API key。SUT：`knowledge_system.BM25Index`；tokenizer 对英文按词、中文按字。该 tokenizer 是教学边界，不代表最佳中文生产方案。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；语料由场景在内存构建，无需下载模型或索引。

## 语料和查询

Tenant A 有 checkpoint runbook、审批 policy、retrieval architecture 三文档。查询为 “resume a long running agent from checkpoint after process restart”。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch09_retrieval.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"invariant_holds":true,"observation":{"abstained":false,"excluded":{"approval":"below_score_threshold","retrieval":"below_score_threshold"},"hits":[{"doc_id":"runbook","score":9.952768,"source_uri":"kb://runbooks/checkpoint-recovery"}]},"passed":true,"scenario":"retrieval"}
```

## 调试断点

在 DF 构建、IDF、长度归一化和 threshold 处观察实际数值；确认 tenant gate 在评分之前。

## 验收标准

PASS 要求 top-1/source 精确匹配，且结果非裸文本。另运行 query `stellar nucleosynthesis`，单测要求 `hits=()` 与 `abstained=true`。

## 证据边界

三文档 fixture 只验证公式、排序和报告结构，不支持对真实知识库 Recall@k 的结论。质量评测需人工 relevance labels、更多 query 和统计区间。
