# AI Agent Systems：原理、Runtime、工程与研究

## 第一篇 基础：从模型接口到可调试 Agent

- [AI Agent Systems：从模型调用到可运行系统](chapters/01-foundation.md)
- [模型基座：Token、结构化生成、工具调用与推理接口](chapters/02-model-substrate.md)
- [Context Engineering：信息进入模型之前已经决定了一半结果](chapters/03-context.md)
- [Messages、Structured Output 与 ReAct 轨迹](chapters/04-messages.md)
- [Planning、Workflow 与 Hybrid Control](chapters/05-planning.md)
- [Agent State、Trajectory 与可调试性](chapters/06-state.md)

## 第二篇 知识、工具、记忆与协议

- [Tool Design：让模型拥有可用而可控的双手](chapters/07-tool-design.md)
- [Tool Runtime：调度、权限、超时、重试与副作用语义](chapters/08-tool-runtime.md)
- [RAG 基础：检索、证据与生成边界](chapters/09-retrieval.md)
- [Hybrid / Agentic RAG：让检索成为决策过程](chapters/10-hybrid-rag.md)
- [长期记忆：从聊天历史到可治理的用户状态](chapters/11-memory.md)
- [Skills、Procedural Memory 与可复用能力](chapters/12-skills.md)
- [MCP：把外部工具与资源接成协议边界](chapters/13-mcp.md)

## 第三篇 Runtime、Durable Execution 与 Harness

- [Agent Loop：从 while 循环到可治理 Runtime](chapters/14-agent-loop.md)
- [Async Runtime：流式、并发、中断与取消](chapters/15-async.md)
- [Human-in-the-Loop：把不可逆动作放进可恢复审批](chapters/16-hitl.md)
- [Sandbox 与权限：控制 Agent 的爆炸半径](chapters/17-sandbox.md)
- [Checkpoint、Journal 与可恢复执行](chapters/18-checkpoint-journal.md)
- [Harness 与插件运行时：模型之外的系统能力如何组合](chapters/19-harness.md)
- [Coding Agent 最小实现：读、改、测、验证](chapters/20-coding-minimal.md)

## 第四篇 专用 Agent 与真实环境

- [Codex、Pi 与 Claude Code 类 Harness 解剖](chapters/21-coding-harness.md)
- [OpenHands 与远程 Agent Server 架构](chapters/22-openhands.md)
- [Browser / Computer Use Agent：观察、动作与环境验证](chapters/23-browser.md)
- [Data Agent：SQL、Python 与可审计分析](chapters/24-data-agent.md)
- [Research Agent：证据链、引用与报告生成](chapters/25-research-agent.md)
- [Graph Runtime：LangGraph / ADK / MAF 的共同抽象](chapters/26-workflow-graph.md)

## 第五篇 Workflow、Multi-Agent 与互操作

- [A2A 与 Multi-Agent 互操作](chapters/27-a2a.md)
- [Multi-Agent 协作：分工、隔离、调度与成本](chapters/28-multi-agent.md)

## 第六篇 Evaluation、Benchmark、Observability、安全与可靠性

- [Agent Evaluation：从最终答案到轨迹验证](chapters/29-evaluation.md)
- [SWE-bench、OSWorld、PaperBench 与 MLE-bench](chapters/30-benchmarks.md)
- [Tracing、Metrics 与 AgentOps](chapters/31-observability.md)
- [Prompt Injection、防护与最小权限](chapters/32-security.md)
- [副作用恢复：COMMITTED、NOT_APPLIED 与 UNKNOWN](chapters/33-effect-recovery.md)
- [性能与成本：Token、延迟、并发和缓存](chapters/34-performance.md)
- [生产 Agent API：服务边界、租户、审批和审计](chapters/35-production-api.md)

## 第七篇 生产工程、训练与持续演进

- [部署工程：Docker、本地开发与 CI 验证](chapters/36-deployment.md)
- [Post-training 与 Agent 能力塑形](chapters/37-post-training.md)
- [多模态、语音、机器人与实时 Agent](chapters/38-multimodal.md)
- [Self-Improving Agent：优化、验证与回滚](chapters/39-self-improve.md)
- [综合案例：AgentOps 平台的端到端闭环](chapters/40-capstone.md)

## 附录

- [附录 A：统一实验环境、调试与复现](appendix-a-environment.md)
- [附录 B：上游开源项目版本锁与源码阅读索引](appendix-b-upstream-lock.md)
- [附录 C：Agent Systems 故障模型与排错速查](appendix-c-failure-debug.md)
- [附录 D：术语、不变量与状态词典](appendix-d-glossary.md)
- [附录 E：2026 AI Agent 研究版图、理论前沿与开放问题](appendix-e-research-frontier.md)
- [附录 F：AI Agent 行业状态、产业影响与 2026–2030 发展判断](appendix-f-industry-future.md)
