# v1.0 Correctness & Evidence Hardening Report

本报告记录公开 `v1.0.0` 基线的 correctness / protocol / experiment-evidence / release hardening。目标不是增加页数，而是让**正文声明、可执行代码、测试 oracle、实验输出与 Release gate**具有一致的证据边界。

## 1. 高优先级问题闭环

| 原问题 | v1.0 修改 | 验收证据 | 状态 |
|---|---|---|---|
| HITL 批准后未真正执行 pending tool | approval 绑定 immutable `action_id`；批准后恢复原 pending effect | approval / reject / expiry / stale-action / resume 测试 | FIXED |
| 外部 effect 已发生、结果未持久化时可能盲目重放 | 引入 `EXECUTING_EFFECT` 与 `NEEDS_RECONCILIATION`；unknown outcome 禁止自动重放 | crash-window recovery test | FIXED |
| Lab 01B 可在 unknown tool 后错误 FINISHED | `NOT_APPLIED` 终止运行，不再进入成功终态 | runtime + core-lab regression | FIXED |
| 非幂等 timeout 被误判安全重试 | timeout → `UNKNOWN`, `retryable=false` | timeout correctness tests | FIXED |
| MCP Core Lab 使用自定义 toy schema | 对齐 2026-07-28 per-request protocol metadata 与 HTTP header 一致性；明确 local conformance ≠ SDK interoperability | MCP deterministic conformance tests | FIXED |
| A2A Core Lab 使用旧/简化 AgentCard 与 Task | 对齐 1.0 `supportedInterfaces`, structured skills, `Task.status.state` 与状态集合 | A2A deterministic conformance tests | FIXED |
| `passed=true` 混淆“观察坏状态”和“系统约束成功” | 结果拆为 oracle/system detection、containment、recovery、invariant；分级 L1–L5 | 80 Core Labs evidence summary | FIXED |
| checkpoint 单文件/弱并发边界 | per-run namespace + version/CAS + writer lock + fsync/replace/fsync-dir | checkpoint concurrency/CAS tests | FIXED |
| journal append 前未强制验证已有链 | append 前验证完整 hash chain；损坏 fail-closed；writer lock + fsync | corruption/concurrency tests | FIXED |
| AgentOps 示例审批只改变 status | tenant/action binding → durable effect → mutation → observation/verifier/evidence | API/service tests | FIXED |
| 跨章模板段落过多 | 通用方法论中央化到附录；章节保留主题特有 failure window/机制/边界 | semantic duplicate QA | FIXED |
| “源码剖析”标题强于正文证据 | 收紧为“实现对照与源码阅读入口” | chapter/slide/book QA | FIXED |
| SOURCE_LOCK 不是 closed-world | 正文 URL 必须被 lock 或显式 allowlist 覆盖 | source-lock coverage QA | FIXED |
| upstream recipe 容易被误读为真实复现 | 10 个 upstream lab 增加机器可读 behavior contract，并标记 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE` | upstream contract QA | FIXED |
| packaging determinism 与 clean rebuild reproducibility 混为一谈 | 两个 gate 分离；legacy reproducible 名称明确降级为 packaging-only alias | deterministic packaging + same-host rebuild gates | FIXED |
| PDF 图路径依赖 Pandoc 临时工作目录 | 改为两阶段 Pandoc→canonical LaTeX→XeLaTeX×2，并让 diagram 引用使用 repo-root 相对路径，避免 checkout 绝对路径泄漏到 XDV/PDF | Book/Workbook publication regression | FIXED |
| EPUB clean rebuild 因随机 UUID 不同 | 使用 course/version/artifact 派生的 UUIDv5 `identifier`；保留 `SOURCE_DATE_EPOCH` | repeated-build SHA-256 + clean-rebuild gate | FIXED |
| XeLaTeX PDF clean rebuild 因 trailer ID 不同 | 为 xdvipdfmx 注入内容派生的 `pdf:trailerid`，不改变正文/排版 | repeated-build SHA-256 + PDF structure QA | FIXED |
| python-pptx ZIP envelope 使用 wall-clock timestamp | 保存后按 `SOURCE_DATE_EPOCH`、固定成员顺序/权限规范化 OOXML ZIP；重新打开验证 | repeated-build SHA-256 + Slides QA | FIXED |
| clean rebuild gate 黑盒 capture，长构建不可诊断 | 改为 Book/Site/Workbook/Slides 分阶段构建、每阶段独立日志/超时/退出码 | same-host clean-rebuild log | FIXED |
| 把 PDF/EPUB 私有封装字节等同于出版语义 | 普通文件保留原始 SHA-256；PDF 比较元数据、layout text 与全页低分辨率渲染，EPUB 比较排序成员 payload 并规范标准修改时间 | format-aware clean-rebuild evidence | CLAIM-BOUNDED |
| builder APT 层无法证明 bit-hermetic | digest-pin base、lock Python；记录 OS package inventory，并明确 claim ceiling | builder contract QA | HARDENED / CLAIM-BOUNDED |

## 2. 实验等级

本版本不再把所有绿色实验统一解释为“机制已经成功约束故障”。

- **L1_MECHANISM**：正常路径可执行，并验证目标机制的基本不变量。
- **L2_ORACLE_ONLY**：故障成功注入，测试 oracle 看到了预期坏状态；不声称系统已阻断。
- **L2_DETECTED**：系统自身显式识别故障/不确定性。
- **L3_CONTAINED**：系统检测并阻止危险结果越过安全边界。
- **L4_RECOVERED**：系统在故障后恢复到验证过的可接受状态。
- **L5_EXTERNAL**：真实外部 SDK/服务/benchmark 的互操作或端到端行为证据；必须单独执行并记录版本与环境。

当前 release 的 fault-path Core Lab 分布为：`L2_ORACLE_ONLY=14`, `L2_DETECTED=2`, `L3_CONTAINED=23`, `L4_RECOVERED=1`。这组数字只描述本仓库 deterministic Core Labs，不等价于 40 个真实外部系统故障实验。

另有 6 个 scoped `L5_EXTERNAL` 官方实现向量：MCP、A2A、OpenAI Agents、LangGraph、Google ADK 与 Microsoft Agent Framework。它们证明各自 evidence vector，不覆盖十个 broad upstream contract，也不产生 benchmark 分数。

## 3. 正式证据边界

本 release 可以证明：

1. 本地 deterministic Runtime/Journal/Checkpoint/approval/reconciliation 机制通过自动化测试；
2. 80 个 Core Labs 全部可执行，且故障证据等级被显式区分；
3. MCP/A2A Core Labs 对当前锁定规范的数据模型/关键不变量做 deterministic conformance 检查；
4. 主书、Workbook、Site、Slides 可以从同一 source tree 生成，并经过结构 QA；
5. source locks、upstream behavior contracts、release/tag/build contracts 有机器 gate。
6. SOURCE-CLEAN 在同一 ARM64 主机、同一 Python、两个独立冷 cache 下完整重建；134 个发布表面中 130 个文件 byte-identical，2 个 PDF 与 2 个 EPUB 的格式感知指纹一致；
7. 六项 pinned 官方实现实验的跨进程/跨重启行为、故障与独立 verifier 已形成可审计证据包。

本 release **不证明**：

- 对任意外部 SaaS/云 API 的 exactly-once side effect；
- 所有 upstream SDK 在本次 release 环境中都已真实执行；
- MCP/A2A local fixture 等价于官方 SDK interoperability；
- Docker builder 的 APT 层已经达到跨时间/跨镜像仓库的 bit-hermetic；
- 跨不同操作系统、不同 TeX/font/runtime 的 artifact byte identity。

这些边界是正式设计的一部分，而不是遗漏：无法被当前证据支持的性质不得写成已证明事实。

## 4. Release 验收口径

正式 `v1.0.0` SOURCE-CLEAN 只有在以下 gate 全部通过后才允许生成：

- locked dependency/bootstrap check；
- 114 个 pytest regression，line coverage 90%；
- 69 个 Python examples；
- 80/80 Core Labs；
- source / content / protocol-source-lock / upstream-contract / builder-contract QA；
- Book / PDF structure / Workbook / Slides / Site output QA；
- repository validation；
- deterministic packaging；
- same-host two-clean-checkout rebuild comparison。

最终 release 的精确测试数、页数、hash 与 gate 输出以 `VALIDATION_REPORT.md`、`EXPERIMENT_STATUS.md` 和 release manifest 为准。
