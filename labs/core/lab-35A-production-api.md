# Lab 35A — 生产 Agent API：服务边界、租户、审批和审计｜正常路径

## 实验目标

启动真实 `127.0.0.1` 回环 HTTP 服务，使用 HMAC bearer token 得到 tenant identity，执行 `POST /v1/runs` 与 `GET /v1/runs/{id}`。相同 tenant + idempotency key + payload 重放必须返回同一 run；数据查询在 SQLite 层带 tenant 条件。

## 环境与版本

- Python 3.11–3.13；标准库 `ThreadingHTTPServer`、`urllib` 与 SQLite；x86_64/arm64；
- 服务绑定 OS 分配的临时回环端口，不访问公网；本地 sandbox 必须允许 loopback socket；
- 不需要模型、Docker 或 API key。内置 HMAC signer 仅为边界实验，不替代生产 OIDC/JWT 验证。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

入口为 `examples/chapters/ch35_production_api.py`；HTTP、认证与 store 位于 `assurance_system.py`：

```python
with running_agent_service("api.db") as (service, auth, store):
    token = auth.issue("tenant-a")
    status, first = http_json(
        "POST", service.base_url + "/v1/runs",
        token=token,
        payload={"task": "audit invoice"},
        idempotency_key="request-35-a",
    )
    status, replay = http_json(...same request...)
    assert first == replay
```

`run_id` 由 tenant 与 idempotency key 的 canonical digest 派生；相同 key 改变 payload 返回 409，不会静默复用。

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch35_production_api.py
```

## 实际验证输出（本发布源码执行所得）

```json
{"create_status":202,"idempotent_replay":true,"requested_run":"run_3d37a81fcb836704","get_status":200,"response":{"run_id":"run_3d37a81fcb836704","state":"ACCEPTED"},"foreign_identifier_leaked":false,"evidence_level":"L1_MECHANISM"}
```

## 调试断点

- Authorization header 解析与 constant-time signature compare；
- `ProductionRunStore.create` 的 `(tenant,idempotency_key)` 唯一约束；
- payload digest conflict 分支；
- `get()` SQL 的 tenant + run_id 双条件。

## 验收标准

退出码 0；两次 POST 都是 202 且 body 相同；GET 为 200；`foreign_identifier_leaked=false`。L1 只证明本机 HTTP/SQLite 正常路径，不代表 TLS、OIDC、网关、队列或多实例部署已验证。

## 生产迁移

真实 API 还需 TLS、OIDC audience/issuer/key rotation、请求 schema/size limit、rate limit、async queue、approval endpoint、audit/effect linkage、pagination、retention 与 deletion policy。不要把 provider API key 暴露给客户端；服务端 credential broker 按 tenant/policy 获取最小权限短期凭据。
