# MCP v2 integration

The official Python SDK v2 implements the 2026-07-28 MCP specification and supports earlier revisions. The experiment uses a local stdio server so no cloud account is required, but the `mcp` package must be installed.

```bash
python -m venv .venv-mcp && source .venv-mcp/bin/activate
pip install 'mcp>=2,<3'
python integrations/mcp/server.py   # see book for client/inspector workflow
```
