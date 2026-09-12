# AgentOps Service Desk — production-style case

这是一个刻意保持小规模、但具有真实 API、持久化、租户隔离、action-bound approval、effect record、状态变更与 verifier evidence 的 FastAPI + SQLite 教学案例。它用于把正文中的 Runtime 正确性边界映射到服务边界，而不是用“审批后把 `status` 改成 FINISHED”代替真实副作用。

> **边界声明**：示例中的资源、effect record 与 run 状态都位于同一个 SQLite 数据库，因此本地写路径可以共享一个数据库事务。真实云 API、浏览器、支付、Kubernetes 等外部副作用不具备这个事务边界；若请求结果不确定，必须依靠 idempotency key、外部 observation/reconciliation 或补偿协议，不能宣称无条件 exactly-once。

## 本地运行

从仓库根目录执行锁定依赖：

```bash
make bootstrap
PYTHONPATH=src uv run uvicorn production.agentops_service.app.main:app --reload --port 8010
```

健康检查：

```bash
curl -s http://127.0.0.1:8010/healthz
```

以下请求都显式带租户身份：

```bash
TENANT=tenant-a
```

### 只读路径

```bash
curl -s -X POST http://127.0.0.1:8010/runs \
  -H "X-Tenant-ID: $TENANT" -H 'content-type: application/json' \
  -d '{"request":"summarize payment incident"}'
```

预期 `status=FINISHED`，且 run detail 中 `verifier_status=PASS`、`effect_executed=false`。

### 高风险写路径

```bash
resp=$(curl -s -X POST http://127.0.0.1:8010/runs \
  -H "X-Tenant-ID: $TENANT" -H 'content-type: application/json' \
  -d '{"request":"delete demo record"}')
echo "$resp"
```

返回 `WAITING_APPROVAL` 和不可变 `action_id`。审批必须绑定该 action：

```bash
RUN_ID='<run_id>'
ACTION_ID='<action_id>'
curl -s -X POST "http://127.0.0.1:8010/runs/$RUN_ID/approval" \
  -H "X-Tenant-ID: $TENANT" -H 'content-type: application/json' \
  -d "{\"decision\":\"approve\",\"action_id\":\"$ACTION_ID\"}"
```

随后检查：

```bash
curl -s "http://127.0.0.1:8010/runs/$RUN_ID" -H "X-Tenant-ID: $TENANT"
curl -s "http://127.0.0.1:8010/runs/$RUN_ID/effects" -H "X-Tenant-ID: $TENANT"
```

验收条件不是只有 `FINISHED`，而是：审批 action_id 匹配、effect 唯一、资源观测达到目标状态、`verifier_status=PASS`、evidence 中能追溯 action/effect/observation。

## 自动化 E2E

```bash
uv run pytest -q tests/e2e/test_agentops_api.py -vv
```

测试覆盖只读 verifier、批准后真实 effect、重复批准幂等、stale action 拒绝、跨租户 404、拒绝时零 effect。

## Docker

从仓库根目录：

```bash
docker compose up --build
```

服务监听 `http://127.0.0.1:8010`。
