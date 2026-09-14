# Changelog

All notable public changes are documented here. The project follows [Semantic Versioning](https://semver.org/) and the structure of [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- README quality gate that checks every local link and requires exact coverage of the 40 canonical chapters, 80 Core Labs, 6 appendices and versioned release download assets.

### Changed

- Rebuilt the Chinese README around reader workflows: auditable PDF/EPUB/HTML downloads, GitHub reading, learning paths, chapter summaries, per-chapter normal/fault lab links, evidence semantics, code entry points and release verification.

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
