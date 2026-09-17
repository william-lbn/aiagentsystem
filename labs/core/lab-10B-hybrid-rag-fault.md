# Lab 10B — 损坏 Retriever Adapter 注入未知 ID｜故障注入

## 实验目标

字符检索 adapter 在 rank 1 返回不属于 authorized corpus 的 `foreign-secret`。融合器不能假设上游已正确鉴权，必须拒绝该 ID 并保留 reason。

## 环境与版本

Python 3.11–3.13，macOS/Linux、arm64/x86_64；无网络/GPU/API key，SUT 与 Lab 10A 相同。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；未知 ID 由确定性损坏 adapter 注入，不读取外部数据。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch10_hybrid_rag.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"invariant_holds":true,"observation":{"fused":[["runbook",0.03252247],["approval",0.01587302],["retrieval",0.015625]],"provenance":{"approval":["char_ngram"],"retrieval":["char_ngram"],"runbook":["bm25","char_ngram"]},"rankings":{"bm25":["runbook"],"char_ngram":["foreign-secret","runbook","approval","retrieval"]},"rejected":{"char_ngram:1:foreign-secret":"unknown_or_forbidden_document"}},"oracle_detected":true,"passed":true,"scenario":"hybrid-rag","system_detected":true}
```

## 验收标准

未知 ID 必须出现在 rejected 且不在 fused；合法 runbook 仍为 top-1。故障到达融合入口并被包含，等级 L3。若只在最终回答中“碰巧未引用”它，不算包含。

## 调试断点

- `allowed_ids`：确认来自当前 tenant 的 corpus manifest；
- adapter 排名循环：检查 duplicate 与 unknown 两道 gate；
- provenance accumulator：被拒绝 ID 不得留下来源或分数；
- stable sort：跨主机同输入结果一致。

## Claim ceiling

本实验不验证真实向量数据库或 reranker。外部升级要故意制造错 namespace/index-version 的返回值，并由独立 verifier 检查融合输出和访问日志。
