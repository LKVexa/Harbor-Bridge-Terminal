"""INV-38-C037 — Atomic prepare/validate/stage/commit config transactions."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

class TxnError(RuntimeError):
    code = "PK_BYPASS_CONFIG_TXN_FAILED"
class TxnConflict(TxnError):
    code = "PK_BYPASS_CONFIG_CONFLICT"

@dataclass
class ConfigStore:
    generation: int = 0
    active: dict = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)

    def apply(self, candidate: dict, *, validate: Callable[[dict], None],
              expected_generation: int) -> int:
        # Optimistic concurrency (C037-T07)
        if expected_generation != self.generation:
            raise TxnConflict(f"expected gen {expected_generation}, have {self.generation}")
        prior = dict(self.active)
        prior_gen = self.generation
        try:
            validate(candidate)                 # validate ENTIRE candidate before commit
        except Exception as exc:                # commit-failure -> restore prior (C037-T06)
            self.active = prior
            self.generation = prior_gen
            raise TxnError(f"validation failed, rolled back: {exc}") from exc
        # atomic swap
        self.active = dict(candidate)
        self.generation += 1
        self.history.append({"generation": self.generation, "config": dict(candidate)})
        return self.generation
