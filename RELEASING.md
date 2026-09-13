# Release Process

1. Update `course.toml`, `pyproject.toml`, `CITATION.cff`, `CHANGELOG.md` and `RELEASE_NOTES.md` consistently.
2. Run `make validate`, then `make release` from a clean source tree.
3. Confirm `git status --short` contains only intentional canonical changes.
4. Merge through a reviewed pull request and wait for all required checks on `main`.
5. Create an annotated, signed release tag when signing is available: `git tag -s vX.Y.Z`.
6. Push the tag. `.github/workflows/release.yml` rebuilds the canonical artifacts, records the builder inventory, creates checksums and provenance, and publishes the GitHub Release.
7. Verify the attached `SHA256SUMS.txt`, artifact attestation, release notes and canonical publication workflow result.

Never build an official release from an uncommitted working tree or upload locally modified artifacts over the workflow outputs. A failed external benchmark or unavailable provider is recorded as failed/not executed; it is not replaced with a synthetic score.
