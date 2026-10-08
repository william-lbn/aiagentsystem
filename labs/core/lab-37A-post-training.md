# Lab 37A — Post-training：轨迹谱系、切分污染与发布门禁｜正常路径

## 实验目标

构造带 `task_family`、split、transcript digest、source run、policy、outcome、安全违规与成本的轨迹记录。验证已声明任务族和 exact transcript 在两个 split 中不相交。来源字段只检查非空，不能声称已向真实 run ledger 追溯。

## 可证伪假设与不变量

本地不变量：只有声明字段完整、task-group 字符串不交叉、exact content digest 不交叉的 fixture 才通过 preflight。它不是训练发布的充分条件；随机按行切分不足以阻止同一模板、同一事故或近重复轨迹跨 split。

## 环境与版本

- Python 3.11–3.13，x86_64/arm64；标准库实现；
- 不训练模型、不制造“提升分数”；实验只验证训练前数据控制面；
- 可将通过审计的 JSONL 交给本地小模型或 OpenAI fine-tuning；API key 只能由环境注入。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
samples = [
    TrajectorySample("train-1", "billing-train", "train", "tool read invoice 7", "run-1", "p0", 1, 0, 3),
    TrajectorySample("eval-1", "billing-heldout", "eval", "audit invoice 42", "run-3", "p0", 1, 0, 4),
]
audit = PostTrainingDatasetGate().audit(samples)
assert audit.promotion_allowed and audit.status == "DATASET_ELIGIBLE"
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch37_post_training.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"status":"DATASET_ELIGIBLE","train_records":2,"eval_records":2,"leaked_task_families":[],"duplicate_transcripts":[],"checks":{"non_empty_splits":true,"unique_sample_ids":true,"group_disjoint":true,"transcript_disjoint":true,"complete_provenance":true,"bounded_labels":true},"evidence_level":"L1_MECHANISM"}
```

## 调试断点

- transcript canonicalization 与 SHA-256；
- task-family 归组是否早于随机切分；
- source run / policy id 是否随记录持久化；
- reward 各维度是否被错误压成一个平均数。

## 验收标准

退出码 0；train/eval 均非空；所有六项 check 为真；状态为 `DATASET_ELIGIBLE`，仅表示当前六项静态检查通过。L1 不声明来源真实性、语义无泄漏、模型训练或质量提升。

## 反例与进阶注入

- 对近重复 transcript 使用 MinHash/embedding 聚类，再按 cluster 切分；
- 用时间切分测未来分布，单独保留真实 incident holdout；
- 对同一数据分别训练小型开源模型与远程模型，但必须固定训练配置并保留真实 artifact/usage/eval。
