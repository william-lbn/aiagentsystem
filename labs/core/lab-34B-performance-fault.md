# Lab 34B — 性能与成本：Token、延迟、并发和缓存｜故障注入

## 实验目标

在 tool stage 注入真实约 30ms 延迟，而该段预算为 15ms。验证测量器定位到具体 stage，并由 release gate 阻止超预算构建；不是事后打印一条慢日志仍继续发布。

## 可证伪假设与故障位置

若系统只检查总平均、只检查最终成功或使用手填 timing，局部尾延迟可能被掩盖。本实验保持 assemble/persist 正常，仅改变 tool critical path，使故障归因可验证。

## 环境与版本

与 Lab 34A 相同。`sleep(0.03)` 是显式故障注入，elapsed 仍由时钟实测；调度器可能使数值高于 30ms，因此不设等值断言。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
operations = [
    ("assemble", assemble_context),
    ("tool", lambda: measured_delay(0.03)),
    ("persist", persist_checkpoint),
]
report = probe.measure(operations)
assert not report.release_allowed
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch34_performance.py --fault
```

## 实际验证输出（本机一次真实执行，数值允许随主机变化）

```json
{"release_allowed":false,"stages":[{"stage":"assemble","within_budget":true},{"stage":"tool","budget_ms":15,"elapsed_ms":30.788,"within_budget":false},{"stage":"persist","within_budget":true}],"total_budget_ms":50,"total_ms":30.924,"within_budget":false,"system_detected":true,"contained":true,"evidence_level":"L3_CONTAINED"}
```

## 调试断点

- delay 调用前后确认实际 elapsed；
- tool stage 比较 `elapsed_ms > 15`；
- total 即使仍小于 50，也必须因 stage breach 失败；
- release path 确认未被调用。

## 验收标准

退出码 0；tool stage `within_budget=false`，assemble/persist 仍正常；整个 report `within_budget=false`、`release_allowed=false`、`evidence_level=L3_CONTAINED`。注意：本次示例 total 约 31ms，小于 50ms，但仍被局部 SLO 阻断，这正是实验重点。

## 反例与进阶注入

- 注入 queue wait、provider 429 + backoff、checkpoint fsync 与 cache miss，分别归因；
- 重复至少 30 次并报告分位数/置信区间；
- 在固定 verified success 下比较小模型、本地模型与 OpenAI 远程模型的成本—质量前沿；
- 检查 timeout/cancel 后后台 tool 是否仍消耗资源，避免“客户端快失败、服务端继续烧钱”。
