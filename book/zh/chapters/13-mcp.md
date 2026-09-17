# MCP：把外部工具与资源接成协议边界

> **本章命题**：MCP 解决的是客户端与能力提供方之间的协议互操作，不自动解决业务授权、提示注入、幂等、副作用恢复或多 Agent 委派。截止 2026-09-11，本书以 MCP 2026-07-28 无会话核心为规范基线，并把手写合同实验与官方 SDK 互操作证据分开。

第二篇前六章建立工具、检索、记忆与 Skill 的本地合同。本章将这些能力放到进程/网络边界上，说明“协议正确”和“业务安全”为什么是两类证明。

![MCP Host、Client、Server 与应用治理的责任边界](../../assets/diagrams/13-mcp-architecture.svg)

## 问题背景与学习目标

没有协议时，每个 Agent 框架都为工具、资源、提示和身份发明一套适配器，导致重复集成与锁定。MCP 提供共享消息和 SDK，但互操作的代价是更清晰地面对版本、transport、路由、缓存、OAuth、状态句柄和 server trust。

本章要求读者：

- 区分 Host、Client、Server 和模型，各自拥有什么权力；
- 理解 2026-07-28 的 per-request version/capabilities 与 stateless core；
- 能解释 Streamable HTTP 的 `Mcp-Method/Mcp-Name` 路由元数据；
- 理解 Multi Round-Trip Requests（MRTR）的 `input_required/requestState/inputResponses`；
- 区分 core protocol、Tasks extension、应用 durable state 与业务 effect；
- 能设计官方 SDK 的跨进程正常/故障/独立 verifier 证据包。

## 核心概念与系统直觉

### Host 是信任根，不是模型

Host 管理用户交互、模型、Client 生命周期、权限与策略。模型只能提出使用某 MCP capability；Host 决定 server 是否可信、哪些工具可见、是否需要批准以及结果如何进入上下文。

### Server 暴露能力，不继承全局权限

Server 的工具/资源边界应对应最小后端身份。连接一个“文件系统 server”不应自动读取整台机器；roots、workspace、network 和 secret scope 由 Host/部署明确限制。

### Stateless Core 不等于应用无状态

2026-07-28 去掉协议级会话依赖，版本和能力随每次请求携带。Server 若要跨调用保存状态，应返回显式 handle，由模型/Host 在后续参数中传回。长任务状态可以进入 Tasks extension 或应用数据库，而不是隐藏在 transport session。

### 协议结果仍是不可信数据

MCP Server 返回的文本、资源和 structured content 可能含错误或提示注入。Host 必须保留来源身份、隔离 channel，并在动作前重新授权。

## 原理与理论基础

一次现代请求可抽象为：

$$
Req=(jsonrpc,id,method,params,meta,headers)
$$

本书验证的核心一致性包括：

$$
meta.protocolVersion = header.MCP\text{-}Protocol\text{-}Version
$$

$$
body.method = header.Mcp\text{-}Method
$$

对于具名方法：

$$
body.name/uri = header.Mcp\text{-}Name
$$

这些是路由/版本完整性，不是用户授权证明。

MRTR 将服务端中途所需输入表示为 `resultType=input_required`，带 opaque `requestState` 和 `inputRequests`；Client 收集输入后重发原操作并带 `inputResponses`。Opaque state 必须原样回传、限制轮数、绑定原 request，防止状态替换。

**不变量**：MCP routing metadata and opaque MRTR request state must be validated on every stateless round trip。

## 关键机制与执行流程

![MCP 无会话请求与 MRTR 的校验和恢复流程](../../assets/diagrams/13-mcp-flow.svg)

1. Host 根据用户/tenant policy 建立可见 server 与能力集合；
2. Client 构造 JSON-RPC 请求，在 `params._meta` 携带 protocol version、client capabilities 与可选 client info；
3. Streamable HTTP 同步发送 version/method/name routing headers；
4. Server 在调用 handler 前验证 header/body、schema、auth token audience 与 capability；
5. 普通结果返回 content/structured content；中途需输入则返回 `input_required`；
6. Host 处理用户确认、sampling 等 input request，并保持 requestState opaque；
7. 重发时验证 request identity、state、响应 shape 和 round budget；
8. 对长任务使用 Tasks extension/应用状态，对副作用仍使用独立 effect journal 与 reconciliation。

## 从原理到实现

