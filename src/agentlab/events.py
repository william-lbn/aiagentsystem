from __future__ import annotations
from dataclasses import dataclass, asdict
from time import time
from typing import Any


@dataclass(slots=True)
class Event:
    type: str
    run_id: str
    step: int
    data: dict[str, Any]
    ts: float = 0.0

    def __post_init__(self):
        if not self.ts:
            self.ts = time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
