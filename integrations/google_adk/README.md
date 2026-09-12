# Google ADK / Agents CLI integration

Current official materials provide ADK plus an Agents CLI lifecycle for scaffold, run, evaluate, deploy and observe. The course uses it as a production toolchain comparison rather than as the core runtime.

Prerequisites: Python 3.11+, uv, Node.js for skills setup, and Gemini/Google Cloud credentials for real model runs.

```bash
uvx google-agents-cli setup
agents-cli create demo-agent --prototype --yes
cd demo-agent
agents-cli install
agents-cli run "Count words in: Agent systems need evidence"
agents-cli eval run
```

Verify the generated project's eval dataset and trace artifacts; do not judge only the final answer.
