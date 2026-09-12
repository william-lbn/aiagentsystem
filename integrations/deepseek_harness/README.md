# DeepSeek Harness / Cordis source-reading lab

DeepSeek Harness is currently a developer preview and explicitly warns about compatibility-breaking changes. It is valuable here because its architecture makes the harness itself composable: tools, LLM adapters, file access and even the agent loop can be plugins in Cordis.

Prerequisites: Node.js, pnpm; real model usage may require provider credentials.

```bash
git clone https://github.com/deepseek-ai/deepseek-harness.git
cd deepseek-harness
pnpm install
pnpm run build
pnpm dsh web
```

Required reading order: root README -> docs/cordis-tutorial -> examples/headless-agent -> examples/jsonrpc-agent -> a plugin's cordis.yml. Record the exact commit used in your lab report.
