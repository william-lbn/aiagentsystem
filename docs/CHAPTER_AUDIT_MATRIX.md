# Chapter Audit Matrix — v1.0

本矩阵由当前 40 个 canonical chapter source 重新扫描生成。`VERIFIED_CORE` 表示本仓库 normal/fault Lab 与章节示例可本地验证；`RESEARCH_REFRESHED` 表示研究证据已按 2026-09-11 cutoff 刷新。外部上游运行仍按 `NOT_RUN_EXTERNAL` 单独记录。

| 章 | 标题 | 技术焦点 | 正文字节 | Python代码块 | 图 | 外部链接数 | 实验状态 | 研究状态 |
|---|---|---|---:|---:|---:|---:|---|---|
| 01 | AI Agent Systems：从模型调用到可运行系统 | Agent 系统边界 | 35175 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 02 | 模型基座：Token、结构化生成、工具调用与推理接口 | 模型基座与结构化动作 | 35061 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 03 | Context Engineering：信息进入模型之前已经决定了一半结果 | Context Engineering | 34366 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 04 | Messages、Structured Output 与 ReAct 轨迹 | 消息、结构化输出和轨迹 | 33315 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 05 | Planning、Workflow 与 Hybrid Control | 规划与混合控制 | 33400 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 06 | Agent State、Trajectory 与可调试性 | 状态、轨迹与调试 | 32846 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 07 | Tool Design：让模型拥有可用而可控的双手 | 工具契约设计 | 33804 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 08 | Tool Runtime：调度、权限、超时、重试与副作用语义 | 工具运行时与副作用 | 33468 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 09 | RAG 基础：检索、证据与生成边界 | RAG 基础 | 32300 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 10 | Hybrid / Agentic RAG：让检索成为决策过程 | Hybrid 与 Agentic RAG | 32550 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 11 | 长期记忆：从聊天历史到可治理的用户状态 | 长期记忆 | 33981 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 12 | Skills、Procedural Memory 与可复用能力 | Skills 与过程记忆 | 32886 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 13 | MCP：把外部工具与资源接成协议边界 | MCP 协议边界 | 34003 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 14 | Agent Loop：从 while 循环到可治理 Runtime | Agent Loop | 32649 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 15 | Async Runtime：流式、并发、中断与取消 | 异步 Runtime | 32338 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 16 | Human-in-the-Loop：把不可逆动作放进可恢复审批 | Human-in-the-Loop | 33434 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 17 | Sandbox 与权限：控制 Agent 的爆炸半径 | Sandbox 与权限 | 33055 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 18 | Checkpoint、Journal 与可恢复执行 | Checkpoint 与 Journal | 33387 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 19 | Harness 与插件运行时：模型之外的系统能力如何组合 | Harness 与插件运行时 | 34248 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 20 | Coding Agent 最小实现：读、改、测、验证 | 最小 Coding Agent | 32833 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 21 | Codex、Pi 与 Claude Code 类 Harness 解剖 | Codex/Pi/Claude Code 类 Harness | 33712 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 22 | OpenHands 与远程 Agent Server 架构 | OpenHands 与远程 Agent Server | 33040 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 23 | Browser / Computer Use Agent：观察、动作与环境验证 | Browser / Computer Use | 33425 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 24 | Data Agent：SQL、Python 与可审计分析 | Data Agent | 33430 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 25 | Research Agent：证据链、引用与报告生成 | Research Agent | 32908 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 26 | Graph Runtime：LangGraph / ADK / MAF 的共同抽象 | Graph Runtime | 33107 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 27 | A2A 与 Multi-Agent 互操作 | A2A 互操作 | 32898 | 2 | 2 | 12 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 28 | Multi-Agent 协作：分工、隔离、调度与成本 | Multi-Agent 协作 | 32867 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 29 | Agent Evaluation：从最终答案到轨迹验证 | Agent Evaluation | 33147 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 30 | SWE-bench、OSWorld、PaperBench 与 MLE-bench | Agent Benchmarks | 32897 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 31 | Tracing、Metrics 与 AgentOps | Observability 与 AgentOps | 33357 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 32 | Prompt Injection、防护与最小权限 | Agent Security | 33663 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 33 | 副作用恢复：COMMITTED、NOT_APPLIED 与 UNKNOWN | 副作用恢复 | 33871 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 34 | 性能与成本：Token、延迟、并发和缓存 | 性能与成本 | 33344 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 35 | 生产 Agent API：服务边界、租户、审批和审计 | 生产 Agent API | 32947 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 36 | 部署工程：Docker、本地开发与 CI 验证 | 部署工程 | 32895 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 37 | Post-training 与 Agent 能力塑形 | Post-training | 33066 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 38 | 多模态、语音、机器人与实时 Agent | 多模态与实时 Agent | 33138 | 2 | 2 | 9 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 39 | Self-Improving Agent：优化、验证与回滚 | Self-Improving Agent | 32906 | 2 | 2 | 10 | VERIFIED_CORE | RESEARCH_REFRESHED |
| 40 | 综合案例：AgentOps 平台的端到端闭环 | AgentOps 端到端闭环 | 34720 | 2 | 2 | 12 | VERIFIED_CORE | RESEARCH_REFRESHED |
