# 上游行为复现：Model Context Protocol Python SDK

- 合同 ID：`UPSTREAM-MCP-001`
- 核验状态：`EXTERNAL_NOT_RUN_IN_THIS_RELEASE`
- 固定版本：`mcp==2.2.0; protocol revision 2026-07-28`
- 官方来源：https://github.com/modelcontextprotocol/python-sdk
- 机制焦点：**2026-07-28 modern stateless request contract**

> **证据边界**：本合同描述完整的跨语言/远程/鉴权复现目标，因此总状态仍是 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。但其中一个范围受限的官方实现实验已经真实执行：`mcp==2.2.0` client/server 位于不同 OS 进程，经 loopback Streamable HTTP 完成工具调用，并由官方 classifier 拒绝 header/body 版本冲突。证据：[`evidence.json`](../../evidence/l5/mcp-sdk-conformance/2026-09-12-macos-arm64-py313-v1.0.0/evidence.json)。这不是“安装成功”，也不应扩大为跨语言或生产安全结论。

## 行为合同

### 正常场景

启动 pinned SDK 的最小 client/server，发出 `tools/call`（或等价官方示例），保存 HTTP/JSON-RPC 原始帧；验证 `MCP-Protocol-Version: 2026-07-28` 与 `params._meta["io.modelcontextprotocol/protocolVersion"]` 一致，并核对 `Mcp-Method` / `Mcp-Name` routing headers 以及 client identity/capabilities envelope。

### 故障场景

故意制造 header/body protocol version 不一致，或缺失 2026-era 必需 envelope 项；保存 SDK/server 的拒绝结果，确认不会被当成合法 modern request。

### 独立 Verifier

wire capture + SDK version + server log；独立解析器只检查规范字段，不依赖业务 handler 的“成功”字符串。

## 环境与版本固定

在独立环境中安装/checkout 上述 pin；开始实验前必须记录 `OS/arch`、语言 runtime、package/tag/commit、模型/provider（若使用）、依赖锁文件与完整命令。若 pin 无法获取，实验应记为 `BLOCKED_PIN_UNAVAILABLE`，不得自动改用最新版。

## 最小证据包

每次真实运行必须至少保存：

- `environment.json`：OS/arch/runtime/package/tag/commit/provider；
- `commands.txt`：按执行顺序记录可复制命令；
- `stdout.log` / `stderr.log`：未经人工改写的输出；
- `verifier.json`：机器可读断言与实际值；
- `artifact-hashes.sha256`：状态、diff、wire capture 或业务 artifact 的哈希；
- 若涉及网络协议，再保存去密后的 raw request/response；若涉及副作用，再保存独立 side-effect counter/observation。

## 判定规则

- `PASS_L5_EXTERNAL`：正常场景、故障场景和独立 verifier 全部通过，且版本证据完整；
- `FAIL_BEHAVIOR`：框架实际行为与合同冲突；
- `BLOCKED_ENVIRONMENT`：缺少 Docker/API Key/浏览器/网络等外部条件；
- `BLOCKED_PIN_UNAVAILABLE`：指定版本无法获得；
- 不允许用“安装成功”“命令返回 0”“模型说完成了”替代行为证据。

## Claim Ceiling

当前证据只支持“官方 Python SDK、两进程、loopback Streamable HTTP、无鉴权”。不得把手写 JSON fixture 称为 SDK interoperability，也不得把这次 Python↔Python 实验写成跨语言、远程 auth 或生产级互操作。
