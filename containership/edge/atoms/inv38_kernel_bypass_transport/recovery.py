"""INV-38-C057 — Crash-consistency / restart generation-epoch semantics (model)."""
from __future__ import annotations
from dataclasses import dataclass, field

class StaleIncarnation(RuntimeError):
    code = "PK_BYPASS_STALE_INCARNATION"

@dataclass
class Incarnation:
    """A restart bumps the epoch; descriptors/keys from a prior epoch are invalid."""
    epoch: int = 0
    def restart(self) -> int:
        self.epoch += 1
        return self.epoch
    def validate(self, presented_epoch: int) -> None:
        if presented_epoch != self.epoch:
            raise StaleIncarnation(f"epoch {presented_epoch} != current {self.epoch}")

def classify_inflight(state: str) -> str:
    """After crash, classify an in-flight op (C057-T06)."""
    return {
        "completed": "COMPLETED",
        "posted_no_completion": "UNKNOWN_REPLAYABLE",
        "validated_not_posted": "REJECTED",
    }.get(state, "CALLER_RECONCILE")

def reconstructible(state_class: str) -> bool:
    # MR keys / queue handles never survive a device reset; must be recreated.
    return state_class in {"ephemeral", "reconstructible"}
