# Content Changelog

## v1.0.0 — 2026-09-11

- 建立 40 章、6 附录、80 Core Labs 的首个公开语义化版本；Build System 独立保持 `1.1.1`。
- 将核心概念从统一模板改写为主题专属定义、系统责任、失败边界、形式模型、指标和可证伪工程假设。
- 研究截止日统一为 2026-09-11；`integrations/SOURCE_LOCK.json` 区分 reproducibility pin、latest observed 与 evidence source。
- 修复 HITL、Unknown Outcome、Tool Outcome、Checkpoint、Journal 和 Production case 的正确性边界。
- MCP 2026-07-28 / A2A 1.0 教学合同与 6 项官方实现证据分层记录。
- 80 Core Labs 引入 evidence level；pytest 为 114，line coverage 为 90%；source locks 为 100；10 个 broad upstream contracts 未执行。
- 跨章通用方法论中央化，主书收敛为 462 页并增加 L5 外部证据。

## 不改变的契约

- 不把 PDF/HTML/EPUB/PPTX 当作 canonical source；
- 不把 deterministic fixture PASS 写成上游框架或生产系统 PASS；
- 不为了追逐最新版本破坏课程复现 pin；
- 不把未执行 benchmark 写成零分或成功。
