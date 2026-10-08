# Lab 38B — 实时多模态 Agent：事件时间与取消 epoch｜故障注入

## 实验目标

候选工具工作在 epoch 0 注册但**未向外部执行器派发**；用户随后说“stop”，session 切换到 epoch 1；旧结果仍到达。验证 completion 被记录为 `STALE_DROPPED`，不会产生本地 commit。不能由此推断已派发的物理动作被撤销。

## 可证伪假设与故障位置

取消请求并不等于工作已经停止。故障位于“打断已确认”和“旧异步 completion 到达”之间；若只设置布尔 `cancelled` 后又被 completion 覆盖，机器人/浏览器仍可能执行用户已撤回的动作。

## 环境与版本

与 Lab 38A 相同。取消传播使用确定性 epoch，不依赖线程调度运气；因此能在任意 CPU 架构稳定复现。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
epoch = session.begin_effect("move-1", 110, {"distance_cm": 5})
session.interrupt(115, "stop")
outcome = session.complete_effect("move-1", epoch, 120, {"moved": True})
assert outcome == "STALE_DROPPED"
assert session.effects == []
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch38_multimodal.py --fault
```

## 实际验证输出（本发布源码执行所得）

```json
{"outcome":"STALE_DROPPED","active_epoch":1,"effect_count":0,"last_event":{"seq":5,"event_time_ms":120,"modality":"tool","kind":"effect.stale_dropped","epoch":1},"system_detected":true,"contained":true,"evidence_level":"L3_CONTAINED"}
```

## 调试断点

- interrupt 是否先原子增加 epoch 再发布事件；
- inflight effect 保存的 started epoch；
- stale completion 是否跳过本地 effect ledger；外部 actuator 不在本实验中；
- dropped 事件能否用于延迟和取消可靠性分析。

## 验收标准

退出码 0；active epoch 为 1；结果为 `STALE_DROPPED`；本地 commit count 为 0；L3 containment 仅限本地结果提交边界。它不证明底层硬件真的停止；真实系统还需要独立 E-stop、actuator receipt 与传感器 observation。

## 反例与进阶注入

- 打断后底层 effect 已不可逆提交，应转入 UNKNOWN/reconciliation，而不是简单丢弃响应；
- 多个并行工具只取消部分 scope，验证 parent/child cancellation；
- 同 timestamp 不同来源时，引入 source clock、watermark 与确定性 tie-break。
