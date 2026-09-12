# Pi coding agent lab

Pi (`@mariozechner/pi-coding-agent`) is deliberately minimal and extensible. Its sessions are JSONL trees with id/parentId, and it supports interactive, print/JSON, RPC and SDK modes. This makes it excellent for teaching session persistence and harness minimalism.

```bash
npm install -g @mariozechner/pi-coding-agent
pi --no-session                # ephemeral comparison
pi --name agentlab-session     # persisted session
pi --mode json -p "Inspect this repository and list test entry points"
```

Then inspect `~/.pi/agent/sessions/` and compare the session tree with AgentLab's checkpoint + journal design. Model/provider authentication is external and must be documented in the report.
