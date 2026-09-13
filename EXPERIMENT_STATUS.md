# Experiment Status — v1.0.0 / Build System 1.1.2

本文件只记录**已经有本地执行证据**的状态，并把“本地确定性 fixture”“系统检测/约束/恢复”“真实上游框架互操作”分开。`PASS` 不再被统一解释为“生产故障已经恢复”。

| Category | Count | Status / Claim Ceiling |
|---|---:|---|
| Core Labs | 80 | **VERIFIED — 80/80**；40 normal + 40 fault |
| Fault evidence | 40 | 14 `L2_ORACLE_ONLY` / 2 `L2_DETECTED` / 23 `L3_CONTAINED` / 1 `L4_RECOVERED` |
| Python examples | 69 | **VERIFIED — 69/69** |
| Pytest | 114 | **VERIFIED — 114/114**；90% line coverage；含 HITL、crash window、CAS、journal corruption/concurrency、MCP 2026 wire contract 与支撑模块 |
| Main book | 462 A4 pages | **VERIFIED** — PDF/HTML/EPUB + structure QA |
| Website | 127 HTML pages | **VERIFIED** |
| Workbook | 164 A4 pages | **VERIFIED** — PDF/HTML/EPUB + structure QA |
| Slides | 90 | **VERIFIED** — PPTX structure QA |
| Source locks | 100 | **VERIFIED** — closed-world coverage for chapter/appendix external URLs |
| Upstream behavior contracts | 10 | **DEFINED, NOT EXECUTED** — `EXTERNAL_NOT_RUN_IN_THIS_RELEASE` |
| Scoped official implementation evidence | 6 | **VERIFIED** — MCP、A2A、OpenAI Agents、LangGraph、Google ADK、MAF；每项均保留独立 claim ceiling |
| External coding/browser benchmarks | 2 | **PINNED CONTRACTS; NOT EXECUTED** — SWE-bench Lite / WebArena；没有发布分数 |
| Cross-host canonical comparison | 2-host matrix | **WORKFLOW DEFINED; NOT EXECUTED** — Ubuntu 22.04/24.04 尚无本发行版 compare artifact |
| Canonical Quarto container | 1 path | **DEFINED/PINNED; NOT EXECUTED** — `linux/arm64` daemon verified; fixed GHCR base pull blocked by EOF/no response |
| Same-host SOURCE-CLEAN rebuild | 2 cold caches / 134 files | **VERIFIED** — 两次 bootstrap、原生依赖导入与全部发布表面哈希一致 |
| Production Docker/Compose path | 1 | **CODE/TEST COVERED; NOT CLAIMED AS CLOUD/PRODUCTION E2E** |

## Evidence semantics

- `L1_MECHANISM`：正常路径的确定性机制断言成立。
- `L2_ORACLE_ONLY`：独立 oracle 看到了故障；**不代表系统已经阻断**。
- `L2_DETECTED`：系统显式识别故障，但未证明约束或恢复。
- `L3_CONTAINED`：系统识别并 fail-closed / containment，不产生与故障矛盾的成功事实。
- `L4_RECOVERED`：在检测与约束基础上完成受验证的恢复/协调。
- `L5_EXTERNAL`：真实 pinned 上游实现完成范围明确的行为、故障、独立 verifier 与证据包。本发行版有 6 项 **scoped** official-implementation evidence，但没有把 10 个完整 upstream contract、真实 benchmark 或生产 exactly-once 宣称为全部 L5 完成。

Core Labs 是教学型 deterministic fixtures。它们证明明确的不变量与 failure semantics，但不替代真实 provider、浏览器、GPU 或云 API。六项官方实现实验的执行向量和上限见 [`docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md`](docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md)。
