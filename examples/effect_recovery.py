from pathlib import Path
from agentlab.journal import EffectJournal
from agentlab.events import Event

p = Path(".agentlab/recovery/journal.jsonl")
p.parent.mkdir(parents=True, exist_ok=True)
p.unlink(missing_ok=True)
j = EffectJournal(p)
j.append(Event("tool_intent", "r1", 1, {"tool": "charge", "idempotency_key": "k1"}))
j.append(Event("tool_result", "r1", 1, {"status": "UNKNOWN"}))
print("journal_valid", j.verify())
print("reconcile_action", "query external system by idempotency_key=k1; never blind retry UNKNOWN")
