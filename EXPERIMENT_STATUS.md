# Experiment Status — v1.0.0 / Build System 1.1.2

本文件只记录**已经有本地执行证据**的状态，并把“本地确定性 fixture”“系统检测/约束/恢复”“真实上游框架互操作”分开。`PASS` 不再被统一解释为“生产故障已经恢复”。

| Category | Count | Status / Claim Ceiling |
|---|---:|---|
| Core Labs | 80 | **VERIFIED — 80/80**；40 normal + 40 fault |
| Fault evidence | 40 | 37 `L3_CONTAINED` / 3 `L4_RECOVERED`; no oracle-only case is promoted as containment |
| Python examples | 69 | **VERIFIED — 69/69** |
| Pytest | 237 | **VERIFIED — 237/237**；89.81% coverage；含 HTTP loopback、HITL、effect reconciliation、dataset leakage、cancellation epoch、canary rollback 与 durable capstone |
| Main book | 328 A4 pages | **VERIFIED LOCALLY** — Pandoc compatibility PDF/HTML/EPUB + structure QA |
| Website | 134 HTML pages | **VERIFIED LOCALLY** |
| Workbook | 135 A4 pages | **VERIFIED LOCALLY** — PDF/HTML/EPUB + structure QA |
| Slides | 90 | **STRUCTURE VERIFIED ONLY** — PPTX 保留中文及东亚字体声明；本机 headless LibreOffice 转 PDF 时 CJK 字形缺失，不能宣称视觉验收通过，需在目标演示软件复核 |
| Source locks | 114 | **VERIFIED** — 106 references / 44 unique chapter/appendix external URLs，plus one `.invalid` fixture allowlist |
| Upstream behavior contracts | 10 | **DEFINED, NOT EXECUTED** — `EXTERNAL_NOT_RUN_IN_THIS_RELEASE` |
| Scoped official implementation evidence | 6 | **VERIFIED** — MCP、A2A、OpenAI Agents、LangGraph、Google ADK、MAF；每项均保留独立 claim ceiling |
| External coding/browser benchmarks | 2 | **PINNED CONTRACTS; NOT EXECUTED** — SWE-bench Lite / WebArena；没有发布分数 |
| Cross-host canonical comparison | 2-host diagnostic | **OUTSIDE RELEASE CLAIM / WORKFLOW REMOVED** — 两端结构与内容 QA 通过，但 Quarto Bootstrap CSS 字节排序不同；v1.0.0 不发布 bit-for-bit 声明 |
| Canonical Quarto container | 1 digest-pinned path | **PENDING FOR THIS WORKTREE** — 历史 CI 结果不冒充当前 Part VI–VII 重写后的结果 |
| Same-host SOURCE-CLEAN rebuild | 2 cold caches | **PENDING FOR THIS WORKTREE** — 旧证据保留但不作为当前源码声明 |
| Production Docker/Compose path | 1 | **STATIC CONTRACT + CODE/TEST COVERED**；校验实际 `IMAGE_LOCK.json` 声明与 Dockerfile base 一致；本机 Docker daemon 未运行，未宣称真实 registry push、签名、SBOM、amd64/arm64 双平台运行或云端 E2E |

## Evidence semantics

- `L1_MECHANISM`：正常路径的确定性机制断言成立。
- `L2_ORACLE_ONLY`：独立 oracle 看到了故障；**不代表系统已经阻断**。
- `L2_DETECTED`：系统显式识别故障，但未证明约束或恢复。
- `L3_CONTAINED`：系统识别并 fail-closed / containment，不产生与故障矛盾的成功事实。
- `L4_RECOVERED`：在检测与约束基础上完成受验证的恢复/协调。
- `L5_EXTERNAL`：真实 pinned 上游实现完成范围明确的行为、故障、独立 verifier 与证据包。本发行版有 6 项 **scoped** official-implementation evidence，但没有把 10 个完整 upstream contract、真实 benchmark 或生产 exactly-once 宣称为全部 L5 完成。

Core Labs 是教学型 deterministic fixtures。它们证明明确的不变量与 failure semantics，但不替代真实 provider、浏览器、GPU 或云 API。六项官方实现实验的执行向量和上限见 [`docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md`](docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md)。
