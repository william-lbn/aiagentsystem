# Lab 13B — MCP 版本冲突与 MRTR 状态替换｜故障注入

## 实验目标

Body/meta 声明 `2026-07-28`，HTTP header 改为 `2025-11-25`；同时把 Server 返回的 opaque requestState 替换为攻击者值。两个故障都必须在 handler 完成前拒绝。

## 环境与版本

Python 3.11–3.13，macOS/Linux、arm64/x86_64；Core 无网络/API key，协议版本与 Lab 13A 一致。

## 环境准备

执行 `uv sync --locked --all-groups --no-install-project`；版本冲突与 state 替换是两个独立故障，验收时必须分别观测 reason。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch13_mcp.py --fault
```

## 实际输出

```json
{"contained":true,"evidence_level":"L3_CONTAINED","fault":true,"invariant_holds":true,"observation":{"mrtr_error":"request_state_mismatch","mrtr_result":null,"protocol_errors":["header_body_version_mismatch"],"protocol_version":"2026-07-28","request_valid":false},"oracle_detected":true,"passed":true,"scenario":"mcp","system_detected":true}
```

## 验收标准

Protocol validator 必须给出精确 mismatch；MRTR 不得产生 complete result；两条故障均 system-detected/contained。若只在测试脚本比较字段、Server 仍执行，则最多 L2。

## 调试断点

分别变更 version、method、name、缺 meta capabilities、缺 input response、超 round budget，确认 reason 独立。再运行官方 SDK 实验的 header/body mismatch，比较教学 validator 与 SDK classifier 的边界。

## Claim ceiling

Core Lab 不覆盖 OAuth、远程网络、跨语言、Tasks durability 或副作用 exactly-once。现有官方 L5 也仅 Python↔Python、两进程、loopback、无鉴权；报告时必须保留该上限。
