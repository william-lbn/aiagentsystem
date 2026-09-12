# Lab 30B — SWE-bench、OSWorld、PaperBench 与 MLE-bench｜故障注入

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

本实验故意把第二次运行的审批阈值从 5,000 美元漂移到 10,000 美元。两次运行仍各自显示 2/2 checks，但 canonical fixture hash 不同；oracle 必须拒绝跨 fixture 比分。

## 调试断点

- `src/agentlab/course_scenarios.py::benchmarks`
- `examples/chapters/ch30_benchmarks.py::main`

## 实验 B：故障注入路径

```bash
PYTHONPATH=src uv run python examples/chapters/ch30_benchmarks.py --fault
```

### 实际验证输出（本发布包 QA 生成）

```json
{"contained": false, "evidence_level": "L2_ORACLE_ONLY", "evidence_meaning": "external_oracle_observed_bad_outcome_only", "fault": true, "fault_injected": true, "invariant": "benchmark claims require a fixed task, environment snapshot, and independent verifier", "invariant_holds": false, "observation": {"comparable": false, "manifest": {"fixture_schema": "agentlab.procurement.v1", "fixture_sha256": "43378cebd6017db188c6019184c45e91e92208eae1a7df9318828d1f89716509", "seed": 20260911, "task_id": "procurement-policy-regression-017", "verifier": "policy-decision-and-effect-count/v1"}, "run1": {"fixture_sha256": "43378cebd6017db188c6019184c45e91e92208eae1a7df9318828d1f89716509", "passed_checks": 2, "total_checks": 2}, "run2": {"fixture_sha256": "cfbdc21ccd0eaf6d1231f51f0bddfc4888c3bc33a8caf1720de1d80460811446", "passed_checks": 2, "total_checks": 2}}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "benchmarks", "system_detected": false}
```

### 验收标准

PASS 当且仅当：进程退出码为 0；JSON 中 `passed=true`、`fault=true`、`oracle_detected=true`。本实验的证据等级为 **`L2_ORACLE_ONLY`**：独立 oracle 成功观察到故障；**不证明系统已经检测、约束或恢复该故障**。 `passed=true` 仅表示“实验 oracle 得到了预期观察”，不得脱离上述证据字段解释为生产级故障恢复成功。

特别注意：两个局部 verifier 都返回 2/2，正是这个 fault 的重点。若 leaderboard 聚合器只读取 score 而不校验 fixture identity，就会把不可比较的结果错误排序。

### 进阶修改

把 fixture 中的故障位置向前或向后移动一步，重新运行并记录状态变化；说明新的恢复点为什么不同。
