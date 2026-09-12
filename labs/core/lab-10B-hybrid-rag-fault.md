# Lab 10B — Hybrid / Agentic RAG：让检索成为决策过程｜故障注入

## 实验目标

验证不变量：**hybrid retrieval must retain per-retriever provenance before fusion**

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

入口：`examples/chapters/ch10_hybrid_rag.py`；核心机制：`src/agentlab/course_scenarios.py::hybrid_rag`。

本实验输入由 `hybrid_rag` 中固定 fixture 定义，保证每次运行能够比较同一状态转移。

## 调试断点

- `src/agentlab/course_scenarios.py::hybrid_rag`
- `examples/chapters/ch10_hybrid_rag.py::main`

## 实验 B：故障注入路径

```bash
PYTHONPATH=src uv run python examples/chapters/ch10_hybrid_rag.py --fault
```

### 实际验证输出（本发布包 QA 生成）

```json
{"contained": false, "evidence_level": "L2_ORACLE_ONLY", "evidence_meaning": "external_oracle_observed_bad_outcome_only", "fault": true, "fault_injected": true, "invariant": "hybrid retrieval must retain per-retriever provenance before fusion", "invariant_holds": false, "observation": {"dense": ["x1", "x2", "x3"], "rrf": [["d1", 0.01639344262295082], ["x1", 0.01639344262295082], ["d3", 0.016129032258064516], ["x2", 0.016129032258064516]], "sparse": ["d1", "d3", "d2"]}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "hybrid-rag", "system_detected": false}
```

### 验收标准

PASS 当且仅当：进程退出码为 0；JSON 中 `passed=true`、`fault=true`、`oracle_detected=true`。本实验的证据等级为 **`L2_ORACLE_ONLY`**：独立 oracle 成功观察到故障；**不证明系统已经检测、约束或恢复该故障**。 `passed=true` 仅表示“实验 oracle 得到了预期观察”，不得脱离上述证据字段解释为生产级故障恢复成功。

### 进阶修改

把 fixture 中的故障位置向前或向后移动一步，重新运行并记录状态变化；说明新的恢复点为什么不同。
