from dataclasses import dataclass


@dataclass
class Observation:
    modality: str
    payload: str
    ts: float


events = [
    Observation("text", "open settings", 1.0),
    Observation("vision", "button:save@440,212", 1.2),
    Observation("audio", "confirmation tone", 1.5),
]
for e in events:
    print({"observe": e.modality, "payload": e.payload, "action": "parse->policy->act"})
