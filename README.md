# AI Agent Systems：从模型、Runtime、协议到生产可靠性

[![CI](https://github.com/william-lbn/aiagentsystem/actions/workflows/ci.yml/badge.svg)](https://github.com/william-lbn/aiagentsystem/actions/workflows/ci.yml)
[![CodeQL](https://github.com/william-lbn/aiagentsystem/actions/workflows/codeql.yml/badge.svg)](https://github.com/william-lbn/aiagentsystem/actions/workflows/codeql.yml)
[![Release](https://img.shields.io/github/v/release/william-lbn/aiagentsystem)](https://github.com/william-lbn/aiagentsystem/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **[下载主书 PDF / EPUB / HTML（v1.0.0 离线包）](https://github.com/william-lbn/aiagentsystem/releases/download/v1.0.0/AI-Agent-Systems-Course-v1.0.0-BOOK.zip)** · **[从目录在线阅读中文正文](book/zh/SUMMARY.md)** · **[浏览 80 个实验](#四十章正文与实验导航)** · **[查看完整 Release](https://github.com/william-lbn/aiagentsystem/releases/tag/v1.0.0)**

这是一套面向工程师、研究者与高校课程的**简体中文开源 AI Agent 系统教材与实验工程**。它不把 Agent 简化为“LLM 加一个循环”，而是围绕下面这条系统主线展开：

> **Agent System = Model + Context + Tools + State + Runtime + Evidence + Governance**

全书把模型接口、Context Engineering、Tool/RAG/Memory、MCP/A2A、Runtime/Harness、Durable Execution、Coding/Browser/Data/Research Agent、Multi-Agent、Evaluation、Security、Recovery、Production、Post-training 与 Self-improvement 连接成一套可以阅读、运行、故障注入和审计的知识体系。

当前公开基线为**内容版本 v1.0.0 / Build System 1.1.2**，知识、协议与研究观察截止到 **2026-09-11（Asia/Shanghai）**。本项目目前只维护简体中文，不提供未经持续校验的翻译版本。

## 先读、先跑还是先下载

| 目标 | 推荐入口 | 你会得到什么 |
|---|---|---|
| 离线阅读主书 | [下载 BOOK.zip](https://github.com/william-lbn/aiagentsystem/releases/download/v1.0.0/AI-Agent-Systems-Course-v1.0.0-BOOK.zip) | 主书 PDF/EPUB/HTML、实验手册 PDF/EPUB/HTML、离线网站；解压后主书 PDF 位于 `book/build/ai-agent-systems-course-v1.0.0.pdf` |
| 在 GitHub 阅读 | [中文目录与 40 章正文](book/zh/SUMMARY.md) | 无需安装环境，按七篇结构逐章阅读 Markdown 正文 |
| 运行实验 | [下载 CODE-LABS.zip](https://github.com/william-lbn/aiagentsystem/releases/download/v1.0.0/AI-Agent-Systems-Course-v1.0.0-CODE-LABS.zip) | Runtime 源码、40 个章节示例、80 个 Core Labs、测试、集成轨道与生产案例 |
| 使用实验手册 | [下载 BOOK.zip](https://github.com/william-lbn/aiagentsystem/releases/download/v1.0.0/AI-Agent-Systems-Course-v1.0.0-BOOK.zip) | 解压后实验手册 PDF 位于 `workbook/build/agent-systems-lab-workbook-v1.0.0.pdf` |
| 授课或分享 | [下载 SLIDES.zip](https://github.com/william-lbn/aiagentsystem/releases/download/v1.0.0/AI-Agent-Systems-Course-v1.0.0-SLIDES.zip) | 90 页 PPTX 以及幻灯片源文件 |
| 获取全部交付物 | [下载 ALL-DELIVERABLES.zip](https://github.com/william-lbn/aiagentsystem/releases/download/v1.0.0/AI-Agent-Systems-Course-v1.0.0-ALL-DELIVERABLES.zip) | 书籍、源码、Labs、Slides、QA evidence、构建元数据与内部组件校验清单 |
| 审计发布 | [SHA256SUMS.txt](https://github.com/william-lbn/aiagentsystem/releases/download/v1.0.0/SHA256SUMS.txt) · [SBOM](https://github.com/william-lbn/aiagentsystem/releases/download/v1.0.0/AI-Agent-Systems-Course-v1.0.0-PYTHON-SBOM.cdx.json) | 全部非清单资产的 SHA-256、CycloneDX SBOM 与 GitHub/Sigstore provenance |

GitHub Release 当前采用**可审计压缩包**分发 PDF，而不是把生成物提交到 `main`。这样可以让 PDF、EPUB、网站、校验和、SBOM 与构建 provenance 保持在同一个版本边界内。所有固定版本链接都指向 v1.0.0，不会在后台静默变成其他内容。

## 这套项目解决什么问题

很多 Agent 教程能演示一次工具调用，却没有回答系统进入真实环境之后最困难的问题：

- 模型提出的 tool call 与真实副作用之间，谁拥有最终执行权？
- 上下文、记忆和检索如何带着来源、版本、预算与删除语义进入模型？
- timeout 发生时，动作究竟是 `COMMITTED`、`NOT_APPLIED` 还是 `UNKNOWN`？
- Agent 崩溃、重启、重复审批或并发写入后，如何恢复而不重复产生不可逆副作用？
- MCP、A2A、OpenAI Agents、LangGraph、Google ADK、Microsoft Agent Framework 的协议或 Runtime 边界如何验证？
- Coding/Browser Agent 的能力应该如何用轨迹、独立 verifier 和真实 benchmark 衡量？
- 从实验 fixture 到官方 SDK、真实 provider、真实环境和生产声明，中间分别缺少什么证据？

因此，每章都尽量保持同一条工程闭环：

```text
系统问题 → 概念与不变量 → 形式化模型 → 关键实现 → 正常路径
        → 故障注入 → 独立验证 → 证据等级 → 上游实现与研究边界
```

本仓库是教材、实验与参考实现 monorepo，**不是**面向 PyPI 发布的通用 Agent SDK，也不把安装成功、模型自述或预设 fixture 分数冒充生产证据。

## 项目规模与已经验证的范围

| 内容 | v1.0.0 canonical release |
|---|---:|
| 中文正文 | 40 章 + 11 附录，分为 7 篇 |
| Core Labs | 80 个：40 条正常路径 + 40 条故障注入路径 |
| Python 示例 | 69 个：40 个章节入口 + 29 个支撑示例 |
| 自动化测试 | 191 项；覆盖率由 `make coverage` 的质量门实时验证 |
| 主书 | PDF 以当前源码构建结果为准 + EPUB + HTML |
| 实验手册 | PDF 以当前源码构建结果为准 + EPUB + HTML |
| 网站构建物 | 132 个 HTML 页面（当前源码构建合同） |
| 教学幻灯片 | 90 页 PPTX |
| 外部来源锁 | 108 项；唯一 URL 数由 source-lock QA 实时核验 |
| Scoped L5 外部证据 | 6 项：MCP、A2A、OpenAI Agents、LangGraph、Google ADK、MAF |

详细状态及每一种 `PASS` 能证明到哪里，见 [EXPERIMENT_STATUS.md](EXPERIMENT_STATUS.md) 与 [v1.0.0 验证报告](VALIDATION_REPORT.md)。

## 推荐学习路径

- **第一次系统学习 Agent**：按第 1–20 章顺序阅读，并逐章运行 A/B 实验；先建立 Model—Runtime—Effect—Evidence 的边界。
- **Agent 平台与应用工程师**：重点阅读第 7–19、26–36、40 章，结合 `src/agentlab/` 与生产 API 案例。
- **协议与框架工程师**：重点阅读第 13、21–28 章，再进入 `integrations/` 的官方实现证据轨道。
- **评测、安全与可靠性研究者**：重点阅读第 18、23、29–34、39 章以及附录 C、E。
- **课程教师**：使用主书 + 80-Lab Workbook + 90 页 Slides；A/B 配对适合课堂演示“正确路径—失效机制—验收证据”。

## 四十章正文与实验导航

每章都对应两个可运行实验：`A` 是正常路径，`B` 是故障注入。正文、实验说明、命令、预期输出、验收条件和证据上限都可以从下表直接打开。

### 第一篇 · 基础：从模型接口到可调试 Agent

| 章 | 核心问题 | 正文 | 实验 |
|---:|---|---|---|
| 01 | 决策、授权、执行、观察与验证如何构成受治理行动系统 | [阅读](book/zh/chapters/01-foundation.md) | [01A 正常](labs/core/lab-01A-foundation.md) · [01B 故障](labs/core/lab-01B-foundation-fault.md) |
| 02 | 概率生成如何经过 syntax/schema/semantic/authorization 成为意图 | [阅读](book/zh/chapters/02-model-substrate.md) | [02A 正常](labs/core/lab-02A-model-substrate.md) · [02B 故障](labs/core/lab-02B-model-substrate-fault.md) |
| 03 | Context 如何作为带 provenance、tenant、trust 与预算的运行时视图 | [阅读](book/zh/chapters/03-context.md) | [03A 正常](labs/core/lab-03A-context.md) · [03B 故障](labs/core/lab-03B-context-fault.md) |
| 04 | 类型化 item、call identity 与 append-only trajectory 如何保持因果关系 | [阅读](book/zh/chapters/04-messages.md) | [04A 正常](labs/core/lab-04A-messages.md) · [04B 故障](labs/core/lab-04B-messages-fault.md) |
| 05 | 候选计划怎样经过 DAG、能力与预算检查才进入执行 | [阅读](book/zh/chapters/05-planning.md) | [05A 正常](labs/core/lab-05A-planning.md) · [05B 故障](labs/core/lab-05B-planning-fault.md) |
| 06 | Reducer、事件重放、Checkpoint CAS 与副作用边界如何支持恢复 | [阅读](book/zh/chapters/06-state.md) | [06A 正常](labs/core/lab-06A-state.md) · [06B 故障](labs/core/lab-06B-state-fault.md) |

### 第二篇 · 知识、工具、记忆与协议

| 章 | 核心问题 | 正文 | 实验 |
|---:|---|---|---|
| 07 | Tool schema、前置条件、后置条件与风险标签如何设计 | [阅读](book/zh/chapters/07-tool-design.md) | [07A 正常](labs/core/lab-07A-tool-design.md) · [07B 故障](labs/core/lab-07B-tool-design-fault.md) |
| 08 | Tool Runtime 如何处理权限、超时、重试、幂等与副作用 | [阅读](book/zh/chapters/08-tool-runtime.md) | [08A 正常](labs/core/lab-08A-tool-runtime.md) · [08B 故障](labs/core/lab-08B-tool-runtime-fault.md) |
| 09 | RAG 如何建立检索、证据、引用和生成之间的边界 | [阅读](book/zh/chapters/09-retrieval.md) | [09A 正常](labs/core/lab-09A-retrieval.md) · [09B 故障](labs/core/lab-09B-retrieval-fault.md) |
| 10 | Hybrid / Agentic RAG 如何把检索变成可评估的决策过程 | [阅读](book/zh/chapters/10-hybrid-rag.md) | [10A 正常](labs/core/lab-10A-hybrid-rag.md) · [10B 故障](labs/core/lab-10B-hybrid-rag-fault.md) |
| 11 | 长期记忆如何写入、检索、合并、过期和删除 | [阅读](book/zh/chapters/11-memory.md) | [11A 正常](labs/core/lab-11A-memory.md) · [11B 故障](labs/core/lab-11B-memory-fault.md) |
| 12 | Skills 与 Procedural Memory 如何版本化和安全复用 | [阅读](book/zh/chapters/12-skills.md) | [12A 正常](labs/core/lab-12A-skills.md) · [12B 故障](labs/core/lab-12B-skills-fault.md) |
| 13 | MCP 的 Host/Client/Server、transport 与 capability 边界 | [阅读](book/zh/chapters/13-mcp.md) | [13A 正常](labs/core/lab-13A-mcp.md) · [13B 故障](labs/core/lab-13B-mcp-fault.md) |

### 第三篇 · Runtime、Durable Execution 与 Harness

| 章 | 核心问题 | 正文 | 实验 |
|---:|---|---|---|
| 14 | Agent Loop 如何从 while 循环升级为有界状态机 | [阅读](book/zh/chapters/14-agent-loop.md) | [14A 正常](labs/core/lab-14A-agent-loop.md) · [14B 故障](labs/core/lab-14B-agent-loop-fault.md) |
| 15 | 流式、并发、中断、取消与 backpressure 如何正确传播 | [阅读](book/zh/chapters/15-async.md) | [15A 正常](labs/core/lab-15A-async.md) · [15B 故障](labs/core/lab-15B-async-fault.md) |
| 16 | Human-in-the-Loop 如何绑定不可变动作并安全恢复 | [阅读](book/zh/chapters/16-hitl.md) | [16A 正常](labs/core/lab-16A-hitl.md) · [16B 故障](labs/core/lab-16B-hitl-fault.md) |
| 17 | Sandbox、权限与资源配额如何限制 Agent 爆炸半径 | [阅读](book/zh/chapters/17-sandbox.md) | [17A 正常](labs/core/lab-17A-sandbox.md) · [17B 故障](labs/core/lab-17B-sandbox-fault.md) |
| 18 | Checkpoint、Journal、CAS 和 hash-chain 如何支持崩溃恢复 | [阅读](book/zh/chapters/18-checkpoint-journal.md) | [18A 正常](labs/core/lab-18A-checkpoint-journal.md) · [18B 故障](labs/core/lab-18B-checkpoint-journal-fault.md) |
| 19 | Harness 如何组合 workspace、tool、policy、approval 与 verifier | [阅读](book/zh/chapters/19-harness.md) | [19A 正常](labs/core/lab-19A-harness.md) · [19B 故障](labs/core/lab-19B-harness-fault.md) |
| 20 | Coding Agent 如何形成“读—改—测—验证”的最小闭环 | [阅读](book/zh/chapters/20-coding-minimal.md) | [20A 正常](labs/core/lab-20A-coding-minimal.md) · [20B 故障](labs/core/lab-20B-coding-minimal-fault.md) |

### 第四篇 · 专用 Agent 与真实环境

| 章 | 核心问题 | 正文 | 实验 |
|---:|---|---|---|
| 21 | Codex、Pi、Claude Code 类 Coding Harness 的责任边界 | [阅读](book/zh/chapters/21-coding-harness.md) | [21A 正常](labs/core/lab-21A-coding-harness.md) · [21B 故障](labs/core/lab-21B-coding-harness-fault.md) |
| 22 | OpenHands 与远程 Agent Server 如何隔离运行环境和会话 | [阅读](book/zh/chapters/22-openhands.md) | [22A 正常](labs/core/lab-22A-openhands.md) · [22B 故障](labs/core/lab-22B-openhands-fault.md) |
| 23 | Browser / Computer Use Agent 如何观察、行动和验证页面状态 | [阅读](book/zh/chapters/23-browser.md) | [23A 正常](labs/core/lab-23A-browser.md) · [23B 故障](labs/core/lab-23B-browser-fault.md) |
| 24 | Data Agent 如何约束 SQL/Python 并留下可审计分析证据 | [阅读](book/zh/chapters/24-data-agent.md) | [24A 正常](labs/core/lab-24A-data-agent.md) · [24B 故障](labs/core/lab-24B-data-agent-fault.md) |
| 25 | Research Agent 如何维护来源、引用、冲突和报告证据链 | [阅读](book/zh/chapters/25-research-agent.md) | [25A 正常](labs/core/lab-25A-research-agent.md) · [25B 故障](labs/core/lab-25B-research-agent-fault.md) |
| 26 | LangGraph / ADK / MAF 的 Graph Runtime 共同抽象 | [阅读](book/zh/chapters/26-workflow-graph.md) | [26A 正常](labs/core/lab-26A-workflow-graph.md) · [26B 故障](labs/core/lab-26B-workflow-graph-fault.md) |

### 第五篇 · Workflow、Multi-Agent 与互操作

| 章 | 核心问题 | 正文 | 实验 |
|---:|---|---|---|
| 27 | A2A 的 AgentCard、Task、状态与跨 Agent 互操作 | [阅读](book/zh/chapters/27-a2a.md) | [27A 正常](labs/core/lab-27A-a2a.md) · [27B 故障](labs/core/lab-27B-a2a-fault.md) |
| 28 | Multi-Agent 的分工、隔离、调度、聚合与成本控制 | [阅读](book/zh/chapters/28-multi-agent.md) | [28A 正常](labs/core/lab-28A-multi-agent.md) · [28B 故障](labs/core/lab-28B-multi-agent-fault.md) |

### 第六篇 · Evaluation、Benchmark、Observability、安全与可靠性

| 章 | 核心问题 | 正文 | 实验 |
|---:|---|---|---|
| 29 | Agent Evaluation 如何同时评价结果、轨迹、成本与安全 | [阅读](book/zh/chapters/29-evaluation.md) | [29A 正常](labs/core/lab-29A-evaluation.md) · [29B 故障](labs/core/lab-29B-evaluation-fault.md) |
| 30 | SWE-bench、OSWorld、PaperBench、MLE-bench 能证明什么 | [阅读](book/zh/chapters/30-benchmarks.md) | [30A 正常](labs/core/lab-30A-benchmarks.md) · [30B 故障](labs/core/lab-30B-benchmarks-fault.md) |
| 31 | Trace、Metrics、Evidence 与 AgentOps 如何形成可观测闭环 | [阅读](book/zh/chapters/31-observability.md) | [31A 正常](labs/core/lab-31A-observability.md) · [31B 故障](labs/core/lab-31B-observability-fault.md) |
| 32 | Prompt Injection、委托权限和最小权限如何系统化防护 | [阅读](book/zh/chapters/32-security.md) | [32A 正常](labs/core/lab-32A-security.md) · [32B 故障](labs/core/lab-32B-security-fault.md) |
| 33 | 外部副作用在 UNKNOWN 结果下如何协调、补偿和恢复 | [阅读](book/zh/chapters/33-effect-recovery.md) | [33A 正常](labs/core/lab-33A-effect-recovery.md) · [33B 故障](labs/core/lab-33B-effect-recovery-fault.md) |
| 34 | Token、延迟、并发、缓存与成本如何联合优化 | [阅读](book/zh/chapters/34-performance.md) | [34A 正常](labs/core/lab-34A-performance.md) · [34B 故障](labs/core/lab-34B-performance-fault.md) |
| 35 | 生产 Agent API 如何处理租户、幂等、审批和审计 | [阅读](book/zh/chapters/35-production-api.md) | [35A 正常](labs/core/lab-35A-production-api.md) · [35B 故障](labs/core/lab-35B-production-api-fault.md) |

### 第七篇 · 生产工程、训练与持续演进

| 章 | 核心问题 | 正文 | 实验 |
|---:|---|---|---|
| 36 | Docker、本地开发、CI 与发布证据如何形成部署基线 | [阅读](book/zh/chapters/36-deployment.md) | [36A 正常](labs/core/lab-36A-deployment.md) · [36B 故障](labs/core/lab-36B-deployment-fault.md) |
| 37 | SFT/RL/Post-training 如何塑造 Agent 的工具与决策能力 | [阅读](book/zh/chapters/37-post-training.md) | [37A 正常](labs/core/lab-37A-post-training.md) · [37B 故障](labs/core/lab-37B-post-training-fault.md) |
| 38 | 多模态、语音、机器人与实时 Agent 如何扩展观察/动作空间 | [阅读](book/zh/chapters/38-multimodal.md) | [38A 正常](labs/core/lab-38A-multimodal.md) · [38B 故障](labs/core/lab-38B-multimodal-fault.md) |
| 39 | Self-Improving Agent 如何优化、评估、门禁和回滚 | [阅读](book/zh/chapters/39-self-improve.md) | [39A 正常](labs/core/lab-39A-self-improve.md) · [39B 故障](labs/core/lab-39B-self-improve-fault.md) |
| 40 | 把 Runtime、协议、审批、恢复、评测与部署合成 AgentOps 闭环 | [阅读](book/zh/chapters/40-capstone.md) | [40A 正常](labs/core/lab-40A-capstone.md) · [40B 故障](labs/core/lab-40B-capstone-fault.md) |

### 十一个附录

| 附录 | 内容 | 入口 |
|---|---|---|
| A | 统一实验环境、调试与复现 | [阅读](book/zh/appendix-a-environment.md) |
| B | 上游开源项目版本锁与源码阅读索引 | [阅读](book/zh/appendix-b-upstream-lock.md) |
| C | Agent Systems 故障模型与排错速查 | [阅读](book/zh/appendix-c-failure-debug.md) |
| D | 术语、不变量与状态词典 | [阅读](book/zh/appendix-d-glossary.md) |
| E | 2026 AI Agent 研究版图、理论前沿与开放问题 | [阅读](book/zh/appendix-e-research-frontier.md) |
| F | 行业状态、产业影响与 2026–2030 发展判断 | [阅读](book/zh/appendix-f-industry-future.md) |
| G | 第一篇六章思考题与实践题参考答案 | [阅读](book/zh/appendix-g-part1-solutions.md) |
| H | 第二篇七章思考题与实践题参考答案 | [阅读](book/zh/appendix-h-part2-solutions.md) |
| I | 第三篇七章思考题与实践题参考答案 | [阅读](book/zh/appendix-i-part3-solutions.md) |
| J | 第四篇六章进阶问题参考答案 | [阅读](book/zh/appendix-j-part4-solutions.md) |
| K | 第五篇两章进阶问题参考答案 | [阅读](book/zh/appendix-k-part5-solutions.md) |

## 运行第一个实验

核心实验支持 macOS、Linux、WSL2，支持 `x86_64` 与 `arm64`，需要 Python 3.11–3.13。80 个 Core Labs 使用确定性 fixture，不要求 API Key、Docker、浏览器或外网。

```bash
git clone https://github.com/william-lbn/aiagentsystem.git
cd aiagentsystem

# 安装锁定依赖并检查环境
make bootstrap
make bootstrap-check

# 第 1 章：正常路径
PYTHONPATH=src uv run python examples/chapters/ch01_foundation.py

# 第 1 章：故障注入路径
PYTHONPATH=src uv run python examples/chapters/ch01_foundation.py --fault
```

进一步验证：

```bash
make labs       # 运行 80 个 Core Labs
make test       # 运行 191 项 pytest
make examples   # 运行 69 个 Python 示例
make validate   # 完整本地质量门与出版验证
```

每个 Lab 文档都包含环境、入口、调试断点、命令、实际输出、PASS 条件和结果解释。想先看完整机制，可从 [Lab 01A](labs/core/lab-01A-foundation.md)、[Lab 18B：Journal 故障](labs/core/lab-18B-checkpoint-journal-fault.md)、[Lab 33B：副作用恢复故障](labs/core/lab-33B-effect-recovery-fault.md) 或 [Lab 40A：端到端 AgentOps](labs/core/lab-40A-capstone.md) 开始。

## 从教学 fixture 到真实外部证据

项目用分级证据防止实验结论越界：

| 等级 | 含义 |
|---|---|
| L1 | 本地确定性机制断言成立 |
| L2 | 独立 oracle 或系统检测到故障 |
| L3 | 系统识别并 fail-closed / containment |
| L4 | 完成可验证的恢复或协调 |
| L5 | 真实 pinned 上游实现完成行为、故障、独立 verifier 与证据包 |

v1.0.0 已保存 6 项范围明确的官方实现证据：

- [MCP](integrations/mcp/README.md) 与 [A2A](integrations/a2a/README.md) SDK / wire-contract 轨道；
- [OpenAI Agents SDK](integrations/openai_agents/README.md)、[LangGraph](integrations/langgraph/README.md)、[Google ADK](integrations/google_adk/README.md) 与 [Microsoft Agent Framework](integrations/microsoft_agent_framework/README.md) Runtime 轨道；
- SWE-bench Lite 与 WebArena 目前只有固定执行合同，**未在 v1.0.0 发布分数**；
- `DEFINED`、`NOT_EXECUTED` 与 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE` 均不是通过状态。

审计总表见 [L5 External Evidence Audit](docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md)。运行真实 provider 的实验时，可以通过环境变量提供 `OPENAI_API_KEY`；仓库不会要求、打印或提交真实 Key。请从 `.env.example` 开始，并始终在提交前运行索引安全门禁。

## 代码与工程地图

```text
book/zh/                      40 章中文正文、11 个附录、唯一目录源
book/assets/diagrams/         80 个 DOT 权威图源及可审查 SVG
src/agentlab/                 Runtime、Tool、State、Checkpoint、Journal、Eval 等核心实现
examples/chapters/            40 个与章节逐一对应的可执行入口
examples/                     29 个支撑性工程示例
labs/core/                    80 个 A/B Core Labs 文档与验收证据
integrations/                 官方 SDK、上游框架、协议和 benchmark 复现轨道
production/agentops_service/  FastAPI + SQLite 的生产风格 AgentOps 案例
tests/                        单元、故障语义与端到端测试
scripts/                      构建、QA、发布、校验和与可复现性门禁
```

推荐从这些实现入口开始读代码：

- [Runtime 主循环](src/agentlab/runtime.py)、[工具注册与执行](src/agentlab/tools.py)、[模型与决策结构](src/agentlab/models.py)
- [第三篇 Runtime 机制](src/agentlab/runtime_system.py)：有界循环、结构化并发、路径能力门禁、插件回滚与 Coding Workspace
- [第四篇专项 Agent 机制](src/agentlab/specialized_system.py)：Session/事件持久化、真实 loopback HTTP、只读 SQL、证据绑定与 durable graph
- [第五篇协调机制](src/agentlab/coordination_system.py)：任务绑定委派、A2A durable task、所有权/权限、预算事务与幂等 join
- [Checkpoint](src/agentlab/checkpoint.py)、[Journal](src/agentlab/journal.py)、[事件模型](src/agentlab/events.py)
- [Workflow](src/agentlab/workflow.py)、[Tracing](src/agentlab/tracing.py)、[Evaluation](src/agentlab/eval.py)
- [Memory](src/agentlab/memory.py)、[Retrieval](src/agentlab/retrieval.py)、[Security](src/agentlab/security.py)
- [生产风格 AgentOps Service](production/agentops_service/README.md)

## 构建书籍、网站、实验手册与幻灯片

仓库采用 **Single Source, Multiple Artifacts**。`course.toml` 保存版本和工具链元数据，`book/zh/SUMMARY.md` 是章节顺序的唯一来源，正文、Lab 与代码都是 canonical source。

先检查 Pandoc、XeLaTeX、Graphviz、Poppler、CJK 字体和 Rust/Cargo：

```bash
make toolchain
make build
```

默认 `make build` 使用已验证的 Pandoc compatibility 路径。有 Quarto 1.11.1 时可运行 canonical 路径：

```bash
make build-canonical
make validate-canonical
```

正式发布由 digest-pinned container 和 tag-triggered GitHub Actions 构建，生成校验和、CycloneDX SBOM 与 GitHub artifact attestation。详细出版架构见 [Build System 1.1.2](docs/BUILD_SYSTEM.md)，发布操作见 [RELEASING.md](RELEASING.md)。

## 验证发布资产

Release 中的 `SHA256SUMS.txt` 使用 basename 覆盖除自身外的每一个下载资产。下载完整 Release 后可以执行：

```bash
gh release download v1.0.0 --repo william-lbn/aiagentsystem
shasum -a 256 -c SHA256SUMS.txt

# 对任一下载资产验证 GitHub/Sigstore provenance
gh attestation verify BUILD-METADATA.json --repo william-lbn/aiagentsystem
```

v1.0.0 的发布保证是：锁定 container 中的 canonical 构建、同一 host 上两次隔离冷环境的 format-aware clean rebuild、结构与语义 QA、SHA-256、SBOM 与 provenance。它**不宣称**不同宿主系统上的第三方 PDF/EPUB 出版器输出逐字节一致；APT/CTAN 供应链也明确记录为 `non-hermetic-recorded`。

## 开源协作

- 许可证与第三方边界：[LICENSE](LICENSE) · [LICENSING.md](LICENSING.md) · [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
- 贡献、行为准则与治理：[CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · [GOVERNANCE.md](GOVERNANCE.md)
- 安全报告：[SECURITY.md](SECURITY.md)；请勿把漏洞或真实凭据提交到公开 Issue
- 使用支持：[SUPPORT.md](SUPPORT.md)
- 学术引用：[CITATION.cff](CITATION.cff)
- 版本变更：[CHANGELOG.md](CHANGELOG.md) · [RELEASE_NOTES.md](RELEASE_NOTES.md)

欢迎提交勘误、失败复现、上游 SDK 兼容性证据和能够提高 claim level 的真实实验。对“已运行”“已恢复”“可复现”或“达到 L5”的修改，请同时提交可独立检查的 verifier 与证据边界，而不只提交成功截图或模型输出。
