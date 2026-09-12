# 上游行为复现：A2A Protocol

- 合同 ID：`UPSTREAM-A2A-001`
- 核验状态：`EXTERNAL_NOT_RUN_IN_THIS_RELEASE`
- 固定版本：`spec v1.0.1 @ 3303592`
- 官方来源：https://github.com/a2aproject/A2A
- 机制焦点：**AgentCard / Task wire contract**

> **证据边界**：本文件定义完整的跨语言、多 transport、持久 store 合同，因此总状态仍是 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。范围受限的官方实现实验已经真实执行：PyPI `a2a-sdk==1.1.2` client 发现 Agent Card，并从独立 server 进程取得 JSON-RPC Task/Status/Artifact 流；旧版 card shape 被严格拒绝。证据：[`evidence.json`](../../evidence/l5/a2a-sdk-conformance/2026-09-12-macos-arm64-py313-v1.0.0/evidence.json)。

## 行为合同

### 正常场景

从 `/.well-known/agent-card.json` 取得 AgentCard，验证 `supportedInterfaces[]` 至少包含一个带 `url`、`protocolBinding`、`protocolVersion` 的接口；随后发送一条消息并保存返回 Task，验证 `task.status.state` 使用 v1 TaskState。

### 故障场景

构造旧 v0.3 风格 card（顶层 `url` / `protocolVersion`）或声明客户端不支持的接口版本；验证适配层明确拒绝/降级，而不是把旧字段静默解释成 v1。

### 独立 Verifier

保存原始 AgentCard、请求/响应 JSON（或 proto JSON 映射）和 schema/SDK 解析结果；独立断言字段层级与 terminal Task state。

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

当前证据只支持“官方 Python SDK、两进程、loopback JSON-RPC、Agent Card discovery 与 completed task lifecycle”。它不支持跨语言、HTTP+JSON/gRPC parity、远程 auth、持久 task store、cancel/subscribe 结论；Core Lab 仍只证明本地 schema invariant。
