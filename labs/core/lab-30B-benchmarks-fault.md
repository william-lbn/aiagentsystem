# Lab 30B — SWE-bench、OSWorld、PaperBench 与 MLE-bench｜故障注入

## 实验目标

给第二次 run 注入未声明的 environment digest 漂移。即使局部任务仍显示 `5/5`，comparability gate 也必须拒绝聚合，防止 leaderboard 把不同环境的数字当作模型差异。

## 可证伪假设与故障位置

假设：point score 不能证明结果可比较。故障只改变 `environment_digest`，保留 task/verifier/harness/seed 与分数不变；若系统仍发布 aggregate，则 provenance gate 失效。

## 环境与版本

与 Lab 30A 相同；无模型、网络、Docker 或 API key。这个实验测试 benchmark control plane，而不是模型能力。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
replay_manifest = replace(
    manifest,
    environment_digest="sha256:unreviewed-host-drift",
)
decision = compare_manifests(manifest, replay_manifest)
assert not decision.aggregate_allowed
```

入口为 `examples/chapters/ch30_benchmarks.py`；真实实现显式比较六个受控字段，而不是仅比较一个显示名称。

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch30_benchmarks.py --fault
```

## 实际验证输出（本发布源码执行所得）

```json
{"comparability":{"aggregate_allowed":false,"comparable":false,"mismatches":["environment_digest"]},"aggregate_published":false,"report":{"accuracy":1.0,"successes":5,"tasks":5,"wilson_95":[0.5655,1.0]},"system_detected":true,"contained":true,"evidence_level":"L3_CONTAINED"}
```

## 调试断点

- manifest 构造后比较两个 environment digest；
- comparability gate 前确认两侧局部分数相同；
- gate 后确认 aggregate/export 路径未被调用；
- `_ok` 确认 L3 是发布被阻断，不是离线脚本打印 warning。

## 验收标准

退出码 0；唯一 mismatch 是 `environment_digest`；`aggregate_published=false`、`contained=true`、`evidence_level=L3_CONTAINED`。若仍输出排名或 delta，实验失败。

## 反例与进阶注入

- 分别漂移 verifier digest、task set、harness revision、seed，确认每项都 fail closed；
- 在相同 manifest 下运行多个真实模型 seed，报告均值、分布和 paired outcome，而不是只选最好一次；
- 让 Docker tag 相同但 image digest 不同，证明 tag 不能充当环境身份；
- 将 `NOT_EXECUTED`、`UNSUPPORTED`、`FAILED_PREFLIGHT`、`SCORE=0` 设为不同状态，防止证据语义混淆。
