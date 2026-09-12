# Research Refresh — 2026-09-10

本报告按“工业现状 → 当前问题 → Research Gap → 代表性方法 → 与本书章节的关系”组织，而不是论文清单。

## Agent Runtime 与长期任务

2026 年的一个明显趋势是：Agent 能力提升不只来自模型，也来自 harness/runtime。Anthropic 关于 long-running apps 和 managed agents 的工程文章显示，initializer、planner/generator/evaluator、progress artifact、git commit、测试与上下文管理会显著影响长任务结果。本书据此强化了第 14–19 章和第 21 章：Agent Loop、Async、HITL、Sandbox、Checkpoint/Journal 和 Harness 都不是配角，而是可研究、可调试、可评估的系统层。

## Tool Side Effect 与可恢复执行

Cordon 的《Semantic Transactions for Tool-Using LLM Agents》把不可逆工具效果从“工具调用失败处理”提升为“语义事务”问题。它与数据库/分布式系统里的 WAL、幂等键、未知提交结果和补偿思想形成强关联。本书据此强化第 8、18、33、40 章：timeout 不能等同 NOT_APPLIED，checkpoint 不能证明外部 effect exactly-once，UNKNOWN 必须进入 reconciliation。

## Memory 与 Context

Memora、Mem2ActBench 和 LongMemEval-V2 把长期记忆的难点从“能不能保存历史”推进到“能否主动使用、处理过期事实、避免错误复用和控制延迟”。本书据此把第 3、11、12 章从向量检索/聊天历史提升为 memory lifecycle：provenance、confidence、forgetting、conflict resolution、skill/procedural memory 与 eval。

## MCP/A2A 与 Agent Identity

MCP 2026-07-28 specification 强调 stateless/self-contained requests、tool/resource/prompt 边界以及工具描述不可信；A2A 提供 agent-to-agent task/artifact/streaming/push 互操作。AIP 则指出 MCP/A2A 解决“如何通信”但不自动解决“谁被授权”。因此第 13、27、28、32 章被强化为 protocol + identity + policy + provenance 的组合，而不是简单 SDK 教程。

## Coding、Browser 与 Research Agent

SWE-bench、AIDev、OSWorld、BrowserGym、PaperBench、BrowseComp/Plus 与 Deep Research Bench 共同说明：专用 Agent 评估必须绑定环境、轨迹、工件和 verifier。第 20–26、29–30 章据此强调：最终答案对不等于代码补丁正确；引用存在不等于 claim 支持；浏览器点击需要环境 observation；benchmark 受基础设施与 harness 影响。

## Security 与 Observability

AgentDojo、Agent Security Bench 和 AgentDyn 将 prompt injection 从单轮 prompt 问题推进到动态工具环境、间接注入和 multi-tool policy 问题。OpenTelemetry GenAI 语义约定提供了 spans/events/metrics 的工业化方向，但 durable effect/recovery 的统一语义仍在演进。本书据此强化第 31–34 章：评估、安全、观测、性能和恢复必须作为同一个 runtime 闭环设计。

## Open Problems

- 如何给跨 MCP/A2A 的多跳 Agent 委托建立标准、低开销、可验证身份链？
- 如何把 external effect 的 UNKNOWN 状态与可审计 reconciliation 形成通用 Runtime API？
- 如何设计既能离线复现又能反映真实 web/browser/coding 工作负载的 benchmark？
- 如何把 agent trace、cost、safety、effect 和 recovery 统一到 OpenTelemetry 级别的语义约定？
- 如何评估 self-improving agent 的长期回归风险，而不只看短期 task success？
