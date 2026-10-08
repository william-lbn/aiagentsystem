# Lab 31A — Tracing、Metrics 与 AgentOps｜正常路径

## 实验目标

生成一条可重建而非只可浏览的 Agent trajectory：每个 span 具有稳定 `run_id/span_id/parent_id/seq`，SQLite 中的每行通过前序 hash 连接；敏感属性在落盘前递归脱敏；只有链与父子图验证通过才允许导出。

## 环境与版本

- Python 3.11–3.13，标准库 SQLite 与 SHA-256；x86_64/arm64；
- duration 来自 `perf_counter_ns()` 的实际测量，但本实验不对微秒级数值作跨主机断言；
- 无模型、网络、collector 或 API key。OpenTelemetry 后端属于后续集成层，不改变本实验的证据要求。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

入口为 `examples/chapters/ch31_observability.py`，核心为 `assurance_system.TamperEvidentTraceStore`：

```python
store.record(run_id="run-31", span_id="root", parent_id=None,
             name="agent.run", operation=lambda: None)
store.record(run_id="run-31", span_id="tool-1", parent_id="root",
             name="tool.execute", operation=search,
             attrs={"tool": "search", "api_key": secret})
verified, reason = store.verify("run-31")
trajectory = store.reconstruct("run-31")
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch31_observability.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"span_count":2,"verified":true,"verification_reason":"VERIFIED","export_allowed":true,"secret_redacted":true,"evidence_level":"L1_MECHANISM"}
```

## 调试断点

- `record()` 的 parent lookup：孤儿 span 必须在写入前被拒绝；
- `redact()`：确认秘密从未先以明文写入数据库；
- row hash 计算：字段、顺序和前序 hash 都进入摘要；
- `reconstruct()`：先调用 `verify()`，而不是“尽量导出”损坏记录。

## 验收标准

退出码 0；两条 span 可按 seq 重建；`verified=true`、`export_allowed=true`、`secret_redacted=true`。L1 不证明分布式 collector 不丢包，也不证明未埋点副作用不存在。

## 扩展观察

生产中还应为 model request、tool intent/result、checkpoint、approval、effect receipt 和 verifier verdict 建 span/event，并用低基数 metrics 聚合 SLO。Trace payload 不应保存完整 prompt、token 或个人数据；采样策略也必须保留 error/security/UNKNOWN 轨迹，否则“降低观测成本”会破坏事故证据。
