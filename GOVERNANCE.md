# Governance

## Scope and stewardship

The project is currently maintainer-led. `@william-lbn` is the release maintainer and final steward for scope, security response and repository administration. Technical decisions should be made in public issues or pull requests unless they contain security-sensitive information.

## Decision principles

Decisions prioritize, in order: correctness and user safety; honest evidence boundaries; reproducibility; educational value; interoperability; and long-term maintenance cost. Popularity or chapter count alone is not sufficient justification for a change.

Routine changes are accepted through reviewed pull requests with passing required checks. Material changes to licensing, governance, security boundaries, canonical formats, protocol interpretation or release claims require an issue, documented rationale and maintainer approval.

## Releases

Releases follow Semantic Versioning for the public repository. A release tag is created only from `main` after required checks pass. Generated artifacts are produced by GitHub Actions, checksummed and attached to the GitHub Release. Evidence status may advance only when raw artifacts and an independent verifier are present.

## Maintainer succession

Additional maintainers may be appointed after sustained, high-quality contributions and demonstrated judgment around evidence and security. Inactivity or conflicts of interest should be disclosed. If the lead maintainer becomes unavailable, active maintainers should document a replacement in a public governance pull request.
