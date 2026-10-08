# Validation Report — v1.0.0 / Build System 1.1.2

## Scope

- Content version: **v1.0.0**
- Build System: **1.1.2**
- Source/protocol/research cutoff: **2026-09-11**
- Dependency security refresh: **2026-10-08**; this operational patch does not change the book's protocol/research cutoff.
- This-worktree local verification date: **2026-10-08**
- Local publisher actually executed: **Pandoc compatibility path**
- Hosted canonical status is **commit-specific and mutable**: use the exact SHA's [CI workflow run](https://github.com/william-lbn/aiagentsystem/actions/workflows/ci.yml) and its `canonical-publication` job as the authority. A historical Quarto run in the digest-pinned OCI builder does not verify a later source revision.
- External upstream/provider/browser/GPU/cloud experiments: **not promoted without execution evidence**

## Validation results

| Gate | Result | Evidence |
|---|---|---|
| Core Labs | PASS | 80/80; fault evidence level is recorded separately |
| Pytest + coverage | PASS | 237/237; 89.81% line/branch-aware coverage; required floor 85% |
| Ruff source lint | PASS | Python source, tests, production service, experiments, scripts, examples and labs |
| Python dependency audit | PASS (2026-10-08) | `pip-audit --local`; urllib3 2.7.0 first failed with 3 advisories, then locked 2.8.0 and reran to zero known vulnerabilities; CycloneDX SBOM regenerated |
| Python examples | PASS | 69/69 |
| Local compatibility Book QA | PASS | 40 chapters / 80 labs / **328-page** PDF |
| PDF structure QA | PASS | 7 parts / 40 chapters / 13 appendices |
| Local compatibility Workbook structure QA | PASS | **135 pages / 80 labs** |
| Slides structure QA | PASS WITH LIMIT | **90 slides**; OOXML contains Chinese text and East Asian font metadata. Headless LibreOffice on this macOS host substituted a font without CJK glyphs, so visual rendering is **not certified**; validate in target PowerPoint/LibreOffice environment before distribution. |
| Local compatibility Output QA | PASS | Site **134 pages**; main book 328; workbook 135 |
| Hosted canonical publication | VERIFY PER COMMIT | Check the exact SHA's `canonical-publication` job; this local report does not freeze an asynchronous GitHub Actions result |
| Source QA | PASS | 40 chapters / 13 appendices / 80 labs / 80 diagrams / 114 source locks |
| SOURCE_LOCK coverage | PASS | 106 references / 44 unique external URLs covered; 1 `.invalid` fixture allowlist |
| Upstream contract QA | PASS | 10 contracts; status=`EXTERNAL_NOT_RUN_IN_THIS_RELEASE` |
| Scoped L5 evidence QA | PASS | 6/6 pinned official/upstream implementation runs; schema v2, source/artifact hashes and claim ceilings verified |
| External benchmark contract QA | PASS | 2 pinned contracts; SWE-bench/WebArena remain `NOT_EXECUTED_IN_THIS_RELEASE` and publish no score |
| Builder contract QA | PASS | digest-pinned base + uv pin + explicit APT non-hermetic ceiling |
| Content semantics QA | PASS | exact/normalized repeat max=1; fuzzy groups=0 |
| Repository QA | PASS | `VALIDATION_OK version=v1.0.0 build_system=1.1.2 chapters=40 labs=80 chapter_examples=40 pdf_pages=328 source_locks=114` |
| PDF visual sample | PASS WITH SCOPE | Current main-book pp. 323–324 inspected as rendered PNG; automated full-book/workbook structure checks passed. This is not a page-by-page visual certification. |
| Repeated artifact serialization | PENDING | Previous evidence predates this worktree; rerun after commit in the release workflow |
| Same-host two-clean-extraction rebuild | PENDING | Previous `same-host-clean-rebuild.json` predates this worktree and is not claimed as current evidence |

## Correctness evidence in v1.0

1. Approval is bound to the exact pending action identity, not a tool name or a new model turn.
2. Resume from `EXECUTING_EFFECT` transitions to `NEEDS_RECONCILIATION`; it does not replay an ambiguous external side effect.
3. `NOT_APPLIED` cannot silently flow into a later successful final answer.
4. Non-idempotent timeout remains `UNKNOWN` and non-retryable without reconciliation proof.
5. Checkpoint uses per-run version/CAS and crash-conscious file+directory fsync; Journal verifies existing history before append.
6. Protocol labs separate local schema/conformance fixtures from official-SDK L5 evidence.
7. Fault-lab PASS semantics distinguish oracle-only detection, system detection, containment and recovery.
8. MCP/A2A official SDKs now cross real process/socket boundaries; OpenAI Agents/LangGraph/ADK/MAF persistence surfaces are separately verified instead of conflated.
9. External benchmark readiness, actual execution and evaluator evidence are separate states; the local preflight is not treated as a score.
10. Parts VI–VII add independent evaluation, benchmark comparability, tamper-evident traces, capability authorization, external-effect reconciliation, tenant-scoped HTTP, deployment contract inspection, dataset contamination gates, realtime cancellation epochs, canary rollback and an end-to-end durable capstone. The 2026-10-08 audit narrowed static, in-memory and local-fixture claims in Chapters 36–40 and fixed the local HTTP reverse-DNS delay.

## Evidence limits

This local report does **not** independently attest hosted-canonical completion (consult the exact commit's CI run), current clean-rebuild equivalence, cross-host bit-for-bit reproducibility, APT snapshot hermeticity, exactly-once external side effects, real SWE-bench/WebArena scores, real post-training quality gains, realtime-provider latency, multi-architecture image execution, or complete execution of the ten third-party upstream contracts. The six scoped external implementation runs prove only the dimensions recorded in their evidence vectors. Detailed audit: [`docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md`](docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md).
