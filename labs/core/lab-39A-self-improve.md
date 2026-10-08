# Lab 39A — Self-Improving Agent：配对评测、Canary 与版本提升｜正常路径

## 实验目标

在同一组四个任务上比较 baseline/candidate：candidate 的 verified success 提升 0.25，成本比 1.025，且没有安全回归。通过离线 hard gate 后进入 canary；独立 verifier 通过才把 active version 从 v1 切到 v2。

## 可证伪假设与不变量

不变量：自我改进产生的是候选 artifact，不是修改生产的权限。candidate 必须在独立、配对、版本化的 eval 上过门，并保留 baseline。本实验只模拟单进程内存指针，不验证生产原子回退。

## 环境与版本

- Python 3.11–3.13；纯标准库；不需要模型或 API key；
- 结果是 rollout 控制面的真实执行，不是训练算法质量实验；
- 实际 prompt/skill/model 优化时，应保存 candidate digest、生成 lineage、held-out results 和 canary telemetry。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
decision = ImprovementGate().compare(baseline, candidate)
assert decision.eligible
rollout = CanaryRollout("policy-v1")
rollout.start("policy-v2", decision)
action = rollout.finish(verifier_passed=True, safety_violations=0)
assert action == "PROMOTED" and rollout.active_version == "policy-v2"
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch39_self_improve.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"offline_gate":{"status":"CANARY_ELIGIBLE","success_delta":0.25,"cost_ratio":1.025,"eligible":true,"checks":{"paired_tasks":true,"success_improves":true,"no_safety_regression":true,"no_high_risk_regression":true,"cost_within_budget":true}},"canary_action":"PROMOTED","active_version":"policy-v2","history":["ACTIVE:policy-v1","CANARY:policy-v2","PROMOTED:policy-v2"],"evidence_level":"L1_MECHANISM"}
```

## 调试断点

- baseline/candidate task ids 是否完全相同；
- 安全指标是否 hard gate 而非与 success 求平均；
- canary 开始时 baseline 是否仍可寻址；
- promotion 是否只改变 active pointer，不覆盖历史 artifact。

## 验收标准

退出码 0；五项离线 check 全真；candidate 进入内存 canary 状态后才 promotion；active version 为 v2。L1 不声称候选来自模型自动优化、真实线上 canary、跨进程原子性或用户收益。

## 反例与进阶注入

- 用 bootstrap/随机种子报告置信区间，不凭四个样本发布生产模型；
- 按 tenant、语言、风险层做 slice，防止总体改善掩盖子群退化；
- 让 candidate 修改 evaluator，确认权限和 digest gate 阻断 Goodhart 攻击。
