# Lab 05A — 六阶段事故计划的静态可行性｜正常路径

## 实验目标

验证 `collect → diagnose → propose → approve → apply → verify` 的依赖 DAG 在能力齐全且预算 20 时可行，并只在所有约束通过后发布执行顺序。

## 环境与版本

Python `3.11–3.13`；macOS/Linux；`arm64/x86_64`；无网络、Docker 或 API key。固定整数 cost 是教学资源单位，不是云账单或真实时延。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与输入

入口 `examples/chapters/ch05_planning.py`；SUT `foundation_system.py::PlanValidator`。六步分别要求读指标、分析 trace、起草变更、人工审批、部署和再次读指标；总成本 17，所有 capability 显式提供。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch05_planning.py
```

## 实际验证输出

```json
{"errors": [], "execution_order": ["collect", "diagnose", "propose", "approve", "apply", "verify"], "execution_started": true, "feasible": true, "total_cost": 17}
```

## 调试断点

检查 step ID 映射、dependency existence、capability set、indegree、稳定 ready queue、cycle 判定、budget gate 和最终 execution order 发布。

## 验收标准

无错误、总成本 17、顺序满足全部依赖、`feasible/execution_started=true`，完整结果 `invariant_holds=true/L1_MECHANISM`。

## 证据解释与上限

实验只证明静态结构/能力/预算可行，不执行任何真实部署，也不证明动作前置条件、持续时间、权限或结果成功。

## 进阶实验

增加两个只读并行分支和一个 fan-in，枚举所有合法拓扑序；随后给资源加并发上限，把 plan feasibility 与 schedule feasibility 分开报告。
