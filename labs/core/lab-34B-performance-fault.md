# Lab 34B — 性能与成本：Token、延迟、并发和缓存｜故障注入

## 实验目标

验证不变量：**end-to-end latency is a critical path across model, tools, persistence, and retries**

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

入口：`examples/chapters/ch34_performance.py`；核心机制：`src/agentlab/course_scenarios.py::performance`。

本实验输入由 `performance` 中固定 fixture 定义，保证每次运行能够比较同一状态转移。

## 调试断点

- `src/agentlab/course_scenarios.py::performance`
- `examples/chapters/ch34_performance.py::main`

## 实验 B：故障注入路径

```bash
PYTHONPATH=src uv run python examples/chapters/ch34_performance.py --fault
```

### 实际验证输出（本发布包 QA 生成）

```json
{"contained": false, "evidence_level": "L2_ORACLE_ONLY", "evidence_meaning": "external_oracle_observed_bad_outcome_only", "fault": true, "fault_injected": true, "invariant": "end-to-end latency is a critical path across model, tools, persistence, and retries", "invariant_holds": false, "observation": {"slo_ms": 250, "stages": {"checkpoint_ms": 5, "model_ms": 120, "retry_ms": 200, "tool_ms": 80}, "total_ms": 405, "within_slo": false}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "performance", "system_detected": false}
```

### 验收标准

PASS 当且仅当：进程退出码为 0；JSON 中 `passed=true`、`fault=true`、`oracle_detected=true`。本实验的证据等级为 **`L2_ORACLE_ONLY`**：独立 oracle 成功观察到故障；**不证明系统已经检测、约束或恢复该故障**。 `passed=true` 仅表示“实验 oracle 得到了预期观察”，不得脱离上述证据字段解释为生产级故障恢复成功。

### 进阶修改

把 fixture 中的故障位置向前或向后移动一步，重新运行并记录状态变化；说明新的恢复点为什么不同。
