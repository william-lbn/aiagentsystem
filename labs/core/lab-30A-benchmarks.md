# Lab 30A — SWE-bench、OSWorld、PaperBench 与 MLE-bench｜正常路径

## 实验目标

验证不变量：**benchmark claims require a fixed task, environment snapshot, and independent verifier**

## 环境与版本

- OS：macOS 13+/Ubuntu 22.04+/WSL2；核心实验不依赖特定内核特性。
- CPU：x86_64 或 arm64；2 核即可。
- Memory：建议 ≥ 4 GiB。
- Python：3.11–3.13；本次发布 QA 使用 Python 3.13.5。
- 核心依赖：AgentLab 本仓库；不需要 API Key、Docker、浏览器或外网。
- 调试器：VS Code Python / PyCharm / `python -m pdb` 均可。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

入口：`examples/chapters/ch30_benchmarks.py`；核心机制：`src/agentlab/course_scenarios.py::benchmarks`。

本实验使用确定性的采购策略回归 fixture：输入、策略、期望决策、schema、seed 与 verifier 都进入 manifest，fixture 采用 canonical JSON 的 SHA-256 作为可比性身份。实验不调用模型，因此它隔离验证 benchmark harness 自身，而不是测模型能力。

## 调试断点

- `src/agentlab/course_scenarios.py::benchmarks`
- `examples/chapters/ch30_benchmarks.py::main`

## 实验 A：正常路径

```bash
PYTHONPATH=src uv run python examples/chapters/ch30_benchmarks.py
```

### 实际验证输出（本发布包 QA 生成）

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "benchmark claims require a fixed task, environment snapshot, and independent verifier", "invariant_holds": true, "observation": {"comparable": true, "manifest": {"fixture_schema": "agentlab.procurement.v1", "fixture_sha256": "43378cebd6017db188c6019184c45e91e92208eae1a7df9318828d1f89716509", "seed": 20260911, "task_id": "procurement-policy-regression-017", "verifier": "policy-decision-and-effect-count/v1"}, "run1": {"fixture_sha256": "43378cebd6017db188c6019184c45e91e92208eae1a7df9318828d1f89716509", "passed_checks": 2, "total_checks": 2}, "run2": {"fixture_sha256": "43378cebd6017db188c6019184c45e91e92208eae1a7df9318828d1f89716509", "passed_checks": 2, "total_checks": 2}}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "benchmarks", "system_detected": false}
```

### 验收标准

PASS 当且仅当：进程退出码为 0；JSON 中 `passed=true`、`fault=false`、`invariant_holds=true`；`evidence_level=L1_MECHANISM` 只证明该确定性 fixture 的正常机制断言成立，不等价于真实外部框架、网络或生产环境已经通过互操作、故障恢复或压力验证。

### 结果解释

这个结果只证明两次 2/2 verifier 结果来自同一个 bit-identical fixture。它不外推成第三方模型或云服务性能结论；真实 coding/browser 路径及其未运行状态见 `experiments/benchmarks/catalog.json`。
