# Canonical Docker / Quarto Validation Handoff — Build System 1.1.1

Docker is **not** required to use or extend this baseline. This document is the optional follow-on gate for teams that want a canonical OCI build environment and provenance evidence.

The repository already includes `Dockerfile.builder`, exact Quarto 1.11.1 metadata, a digest-pinned Quarto base image, `make release-container`, and SHA-pinned Actions. The current local validation host has no Docker daemon/Quarto CLI, so no container runtime PASS is claimed.

On a Docker-capable runner:

```bash
make release-container
```

Recommended additional evidence for the first hosted release:

```text
source commit/tag
final builder image digest
Quarto version
SOURCE_DATE_EPOCH
release SHA256SUMS.txt
second isolated canonical build SHA comparison
CI provenance/attestation if available
```

If the final self-built builder image is published, record its **final image digest**, not only the upstream Quarto base digest. This closes the remaining environment-level reproducibility gap without changing the Build System 1.1.1 source architecture.
