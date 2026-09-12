# 与 `bojieli/ai-agent-book` 的对照评估

核验基线：2026-09-09 的公开主仓库。

## 总体判断

`bojieli/ai-agent-book` 仍是成熟度极高的开源 Agent 教材基线：当前主仓库公开说明为 **10 章、109 个实验、PDF/EPUB、多语言与持续维护**。V9 不应靠“页数更多”宣称全面超过，而应在**统一 Runtime、生产可靠性、故障语义、源码对照和工程验证链路**上建立清晰优势，同时承认外部实验规模、社区反馈与多语言成熟度仍落后。

## 逐维度对照

| 维度 | ai-agent-book | AI Agent Systems V9 | 判断 |
|---|---|---|---|
| 教材主线 | Agent = LLM + Context + Tools，10 章覆盖到多模态、评测、训练、自演进、多 Agent | 6 篇 35 章，从模型接口一直到 Effect Journal、生产平台、SLO 与运营 | V9 更偏系统工程纵深 |
| 实验规模 | 109 个实验，包含本地与外部复现 | 70 个 Lab：35 A + 35 B；29 个 unique 离线 examples | ai-agent-book 数量更强；V9 强调统一证据模型 |
| 代码组织 | 多章节实验项目 | `src/agentlab/` 统一 Runtime 连续演进 + examples + production | V9 更适合沿一套 Runtime 单步学习 |
| Runtime / Harness | 覆盖 tool/runtime 等核心机制 | 独立章节处理 loop、async、checkpoint、HITL、sandbox、policy、journal、recovery | V9 更深入生产控制面 |
| Coding Agent | 有 Coding Agent 实验 | 两章：最小读搜改测 + Codex/Pi/DeepSeek Harness/OpenHands/Claude Code 公开设计对照 | V9 更强调源码映射和权限/恢复 |
| 协议 | MCP 等工具生态 | MCP v2 + A2A 对象/版本/安全边界分章 | V9 更强调协议与分布式任务语义 |
| Evaluation | 有评测章节与实验 | Eval + benchmark/statistics + observability 三章，并要求 L0-L3 证据等级 | V9 更强调证据驱动工程 |
| 生产可靠性 | 有工程实践与实验 | Effect Journal、idempotency、UNKNOWN、reconciliation、checkpoint/resume 单独成体系 | V9 的核心差异化 |
| 生产案例 | 多种专题实验 | 企业 Research Agent、Coding/Ops Agent、AgentOps API、部署/SLO | V9 更强调端到端平台化 |
| 书籍工程 | PDF/EPUB、网页、多语言、社区成熟 | PDF/HTML/EPUB、79 页 PPTX、DOT/SVG/PDF 图、Makefile/CI/QA | V9 开发流程完整，但多语言/社区仍弱 |
| 事实边界 | 专门维护实验状态 | V9 也区分 verified-local / documented-external，并增加 upstream verification | 两者都应继续坚持不伪造 |

## V9 真正应该“超过”的地方

V9 的目标不是把 109 改成 120，而是让读者在学完后能处理传统 Agent 教程经常略过的问题：

1. 模型返回 tool call 之后，**谁拥有真正执行权**？
2. 高风险动作如何进入 **policy / approval / sandbox / credential** 边界？
3. 进程重启后，运行状态如何通过 **checkpoint/resume** 恢复？
4. 外部请求超时但可能已成功时，为什么必须有 **UNKNOWN / reconciliation**？
5. 如何用 **trace / journal / test / artifact / task state** 证明 Agent 完成了任务？
6. 如何把同一原理映射到 **Codex、Pi、DeepSeek Harness、OpenHands、OpenAI Agents SDK、ADK、LangGraph、MAF**，而不是被某个框架 API 绑定？

如果这些能力都能通过真实代码、失败注入和证据验证，V9 才在“Agent Systems Engineering”这一维度上形成实质性超越。

## 仍然存在的差距

- V9 的 B 轨外部真实执行覆盖仍低于理想状态；不能把完整步骤等同于已复现。
- 没有 ai-agent-book 的社区规模、多语言覆盖和长期读者反馈。
- GPU 后训练、真实机器人、完整 OSWorld/SWE-bench 仍属于外部重型实验。
- 生产案例是 production-style teaching system，不声称经过真实企业流量认证。
