# OpenAI Agents SDK integration

Purpose: compare AgentLab's explicit loop with the SDK's Agent/Runner/Tool/Session/Tracing primitives.

Prerequisites: Python 3.11+, network, `OPENAI_API_KEY` or supported OpenAI auth.

```bash
pip install -e '.[openai]'
export OPENAI_API_KEY=...
python integrations/openai_agents/demo.py
```

The official SDK is a higher-level runtime around model calls. Record model name, date, tool schema, trace ID and output because provider behavior changes over time.
