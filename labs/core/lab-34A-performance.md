# Lab 34A — 性能与成本：Token、延迟、并发和缓存｜正常路径

## 实验目标

用 `perf_counter_ns()` 实测 context assembly、tool 与 persistence 三段关键路径，并将 stage budget 与 end-to-end budget 同时作为 release gate。实验不再把手填的 `120ms/80ms` 当成测量数据。

## 环境与版本

- Python 3.11–3.13；x86_64/arm64；单进程标准库；
- 本实验的本地微基准用于证明 instrumentation/gate，不用于比较 CPU、OS 或模型 provider；
- 无模型、网络、Docker 或 API key；真实模型 latency/cost 需另建锁定环境的重复试验。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

入口为 `examples/chapters/ch34_performance.py`；测量实现为 `assurance_system.PerformanceProbe`：

```python
probe = PerformanceProbe(
    {"assemble": 10, "tool": 15, "persist": 10},
    total_budget_ms=50,
)
report = probe.measure([
    ("assemble", assemble_context),
    ("tool", execute_tool),
    ("persist", persist_checkpoint),
])
```

每段围绕真实函数调用读取单调高分辨率时钟；release 只有在所有 stage 和 total 都通过时允许。

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch34_performance.py
```

## 实际验证输出（本机一次真实执行，数值允许随主机变化）

```json
{"release_allowed":true,"stages":[{"stage":"assemble","budget_ms":10,"elapsed_ms":0.046,"within_budget":true},{"stage":"tool","budget_ms":15,"elapsed_ms":0.001,"within_budget":true},{"stage":"persist","budget_ms":10,"elapsed_ms":0.007,"within_budget":true}],"total_budget_ms":50,"total_ms":0.068,"within_budget":true,"evidence_level":"L1_MECHANISM"}
```

## 调试断点

- 每个 operation 前后 `perf_counter_ns()`；
- stage budget lookup，未配置的 stage 必须失败；
- total critical path 计算；
- `release_allowed`，确认不是只看平均值或只看 total。

## 验收标准

退出码 0；所有 `within_budget=true` 且 `release_allowed=true`。毫秒具体值不是验收常量；在共享 CI 中只断言宽松正常预算。L1 不等于经过负载、并发、长尾或 provider 成本验证。

## 真实负载扩展

至少报告 warm/cold、p50/p95/p99、arrival rate、queue time、model/tool/checkpoint/retry 分解、token 与货币成本，以及 verified-success denominator。缓存命中率必须与 stale/permission leakage 一起测；并发提升必须检查 provider rate limit、workspace 冲突与 retry amplification。
