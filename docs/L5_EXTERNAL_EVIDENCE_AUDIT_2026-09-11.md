# AI Agent Systems L5 外部证据深度审计

> 截止日期：2026-09-11（Asia/Shanghai）<br>
> 审计对象：协议互操作、durable execution、coding/browser benchmark、canonical reproducibility<br>
> 核心规则：**只把实际运行、可重放、带独立 verifier 和 claim ceiling 的结果写成证据。**

## 1. 执行结论

本轮升级已经把项目从“章节多、fixture 多、上游链接多”推进到一组真实但严格限域的外部实现证据：六个 pinned 官方/上游 runtime 实验全部有命令、环境、原始 stdout/stderr、机器断言、业务 observation、source hash 与 artifact hash，并通过统一证据 QA。尤其是 MCP 与 A2A 已不再停留在手写 wire shape 或进程内调用，而是让官方 client/server 穿过 loopback socket 和独立 OS 进程完成真实协议交互。

但项目还不能宣称“L5 全面完成”。真实 SWE-bench/WebArena 本次没有运行；跨 Ubuntu host 的 canonical workflow 已定义但没有获得 CI 运行证据；MCP/A2A 也尚未完成跨语言、远程鉴权和多 transport 矩阵。准确结论是：

- **协议**：两项 scoped official-SDK interoperability 已通过；跨语言/远程/security profile 未通过验收。
- **durability**：OpenAI Agents、LangGraph、Google ADK、Microsoft Agent Framework 各自的真实持久化 surface 已跨进程验证；不能把这些不同 surface 统称为 exactly-once durable execution。
- **benchmark**：真实官方 harness 契约与手工 CI 入口已建立；当前只有 readiness evidence，没有模型成绩。
- **reproducibility**：same-host 机制与 cross-host hash comparator 已实现；跨 host 结果仍待实际 workflow 产出。

这比继续增加篇幅更有价值，因为它把“代码看起来合理”提升为“外部实现实际做了什么、在什么边界内成立、怎样被第三方复验”。

## 2. L5 应被建模为证据向量

把 L5 当作单一布尔值会诱发过度声明。更可靠的表示是：

$$
E=(A,B,F,V,D,N,R,C)
$$

其中：

- $A$ — authority：手写模拟、社区实现还是官方 release；
- $B$ — execution boundary：同函数、同进程、跨进程、跨 container、跨 host 还是远程服务；
- $F$ — fault：是否注入可证伪故障，故障发生在哪个窗口；
- $V$ — verifier：是否独立于被测 agent 的自述，是否检查外部 effect；
- $D$ — durability：保存的是 session、event、graph checkpoint、instruction pointer 还是 effect receipt；
- $N$ — environment：fixture、真实 repo、真实 browser stack、真实 provider 或真实业务系统；
- $R$ — reproduction：单次、同 host 重建、跨 host、跨实现；
- $C$ — claim ceiling：哪些结论明确不能从本实验推出。

一个实验可以在 authority 上达到官方 release，在 environment 上仍是 synthetic；也可以跨进程恢复 graph，却没有证明外部 API exactly-once。仓库的 [`experiments/l5/catalog.json`](../experiments/l5/catalog.json) 与 `evidence.json` 正是按这个向量保存结论，而不是只记录 `PASS`。

## 3. 已实际运行的六项外部实现证据

