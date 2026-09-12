# v1.0.0 Open-Source Baseline Audit

## Decision

**PASS as the next source baseline, with explicit evidence boundaries.**

The first public baseline repairs the hardest defects at the state-machine, test and evidence layers rather than hiding them through editorial changes. Build System 1.1.1 remains independently versioned; public content follows Semantic Versioning.

## Why this baseline is stronger

- HITL now resumes the exact approved pending action and models the ambiguous crash window explicitly.
- Tool outcomes preserve `COMMITTED / NOT_APPLIED / UNKNOWN`; fail-closed semantics are test-covered.
- MCP 2026-07-28 and A2A 1.0 Core Labs use protocol-aligned fields with a clear claim ceiling.
- 80 Core Labs expose evidence level instead of conflating “fault observed” with “fault contained/recovered”.
- 114 tests cover runtime correctness and the retrieval, memory, evaluation and workflow support modules.
- SOURCE_LOCK is closed-world for chapter/appendix URLs; upstream labs have auditable behavior contracts.
- Cross-chapter boilerplate was centralized; after the L5 evidence upgrade the main PDF is 462 pages rather than 516 while preserving the 40-chapter/6-appendix curriculum.
- Release gates distinguish packaging determinism, same-host clean rebuild and canonical container identity rather than using a single over-broad “reproducible” label.

## Local artifact baseline

- Main book: PDF/HTML/EPUB; **462 A4 pages**.
- Website: **127 HTML pages**.
- Workbook: PDF/HTML/EPUB; **164 A4 pages**.
- Slides: **90**.
- Core Labs: **80/80**; Python examples: **69/69**; pytest: **114/114**; line coverage: **90%**.
- Source locks: **100**; upstream behavior contracts: **10** (not externally executed in this release).
- Scoped official/upstream implementation evidence: **6/6** (MCP, A2A, OpenAI Agents, LangGraph, Google ADK, MAF), each with an explicit claim ceiling.
- External benchmark contracts: **2**, both explicitly not executed; no SWE-bench or WebArena score is claimed.
- Same-host SOURCE-CLEAN rebuild: **2 independent cold caches / 134 artifact files**, byte-equivalent with native-extension import audits.

## Remaining claim ceilings

The source is suitable as the next development trunk, but it must not be described as proving: cross-platform hermetic rebuild, real cloud/browser/provider E2E, cross-language interoperability, official SDK interoperability for all upstream contracts, or unconditional exactly-once external effects. The six executed experiments are scoped L5 vectors, not a blanket production certification.
