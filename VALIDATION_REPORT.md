# Validation Report — v1.0.0 / Build System 1.1.1

## Scope

- Content version: **v1.0.0**
- Build System: **1.1.1**
- Local publisher actually executed: **Pandoc compatibility path**
- Canonical Quarto/Docker path: configured and source-QA checked; local `linux/arm64` daemon verified, but fixed GHCR base pull failed with EOF/no response, so **not executed in this evidence set**
- External upstream/provider/browser/GPU/cloud experiments: **not promoted without execution evidence**

## Local validation results

| Gate | Result | Evidence |
|---|---|---|
| Core Labs | PASS | 80/80; fault evidence level is recorded separately |
| Pytest + coverage | PASS | 114/114; 90% line coverage; required floor 85% |
| Ruff source lint | PASS | Python source, tests, production service, experiments, scripts, examples and labs |
| Python dependency audit | PASS | `pip-audit --local`; no known vulnerabilities; CycloneDX SBOM generated |
| Python examples | PASS | 69/69 |
| Book QA | PASS | 40 chapters / 80 labs / **462-page** PDF |
| PDF structure QA | PASS | 7 parts / 40 chapters / 6 appendices |
| Workbook structure QA | PASS | **164 pages / 80 labs** |
| Slides QA | PASS | **90 slides** |
| Output QA | PASS | Site **127 pages**; main book 462; workbook 164 |
| Source QA | PASS | 40 chapters / 6 appendices / 80 labs / 80 diagrams / 100 source locks |
| SOURCE_LOCK coverage | PASS | 48 unique external URLs covered; 1 `.invalid` fixture allowlist |
| Upstream contract QA | PASS | 10 contracts; status=`EXTERNAL_NOT_RUN_IN_THIS_RELEASE` |
| Scoped L5 evidence QA | PASS | 6/6 pinned official/upstream implementation runs; schema v2, source/artifact hashes and claim ceilings verified |
| External benchmark contract QA | PASS | 2 pinned contracts; SWE-bench/WebArena remain `NOT_EXECUTED_IN_THIS_RELEASE` and publish no score |
| Builder contract QA | PASS | digest-pinned base + uv pin + explicit APT non-hermetic ceiling |
| Content semantics QA | PASS | exact/normalized repeat max=2; fuzzy groups=0 |
| Repository QA | PASS | `VALIDATION_OK version=v1.0.0 ... pdf_pages=462 source_locks=100` |
| Repeated artifact serialization | PASS | Book PDF/EPUB, Workbook PDF/EPUB, Slides PPTX rebuilt twice with identical SHA-256; PPTX reopened successfully |
| Same-host two-clean-extraction rebuild | PASS | `SAME_HOST_CLEAN_REBUILD_EQUIVALENCE_OK files=134`; SOURCE-CLEAN SHA、主机/Python 与逐文件哈希见 `validation_logs/same-host-clean-rebuild.json` |

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

## Evidence limits

This report does **not** claim cross-host bit-for-bit reproducibility, APT snapshot hermeticity, exactly-once external side effects, real SWE-bench/WebArena scores, or complete execution of the ten third-party upstream contracts. The six scoped external implementation runs prove only the dimensions recorded in their evidence vectors. Detailed audit: [`docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md`](docs/L5_EXTERNAL_EVIDENCE_AUDIT_2026-09-11.md).
