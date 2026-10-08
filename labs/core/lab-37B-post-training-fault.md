# Lab 37B — Post-training：轨迹谱系、切分污染与发布门禁｜故障注入

## 实验目标

把一条 train transcript 复制到 eval，并保留相同 `task_family`。验证系统同时识别 group leakage 与字节级 transcript duplication，将数据集置为 `QUARANTINED`。

## 可证伪假设与故障位置

若仅按 sample id 去重，复制后改名即可绕过；若仅按 transcript 去重，同一任务模板的改写仍会泄漏。故障同时打穿两层，要求 gate 自己阻断而非等模型分数异常后再猜污染。

## 环境与版本

与 Lab 37A 相同。样本为显式教学 fixture；没有运行 SFT、DPO 或 RFT，因此不会伪造 loss、reward 或 benchmark 数值。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
samples.append(TrajectorySample(
    "leaked-copy", "billing-train", "eval",
    "tool read invoice 7", "run-leak", "p0", 1, 0, 3,
))
audit = PostTrainingDatasetGate().audit(samples)
assert audit.status == "QUARANTINED"
assert not audit.checks["group_disjoint"]
assert not audit.checks["transcript_disjoint"]
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch37_post_training.py --fault
```

## 实际验证输出（本发布源码执行所得）

```json
{"status":"QUARANTINED","train_records":2,"eval_records":3,"leaked_task_families":["billing-train"],"duplicate_transcripts":["7e1f4255876157343e9aab7f30b129be1f9483964d9c44f86f1cb110bb1dd9a9"],"promotion_allowed":false,"system_detected":true,"contained":true,"evidence_level":"L3_CONTAINED"}
```

## 调试断点

- `task_family` 交集；
- train/eval digest 交集；
- quarantine 之后训练 job 是否仍可取到该 manifest；
- audit 输出能否定位污染而不泄露原始敏感 transcript。

## 验收标准

退出码 0；两项 disjoint check 为 false；promotion 被阻断；证据为 L3。它只证明污染数据未进入本实验的后续阶段，不证明历史模型没有见过相似数据。

## 反例与进阶注入

- 对 transcript 做轻微改写，展示 exact digest 的盲区；
- 同一用户/仓库/事故跨任务 id，要求按实体或时间归组；
- 让生成策略与 judge 为同一模型，测 correlated error 与 preference self-bias。
