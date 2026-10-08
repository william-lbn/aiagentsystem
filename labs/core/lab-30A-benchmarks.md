# Lab 30A — SWE-bench、OSWorld、PaperBench 与 MLE-bench｜正常路径

## 实验目标

验证 benchmark 的身份先于分数：只有 task set、environment、verifier、harness revision 和 seed 全部一致，两次 run 才允许聚合或排序；同时对 5 个确定性任务报告 Wilson 95% 区间，避免把小样本 `5/5` 误写成已知的真实成功率 100%。

## 环境与版本

- Python 3.11–3.13；x86_64/arm64；核心实验不需要 Docker、网络、模型或 API key；
- fixture 是本地采购规则，不冒充 SWE-bench/WebArena 成绩；
- 外部 coding/browser 合约状态仍为 `NOT_EXECUTED_IN_THIS_RELEASE`，见 `experiments/benchmarks/catalog.json`。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

入口为 `examples/chapters/ch30_benchmarks.py`；`BenchmarkManifest` 和 `compare_manifests` 位于 `src/agentlab/assurance_system.py`。Manifest 本身也 canonical hash：

```python
manifest = BenchmarkManifest(
    benchmark="agentlab-procurement-5",
    task_set_digest=content_digest(tasks),
    environment_digest="sha256:publisher-image-locked",
    verifier_digest=content_digest(verifier_contract),
    harness_revision="agentlab-assurance-v1",
    seed=20260911,
)
decision = compare_manifests(manifest, replay_manifest)
report = benchmark_report(manifest, verified_outcomes)
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch30_benchmarks.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"comparability":{"aggregate_allowed":true,"comparable":true,"mismatches":[]},"aggregate_published":true,"report":{"accuracy":1.0,"successes":5,"tasks":5,"wilson_95":[0.5655,1.0]},"evidence_level":"L1_MECHANISM"}
```

## 调试断点

- `BenchmarkManifest.digest`：确认所有受控变量进入身份；
- `compare_manifests`：确认在计算跨 run delta 前执行；
- `wilson_interval`：观察为什么 `5/5` 的下界只有约 0.5655；
- `aggregate_published`：确认由 comparability gate 决定，不由高分决定。

## 验收标准

退出码 0；`mismatches=[]`、`aggregate_allowed=true`；report 为 `5/5` 且带区间。L1 证明本地 harness 身份与统计报告机制，不证明任一大模型能力。

## 外部基准执行约束

真实 SWE-bench 必须保存实例、repository/base commit、test patch、Docker image、harness commit、模型配置、完整 patch 和官方 evaluator 输出；真实 browser benchmark 还需站点 snapshot/reset、账户状态和 action/observation trajectory。预检通过不等于 benchmark 已运行，下载数据不等于任务 resolved。
