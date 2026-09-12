# v1.0 Research Audit — cutoff 2026-09-11

## Scope

v1.0 freezes Build System 1.1.1 and the public knowledge baseline. The evidence set is recorded in `integrations/SOURCE_LOCK.json`; reproducibility pins remain distinct from latest-observed ecosystem versions.

## Evidence policy

1. Prefer primary research papers, official specifications, official release notes, standards/regulatory publications and first-party engineering reports.
2. Treat vendor product posts as evidence of product capability/direction, not as independent proof of market-wide ROI.
3. Treat arXiv preprints as current research evidence, not settled consensus.
4. Keep experiment pins stable unless an upstream lab is re-run; record a separate `latest_observed` field for current ecosystem state.
5. Every research claim added to a chapter must change an invariant, failure model, metric, design boundary or open problem; otherwise it belongs in this audit/appendix rather than the core narrative.

## Major 2026 research changes absorbed

- Planning: APB separates planning diagnosis from end-to-end execution and adds broken-tool, extraneous-tool and unsolvable-task settings.
- Long-horizon execution: external task state, checkpointing and independent auditing are treated as first-class runtime concerns.
- Memory: the target shifts from recall to write/update/forget/provenance/deletion fidelity; Memora, LongMemEval-V2 and deployment-time memorization are reflected in Chapter 11 and Appendix E.
- Effect semantics: Semantic Transactions/Cordon motivates task-level containment, staged effect release and explicit `UNKNOWN` outcomes.
- Agentic RL: ToolVerse illustrates the shift toward large tool environments, long horizons and process/turn-aware credit assignment.
- Protocols and identity: MCP 2026-07-28 stateless core, A2A lifecycle hardening, NIST agent identity/standards are separated into interoperability vs authorization/trust.
- Multi-agent: coordination cost, ownership, resource contention and deadlock are treated as systems problems rather than persona design.
- Evaluation: trajectory/environment/artifact/cost/risk evaluation and benchmark validity are promoted above final-answer-only scores.
- Security: prompt injection is treated as ingress risk; identity/policy/capability/approval/sandbox define the actual damage boundary.
- Research agents: machine-checkable artifacts (e.g. formal proof) are used to explain why strong verifiers change the feasible autonomy boundary.

## Near-cutoff evidence

The final refresh includes sources published or updated close to 2026-09-11: OpenAI Agents SDK 0.22.2 and Codex CLI 0.154.0 (Sep 9), the A2A Python source tag 1.1.4 (Sep 8; PyPI distribution 1.1.2), Google ADK 2.9.0 and Microsoft Agent Framework 1.18.0 (Sep 10), Anthropic multi-agent research (Aug 13), automated alignment researchers (Aug 28), formalized Fermat proof (Sep 4), cybersecurity incident assessment (Sep 9), and OpenAI Data agent/Financial Services releases (Sep 10).

## Boundaries

v1.0 does not claim that every external SDK or benchmark was executed in the release environment. Core repository labs/tests/examples are executable and separately validated. External papers/products/standards are evidence sources and remain clearly separated from executable course dependencies.
