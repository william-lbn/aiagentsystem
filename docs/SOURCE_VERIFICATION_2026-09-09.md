# Source Verification — 2026-09-09

本表只收录能够由官方仓库、官方文档或正式论文页面核验的事实。第三方博客不作为版本/源码事实的唯一依据。

## bojieli/ai-agent-book
- Source: https://github.com/bojieli/ai-agent-book
- Lock/status: `main; 10 chapters / 109 experiments observed 2026-09-09`
- Verified statement: 对标开源教材：正文、实验 ledger、PDF/EPUB、多语言。

## OpenAI Agents SDK
- Source: https://github.com/openai/openai-agents-python
- Lock/status: `v0.22.0 @ 4df9ecf`
- Verified statement: Agent/Runner/Tools/Handoffs/Guardrails/Sessions/HITL/Tracing；0.22.0 包含 runtime hardening。

## OpenAI Agents documentation
- Source: https://openai.github.io/openai-agents-python/
- Lock/status: `docs observed 2026-09-09`
- Verified statement: SDK 管理 agent loop、tools、handoffs、sessions；也提供 tracing 与 sandbox agent 等能力。

## OpenAI Codex CLI
- Source: https://github.com/openai/codex
- Lock/status: `0.139.0 historical reproducibility pin`
- Verified statement: 开源 Rust coding agent；公开源码可分析 sandbox、approval 与 CLI execution boundary。
- Verified paths: codex-rs/utils/cli/src/shared_options.rs, codex-rs/core/config.schema.json

## Google Agent Development Kit
- Source: https://github.com/google/adk-python
- Lock/status: `v2.1.0 @ 6d15e19`
- Verified statement: Agent、workflow、sandbox、telemetry、evaluation/deployment 参考实现。

## Google ADK documentation
- Source: https://google.github.io/adk-docs/
- Lock/status: `docs observed 2026-09-09`
- Verified statement: Agent/Sequential/Parallel/Loop、多 Agent、session/memory/eval/deployment。

## LangGraph
- Source: https://github.com/langchain-ai/langgraph
- Lock/status: `langgraph==1.2.11 @ 644815f`
- Verified statement: 状态图、durable execution、checkpointer、HITL、pending writes/fault tolerance。

## LangGraph / LangChain HITL docs
- Source: https://docs.langchain.com/oss/python/langchain/human-in-the-loop
- Lock/status: `docs observed 2026-09-09`
- Verified statement: interrupt/resume 依赖持久化 graph state。

## Microsoft Agent Framework
- Source: https://github.com/microsoft/agent-framework
- Lock/status: `Python 1.13.0`
- Verified statement: Agents、Workflows、Memory、Tools、Skills、Security、Hosting、Observability。

## Microsoft Agent Framework checkpoints
- Source: https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints
- Lock/status: `docs observed 2026-09-09`
- Verified statement: checkpoint 捕获 executor states、pending messages/requests、shared state，用于 resume。

## DeepSeek Harness
- Source: https://github.com/deepseek-ai/deepseek-harness
- Lock/status: `@deepseek-ai/dsh 0.1.2-rc.1 reproducibility pin`
- Verified statement: Developer preview；Everything is a Plugin，基于 Cordis context/service/lifecycle。
- Verified paths: docs/architecture.md, docs/user/develop/framework/service.md

## DeepSeek Harness documentation
- Source: https://www.deepseek.com/harness/en/
- Lock/status: `developer preview`
- Verified statement: 模型、工具、技能、会话、sandbox、存储、loop、scheduling、UI 可插件化。

## Pi Coding Agent
- Source: https://github.com/earendil-works/pi
- Lock/status: `@earendil-works/pi-coding-agent 0.85.1`
- Verified statement: 极简 terminal coding harness；extensions、skills、sessions、branching/compaction；旧 @mariozechner 包已弃用。

## OpenHands Software Agent SDK
- Source: https://github.com/OpenHands/software-agent-sdk
- Lock/status: `v1.24.0 @ fdc2bdf`
- Verified statement: agents、tools、conversations、workspaces、events，支持 Agent Server。

## OpenHands SDK architecture
- Source: https://docs.openhands.dev/sdk/arch/overview
- Lock/status: `docs observed 2026-09-09`
- Verified statement: Software Agent SDK / Agent Server / applications 分层。

