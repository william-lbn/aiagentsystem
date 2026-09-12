# Third-Party Notices

This repository documents and interoperates with third-party software and standards. Those projects keep their own copyrights, licenses and trademarks.

## Dependency and protocol boundaries

- Python dependencies are resolved by `uv.lock`; their license metadata remains authoritative upstream.
- The canonical publisher uses the digest-pinned Quarto container named in `builder.lock.json` and `Dockerfile.builder`.
- System packages and Noto CJK fonts are installed by the builder image and are not vendored in SOURCE-CLEAN.
- MCP, A2A, OpenAI Agents SDK, LangGraph, Google ADK and Microsoft Agent Framework experiments use the exact official releases recorded in `experiments/l5/catalog.json`.
- SWE-bench and WebArena remain external harnesses. The repository stores pinned execution contracts, not copies of their repositories or datasets.
- Papers, specifications and websites referenced by the book are citations. The observation and reproducibility locks are recorded in `integrations/SOURCE_LOCK.json`.

No third-party trademark grants are implied. Before redistributing generated bundles together with additional assets, distributors are responsible for checking the corresponding upstream terms. If an attribution or provenance record is missing, please open an issue; suspected rights violations may be reported privately through the security channel.
