# Hugging Face smolagents lab

smolagents keeps the agent loop small and offers both CodeAgent and ToolCallingAgent. It is useful for comparing code-as-action with JSON tool calls and for discussing sandboxed code execution.

```bash
python -m venv .venv-smol && source .venv-smol/bin/activate
pip install 'smolagents[toolkit]'
```

Use a local or explicitly configured model provider and record the provider/model in the experiment report.