## Model Context Protocol Python SDK
- Source: https://github.com/modelcontextprotocol/python-sdk
- Lock/status: `mcp==2.2.0 (v2 stable line); protocol revision 2026-07-28`
- Verified statement: v2 当前稳定线；新 revision 取消新路径的 handshake/session，Client 可向旧 revision 回退。
- Verified paths: docs/whats-new.md, docs/protocol-versions.md, ROADMAP.md

## A2A Protocol
- Source: https://github.com/a2aproject/A2A
- Lock/status: `spec v1.0.1 @ 3303592 (v1.0.0 @ 1736957)`
- Verified statement: Agent Card、task/artifact、streaming/push 与跨实现互操作；v1.0 为稳定线。

## Hugging Face smolagents
- Source: https://github.com/huggingface/smolagents
- Lock/status: `source observed 2026-09-09`
- Verified statement: CodeAgent 与 ToolCallingAgent 的轻量实现对照。

## Letta
- Source: https://github.com/letta-ai/letta
- Lock/status: `source observed 2026-09-09`
- Verified statement: stateful agents / long-term memory 参考。

## Mem0
- Source: https://github.com/mem0ai/mem0
- Lock/status: `source observed 2026-09-09`
- Verified statement: 记忆抽取、检索与评估参考。

## SWE-bench
- Source: https://github.com/swe-bench/SWE-bench
- Lock/status: `benchmark source observed 2026-09-09`
- Verified statement: 真实 GitHub issue + repository snapshot + Docker/test verifier。

## OSWorld
- Source: https://github.com/xlang-ai/OSWorld
- Lock/status: `benchmark source observed 2026-09-09`
- Verified statement: 真实计算机环境的 observation/action/evaluator。

## OpenAI PaperBench
- Source: https://openai.com/index/paperbench/
- Lock/status: `2025 benchmark`
- Verified statement: 论文复现任务与细粒度 rubric/grader。

## OpenAI MLE-bench
- Source: https://openai.com/index/mle-bench/
- Lock/status: `2024 benchmark`
- Verified statement: 75 个 Kaggle-style ML engineering competitions。

## Anthropic: Building Effective Agents
- Source: https://www.anthropic.com/engineering/building-effective-agents
- Lock/status: `official engineering article`
- Verified statement: 从简单、可组合的 workflow/agent 模式开始。

## Anthropic: Writing effective tools for agents
- Source: https://www.anthropic.com/engineering/writing-tools-for-agents
- Lock/status: `official engineering article`
- Verified statement: 工具接口本身是 Agent 性能与安全的重要变量。

## Anthropic: Demystifying evals for AI agents
- Source: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Lock/status: `2026-01-09`
- Verified statement: Agent eval 需要 task/environment/trajectory/grader 共同设计。

## Anthropic: Harness design for long-running apps
- Source: https://www.anthropic.com/engineering/harness-design-long-running-apps
- Lock/status: `2026-03-24`
- Verified statement: long-running coding 中 planner/generator/evaluator 与 harness 设计影响结果。

## 研究论文
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) — 提出 reasoning/action 交错轨迹，连接语言推理与外部环境动作。
- [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/abs/2302.04761) — 探索模型学习何时调用外部工具以及如何把工具结果纳入后续预测。
- [Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://proceedings.neurips.cc/paper_files/paper/2023/hash/271db9922b8d1f4dd7aaef84ed5ac703-Abstract-Conference.html) — 把单路径推理扩展为可搜索的 thought tree，支持 lookahead/backtracking。
- [Language Agent Tree Search](https://proceedings.mlr.press/v235/zhou24r.html) — ICML 2024；把 tree search、环境反馈、反思和值函数组合到 Agent 决策。
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366) — 通过外部反馈与语言化反思把失败经验写入后续尝试。
- [Voyager: An Open-Ended Embodied Agent with Large Language Models](https://arxiv.org/abs/2305.16291) — 自动课程、技能库和迭代 prompting 的 embodied agent。
- [AgentBench: Evaluating LLMs as Agents](https://arxiv.org/abs/2308.03688) — 多环境 Agent benchmark，推动从答案评估转向交互任务评估。
- [AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses](https://arxiv.org/abs/2406.13352) — 以工具返回内容中的 prompt injection 测试 Agent 安全边界。
- [Agent Security Bench](https://arxiv.org/abs/2410.02644) — 多场景、多工具、多攻击/防御类型的 Agent 安全评测。