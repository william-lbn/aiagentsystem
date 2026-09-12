# Lab 02A — 模型基座：Token、结构化生成、工具调用与推理接口｜正常路径

## 实验目标

验证不变量：**model output crossing a software boundary must be parsed and validated**

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

入口：`examples/chapters/ch02_model_substrate.py`；核心机制：`src/agentlab/course_scenarios.py::model_substrate`。

本实验输入由 `model_substrate` 中固定 fixture 定义，保证每次运行能够比较同一状态转移。

## 调试断点

- `src/agentlab/course_scenarios.py::model_substrate`
- `examples/chapters/ch02_model_substrate.py::main`

## 实验 A：正常路径

```bash
PYTHONPATH=src uv run python examples/chapters/ch02_model_substrate.py
```

### 实际验证输出（本发布包 QA 生成）

```json
{"contained": false, "evidence_level": "L1_MECHANISM", "evidence_meaning": "normal_path_assertion_satisfied", "fault": false, "fault_injected": false, "invariant": "model output crossing a software boundary must be parsed and validated", "invariant_holds": true, "observation": {"object": {"args": {"q": "agent runtime"}, "tool": "search"}, "parsed": true, "token_proxy": 6}, "oracle_detected": false, "passed": true, "recovered": false, "scenario": "model-substrate", "system_detected": false}
```

### 验收标准

PASS 当且仅当：进程退出码为 0；JSON 中 `passed=true`、`fault=false`、`invariant_holds=true`；`evidence_level=L1_MECHANISM` 只证明该确定性 fixture 的正常机制断言成立，不等价于真实外部框架、网络或生产环境已经通过互操作、故障恢复或压力验证。

### 结果解释

这个结果只证明本仓库确定性 fixture 在上述机制上满足预期，不外推成第三方模型或云服务性能结论。
