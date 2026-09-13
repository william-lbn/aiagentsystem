# v1.0.0 — First Public Open-Source Baseline

`v1.0.0` 是项目第一个采用 Semantic Versioning 的公开基线。它不扩张章节数量，重点确保 Runtime correctness、协议准确性、实验 claim semantics、source evidence、开源治理与 release gates 可被独立审计。

## 关键正确性修复

- **HITL durable resume**：审批绑定 immutable `action_id`；批准后执行原 pending effect；拒绝、过期、stale approval 均 fail-closed。
- **Crash/Unknown Outcome**：在进入 effect 前持久化 `EXECUTING_EFFECT`；若进程在外部副作用与本地结果落盘之间崩溃，恢复进入 `NEEDS_RECONCILIATION`，禁止盲目重放；不宣称无条件 exactly-once。
- **Tool failure semantics**：`COMMITTED / NOT_APPLIED / UNKNOWN` 分离；unknown tool 不再继续生成虚假 `FINISHED`；非幂等 timeout 不再标记为安全可重试。
- **Checkpoint/Journal**：run namespace、version/CAS、writer lock、file+directory fsync、完整 hash-chain 校验；损坏历史 fail-closed。
- **Production case**：approval → durable intent/effect → local mutation → independent observation/verifier/evidence；明确 SQLite 本地事务不能外推成跨系统 exactly-once。

## 协议与研究准确性

- MCP Core Lab 对齐 **2026-07-28** per-request metadata：`io.modelcontextprotocol/protocolVersion`、`clientCapabilities` 与 HTTP `MCP-Protocol-Version` 一致性；明确 deterministic fixture ≠ official SDK interoperability。
- A2A Core Lab 对齐 **1.0** AgentCard/Task：`supportedInterfaces`、结构化 `skills`、`Task.status.state` 与完整 TaskState 集合。
- 补充 OWASP Agentic Top 10 2026 / Agent Control Standard 等 2026 evidence，并纳入 SOURCE_LOCK。
- 10 个 upstream lab 改为行为合同：normal/fault/independent verifier/evidence package/claim ceiling；本发行版统一标记 `EXTERNAL_NOT_RUN_IN_THIS_RELEASE`。

## 实验与 QA 语义

- 80 个 Core Labs 仍为 **80/80 PASS**，但 `passed=true` 只表示 scenario oracle 的预期成立，不再等价为“故障被系统恢复”。
- 40 个 fault labs 分层：14 `L2_ORACLE_ONLY`、2 `L2_DETECTED`、23 `L3_CONTAINED`、1 `L4_RECOVERED`。
- pytest 扩展到 **114 tests**，覆盖 HITL action identity、expiry/stale/reject、effect crash window、checkpoint CAS、多 run 隔离、journal corruption/concurrency，以及 retrieval/memory/evaluation/workflow 支撑模块。
- 新增 6 个 scoped 官方实现 L5 实验：MCP、A2A、OpenAI Agents、LangGraph、Google ADK、Microsoft Agent Framework；每项保存 source/artifact hash 与独立 claim ceiling。
- SWE-bench Lite 与 WebArena 只发布固定 harness/task/证据要求的执行合同；本发行版未执行、不发布分数。
- 章节 exact/normalized/fuzzy 跨章模板化 QA 收紧；≥80 字跨 ≥3 章的高相似模板组当前为 0。

## Build / Release Hardening

- SOURCE_LOCK 改为 closed-world coverage gate；当前 100 locks 覆盖正文/附录 48 个唯一 external URLs。
- release workflow 已接入 tag==`course.toml` gate。
- packaging determinism 与 clean rebuild reproducibility 分开命名；不再把“同一 source tree 打包两次”夸大成 hermetic rebuild。
- Builder base image digest pinned；Python dependency 由 `uv.lock` 锁定；APT 仍明确标注 **not bit-hermetic**，release 必须保存实际 `dpkg` inventory，而不是伪称全 hermetic。
- 修复 Pandoc→XeLaTeX vector-diagram path：出版链改为显式两阶段构建，并从 repo root 使用稳定相对图路径；既避免旧的一步式临时目录查找问题，也避免不同 checkout 的绝对路径泄漏到 PDF。
- Lab runner / example runner 为并发任务隔离 `AGENTLAB_HOME`，避免共享 checkpoint/journal 把资源竞争误报成语义失败。
- **Artifact serialization determinism**：EPUB 固定 course/version/artifact 派生 UUIDv5 identifier；XeLaTeX/xdvipdfmx 使用内容派生 trailer ID；PPTX 在 `python-pptx` 保存后按 `SOURCE_DATE_EPOCH` 规范化 ZIP timestamp/member order/permissions。
- **Canonical input determinism**：Quarto Book/Workbook 使用稳定 publication UUID；127 个 Website 输入使用显式顺序，prepared source mtime 统一到 `SOURCE_DATE_EPOCH`。
- **Clean rebuild gate 可诊断化**：两份 SOURCE-CLEAN extraction 分别按 Book → Site → Workbook → Slides 执行，每 surface 有独立 timeout/exit status；PPTX/HTML/SVG/PNG/CSS/JS 等稳定文件比较原始 SHA-256，PDF/EPUB 比较结构、内容与渲染/payload 指纹，不把“能够构建”、格式语义等价与容器封装 byte-identical 混为一个模糊结论。
- **可直接验证的发布清单**：外部 `SHA256SUMS.txt` 只使用 basename，并覆盖除清单自身外的全部 GitHub Release 资产；发布前会重新读取、重算并拒绝遗漏、重复、路径项或摘要不一致。

## 本地已验证出版规模

- Main Book：**462 A4 pages**，PDF/HTML/EPUB；
- Website：**127 HTML pages**；
- Workbook：**164 A4 pages**，PDF/HTML/EPUB；
- Slides：**90 slides**；
- Core Labs：**80/80**；Python examples：**69/69**；pytest：**114/114**；行覆盖率：**90%**；Source locks：**100**；scoped L5 evidence：**6/6**。

GitHub hosted canonical CI 另已在 digest-pinned Quarto 1.11.1 builder 中验证：Main Book **484 pages**、Workbook **165 pages**、Website **127 pages**、Slides **90**。两种 publisher 的分页差异属于排版后端差异，报告分别保留，不互相覆盖。

本版本把跨章通用方法论中央化并移除模板化重复，同时加入 L5 外部实现证据。目标是提高每页信息密度，而不是用页数替代技术深度。

## 开源发布基础设施

- MIT 授权范围、第三方边界、DCO、治理、安全、支持和引用元数据已进入仓库；
- CI 覆盖 Python 3.11–3.13、lint、coverage、依赖漏洞审计、CycloneDX SBOM、CodeQL 与 canonical publication；
- Git 索引门禁拒绝生成物、运行状态、凭据文件、疑似实密钥与异常大文件进入公开提交；当前锁定 Python 环境经 `pip-audit` 检查未发现已知漏洞；
- tag release 由锁定的 container builder 重建，上传校验和并生成 GitHub artifact attestation；
- 生成物不进入 `main`，正式 PDF/EPUB/PPTX/Website/Release ZIP 由 GitHub Release 分发。
