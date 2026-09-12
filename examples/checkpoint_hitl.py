from pathlib import Path
from agentlab import AgentRuntime, ModelDecision, ScriptedModel, ToolRegistry, tool
from agentlab.checkpoint import JsonCheckpointStore
from agentlab.journal import EffectJournal
from agentlab.security import PolicyEngine

base = Path(".agentlab/hitl")
base.mkdir(parents=True, exist_ok=True)


@tool("Delete a stale demo row", risk="high", idempotent=True)
def delete_demo(row_id: int):
    return {"deleted": row_id}


t = ToolRegistry()
t.register(delete_demo)
cp = JsonCheckpointStore(base / "checkpoint.json")
j = EffectJournal(base / "journal.jsonl")
model = ScriptedModel(
    [ModelDecision(tool="delete_demo", args={"row_id": 9}), ModelDecision(final="deleted after approval")]
)
r = AgentRuntime(model, t, checkpoint=cp, journal=j, policy=PolicyEngine(approval_tools={"delete_demo"}))
first = r.run("删除演示行 9")
print("first", first["status"], first["pending_approval"])
action_id = first["pending_approval"]["action_id"]
second = r.run("删除演示行 9", resume=True, run_id=first["run_id"], approval="approve", approval_action_id=action_id)
print("second", second["status"], second["answer"])
