from agentlab.tracing import TraceRecorder
import time

tr = TraceRecorder()
with tr.span("agent.run", tenant="demo"):
    with tr.span("tool.search", query="mcp"):
        time.sleep(0.002)
print(tr.spans)
