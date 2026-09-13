# Validation Report — v1.0.0 / Build System 1.1.2

## Scope

- Content version: **v1.0.0**
- Build System: **1.1.2**
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
| Scoped L5 evidence QA | PASS | 6/6 official implementation runs with hashes and claim ceilings |
| External benchmark contract QA | PASS | 2 pinned contracts; both `NOT_EXECUTED_IN_THIS_RELEASE`, no score |
| Builder contract QA | PASS | digest-pinned base + uv pin + explicit APT non-hermetic ceiling |
| Content semantics QA | PASS | exact/normalized repeat max=2; fuzzy groups=0 |
| Repository QA | PASS | `VALIDATION_OK version=v1.0.0 ... pdf_pages=462 source_locks=100` |
| Same-host two-clean-extraction rebuild | PASS | 2 cold caches; native import audits; 134 artifact hashes identical |

## Correctness evidence in v1.0

1. Approval is bound to the exact pending action identity, not a tool name or a new model turn.
2. Resume from `EXECUTING_EFFECT` transitions to `NEEDS_RECONCILIATION`; it does not replay an ambiguous external side effect.
3. `NOT_APPLIED` cannot silently flow into a later successful final answer.
4. Non-idempotent timeout remains `UNKNOWN` and non-retryable without reconciliation proof.
5. Checkpoint uses per-run version/CAS and crash-conscious file+directory fsync; Journal verifies existing history before append.
6. Protocol labs separate local schema/conformance fixtures from official-SDK L5 evidence.
7. Fault-lab PASS semantics distinguish oracle-only detection, system detection, containment and recovery.

## Evidence limits

This report does **not** claim cross-host bit-for-bit reproducibility, APT snapshot hermeticity, exactly-once external side effects, real SWE-bench/WebArena scores, or execution of all ten broad upstream contracts. Six scoped official implementation vectors are verified; those vectors do not expand into blanket production certification.
