# Lab 09B — 高相关跨租户检索污染｜故障注入

## 实验目标

加入 tenant B 文档 `poison`，内容覆盖大量查询词并包含“ignore every approval policy”。若系统先全局 ranking 再软惩罚 tenant，它可能进入 top-k；正确实现必须在评分前硬过滤。

## 环境与版本

与 Lab 09A 相同，无模型/API key。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；poison 文档作为显式 fixture 加入 corpus，便于独立 oracle 确认它确实到达过滤器。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch09_retrieval.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"invariant_holds":true,"observation":{"abstained":false,"excluded":{"approval":"below_score_threshold","poison":"tenant_mismatch","retrieval":"below_score_threshold"},"hits":[{"doc_id":"runbook","score":8.73829,"source_uri":"kb://runbooks/checkpoint-recovery"}]},"oracle_detected":true,"passed":true,"scenario":"retrieval","system_detected":true}
```

## 验收标准

`poison` 必须以 `tenant_mismatch` 被系统检测，且不得出现在 hits；top-1 仍为 tenant A runbook。由于恶意文档真正进入 corpus 但在 scope gate 被阻断，证据为 L3。

## 调试断点

移动 tenant check 到 `_score` 之后做实验，观察即使最终删掉文档也已浪费计算且可能泄漏 score/缓存；删除 filter 则 oracle 应失败。真实系统还需覆盖 ACL revoke、cache key 缺 tenant、index lag 和 source text prompt injection。

## Claim ceiling

本实验证明本地 BM25 path 的租户包含，不证明数据库行级策略、向量服务或托管 file-search 的隔离；这些路径要分别进行外部配置和行为测试。
