# Full-Book Technical Audit — v1.0

## 结论

v1.0 已从“覆盖 Agent API 与框架”的课程收敛为 **Agent Systems 教材**：模型负责概率决策，runtime 拥有执行与状态转换，truth/recovery plane 负责证据、UNKNOWN 与恢复，governance plane 负责权限、审批、审计和评测。研究更新不作为新闻列表存在，而被绑定到章节中的系统不变量、失败模式与可验证假设。

2026-10-08 对 40 个 canonical 章节、80 个 Core Lab 入口、代码与发布证据重新核对后，结论是：**结构覆盖达到系统教程要求，但不能宣称所有前沿实验均已完成或已具备生产级外部证据。** 特别是本地 fixture、官方 SDK 的六个 scoped L5 向量、真实 benchmark、实际模型训练与跨架构发布是不同等级，不可相互替代。章节级结构计数由 [`CHAPTER_AUDIT_MATRIX.md`](CHAPTER_AUDIT_MATRIX.md) 自动重算；结构齐全不是内容正确性证明。

## 七篇审计发现与本轮修复

| 范围 | 关键问题与证据边界 | 本轮处理 / 剩余项 |
|---|---|---|
| 第一篇 01–06 | 第 01 章形式化把下一规范状态写成模型策略输出，与 Runtime 拥有状态/执行权矛盾。 | 改为模型提议、授权判定、可信 Runtime 状态转移及 `UNKNOWN` 回执；其余章节须继续按该共同语义核对。 |
| 第二篇 07–13 | MCP Core Lab 是协议子集实现，不等于官方 SDK；官方 Python↔Python loopback L5 的范围有限。 | 保持 Core 与 `evidence/l5/` 分层。跨语言、OAuth、多租户、真实远程网络仍未验证。 |
| 第三篇 14–20 | durable / HITL 的正确性依赖动作绑定、持久状态、重试与独立验证，不由 `while` loop 证明。 | 检查章节-实验-代码入口完整；真实 provider 崩溃恢复仍需外部运行。 |
| 第四篇 21–26 | 本地 browser 用真实 loopback HTTP，但不是浏览器渲染器或 WebArena；本地 HTTP 启动会在离线主机 reverse DNS 阻塞。 | 给两处教学 HTTP 服务换成不做 DNS 查询的固定回环服务，保留真正 socket/HTTP 检验；真实 browser/coding benchmark 尚未执行。 |
| 第五篇 27–28 | A2A 本地合同与官方 SDK scoped 互操作不可互换；委派授权不等于远端 effect 安全。 | 现有 evidence pack 的 claim ceiling 保持独立；跨语言、远端鉴权与分布式取消仍属空缺。 |
| 第六篇 29–35 | 故障证据过去按 scenario slug 授予 L3/L4，可能把 oracle 看见故障误写成系统约束。 | 改为逐场景传入实际检测、阻断、恢复观察；加入失败场景不能按名称升级等级的反例测试。 |
| 第七篇 36–40 | 部署平台声明曾由函数默认值凭空产生；实时取消被误读为物理撤销；canary 内存回退被称为原子发布；Capstone 自行审批且授权预检提前记成 effect。 | 从真实锁文件读取平台和镜像，状态降为静态契约；限定 realtime 为本地 completion fence、canary 为单进程状态；Capstone 改为外部传入教学审批夹具及无副作用 capability preflight，并检查 ledger 序号/转移。真实双架构镜像、硬件 E-stop、持久多实例 CAS、人审服务仍未运行。 |

本轮还强化了配对评测输入：重复 task ID、风险层重标和非法成本/安全指标 fail closed。Post-training Lab 的 `source_run`/`policy_id` 仅是声明字段，exact digest 与 task-family 字符串检查不能证明来源真实或语义无泄漏；正文已收紧结论。所有类似 `DATASET_ELIGIBLE`/`STATIC_CONTRACT_READY` 状态名都必须按其局部门禁解释，不能作为产品发布许可。

演示文稿另有平台兼容风险：本轮给 PPTX 的文本段落增加 `a:ea` 东亚字体与 `zh-CN` 语言元数据，OOXML 中可见完整中文，但本机 headless LibreOffice 转 PDF 仍错误替换为缺少中文字形的字体。`SLIDES_QA_OK` 只验证结构与文本存在；**视觉交付不能据此标为通过**。应在目标 PowerPoint/LibreOffice 环境打开抽检或在受控 Linux builder 中执行带中文字体的渲染快照，再决定是否发布该 PPTX。

## Repository inventory

- Canonical truth：`course.toml`、`book/zh/SUMMARY.md`、40 章、13 附录、80 DOT、代码/Labs、`SOURCE_LOCK.json`。
- Generated artifacts：assembled book、PDF/HTML/EPUB、site、Workbook、PPTX、release ZIP。
- Current-worktree local verification（2026-10-08）：80 Core Labs、69 examples、237 pytest、89.81% coverage、publication/structure/content/repository QA 与当前主书 pp. 323–324 渲染抽检。历史 SOURCE-CLEAN/hosted CI 结果不自动继承到此修订，必须在新 commit 上重跑。
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