`validate_mcp_2026_request` 明确声明只是规范子集，不冒充完整 SDK。它检查 meta 与 HTTP 路由一致性：

```python
version = meta.get(MCP_PROTOCOL_VERSION_META_KEY)
if version != MCP_PROTOCOL_VERSION:
    errors.append("invalid_protocol_version_meta")

header_version = normalized.get(MCP_PROTOCOL_VERSION_HEADER)
if header_version != version:
    errors.append("header_body_version_mismatch")

header_method = normalized.get(MCP_METHOD_HEADER)
if header_method != method:
    errors.append("header_body_method_mismatch")
```

MRTR coordinator 只把 opaque state 当 token 比较，不解析或接受替换：

```python
def resume(self, request_id, *, request_state, input_responses):
    expected_state, round_number, required = self._pending[request_id]
    if request_state != expected_state:
        raise ValueError("request_state_mismatch")
    if round_number > self.max_rounds:
        raise ValueError("mrtr_round_limit_exceeded")
    if set(input_responses) != set(required):
        raise ValueError("input_response_shape_mismatch")
    del self._pending[request_id]
    return {"resultType": "complete", ...}
```

该实现验证协议不变量；官方 SDK 的跨进程 Streamable HTTP 行为由独立 L5 实验承担。

## 主流系统实现对照与源码阅读入口