| 实验 | 固定版本 | 真实执行边界与故障 | 独立观察/verifier | 结论上限 |
|---|---|---|---|---|
| MCP SDK conformance | `mcp==2.2.0`, `mcp-types==2.2.0` | 官方 `Client` → loopback Streamable HTTP → 独立 `MCPServer` 进程；另制造 header/body version mismatch | 服务端 PID 和采购计价 effect、协商版本、官方 request classifier、artifact hashes | 只证明 Python↔Python、本机、无鉴权；不证明跨语言/远程/auth |
| A2A SDK conformance | PyPI `a2a-sdk==1.1.2` | Agent Card discovery → JSON-RPC → 独立 server；另提交旧 v0.3 顶层 card shape | `SUBMITTED → WORKING → Artifact → COMPLETED`、task/context identity、服务端风险决策 effect、ProtoJSON rejection | 只证明 Python↔Python JSON-RPC；不证明 HTTP+JSON/gRPC parity、持久 store、cancel/subscribe |
| OpenAI Agents RunState restart | `openai-agents==0.22.0` | 进程 A 停在真实 tool approval；JSON state 在进程 B 恢复 approve/reject | exact call identity、approve effect count=1、reject effect count=0 | 使用 SDK `ScriptedModel` 和本地 tool；不证明 hosted provider 或外部 exactly-once |
| LangGraph durable restart | `langgraph==1.2.11`, SQLite checkpointer `3.1.1` | 进程 A 在 `interrupt` 暂停；进程 B 用同一 `thread_id` approve/reject | SQLite checkpoint、PID、恢复分支、prefix replay/effect counter | 不证明分布式 DB failover 或任意 graph migration；pre-interrupt effect 需应用幂等 |
| Google ADK session restart | `google-adk==2.1.0` + SQLite dependencies | 不同进程写读 `DatabaseSessionService` 并形成 approve/deny event trajectory | DB session state、events、业务 artifact、process IDs | 证明 session/event 持久化，不证明 resumable instruction pointer 或 tool exactly-once |
| Microsoft Agent Framework checkpoint restart | `agent-framework-core==1.13.0` | 进程 A 在 durable superstep 后硬退出；进程 B 先用改变后的 graph 恢复并被拒绝，再用原图继续 | file checkpoint lineage、graph hash、最终 output、effect count | 单机 local disk/core workflow only；不证明 Cosmos/distributed failover、graph migration 或外部 exactly-once |

证据入口：[`MCP`](../evidence/l5/mcp-sdk-conformance/2026-09-12-macos-arm64-py313-v1.0.0/evidence.json)、[`A2A`](../evidence/l5/a2a-sdk-conformance/2026-09-12-macos-arm64-py313-v1.0.0/evidence.json)、[`OpenAI Agents`](../evidence/l5/openai-agents-runstate-restart/2026-09-12-macos-arm64-py313-v1.0.0/evidence.json)、[`LangGraph`](../evidence/l5/langgraph-durable-restart/2026-09-12-macos-arm64-py313-v1.0.0/evidence.json)、[`Google ADK`](../evidence/l5/google-adk-session-restart/2026-09-12-macos-arm64-py313-v1.0.0/evidence.json)、[`MAF`](../evidence/l5/maf-checkpoint-restart/2026-09-12-macos-arm64-py313-v1.0.0/evidence.json)。六项证据于 2026-09-12 针对 v1.0.0 源码重新执行；知识与协议观察截止日期仍为 2026-09-11。统一 verifier 会重新计算 source/artifact SHA-256、核对 package pin、断言集合和 catalog claim，任何缺失 evidence run 都会使 QA 失败。

## 4. 协议：从“JSON 长得像”到真实互操作

### 4.1 MCP 2026-07-28

