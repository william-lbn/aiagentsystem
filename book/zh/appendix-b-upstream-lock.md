# 附录 B：上游开源项目版本锁与源码阅读索引

> 核验日期：2026-09-11。本附录是 `integrations/SOURCE_LOCK.json` 的出版视图。`course_pin` 用于复现实验；`latest_observed` 用于研究刷新。当前有 6 项 scoped 官方实现证据；其余没有运行的外部框架、完整 upstream contract 与 benchmark 仍只作为来源/执行合同，不作运行成功声明。

## B.0 源码阅读与上游实验的证据规则

章节中的“源码阅读入口”只追公开可定位对象，不根据产品 UI 或客户端行为猜测闭源服务端实现。建议固定四条线：**入口/API → session/durable state → tool/workspace/protocol boundary → trace/checkpoint/verifier**。若某条线在上游没有公开证据，记录“未公开/未核验”比补一个看似合理的内部组件名更准确。

上游复现实验与 Core Lab 分开：clone、安装和版本打印属于 preparation；只有执行章节指定的 behavior scenario、保留 observation，并让独立 verifier 判定，才能授予有 scope 的 L5_EXTERNAL。本次已执行 MCP、A2A、OpenAI Agents、LangGraph、Google ADK 与 MAF 六项范围受限实验；它们不自动完成十个更宽的 upstream contracts。没有真正执行的部分继续标为 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

六项 evidence vector、真实 benchmark 状态与 claim ceiling 见[《L5 外部证据深度审计》](../../docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md)。

## B.1 版本锁原则

- **Reproducibility pin**：课程实验/源码阅读依赖的固定版本，不因“今天有更新”而静默漂移。
- **Latest observed**：截至研究截止日观察到的最新稳定版本，用于解释生态变化。
- **Evidence source**：论文、规范、监管材料与厂商研究记录为知识证据，不自动变成代码依赖。

