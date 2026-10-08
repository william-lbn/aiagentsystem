# Changelog

All notable public changes are documented here. The project follows [Semantic Versioning](https://semver.org/) and the structure of [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Recomputable 40-chapter audit matrix, checked in CI against canonical source and all 80 A/B lab links.
- Negative tests for fault-evidence grading, deployment lock absence/mismatch, paired-evaluation manipulation, and stale capstone approval.
- README quality gate that checks every local link and requires exact coverage of the 40 canonical chapters, 80 Core Labs, 13 appendices and versioned release download assets.
- Two executable assurance modules for evaluation, benchmark comparability, tamper-evident traces, capability authorization, effect reconciliation, production HTTP, deployment contracts, dataset leakage, realtime cancellation, canary rollback and the durable capstone.
- Part VI and Part VII solution appendices with 60 evidence-oriented answers.

### Changed

- Corrected Chapter 1's model/runtime state-transition formalism and narrowed Chapters 36–40's static, local, in-memory and fixture evidence claims.
- Replaced scenario-name-based L3/L4 grading with explicit observed detection, containment and recovery facts.
- Removed offline reverse-DNS startup delay from local browser/API experiments; both still use real loopback HTTP.
- Made deployment preflight read the actual image lock, and made capstone capability preflight side-effect-free with caller-supplied, intent-bound teaching approval.
- Pinned urllib3 2.8.0 after the 2026-10-08 audit found three new advisories in 2.7.0; the refreshed audit reports no known vulnerabilities.
- Added East Asian OOXML font metadata to generated course slides for better cross-application handling.
- Rebuilt the Chinese README around reader workflows: auditable PDF/EPUB/HTML downloads, GitHub reading, learning paths, chapter summaries, per-chapter normal/fault lab links, evidence semantics, code entry points and release verification.
- Rewrote Chapters 29–40 and Labs 29A–40B around executable invariants, independent verifiers, explicit claim ceilings and real normal/fault outputs; all 40 fault labs now reach either containment or verified recovery.
- Expanded the local suite to 237 tests and 89.81% coverage, with 80/80 Core Labs and 69/69 executable examples passing.
- Pinned AnyIO 4.14.2 to remediate CVE-2026-63374 and CVE-2026-64847; the refreshed dependency audit reports no known vulnerabilities.
- Marked hosted canonical publication and clean-rebuild equivalence as pending for this worktree instead of inheriting evidence from an earlier commit.

## [1.0.0] - 2026-09-11

### Added

- Public open-source governance: DCO, CODEOWNERS, contribution, security, support, citation, licensing and third-party policies.
- Structured issue/PR templates, Dependabot, CodeQL, coverage, dependency audit, CycloneDX SBOM and release provenance workflows.
- Six scoped official implementation experiments for MCP, A2A, OpenAI Agents SDK, LangGraph, Google ADK and Microsoft Agent Framework.
- Pinned SWE-bench Lite and WebArena execution contracts with explicit not-executed status and raw-evidence requirements.
- Digest-pinned canonical Quarto container workflow with downloadable publication artifacts.

### Changed

- Established `v1.0.0` as the first public Semantic Versioning baseline; Build System remains independently versioned at `1.1.2`.
- Hardened HITL action identity, unknown-outcome reconciliation, checkpoint CAS/durability, journal integrity and tool failure semantics.
- Aligned MCP 2026-07-28 and A2A 1.0 teaching contracts with their protocol structures while separating fixtures from official SDK evidence.
- Made SOURCE_LOCK coverage closed-world for chapter and appendix URLs and attached explicit claim ceilings to external evidence.
- Centralized repeated methodology so the 462-page book carries higher information density without expanding the 40-chapter scope.
- Made canonical PDF rendering fail closed: all observed TeX dependencies are declared in the builder lock, Quarto package auto-installation is disabled, diagram paths are valid in both per-chapter Quarto and assembled-book Pandoc contexts, PDF Babel language is explicitly mapped while preserving `zh-Hans` document metadata, and PDF dates/trailer IDs are derived from locked build inputs.
- Stabilized canonical EPUB identifiers, prepared-source timestamps and website render ordering without treating third-party cross-host CSS byte ordering as a release guarantee.

### Verified

- 80 Core Labs, 114 pytest tests, 90% line coverage and 69 executable examples.
- Hosted canonical publication: 484-page book, 165-page workbook, 127-page website and 90-slide deck; local compatibility publication: 462-page book and 164-page workbook.
- Six scoped L5 evidence packages and 100 external source locks.
- Two isolated same-host compatibility cold rebuilds with 134 format-aware publication comparisons: 130 byte-exact SHA-256 values, 2 PDF semantic/render fingerprints and 2 EPUB payload fingerprints.

### Known evidence limits

- SWE-bench Lite and WebArena are not executed in this release and have no published score.
- Cross-host bit-for-bit output identity, real provider/browser/cloud E2E and all ten broad upstream contracts are not claimed as verified.
- The six official implementation experiments do not imply cross-language, remote-auth, distributed-failover or unconditional exactly-once certification.

[1.0.0]: https://github.com/william-lbn/aiagentsystem/releases/tag/v1.0.0
