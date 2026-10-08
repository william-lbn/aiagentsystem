# 全书章节审计矩阵（源码结构核验）

本表由 `python scripts/generate_chapter_audit_matrix.py --write` 从当前 canonical 章节和 Core Labs 机械生成；CI 使用 `--check` 防止陈旧数字。它**只核验结构、文件与链接入口**，不把章节长度、代码块数或存在实验等同于理论正确、模型效果、外部 SDK 互操作或 L5 证据。协议/研究事实的书内时间边界仍为 2026-09-11。

全书实质性审计结论与未完成项见 [Full-Book Technical Audit](FULL_BOOK_TECHNICAL_AUDIT.md)。若新增理论主张、性能数字、外部兼容声明或训练结果，必须单独提交来源、执行日志、verifier 与环境身份。

| 章 | Canonical 正文 | UTF-8 字节 | Python 块 | 图 | 外链 | A/B 实验入口 | 必备论证结构 |
|---|---|---:|---:|---:|---:|---|---|
| 01 | [AI Agent Systems：从生成模型到可治理行动系统](../book/zh/chapters/01-foundation.md) | 17234 | 2 | 2 | 8 | [A](../labs/core/lab-01A-foundation.md) / [B](../labs/core/lab-01B-foundation-fault.md) | 齐全 |
| 02 | [模型基座：概率生成、结构化决策与工具调用边界](../book/zh/chapters/02-model-substrate.md) | 14461 | 2 | 2 | 4 | [A](../labs/core/lab-02A-model-substrate.md) / [B](../labs/core/lab-02B-model-substrate-fault.md) | 齐全 |
| 03 | [Context Engineering：把信息配置成受治理的运行时视图](../book/zh/chapters/03-context.md) | 14040 | 2 | 2 | 5 | [A](../labs/core/lab-03A-context.md) / [B](../labs/core/lab-03B-context-fault.md) | 齐全 |
| 04 | [Messages 与 Trajectory：Agent 的类型化事件语言](../book/zh/chapters/04-messages.md) | 12876 | 2 | 2 | 7 | [A](../labs/core/lab-04A-messages.md) / [B](../labs/core/lab-04B-messages-fault.md) | 齐全 |
| 05 | [Planning 与 Hybrid Control：从候选步骤到可执行计划](../book/zh/chapters/05-planning.md) | 13521 | 2 | 2 | 7 | [A](../labs/core/lab-05A-planning.md) / [B](../labs/core/lab-05B-planning-fault.md) | 齐全 |
| 06 | [Agent State 与 Trajectory：可恢复、可重放、可并发的执行语义](../book/zh/chapters/06-state.md) | 13360 | 2 | 2 | 5 | [A](../labs/core/lab-06A-state.md) / [B](../labs/core/lab-06B-state-fault.md) | 齐全 |
| 07 | [Tool Design：让模型拥有可用而可控的双手](../book/zh/chapters/07-tool-design.md) | 14297 | 2 | 2 | 4 | [A](../labs/core/lab-07A-tool-design.md) / [B](../labs/core/lab-07B-tool-design-fault.md) | 齐全 |
| 08 | [Tool Runtime：调度、权限、超时、重试与副作用语义](../book/zh/chapters/08-tool-runtime.md) | 12632 | 2 | 2 | 1 | [A](../labs/core/lab-08A-tool-runtime.md) / [B](../labs/core/lab-08B-tool-runtime-fault.md) | 齐全 |
| 09 | [RAG 基础：检索、证据与生成边界](../book/zh/chapters/09-retrieval.md) | 11868 | 2 | 2 | 3 | [A](../labs/core/lab-09A-retrieval.md) / [B](../labs/core/lab-09B-retrieval-fault.md) | 齐全 |
| 10 | [Hybrid / Agentic RAG：让检索成为决策过程](../book/zh/chapters/10-hybrid-rag.md) | 11888 | 2 | 2 | 3 | [A](../labs/core/lab-10A-hybrid-rag.md) / [B](../labs/core/lab-10B-hybrid-rag-fault.md) | 齐全 |
| 11 | [长期记忆：从聊天历史到可治理的用户状态](../book/zh/chapters/11-memory.md) | 12104 | 2 | 2 | 2 | [A](../labs/core/lab-11A-memory.md) / [B](../labs/core/lab-11B-memory-fault.md) | 齐全 |
| 12 | [Skills、Procedural Memory 与可复用能力](../book/zh/chapters/12-skills.md) | 10991 | 2 | 2 | 0 | [A](../labs/core/lab-12A-skills.md) / [B](../labs/core/lab-12B-skills-fault.md) | 齐全 |
| 13 | [MCP：把外部工具与资源接成协议边界](../book/zh/chapters/13-mcp.md) | 12826 | 2 | 2 | 2 | [A](../labs/core/lab-13A-mcp.md) / [B](../labs/core/lab-13B-mcp-fault.md) | 齐全 |
| 14 | [Agent Loop：从概率决策到可治理状态机](../book/zh/chapters/14-agent-loop.md) | 12627 | 2 | 2 | 3 | [A](../labs/core/lab-14A-agent-loop.md) / [B](../labs/core/lab-14B-agent-loop-fault.md) | 齐全 |
| 15 | [异步 Runtime：结构化并发、流式事件与取消语义](../book/zh/chapters/15-async.md) | 10512 | 2 | 2 | 4 | [A](../labs/core/lab-15A-async.md) / [B](../labs/core/lab-15B-async-fault.md) | 齐全 |
| 16 | [Human-in-the-Loop：把人类决定变成可验证授权](../book/zh/chapters/16-hitl.md) | 10341 | 2 | 2 | 4 | [A](../labs/core/lab-16A-hitl.md) / [B](../labs/core/lab-16B-hitl-fault.md) | 齐全 |
| 17 | [Sandbox 与能力安全：限制 Agent 的真实爆炸半径](../book/zh/chapters/17-sandbox.md) | 10771 | 2 | 2 | 4 | [A](../labs/core/lab-17A-sandbox.md) / [B](../labs/core/lab-17B-sandbox-fault.md) | 齐全 |
| 18 | [Checkpoint、Journal 与 Durable Execution](../book/zh/chapters/18-checkpoint-journal.md) | 10797 | 2 | 2 | 4 | [A](../labs/core/lab-18A-checkpoint-journal.md) / [B](../labs/core/lab-18B-checkpoint-journal-fault.md) | 齐全 |
| 19 | [Agent Harness：模型之外的系统产品](../book/zh/chapters/19-harness.md) | 10174 | 2 | 2 | 5 | [A](../labs/core/lab-19A-harness.md) / [B](../labs/core/lab-19B-harness-fault.md) | 齐全 |
| 20 | [最小 Coding Agent：读、定位、修改、验证与回滚](../book/zh/chapters/20-coding-minimal.md) | 10709 | 2 | 2 | 4 | [A](../labs/core/lab-20A-coding-minimal.md) / [B](../labs/core/lab-20B-coding-minimal-fault.md) | 齐全 |
| 21 | [Codex、Pi 与 Claude Code 类 Harness 解剖](../book/zh/chapters/21-coding-harness.md) | 12960 | 2 | 2 | 1 | [A](../labs/core/lab-21A-coding-harness.md) / [B](../labs/core/lab-21B-coding-harness-fault.md) | 齐全 |
| 22 | [OpenHands 与远程 Agent Server 架构](../book/zh/chapters/22-openhands.md) | 12194 | 2 | 2 | 1 | [A](../labs/core/lab-22A-openhands.md) / [B](../labs/core/lab-22B-openhands-fault.md) | 齐全 |
| 23 | [Browser / Computer Use Agent：观察、动作与环境验证](../book/zh/chapters/23-browser.md) | 11636 | 2 | 2 | 1 | [A](../labs/core/lab-23A-browser.md) / [B](../labs/core/lab-23B-browser-fault.md) | 齐全 |
| 24 | [Data Agent：SQL、Python 与可审计分析](../book/zh/chapters/24-data-agent.md) | 10924 | 2 | 2 | 0 | [A](../labs/core/lab-24A-data-agent.md) / [B](../labs/core/lab-24B-data-agent-fault.md) | 齐全 |
| 25 | [Research Agent：证据链、引用与报告生成](../book/zh/chapters/25-research-agent.md) | 11059 | 2 | 2 | 0 | [A](../labs/core/lab-25A-research-agent.md) / [B](../labs/core/lab-25B-research-agent-fault.md) | 齐全 |
| 26 | [Graph Runtime：LangGraph / ADK / MAF 的共同抽象](../book/zh/chapters/26-workflow-graph.md) | 11788 | 2 | 2 | 0 | [A](../labs/core/lab-26A-workflow-graph.md) / [B](../labs/core/lab-26B-workflow-graph-fault.md) | 齐全 |
| 27 | [A2A 与 Multi-Agent 互操作](../book/zh/chapters/27-a2a.md) | 17048 | 2 | 2 | 5 | [A](../labs/core/lab-27A-a2a.md) / [B](../labs/core/lab-27B-a2a-fault.md) | 齐全 |
| 28 | [Multi-Agent 协作：分工、隔离、调度与成本](../book/zh/chapters/28-multi-agent.md) | 16588 | 2 | 2 | 5 | [A](../labs/core/lab-28A-multi-agent.md) / [B](../labs/core/lab-28B-multi-agent-fault.md) | 齐全 |
| 29 | [Agent Evaluation：从最终答案到轨迹验证](../book/zh/chapters/29-evaluation.md) | 15335 | 2 | 2 | 0 | [A](../labs/core/lab-29A-evaluation.md) / [B](../labs/core/lab-29B-evaluation-fault.md) | 齐全 |
| 30 | [SWE-bench、OSWorld、PaperBench 与 MLE-bench](../book/zh/chapters/30-benchmarks.md) | 15108 | 2 | 2 | 4 | [A](../labs/core/lab-30A-benchmarks.md) / [B](../labs/core/lab-30B-benchmarks-fault.md) | 齐全 |
| 31 | [Tracing、Metrics 与 AgentOps](../book/zh/chapters/31-observability.md) | 13724 | 2 | 2 | 0 | [A](../labs/core/lab-31A-observability.md) / [B](../labs/core/lab-31B-observability-fault.md) | 齐全 |
| 32 | [Prompt Injection、防护与最小权限](../book/zh/chapters/32-security.md) | 14418 | 2 | 2 | 0 | [A](../labs/core/lab-32A-security.md) / [B](../labs/core/lab-32B-security-fault.md) | 齐全 |
| 33 | [副作用恢复：COMMITTED、NOT_APPLIED 与 UNKNOWN](../book/zh/chapters/33-effect-recovery.md) | 13614 | 2 | 2 | 0 | [A](../labs/core/lab-33A-effect-recovery.md) / [B](../labs/core/lab-33B-effect-recovery-fault.md) | 齐全 |
| 34 | [性能与成本：Token、延迟、并发和缓存](../book/zh/chapters/34-performance.md) | 13626 | 2 | 2 | 0 | [A](../labs/core/lab-34A-performance.md) / [B](../labs/core/lab-34B-performance-fault.md) | 齐全 |
| 35 | [生产 Agent API：服务边界、租户、审批和审计](../book/zh/chapters/35-production-api.md) | 13650 | 2 | 2 | 0 | [A](../labs/core/lab-35A-production-api.md) / [B](../labs/core/lab-35B-production-api-fault.md) | 齐全 |
| 36 | [部署工程：Docker、本地开发与 CI 验证](../book/zh/chapters/36-deployment.md) | 14772 | 2 | 2 | 2 | [A](../labs/core/lab-36A-deployment.md) / [B](../labs/core/lab-36B-deployment-fault.md) | 齐全 |
| 37 | [Post-training 与 Agent 能力塑形](../book/zh/chapters/37-post-training.md) | 13932 | 2 | 2 | 3 | [A](../labs/core/lab-37A-post-training.md) / [B](../labs/core/lab-37B-post-training-fault.md) | 齐全 |
| 38 | [多模态、语音、机器人与实时 Agent](../book/zh/chapters/38-multimodal.md) | 13938 | 2 | 2 | 3 | [A](../labs/core/lab-38A-multimodal.md) / [B](../labs/core/lab-38B-multimodal-fault.md) | 齐全 |
| 39 | [Self-Improving Agent：优化、验证与回滚](../book/zh/chapters/39-self-improve.md) | 12722 | 2 | 2 | 2 | [A](../labs/core/lab-39A-self-improve.md) / [B](../labs/core/lab-39B-self-improve-fault.md) | 齐全 |
| 40 | [综合案例：AgentOps 平台的端到端闭环](../book/zh/chapters/40-capstone.md) | 14676 | 2 | 2 | 0 | [A](../labs/core/lab-40A-capstone.md) / [B](../labs/core/lab-40B-capstone-fault.md) | 齐全 |

判读：A/B 表示正常路径与故障路径的教材入口存在；是否实际执行见 `VALIDATION_REPORT.md` 和对应 CI run。外链数仅统计 URL 的出现，不保证链接内容、日期或主张获验证。目录级 QA 无法代替逐条研究核证或外部可复现性。
