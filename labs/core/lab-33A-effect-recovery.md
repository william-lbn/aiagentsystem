# Lab 33A — 副作用恢复：COMMITTED、NOT_APPLIED 与 UNKNOWN｜正常路径

## 实验目标

通过两个独立 SQLite 数据库模拟 runtime 与外部支付方：本地先写 intent，远端按 idempotency key 提交 effect，本地收到 receipt 后才标记 `COMMITTED`；重复执行返回同一 receipt，远端只有一条记录。

## 环境与版本

- Python 3.11–3.13，SQLite WAL + `synchronous=FULL`；x86_64/arm64；
- 两个数据库代表两个 durability domain，但仍在同一进程/主机；
- 无模型、网络、Docker 或 API key。生产系统需把 `lookup` 替换为 provider 官方查询接口。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

入口为 `examples/chapters/ch33_effect_recovery.py`；核心是 `ExternalEffectLedger` 与 `EffectCoordinator`：

```python
receipt = coordinator.execute("charge-33", "charge_cents", 4200)
same_receipt = coordinator.execute("charge-33", "charge_cents", 4200)
assert receipt == same_receipt
assert remote.count("charge-33") == 1
```

idempotency key 与 operation/amount 绑定；相同 key 改变参数会失败，不能把“去重”变成悄悄复用旧结果。

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch33_effect_recovery.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"reported_before_reconcile":"COMMITTED","reconciled":"COMMITTED","receipt":"rcpt_046c902140291034","remote_effect_count":1,"evidence_level":"L1_MECHANISM"}
```

## 调试断点

- local intent 的 `PREPARED` commit；
- remote `INSERT OR IGNORE` 与参数一致性检查；
- receipt 返回、本地 `COMMITTED` 更新之间的窗口；
- 重复 execute 的 fast path，确认不再次写远端。

## 验收标准

退出码 0；receipt 稳定；本地最终 `COMMITTED`；远端 effect count 为 1。L1 证明正常提交和幂等重放，不证明网络超时后的恢复，后者由 Lab 33B 验证。

## 生产迁移

支付、邮件、部署和消息各自需要不同 reconciliation：查询 provider by idempotency key、读取 message receipt、观察 deployment revision 或消费 outbox。只有 provider 支持稳定查询与去重时才能安全自动恢复；否则 UNKNOWN 应进入人工队列，不可乐观重试。
