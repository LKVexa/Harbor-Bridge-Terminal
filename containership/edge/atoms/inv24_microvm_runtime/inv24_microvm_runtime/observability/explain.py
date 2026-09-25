"""Decision/explain records linking outcomes to policy, config and release (MC-044)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..security.secrets import redact


@dataclass
class DecisionRecord:
    decision: str            # e.g. "admission"
    outcome: str             # "accepted" | "rejected"
    code: str | None
    reasons: list[str]
    inputs: dict
    policy: dict             # config revision/digest, policy ids
    release: dict            # runtime version, firecracker version, manifest version
    topology: dict = field(default_factory=dict)  # node, site, environment
    trace_id: str | None = None
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {"schema": "PK_MICROVM_DECISION/1", "decision": self.decision, "outcome": self.outcome,
                "code": self.code, "reasons": self.reasons[:20], "inputs": redact(self.inputs),
                "policy": self.policy, "release": self.release, "topology": self.topology,
                "trace_id": self.trace_id, "ts": round(self.ts, 3)}
