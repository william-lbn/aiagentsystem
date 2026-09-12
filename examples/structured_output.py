from dataclasses import dataclass, asdict
import json


@dataclass
class Ticket:
    severity: str
    service: str
    summary: str


raw = {"severity": "P1", "service": "payments", "summary": "checkout returns 500"}
t = Ticket(**raw)
print(json.dumps(asdict(t), ensure_ascii=False, indent=2))
