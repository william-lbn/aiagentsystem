# Lab 13A — MCP 2026-07-28 请求与 MRTR｜正常路径

## 实验目标

验证教学协议子集中的 JSON-RPC、per-request protocol/client metadata、Streamable HTTP routing headers，以及 MRTR opaque requestState 的正常回传。

## 环境与版本

- Core：Python 3.11–3.13，无网络/API key，手写规范子集；
- External：锁定 `mcp==2.2.0` 的官方 SDK 双进程 loopback 实验，见 `experiments/l5/mcp_sdk_conformance.py`；
- 两者证据不可合并，Core 不称为 SDK interoperability。

## 环境准备

Core 路径执行 `uv sync --locked --all-groups --no-install-project`。L5 路径必须使用隔离环境与锁定 `mcp==2.2.0`，不得从 Core PASS 推导 SDK PASS。

## 实验代码

```bash
PYTHONPATH=src uv run python examples/chapters/ch13_mcp.py
```

## 实际输出

```json
{"evidence_level":"L1_MECHANISM","fault":false,"invariant_holds":true,"observation":{"mrtr_error":null,"mrtr_result":{"acceptedInputs":["approval"],"requestId":"req-13","resultType":"complete"},"protocol_errors":[],"protocol_version":"2026-07-28","request_valid":true},"passed":true,"scenario":"mcp"}
```

## 调试断点

在 `validate_mcp_2026_request` 比较 meta/header/body；在 `MRTRCoordinator.require_input/resume` 观察 opaque state。

## 验收标准

PASS 要求零 protocol error、request valid、MRTR complete 且只接受预期 approval 字段。Core 结果不得写成官方 SDK 互操作结果。

## 官方 SDK 升级

```bash
python experiments/l5/mcp_sdk_conformance.py --evidence-root /tmp/mcp-evidence
```

只有 wire、server effect、两侧版本、正常/故障断言和独立 verifier 齐全才可报告 L5；安装成功不算。
