# Full-Book Technical Audit — v1.0

## 结论

v1.0 已从“覆盖 Agent API 与框架”的课程收敛为 **Agent Systems 教材**：模型负责概率决策，runtime 拥有执行与状态转换，truth/recovery plane 负责证据、UNKNOWN 与恢复，governance plane 负责权限、审批、审计和评测。研究更新不作为新闻列表存在，而被绑定到章节中的系统不变量、失败模式与可验证假设。

## Repository inventory

- Canonical truth：`course.toml`、`book/zh/SUMMARY.md`、40 章、6 附录、80 DOT、代码/Labs、`SOURCE_LOCK.json`。
- Generated artifacts：assembled book、PDF/HTML/EPUB、site、Workbook、PPTX、release ZIP。
- Local verification：80 Core Labs、69 examples、114 pytest、90% line coverage、publication/structure/content/repository QA，以及两次 SOURCE-CLEAN 冷缓存重建的 130 个原始哈希 + 4 个 PDF/EPUB 格式感知指纹等价。
- External boundary：6 个 scoped 官方 SDK/框架向量已实跑；Docker canonical runner、商业模型 API、真实浏览器 benchmark、GPU/机器人/云资源及其余广义合同继续按证据状态独立记录。

## v1.0 的主要质量修复

| 发现 | 风险 | v1.0 处理 |
|---|---|---|
| 核心概念共享固定 What/How 话术 | 概念辨识度低 | 160 个概念改为主题专属定义/责任/失败边界 |
| 前沿研究集中在章节末尾 | 研究与系统设计脱节 | 研究结论绑定 formal model、failure boundary、metrics 与 engineering hypothesis |
| 长期 Agent 常被简化为 LLM+Tools | 无法解释 crash、UNKNOWN、side effects、identity | 引入 decision/execution/truth-recovery/governance 四平面视角 |
| “最新版本”与“可复现 pin”混淆 | 教材很快过时或实验漂移 | SOURCE_LOCK 明确区分 course pin / latest observed / evidence |
| 行业讨论易沦为宣传 | 不能指导工程决策 | Appendix F 区分 observed adoption、system boundary、risk 与 scenario forecast |
| 跨章重复模板降低信息密度 | 页数增加但知识密度不增 | 长段落重复扫描 + 中央化通用环境说明 |

## 内容覆盖

理论主线覆盖 Context/Planning/State/Tool/RAG/Memory/Protocols/Runtime/Durability/Evaluation/Security/Recovery/Post-training/Self-improvement；工程主线覆盖 Coding/Browser/Data/Research/Multi-Agent、observability、production API 与 deployment；前沿主线覆盖 agentic RL、long-horizon execution、memory formation/forgetting、identity/delegation、trajectory evaluation、semantic transactions、multi-agent risk 与 research automation。

## 真实性等级

- `VERIFIED`：本仓库 labs/examples/tests/publication QA 实跑。
- `DOC_VERIFIED`：官方文档、论文、规范或机构报告核验。
- `STATIC_VERIFIED`：源码/配置/版本锁静态检查。
- `L5_EXTERNAL`：真实 pinned 官方实现跨进程或跨重启执行，保存行为、故障、verifier、环境与 artifact hash，并限制 claim scope。
- `NOT_RUN_EXTERNAL`：需要 API Key、Docker、浏览器、GPU、云或外部 runtime 的实验。

## 剩余长期工作

后续版本最有价值的增强不是增加页数，而是扩大真实外部复现实验：固定小规模 benchmark 子集、真实 provider trace、browser/computer-use replay、container/K8s failure injection、agentic RL environment reproduction，以及更多逐函数源码剖析。
