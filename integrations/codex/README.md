# OpenAI Codex CLI source and sandbox lab

Codex CLI is open source and runs locally. Use it to study a mature coding-agent implementation, especially sandbox policy, approval policy, command segmentation, protocol events and workspace trust.

Install using an official method, for example:
```bash
npm install -g @openai/codex
codex
```

Safe lab: run inside the provided `production/coding_ops/fixture_repo`, first read-only, then workspace-write with approvals. Never use the dangerous sandbox-bypass option in the course lab. For source reading, inspect `openai/codex`'s `codex-rs/core`, `protocol`, sandbox and exec-policy code at the commit recorded in your report.