| 来源 | 锁定状态 | 本书实际核验范围 |
|---|---|---|
| [MCP 2026-07-28 发布说明](https://blog.modelcontextprotocol.io/posts/2026-07-28/) | 截止 2026-09-11 的规范基线 | stateless core、MRTR、routing header、Tasks extension 与弃用迁移语义 |
| [官方 Python SDK](https://github.com/modelcontextprotocol/python-sdk) | `mcp==2.2.0` | 两个 OS 进程、loopback Streamable HTTP 工具调用及版本冲突拒绝 |
| 本书 `protocols.py` | 教学子集 | header/body/meta 的确定性合同测试 |
| 本书 `MRTRCoordinator` | 教学子集 | requestState substitution 与 input shape/round gate |

官方 SDK 实验的证据位于 `evidence/l5/mcp-sdk-conformance/`：环境、命令、stdout/stderr、wire、server effect、verifier 和哈希均保存。运行日期为 2026-09-12，是发布验证时间；协议与依赖内容仍锁定在用户要求的 2026-09-11 知识截止。

## 设计方案与方法对比

| 选择 | 优势 | 风险/代价 |
|---|---|---|
| stdio 本地 server | 简单、进程边界清楚 | 本地主机权限过宽、生命周期管理 |
| Streamable HTTP | 远程部署、标准基础设施 | auth、路由、网络故障与多租户 |
| 显式 handle | 状态可见、可迁移 | handle 生命周期与授权要治理 |
| 隐式 transport session | 编程直观 | 粘性、扩缩容、恢复与观察困难 |
| MCP Tool | 通用调用 | 副作用语义需应用补充 |
| Tasks extension | 长任务状态 | 不自动提供外部 exactly-once effect |

## 可复现实验

### 实验环境与证据分层

Core Lab 只需 Python 3.11–3.13，无网络/API key，验证手写协议子集，等级最高 L3。官方 SDK L5 实验需要隔离环境安装锁定 `mcp==2.2.0`，启动两个进程并使用 loopback HTTP；它不需要模型 key。

### Lab 13A：现代请求与 MRTR 正常完成

```bash
PYTHONPATH=src uv run python examples/chapters/ch13_mcp.py
```

实际结果：`protocol_version=2026-07-28`、`request_valid=true`、无 protocol errors，MRTR 返回 `resultType=complete` 和 accepted `approval`；等级 `L1_MECHANISM`。

### Lab 13B：版本冲突与 requestState 替换

```bash
PYTHONPATH=src uv run python examples/chapters/ch13_mcp.py --fault
```

实际结果同时出现 `header_body_version_mismatch` 与 `request_state_mismatch`，handler 未完成，故为 `L3_CONTAINED`。Core Labs 见 [Lab 13A](../../../labs/core/lab-13A-mcp.md)、[Lab 13B](../../../labs/core/lab-13B-mcp-fault.md)；官方 SDK 复现合同见 [上游 MCP Lab](../../../labs/upstream/mcp.md)。

可在已安装 L5 锁定依赖的隔离环境运行：

```bash
python experiments/l5/mcp_sdk_conformance.py --evidence-root /tmp/mcp-evidence
```

不要把脚本存在或 package 安装成功算作 PASS；verifier 必须看到跨进程 wire、server effect 与故障拒绝。

### 关键断点与验收标准

**关键断点**：在 JSON-RPC body、per-request metadata、Streamable HTTP routing header、capability gate、MRTR `requestState` 和 round budget 处分层观察。**验收标准**：Core 正常实际输出必须无 protocol error 并完成 MRTR；版本冲突与 state 替换必须在 handler 完成前拒绝。L5 只有在官方 SDK 跨进程 wire、server effect、正反例断言和独立 verifier 同时存在时成立。

## 工程场景与系统设计

企业 Host 连接 CRM、代码仓库和工单 MCP servers 时，应为每个 server 配独立 OAuth audience、tenant mapping、tool allowlist、egress policy 与 result trust label。高风险 tool 每次仍需 action-bound approval；Server 的 `destructive` annotation 可帮助 UI，但不能替代 Host policy。

Server 扩缩容不应依赖内存 session。显式 handle 存入共享状态层，handle 本身只是不透明引用，读取时重做 tenant/subject auth。对长任务，task status 与 artifact identity 可持久化；真实外部写效果仍由第八章协议管理。

## 故障模型、失败模式与排错

- **header/body version 不一致**：在 handler 前拒绝，记录双方字段；
- **client/server capability 漂移**：明确 unsupported，不静默降级为旧语义；
- **MRTR state substitution/replay**：绑定原 request，opaque equality、轮数和过期检查；
- **server result prompt injection**：标记 untrusted content，禁止改变 Host policy；
- **OAuth confused deputy**：校验 issuer/audience/resource，token 不跨 server 复用；
- **server crash 丢隐式状态**：迁移为显式 handle/Tasks/应用持久层；
- **工具成功但业务未知**：协议 success 不等于 effect completion，进入 receipt/reconciliation。

## 性能、可靠性与工程化

采集每 server/method 的 discovery/list latency、cache hit、call p95/p99、MRTR rounds、input-required latency、task age、protocol rejection、auth failure、payload bytes 和 UNKNOWN effects。2026-07-28 list/read 响应的缓存元数据需要与租户和权限范围一起组成 cache key。

Client 要有 per-server bulkhead、deadline、circuit breaker 和最大并发；Host trace 应把 provider tool item、本地 action、MCP request、remote task 和 effect receipt 通过不同 ID 映射，不能共用一个字符串掩盖生命周期差异。

## 技术边界与设计取舍

当前 L5 证据是 Python↔Python、loopback、两进程、无鉴权的 Streamable HTTP；它不证明跨语言、远程网络、OAuth、生产多租户或 Tasks durability。Core Lab 更低，只验证本地合同。书中明确保持这两个 claim ceiling。

MCP 通常不需要模型 API key。若 Host 同时使用 OpenAI，`OPENAI_API_KEY` 只用于模型提供方；MCP OAuth/服务凭据分别注入，日志统一脱敏。开源仓库只提交 example env 名称和 redacted evidence，不提交任何真实 token。

## 前沿研究与演进方向

协议正在从“工具线缆”演进为可扩展能力平面：无会话核心支持标准扩缩容，MRTR 支持中途输入，Tasks 承载长任务。仍待研究和工程统一的领域包括 agent identity/delegation、capability attenuation、跨协议 trace、可信 server metadata 和 effect receipts。

### 深度审计与研究证据链：协议互操作不是系统安全

本章具有三层证据：规范文本定义应然合同；Core Lab 对手写子集做故障包含；官方 SDK L5 实验真实跨进程执行。即便三层都通过，也不能推出业务授权或副作用 exactly-once；这些结论分别属于 Host policy 和 Tool Runtime。

## 本章总结与进阶实践

MCP 的价值是标准化 Host 与能力提供方的边界。越是标准化，越要明确版本、身份、状态和内容信任；否则“能连上”会被误写成“安全可用”。

进阶问题：

1. stateless core 为什么不等于 server 不能保存应用状态？
2. MRTR 的 requestState 为什么必须 opaque 且绑定原请求？
3. routing header 一致性证明了什么，又没有证明什么？
4. Tasks extension 为什么不能替代 effect journal？
5. 怎样把 MCP Python↔Python 证据升级为跨语言 L5？

参考答案见[附录 H：第二篇问题参考答案](../appendix-h-part2-solutions.html#part2-solutions-ch13)。
