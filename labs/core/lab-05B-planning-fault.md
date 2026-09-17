# Lab 05B — 缺失部署能力的 fail-before-execute｜故障注入

## 实验目标

从 capability manifest 删除 `deploy_change`；要求完整计划在执行之前被判为不可行，不暴露可被误用的部分 execution order。

## 环境与版本

Python `3.11–3.13`；macOS/Linux；`arm64/x86_64`；无网络、Docker 或 API key。与 05A 使用同一 DAG 和预算。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码与故障模型

入口 `examples/chapters/ch05_planning.py --fault`。唯一自变量是能力集合缺失 `deploy_change`；`apply` 步骤仍显式声明该能力，因而 checker 必须识别而不是让 planner 换名逃避。

## 运行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch05_planning.py --fault
```

## 实际验证输出

```json
{"errors": ["unavailable_capability:apply:deploy_change"], "execution_order": [], "execution_started": false, "feasible": false, "total_cost": 17}
```

## 调试断点

在 capability membership 检查确认错误绑定 step `apply`；在 validator 返回处确认即使内部算出部分顺序，对外仍为空；scheduler 入口不得命中。

## 验收标准

reason code 精确、feasible 为 false、执行顺序为空、执行未启动；结果为 `system_detected=true/contained=true/L3_CONTAINED`。

## 证据解释与上限

L3 证明本地静态 checker 约束了缺能力计划，不证明系统能自动获得能力或完成目标。无业务恢复，所以不是 L4。

## 进阶实验

比较三种策略：严格拒绝、删除 apply/verify 后降级为只读报告、请求人工提供能力。为每种策略定义不同后置条件，禁止把降级报告标为原任务完成。