| 来源 | Course Pin / Evidence Pin | Latest Observed | 用途/说明 | 官方来源 |
|---|---|---|---|---|
| A2A Protocol | `spec v1.0.1 @ 3303592` | A2A spec v1.0.1；a2a-python source tag v1.1.4（2026-09-08）；PyPI `a2a-sdk==1.1.2`（observed 2026-09-11） | spec v1.0.1 @ 3303592 (v1.0.0 @ 1736957) | [source](https://github.com/a2aproject/A2A) |
| A2A Python SDK release evidence | `source tag v1.1.4 @ 2d4d304; 2026-09-08` | PyPI latest remains `1.1.2` | ownership, cancel/subscribe, store correctness；源码 tag 与分发版本必须分开记录 | [source](https://github.com/a2aproject/a2a-python/releases/tag/v1.1.4) |
| American Bar Association: Agentic AI and legal supervision | `2026; observed 2026-09-11` | - | legal professional responsibility and supervision | [source](https://www.americanbar.org/groups/law_practice/resources/law-practice-today/2026/may-june-2026/agentic-ai/) |
| Google Agent Development Kit | `v2.1.0 @ 6d15e19 retained unless upstream lab is re-run` | google-adk 2.9.0 @ 1679384（released 2026-09-10, observed 2026-09-11） | v2.1.0 @ 6d15e19 | [source](https://github.com/google/adk-python) |
| Google ADK release evidence | `2.9.0 @ 1679384; 2026-09-10` | - | workflow/runtime ecosystem observation | [source](https://github.com/google/adk-python/releases/tag/v2.9.0) |
| Google ADK documentation | `docs observed 2026-09-09` | - | docs observed 2026-09-09 | [source](https://google.github.io/adk-docs/) |
| Agent Memory as a System | `arXiv:2606.06448; observed 2026-09-11` | - | memory systems and control | [source](https://arxiv.org/abs/2606.06448) |
| AgentBench | `arXiv:2308.03688` | - | foundational LLM-agent benchmark | [source](https://arxiv.org/abs/2308.03688) |
| AgentDojo | `arXiv:2406.13352` | - | prompt-injection security benchmark | [source](https://arxiv.org/abs/2406.13352) |
| AgentDyn | `arXiv 2602.03117; observed 2026-09-10` | - | arXiv 2602.03117; observed 2026-09-10 | [source](https://arxiv.org/abs/2602.03117) |
| bojieli/ai-agent-book | `main; 10 chapters / 109 experiments observed 2026-09-09` | - | main; 10 chapters / 109 experiments observed 2026-09-09 | [source](https://github.com/bojieli/ai-agent-book) |
| AIDev: Studying AI Coding Agents on GitHub | `arXiv 2602.09185; observed 2026-09-10` | - | arXiv 2602.09185; observed 2026-09-10 | [source](https://arxiv.org/abs/2602.09185) |
| AIP: Agent Identity Protocol for Verifiable Delegation Across MCP and A2A | `arXiv 2603.24775; observed 2026-09-10` | - | arXiv 2603.24775; observed 2026-09-10 | [source](https://arxiv.org/abs/2603.24775) |
| Anthropic: Building Effective Agents | `official engineering article` | - | official engineering article | [source](https://www.anthropic.com/engineering/building-effective-agents) |
| Anthropic: Automated researchers can reliably mitigate alignment failures | `2026-08-28` | - | research agents and automated oversight | [source](https://www.anthropic.com/research/automated-researchers-mitigate-alignment-failures) |
| Anthropic: Alignment assessment of recent cybersecurity incidents | `2026-09-09` | - | real-world agentic security incidents | [source](https://www.anthropic.com/research/alignment-assessment-cybersecurity-incidents) |
| Anthropic: Demystifying evals for AI agents | `2026-01-09` | - | 2026-01-09 | [source](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) |
| Anthropic: Formalizing Fermat's Last Theorem | `2026-09-04` | - | long-running research/formalization agent | [source](https://www.anthropic.com/research/formalizing-fermats-last-theorem) |
| Anthropic: Harness design for long-running apps | `2026-03-24` | - | 2026-03-24 | [source](https://www.anthropic.com/engineering/harness-design-long-running-apps) |
| Anthropic: Patterns and problems in emerging multiagent systems | `2026-08-13` | - | multi-agent coordination and societal/system risks | [source](https://www.anthropic.com/research/multiagent-systems) |
| Anthropic: Writing effective tools for agents | `official engineering article` | - | official engineering article | [source](https://www.anthropic.com/engineering/writing-tools-for-agents) |
| Agent Planning Benchmark | `arXiv:2606.04874; observed 2026-09-11` | - | planning diagnostics; 4,209 cases | [source](https://arxiv.org/abs/2606.04874) |
| Bank of England Financial Stability Report July 2026 | `2026-07` | - | autonomous AI in financial markets | [source](https://www.bankofengland.co.uk/financial-stability-report/2026/july-2026) |
| OpenAI Codex CLI | `codex@0.139.0 historical reproducibility pin` | Codex CLI v0.154.0 (released 2026-09-09, observed 2026-09-11) | historical reproducibility pin retained | [source](https://github.com/openai/codex) |
| OpenAI Codex CLI release evidence | `0.154.0; 2026-09-09` | - | coding agent harness latest-observed release | [source](https://github.com/openai/codex/releases/tag/rust-v0.154.0) |
| Deployment-Time Memorization in Foundation-Model Agents | `arXiv:2606.10062; observed 2026-09-11` | - | memory privacy, deletion fidelity, forgetting residue | [source](https://arxiv.org/abs/2606.10062) |
| DPBench | `arXiv 2602.13255; observed 2026-09-10` | - | arXiv 2602.13255; observed 2026-09-10 | [source](https://arxiv.org/abs/2602.13255) |
| DeepSeek Harness | `@deepseek-ai/dsh 0.1.2-rc.1 reproducibility pin` | - | @deepseek-ai/dsh 0.1.2-rc.1 reproducibility pin | [source](https://github.com/deepseek-ai/deepseek-harness) |
| DeepSeek Harness documentation | `developer preview` | - | developer preview | [source](https://www.deepseek.com/harness/en/) |
| EduAgentBench | `arXiv:2605.14322; observed 2026-09-11` | - | education agent evaluation | [source](https://arxiv.org/abs/2605.14322) |
| Financial Stability Board: Sound Practices for Responsible Adoption of AI | `consultation report 2026-06-10` | - | financial-sector AI governance | [source](https://www.fsb.org/2026/06/sound-practices-for-responsible-adoption-of-artificial-intelligence-ai-consultation-report/) |
| HealthAgentBench | `arXiv:2606.31179; observed 2026-09-11` | - | healthcare agent evaluation | [source](https://arxiv.org/abs/2606.31179) |
| LangGraph / LangChain HITL docs | `docs observed 2026-09-09` | - | docs observed 2026-09-09 | [source](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) |
| LangGraph | `langgraph==1.2.11 @ 644815f` | - | langgraph==1.2.11 @ 644815f | [source](https://github.com/langchain-ai/langgraph) |
| Letta | `source observed 2026-09-09` | - | source observed 2026-09-09 | [source](https://github.com/letta-ai/letta) |
| LongHorizon-Harness | `arXiv 2608.01964; observed 2026-09-10` | - | arXiv 2608.01964; observed 2026-09-10 | [source](https://arxiv.org/abs/2608.01964) |
| LongMemEval-V2 | `arXiv 2605.12493; observed 2026-09-10` | - | arXiv 2605.12493; observed 2026-09-10 | [source](https://arxiv.org/abs/2605.12493) |
| Microsoft Agent Framework | `Python 1.13.0 retained for course notes unless upstream lab is re-run` | Python 1.18.0 @ 3ad2b07（released 2026-09-10, observed 2026-09-11） | Python 1.13.0 | [source](https://github.com/microsoft/agent-framework) |
| Microsoft Agent Framework release evidence | `Python 1.18.0 @ 3ad2b07; 2026-09-10` | - | hosting, replay, concurrency contracts | [source](https://github.com/microsoft/agent-framework/releases/tag/python-1.18.0) |
| Microsoft Agent Framework checkpoints | `docs observed 2026-09-09` | - | docs observed 2026-09-09 | [source](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints) |
| Model Context Protocol Python SDK | `mcp==2.2.0` | Python SDK v2.2.0; protocol revision 2026-07-28 | mcp==2.2.0 (v2 stable line); protocol revision 2026-07-28 | [source](https://github.com/modelcontextprotocol/python-sdk) |
| MCP 2026-07-28 Specification | `official specification release; observed 2026-09-11` | - | stateless core, MRTR, routing, auth hardening | [source](https://blog.modelcontextprotocol.io/posts/2026-07-28/) |
| Mem0 | `source observed 2026-09-09` | - | source observed 2026-09-09 | [source](https://github.com/mem0ai/mem0) |
| Mem2ActBench | `arXiv 2601.19935; observed 2026-09-10` | - | arXiv 2601.19935; observed 2026-09-10 | [source](https://arxiv.org/abs/2601.19935) |
| MemGym | `arXiv:2605.20833; observed 2026-09-11` | - | agent memory evaluation | [source](https://arxiv.org/abs/2605.20833) |
| Memora: From Recall to Forgetting | `arXiv 2604.20006; observed 2026-09-10` | - | arXiv 2604.20006; observed 2026-09-10 | [source](https://arxiv.org/abs/2604.20006) |
| Memory for AI Agents Survey | `arXiv:2603.07670; observed 2026-09-11` | - | agent memory taxonomy and research gaps | [source](https://arxiv.org/abs/2603.07670) |
| OpenAI MLE-bench | `2024 benchmark` | - | 2024 benchmark | [source](https://openai.com/index/mle-bench/) |
| MultiAgentBench | `arXiv 2503.01935; observed 2026-09-10` | - | arXiv 2503.01935; observed 2026-09-10 | [source](https://arxiv.org/abs/2503.01935) |
| NIST: Accelerating adoption of software and AI agent identity | `2026-02-05` | - | agent identity and delegated authority | [source](https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd) |
| NIST AI Agent Standards Initiative | `2026 initiative; observed 2026-09-11` | - | agent interoperability, standards, security | [source](https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative) |
| NIST AI 800-5: Security Considerations for AI Agents | `published 2026-05-18` | - | agent threats, mitigations, assessment | [source](https://csrc.nist.gov/pubs/ai/800/5/final) |
| NVIDIA/Skild AI S1 Physical AI | `2026; observed 2026-09-11` | - | physical AI foundation model/robotics industry signal | [source](https://blogs.nvidia.com/blog/skild-ai-s1-physical-ai/) |
| OGX: Open GenAI Stack | `arXiv 2608.14580; observed 2026-09-10` | - | arXiv 2608.14580; observed 2026-09-10 | [source](https://arxiv.org/abs/2608.14580) |
| OpenAI Agents SDK | `v0.22.0 @ 4df9ecf for reproducible source notes` | v0.22.2 @ 83c737f (released 2026-09-09, observed 2026-09-11) | v0.22.0 @ 4df9ecf | [source](https://github.com/openai/openai-agents-python) |
| OpenAI Agents SDK release evidence | `v0.22.2 @ 83c737f; 2026-09-09` | - | latest-observed runtime/sandbox/session hardening | [source](https://github.com/openai/openai-agents-python/releases/tag/v0.22.2) |
| OpenAI: How agents are transforming work | `2026-06-25` | - | long-horizon delegated tasks and work patterns | [source](https://openai.com/index/how-agents-are-transforming-work/) |
| OpenAI Agents documentation | `docs observed 2026-09-09` | - | docs observed 2026-09-09 | [source](https://openai.github.io/openai-agents-python/) |
| OpenAI BrowseComp | `official benchmark` | - | deep web browsing/research evaluation | [source](https://openai.com/index/browsecomp/) |
| OpenAI: Separating signal from noise in coding evaluations | `2026-07-08` | - | benchmark validity and broken tasks | [source](https://openai.com/index/separating-signal-from-noise-coding-evaluations/) |
| OpenAI computer-using agent | `official product/research page` | - | computer-use agent architecture and safety | [source](https://openai.com/index/computer-using-agent/) |
| OpenAI: Now everyone can put data to work | `2026-09-10` | - | Data agent, enterprise data analysis | [source](https://openai.com/index/put-data-to-work/) |
| OpenAI: ChatGPT for Financial Services | `2026-09-10` | - | financial research/modeling product signal | [source](https://openai.com/index/introducing-chatgpt-financial-services/) |
| OpenAI GDPval | `official evaluation; observed 2026-09-11` | - | economically valuable task evaluation | [source](https://openai.com/index/gdpval/) |
| OpenAI: The next evolution of the Agents SDK | `2026-04-15` | - | model-native harness, sandbox, long-horizon execution | [source](https://openai.com/index/the-next-evolution-of-the-agents-sdk/) |
| OpenAI: Research acceleration | `2026-09-06` | - | research agent workflows and scientific acceleration | [source](https://openai.com/index/research-acceleration-view-inside-openai/) |
| OpenAI: Scientific computing and agentic AI | `2026-07-28` | - | scientific computing agents | [source](https://openai.com/index/scientific-computing-agentic-ai/) |
| OpenAI: How AI is expanding what people do at work | `2026-07-27` | - | work-task boundary analysis | [source](https://openai.com/index/how-ai-is-expanding-what-people-do-at-work/) |
| OpenHands SDK architecture | `docs observed 2026-09-09` | - | docs observed 2026-09-09 | [source](https://docs.openhands.dev/sdk/arch/overview) |
| OpenHands Software Agent SDK | `v1.24.0 @ fdc2bdf` | v1.24.0 @ fdc2bdf observed in GitHub release search 2026-09-10 | v1.24.0 @ fdc2bdf | [source](https://github.com/OpenHands/software-agent-sdk) |
| OSWorld | `benchmark source observed 2026-09-09` | - | benchmark source observed 2026-09-09 | [source](https://github.com/xlang-ai/OSWorld) |
| OSWorld 2.0 | `arXiv:2606.29537; observed 2026-09-11` | - | computer-use agent evaluation | [source](https://arxiv.org/abs/2606.29537) |
| OpenTelemetry GenAI semantic conventions | `repository observed 2026-09-10` | - | repository observed 2026-09-10 | [source](https://github.com/open-telemetry/semantic-conventions/tree/main/docs/gen-ai) |
| OpenAI PaperBench | `2025 benchmark` | - | 2025 benchmark | [source](https://openai.com/index/paperbench/) |
| Pi Coding Agent | `treat 0.85.1 as NOT_RUN_EXTERNAL until npm install is executed` | GitHub releases show v0.83.0; package/version references around 0.85.1 require external package verification | @earendil-works/pi-coding-agent 0.85.1 | [source](https://github.com/earendil-works/pi) |
| ReAct: Synergizing Reasoning and Acting in Language Models | `arXiv:2210.03629` | - | foundational reasoning/action trajectories | [source](https://arxiv.org/abs/2210.03629) |
| SciAgentArena | `arXiv:2606.12736; observed 2026-09-11` | - | scientific research agents | [source](https://arxiv.org/abs/2606.12736) |
| Semantic Transactions for Tool-Using LLM Agents | `arXiv 2606.17573; observed 2026-09-10` | - | arXiv 2606.17573; observed 2026-09-10 | [source](https://arxiv.org/abs/2606.17573) |
| Hugging Face smolagents | `source observed 2026-09-09` | - | source observed 2026-09-09 | [source](https://github.com/huggingface/smolagents) |
| SWE-bench | `benchmark source observed 2026-09-09` | - | benchmark source observed 2026-09-09 | [source](https://github.com/swe-bench/SWE-bench) |
| Thomson Reuters 2026 AI in Professional Services Report | `2026 report; observed 2026-09-11` | - | professional services adoption and ROI | [source](https://www.thomsonreuters.com/en/institute/reports/2026-ai-in-professional-services-report) |
| Toolformer: Language Models Can Teach Themselves to Use Tools | `arXiv:2302.04761` | - | foundational tool-use learning | [source](https://arxiv.org/abs/2302.04761) |
| ToolVerse | `arXiv:2607.15660; observed 2026-09-11` | - | agentic RL, massive MCP tool environments | [source](https://arxiv.org/abs/2607.15660) |
| WebArena: A Realistic Web Environment for Building Autonomous Agents | `arXiv:2307.13854` | - | web-agent environment/evaluation | [source](https://arxiv.org/abs/2307.13854) |
| WEF: AI Agents in Action | `2026-05-26` | - | trusted adoption, authorization and scaling | [source](https://www.weforum.org/publications/ai-agents-in-action-a-playbook-for-trusted-adoption-authorization-and-scaling/) |
| WEF AI Playbook for Financial Services | `2026; observed 2026-09-11` | - | financial services AI strategy/governance | [source](https://www.weforum.org/publications/ai-playbook-for-financial-services/) |
| WEF: Agentic AI in manufacturing | `2026-06; observed 2026-09-11` | - | industrial agent adoption and governance | [source](https://www.weforum.org/stories/2026/06/agentic-ai-manufacturing/) |

## B.2 阅读方法

对框架源码不要从功能列表开始。优先沿 `public entry → run/session state → tool/workspace/protocol boundary → checkpoint/trace/verifier` 追踪责任归属；对论文则追踪 `problem → assumptions → environment/data → metric → failure cases → limitations`。只有当来源能改变章节中的不变量、故障模型、实验或工程判断时，才进入正文。

## B.3 版本新旧不是质量结论

本书刻意保留“课程复现 pin”和“最新观察版本”两列。例如 OpenAI Agents SDK 的课程源码笔记仍基于固定版本，而生态观察更新到 v0.22.2；Codex CLI 的历史复现 pin 不会因为 0.154.0 发布就自动改变。这样既能复现，也不会把旧 pin 误写成当前生态最新状态。
