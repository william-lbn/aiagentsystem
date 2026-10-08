# Lab 35B — 生产 Agent API：服务边界、租户、审批和审计｜故障注入

## 实验目标

先由 tenant B 创建真实 run，再用 tenant A 的有效 token 请求该 run。验证服务在数据库查询层隔离 tenant，并对“不存在”和“属于他人”统一返回 404，避免资源枚举与 body 泄漏。

## 可证伪假设与故障位置

认证成功不等于对象授权成功。若 handler 先按 run_id 查全局记录、再在响应层隐藏部分字段，日志、缓存或错误 body 仍可能泄漏。故障使用合法 A token 与真实 B run id，专门测试 object-level authorization。

## 环境与版本

与 Lab 35A 相同；实验会绑定临时 `127.0.0.1` 端口。先运行 35A 建立幂等正常基线。

## 环境准备

```bash
python -m pip install uv==0.10.0
uv sync --locked --all-groups --no-install-project
```

## 实验代码

```python
_, tenant_b = http_json("POST", base + "/v1/runs", token=token_b,
                        payload={"task": "private tenant-b task"},
                        idempotency_key="request-35-b")
status, body = http_json(
    "GET", base + f"/v1/runs/{tenant_b['run_id']}", token=token_a
)
assert status == 404 and body == {"error": "not_found"}
```

## 执行步骤

```bash
PYTHONPATH=src uv run python examples/chapters/ch35_production_api.py --fault
```

## 实际验证输出（本发布源码执行所得）

```json
{"create_status":202,"idempotent_replay":true,"requested_run":"run_ef0d87f7ac1120c9","get_status":404,"response":{"error":"not_found"},"foreign_identifier_leaked":false,"system_detected":true,"contained":true,"evidence_level":"L3_CONTAINED"}
```

## 调试断点

- token A/B 验证后得到的 tenant identity；
- `get(tenant, run_id)` SQL 条件；
- foreign 与 absent 两种路径的 status/body/header；
- access log/audit，确认可供安全团队审计但不回显给调用者。

## 验收标准

退出码为 0，并同时满足：

- A 读取 B run 返回 404 与统一的 `{"error":"not_found"}` body；
- 响应不含 B 的 `state`、`task`、`tenant` 或真实 run 内容；
- `foreign_identifier_leaked=false` 且 `contained=true`；
- `evidence_level=L3_CONTAINED`。

L3 只证明越权读取被检测并阻断，不代表 B 的任务已恢复，也不代表攻击主体已被封禁。

## 反例与进阶注入

- 用伪造 token，预期 401；有效 token + foreign object 仍应是 404；
- 相同 key 改 payload，预期 409，且原 run 不改变；
- 并发 20 个相同 POST，确认只产生一个 run；
- 在多实例/队列/缓存环境复测 tenant key，尤其检查 cache key 是否遗漏 tenant；
- 审批 callback、artifact 下载与 trace 查询也必须复用同一 ownership policy。
