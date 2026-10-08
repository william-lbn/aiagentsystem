# Lab 39B — Self-Improving Agent：配对评测、Canary 与版本提升｜故障注入

## 实验目标

候选通过离线 gate，但 canary 独立 verifier 发现一条安全违规。验证 active pointer 回到 `policy-v1`，候选记录为 `ROLLED_BACK`，而不是因离线均值较高继续扩大流量。

## 可证伪假设与故障位置

离线分布无法覆盖线上状态、工具与攻击。本实验把 canary verifier 失败作为**注入的观察值**，不是少量真实用户流量；内存状态机必须保留 baseline。真实发布还要冻结扩容并把 incident 写入回归集。

## 环境与版本

与 Lab 39A 相同。fault 是可审计的 canary observation；没有虚构在线用户流量或模型结果。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
rollout = CanaryRollout("policy-v1")
rollout.start("policy-v2", eligible_decision)
action = rollout.finish(verifier_passed=False, safety_violations=1)
assert action == "ROLLED_BACK"
assert rollout.active_version == "policy-v1"
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch39_self_improve.py --fault
```

## 实际验证输出（本发布源码执行所得）

```json
{"offline_gate":{"status":"CANARY_ELIGIBLE","success_delta":0.25,"cost_ratio":1.025,"eligible":true},"canary_action":"ROLLED_BACK","active_version":"policy-v1","history":["ACTIVE:policy-v1","CANARY:policy-v2","ROLLED_BACK:policy-v2"],"system_detected":true,"contained":true,"evidence_level":"L3_CONTAINED"}
```

## 调试断点

- offline eligible 与 online promote 必须是不同状态；
- safety violation 是否立即阻断流量扩大；
- rollback 是否只切指针、不删除失败 evidence；
- active version 查询是否可能被 cache/stale config 延迟。

## 验收标准

退出码 0；offline gate 仍为 eligible；canary action 为 `ROLLED_BACK`；单进程 active version 为 v1；证据为内存状态机的 L3。L3 不表示候选造成的任何外部 effect 已自动补偿，也不证明跨进程持久回滚。

## 反例与进阶注入

- rollout 过程中进程崩溃，重启后根据 durable active pointer 收敛；
- 多区域配置传播不一致，验证 kill switch 与版本 fencing；
- 将 canary incident 固化为 held-out regression，但防止再次进入训练 split。
