# Lab 31B — Tracing、Metrics 与 AgentOps｜故障注入

## 实验目标

在两条 span 已持久化后直接篡改 `tool.execute` 的名称，模拟越权数据库写入、损坏导入或不可信处理器。验证 hash mismatch 被系统发现，且证据导出 fail closed。

## 可证伪假设与故障位置

普通 tracing SDK 只能证明“收到了某些 span”，不能证明记录未变。本实验的故障绕过公开 `record()` API，直接修改 SQLite；若 `reconstruct()` 仍返回轨迹，审计链就不可信。

## 环境与版本

与 Lab 31A 相同；本地 SQLite 为真实持久介质，但不等于远程 append-only/WORM 存储。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
store.db.execute("UPDATE spans SET name='forged.tool' WHERE span_id='tool-1'")
store.db.commit()
verified, reason = store.verify("run-31")
trajectory = store.reconstruct("run-31")  # 必须抛错并阻断导出
```

入口为 `examples/chapters/ch31_observability.py`；场景捕获导出异常并记录 `export_allowed=false`。

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch31_observability.py --fault
```

## 实际验证输出（本发布源码执行所得）

```json
{"span_count":2,"verified":false,"verification_reason":"HASH_MISMATCH","export_allowed":false,"secret_redacted":true,"system_detected":true,"contained":true,"evidence_level":"L3_CONTAINED"}
```

## 调试断点

- SQL update 前后读取 row hash，确认攻击者没有同步重算可信 anchor；
- `verify()` 的 canonical payload 重算；
- `reconstruct()` 的 fail-closed 分支；
- 导出/审计消费者，确认未接收部分或伪造 trajectory。

## 验收标准

退出码 0；reason 为 `HASH_MISMATCH`；`verified=false`、`export_allowed=false`、`contained=true`、`evidence_level=L3_CONTAINED`。本实验证明受损记录不会被当作证据导出，不证明数据库已自动修复。

## 反例与进阶注入

- 删除中间 seq，预期 `CHAIN_DISCONTINUITY`；
- 伪造 parent 指向后来的 span，预期 `INVALID_PARENT`；
- 轮转 hash anchor 到外部签名/WORM 存储，验证数据库管理员也不能无痕重写全链；
- 注入 collector 丢包并区分“源端链完整、传输不完整”与“源端记录已损坏”。
