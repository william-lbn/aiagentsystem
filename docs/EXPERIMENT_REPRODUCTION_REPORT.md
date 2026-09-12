# Experiment Reproduction Report — v1.0

## 实验分类

| 类型 | 状态定义 | 本轮处理 |
|---|---|---|
| Core Labs | 本仓库 deterministic normal/fault lab | 执行 `make labs` 验证 80/80 |
| Chapter Examples | 每章 Python 入口 | 执行 `make examples` 验证 69 个 Python examples |
| Unit/Integration Tests | pytest 下的核心 runtime 与 production API 测试 | 执行 `make test` |
| Book/Site/Workbook/Slides QA | 出版产物和链接/图像/编号验证 | 执行 `make validate` |
| Scoped L5 official runs | MCP/A2A SDK 与 OpenAI Agents/LangGraph/ADK/MAF durable surfaces | 6/6 已实跑；范围、故障、verifier、版本和哈希独立记录 |
| Broad upstream contracts | OpenAI/ADK/LangGraph/MAF/DeepSeek/Pi/Codex/OpenHands/MCP/A2A 十类完整合同 | `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`；不能由 6 个 scoped 向量替代 |
| Coding/browser benchmarks | SWE-bench Lite / WebArena | 真实任务与 harness 已固定，但本发行版未执行、无分数 |

## 核心实验语义审计

80 个核心 Lab 均包含 normal path 与 fault path。normal path 验证机制 happy path；fault path 的 `passed=true` 只表示该场景的预期 oracle 成立。证据还必须分别读取 system detection、containment 与 recovery；14 个 `L2_ORACLE_ONLY` 明确只证明 oracle 看见故障，不证明系统已约束它。

## 防止假实验的规则

- deterministic fixture 必须声明它模拟什么，不能证明什么；
- 上游框架没有真实安装运行时，状态只能是 `NOT_RUN_EXTERNAL`；已运行的 6 个向量也只能声明各自记录的 scope；
- unit test PASS 不能写成生产验证；
- Docker 当前若不可用，不能把 compose 静态检查写成容器 E2E；
- benchmark 未下载真实数据/环境时，只能作为阅读/复现手册。

## 本轮执行记录

最终执行结果写入根目录 `VALIDATION_REPORT.md` 与 `docs/FINAL_VALIDATION_REPORT.md`。发行包中的 `QA-EVIDENCE` 包含 validation logs、PDF/PPT 抽样与 checksum。
