# Lab 25B — Research Agent：证据链、引用与报告生成｜故障注入

## 实验目标

验证不变量：**every externally checkable claim needs a traceable evidence object**

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

入口：`examples/chapters/ch25_research_agent.py`；核心机制：`src/agentlab/course_scenarios.py::research_agent`。

本实验输入由 `research_agent` 中固定 fixture 定义，保证每次运行能够比较同一状态转移。

## 调试断点

- `src/agentlab/course_scenarios.py::research_agent`
- `examples/chapters/ch25_research_agent.py::main`

## 实验 B：故障注入路径

```bash
PYTHONPATH=src uv run python examples/chapters/ch25_research_agent.py --fault
```

### 实际验证输出（本发布包 QA 生成）

```json
{"contained": true, "evidence_level": "L3_CONTAINED", "evidence_meaning": "fault_detected_and_contained", "fault": true, "fault_injected": true, "invariant": "every externally checkable claim needs a traceable evidence object", "invariant_holds": true, "observation": {"claims": [["MCP protocol revision", "s1"], ["A2A interoperability", "s2"], ["unverified benchmark gain", "missing"]], "missing_evidence": ["unverified benchmark gain"]}, "oracle_detected": true, "passed": true, "recovered": false, "scenario": "research-agent", "system_detected": true}
```

### 验收标准

PASS 当且仅当：进程退出码为 0；JSON 中 `passed=true`、`fault=true`、`oracle_detected=true`。本实验的证据等级为 **`L3_CONTAINED`**：被测组件显式检测故障并 fail-closed/阻断错误继续扩散；不声明已经恢复业务结果。 `passed=true` 仅表示“实验 oracle 得到了预期观察”，不得脱离上述证据字段解释为生产级故障恢复成功。

### 进阶修改

把 fixture 中的故障位置向前或向后移动一步，重新运行并记录状态变化；说明新的恢复点为什么不同。