2026-07-28 revision 把 MCP 核心改为无 transport session 的 self-describing request：版本、client identity 与 capabilities 进入每次请求的 `_meta`，HTTP 使用 `Mcp-Method` / `Mcp-Name` 做路由；`initialize/initialized` 与 `Mcp-Session-Id` 不再属于新 core path。官方还把 MRTR、可缓存 list、authorization hardening 与 extension framework 纳入这一 revision。[MCP 官方发布说明](https://blog.modelcontextprotocol.io/posts/2026-07-28/)

本仓库做了两层验证。Core Lab 13 用本地 validator 快速故障注入，适合教学；L5 实验则启动官方 server，官方 client 真的发送 `tools/call`，服务端在另一个 PID 计算采购订单含税金额并写 effect record。随后对同一 body 改写 header version，确认官方 classifier 返回 `HEADER_MISMATCH`。两层结果一致，但证据意义不同。

仍需完成的互操作矩阵至少包括：Python client ↔ TypeScript/Go/C# server、反向组合、TLS/OAuth issuer validation、代理/WAF 保留 routing headers、超时/中断/MRTR、远程网络 fault，以及 tool side-effect reconciliation。没有这些证据前，“支持 MCP”只能解释为已验证组合，而不是生态兼容承诺。

### 4.2 A2A v1

A2A v1 把 `a2a.proto` 提升为规范真值，JSON 采用 ProtoJSON 规则；enum 从 kebab-case 改为 SCREAMING_SNAKE_CASE，`protocolVersion` 移入每个 `AgentInterface`，旧 `preferredTransport/additionalInterfaces` 合并为 `supportedInterfaces[]`，并正式定义 JSON-RPC、HTTP+JSON、gRPC 三种 binding。[A2A v1 官方变更说明](https://github.com/a2aproject/A2A/blob/main/docs/whats-new-v1.md)

实验没有复制官方 Hello World。服务端实现一个确定性的采购风险 agent：输入金额与 vendor risk，输出 policy、approve bit 与 reason codes。这样 task/artifact 不只是“echo 成功”，而是有可由服务器 effect 独立核对的业务语义。客户端还必须先发现 Agent Card，随后观测完整 task lifecycle。

当前 source tag 与 PyPI distribution 必须分开记录：仓库观察到 `a2a-python` source tag v1.1.4，但 2026-09-11 可安装并用于实验的发行是 `a2a-sdk==1.1.2`。把源码 tag 写成运行 package version 会破坏可复现性。

## 5. Durable execution：四个框架证明的不是同一件事

### 5.1 OpenAI Agents SDK

OpenAI Agents SDK 的 HITL 流会把待审批 tool call 暴露为 interruption；`RunState` 可序列化，调用 `approve`/`reject` 后把原 state 交回 Runner 继续。官方文档还强调 per-call approval 绑定具体 call ID，而 sticky decision 才扩展到同一 tool identity。[OpenAI Agents SDK HITL 文档](https://openai.github.io/openai-agents-python/human_in_the_loop/)；[`RunState` API](https://openai.github.io/openai-agents-python/ref/run_state/)

本仓库的关键断言不是“JSON 能保存”，而是恢复后执行的仍是原 pending call，而非新模型 turn 生成的同名调用。approve/reject 分支在新 OS 进程运行，effect counter 分别为 1/0。测试不用 provider key，因此只隔离 SDK state machine；将来加入真实 OpenAI model path 时应把 model snapshot、response IDs、usage、provider request error 与 tracing 一并存证，且绝不保存 API key。

### 5.2 LangGraph

LangGraph 官方文档说明：`interrupt()` 依赖 checkpointer 保存状态，`thread_id` 是恢复游标，恢复时用 `Command(resume=...)`；更重要的是节点从头重新执行，位于 `interrupt` 之前的代码会 replay，因此前置副作用应幂等、移到 interrupt 之后或拆分到独立 node。[LangGraph interrupts 官方文档](https://docs.langchain.com/oss/python/langgraph/interrupts)

本实验用 SQLite checkpointer 跨进程验证了这一事实，并把 replay count 纳入 observation。它反驳了一个常见误解：checkpoint 提供的是可重放状态转移，不是数据库和外部世界的原子事务。

### 5.3 Google ADK

ADK 的 `Session` 容纳 identity、events、state 与 last update；`SessionService` 负责创建、恢复和 append event。官方资料明确区分 `InMemorySessionService`（重启丢失）与 `DatabaseSessionService`（关系数据库持久化且可跨应用重启）。[Google ADK Session 官方文档](https://adk.dev/sessions/session/)

因此本实验只宣称 session/event durability。若要证明“从 workflow 的下一条指令恢复”，必须另外验证 runner/program counter、pending tool call、model response identity、version migration 与重复执行语义；不能仅凭 session 还在就推导出来。

### 5.4 Microsoft Agent Framework

MAF 官方把内置 checkpoint store 区分为：in-memory 仅进程内、file 适合单机重启、Cosmos 面向 distributed/cross-process；并明确把 checkpoint storage 视为受信任边界，file/Cosmos 对非 JSON 类型涉及受限 pickle 反序列化。[Microsoft Agent Framework checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)

本实验选择 `FileCheckpointStorage`，所以采用 hard exit + fresh process + unchanged graph identity 的验收。它还主动用变更 topology 的 graph 尝试恢复并要求失败，防止“错误图也能读 checkpoint”被当成兼容。生产多实例结论必须换用生产 store，并验证并发 ownership、lease、split-brain、schema migration 与 checkpoint tampering。

## 6. 真实 coding/browser benchmark：当前没有成绩

### 6.1 SWE-bench Lite coding agent contract

仓库固定一个真实实例 `sympy__sympy-20590` 和官方 harness commit。计划先运行 gold patch，证明 Docker evaluator 本身健康；再由官方 `swebench infer`/mini-SWE-agent 生成 patch；最后由官方 evaluator 执行 repository tests。官方文档把 `resolved` 定义为 patch 使目标测试通过，并输出 `report.json`、`test_output.txt`、`run_instance.log`、`eval.sh` 和 `patch.diff`；运行进程“没有 crash”并不等于实例 resolved。[SWE-bench 官方 evaluation guide](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/evaluation.md)

本次没有执行该任务。实际预检显示 Docker daemon `27.4.0` 可达，但可用空间 `87,892,013,056` bytes 低于本仓库 full-harness 安全门 `120 GiB`，且当前进程没有 `OPENAI_API_KEY`。因此正确状态是 `NOT_EXECUTED_IN_THIS_RELEASE`，不是 0 分。0 分只有在 agent 轨迹与官方 grader 原始输出实际生成后才是有效结果。

### 6.2 WebArena browser agent contract

WebArena 官方明确要求可复现实验使用自托管网站，demo 只供浏览；需配置七个站点 URL、生成 configs、取得 auto-login cookies，并在一轮评测后 reset 环境。[WebArena 官方仓库与 E2E 指南](https://github.com/web-arena-x/webarena)

当前七个 endpoint 都未配置，因此没有运行 Browser Agent，也没有 success rate。仓库只固定官方 commit、单任务范围、模型显式输入和 evidence requirements；`.github/workflows/external-agent-benchmarks.yml` 必须在隔离的 self-hosted runner 手工触发。浏览器任务还应保存 DOM/accessibility/screenshot observation、每一步 action、cookie setup 结果、Playwright/Chromium 版本、站点 image identity、grader 输出和 reset log。

### 6.3 为什么不能用“看起来成功”的 demo 代替

真实 Agent benchmark 评估的是闭环：

$$
TaskSnapshot + EnvironmentIdentity + AgentTrajectory + ExternalEffects + IndependentVerifier
$$

缺任何一项都可能把 harness error、数据漂移、缓存复用、登录失效或人工介入误写成模型能力。仓库 Core Lab 30 现在用采购策略 drift 演示这一点：两次局部 verifier 都为 2/2，但 fixture SHA-256 不同，所以比较必须失败。

## 7. Canonical reproducibility：定义完成，跨 host 尚未证明

`.github/workflows/cross-host-canonical.yml` 在 `ubuntu-22.04` 与 `ubuntu-24.04` 上构建同一个 digest-pinned builder path，输出 semantic artifact hash manifest，再由独立 compare job 检查。`scripts/hash_canonical_outputs.py` 与 `scripts/compare_canonical_hashes.py` 已实现 producer、surface 和 hash 的闭环。

当前仍不能写“cross-host reproducible”，因为 workflow 没有产生本次 release 的两份 runner manifest 与 compare artifact。并且 builder 中普通 APT repository 仍非 snapshot-hermetic；即使 base image digest 固定，build-time package index 也可能漂移。最终验收需要：

1. 保存两个 host 的 runner image、kernel、Docker/BuildKit、builder image digest；
2. 保存所有输入 lock/source commit 和 `SOURCE_DATE_EPOCH`；
3. 比较 PDF/EPUB/HTML/PPTX/manifest 的适当 canonical surface；
4. 对不应 bit-identical 的 metadata 先定义 semantic normalization，不能在结果出来后临时删字段；
5. 将 APT 改为 snapshot repository 或提交完整 package inventory，并在 claim ceiling 中保留剩余 non-hermetic source。

## 8. 书籍与实验应采用的统一章节结构

每个关键工程机制都应按以下链条组织，而不是“概念介绍 → API 片段 → 成功截图”：

1. **Invariant**：必须一直成立的可判定性质；
2. **State transition**：输入、前态、动作、后态和 durable boundary；
3. **Real implementation code**：关键类型、函数、identity 与 storage；
4. **Fault window**：timeout、crash、duplicate、stale state、schema drift、auth mismatch；
5. **Observation**：来自被测边界之外的事实，例如 provider receipt、server effect、repo tests；
6. **Verifier**：机器断言，不能读取 agent 自述作为真值；
7. **Evidence package**：command、environment、raw logs、artifact、hash、secret-redaction policy；
8. **Claim ceiling**：明确未证明内容；
9. **Source/pin**：course pin 与 latest observed 分开，升级必须重跑实验。

这样理论会直接决定代码中的状态字段、持久化点与 verifier，代码结果又会反过来限制正文措辞。

## 9. 密钥与外部 provider 规则

- 示例统一使用 `OPENAI_API_KEY` 环境变量，只记录是否存在，永不打印、写入 evidence 或 commit；
- 禁止 `set -x`，异常对象和 HTTP dump 在落盘前必须经过 generic `API_KEY/TOKEN/SECRET/PASSWORD/CREDENTIALS` 字段清洗；
- evidence runner 默认不把任何 secret value 传入报告，当前六项实验均不需要真实 key；
- 未来 provider run 应保存 model identifier、sampling/config、SDK version、response/request IDs、usage 与错误分类，但不保存 Authorization header；
- 一旦怀疑日志泄密，先撤销/轮换密钥，再处理历史，不用“删除一行”假设 secret 从 Git history 消失。

## 10. 下一阶段的验收优先级

### P0 — 把“已定义”变成真实外部结果

1. 在满足磁盘和隔离条件的 runner 上执行一条 SWE-bench Lite 真实任务，提交 agent trajectory、patch、gold sanity、官方 evaluator 原始文件与 hash；无论 resolved 与否都如实记录。
2. 部署并 reset WebArena 自托管 stack，执行一个固定 task，提交站点 image/config/login/trajectory/evaluator/reset 全证据。
3. 运行 cross-host canonical workflow，保存 Ubuntu 22.04/24.04 manifests 和 compare artifact；若不一致，先分类 nondeterministic surface，再修复或缩窄 claim。

### P1 — 增加真正的 interoperability/failover 深度

1. MCP：Python↔TypeScript/Go 双向矩阵、TLS/OAuth、MRTR、proxy headers、disconnect/retry 与 side-effect reconciliation。
2. A2A：Python↔Java/Go、三种 binding、authenticated task ownership、cancel、subscribe/reconnect、persistent task store 与 malformed artifact。
3. OpenAI Agents：真实 hosted model 的 approval/resume run；在不泄露 key 的前提下保存 response IDs、usage 与 provider error；对可能已送达 provider 的 UNKNOWN 单独建模。
4. LangGraph/ADK/MAF：生产数据库上的 process kill、lease/concurrency、storage outage、checkpoint corruption、schema/topology migration 与 duplicate effect。

### P2 — 从 smoke 走向研究级结论

1. 扩大 benchmark task coverage，预先注册 sampling、预算、模型参数、失败 taxonomy 和统计方法；
2. 重复运行并报告方差、confidence interval、environment failure 与 cost-per-resolved，而非只报平均分；
3. 增加 contamination、grader disagreement、prompt injection、long-horizon memory 和 human intervention audit；
4. 让第三方在干净 host 按 committed commands 重建证据，并记录无法复现的差异。

## 11. 最终审计判断

项目已经具备高质量开源教材应有的主体：理论不变量、可运行 Core Labs、真实官方 runtime 实验、机器证据门、外部 benchmark 契约和可复现构建接口。最重要的进步不是文件数增加，而是正文开始服从证据等级。

下一版不应继续追求“更多章节/更多 Hello World”。发布质量应由四个问题决定：是否真的穿过外部边界、是否真的触发并观察故障、是否有独立 verifier、是否把没有证明的部分清楚写出来。只有在真实 benchmark 和 cross-host 证据落库后，项目才可以把相应状态从 `DEFINED/NOT_EXECUTED` 升级为 `VERIFIED`。
