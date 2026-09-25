"""MC-51 staged rollout of a configuration/policy revision with an automated health gate.

Stages widen the fraction of decisions served by the candidate revision.  At each stage
the gate compares candidate vs baseline refusal rate and p99 latency; a breach, or too few
samples to judge, stops the rollout and rolls back.  Insufficient evidence is never a pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

STAGES = (0.01, 0.05, 0.25, 0.5, 1.0)


@dataclass
class StageResult:
    fraction: float
    verdict: str        # PASS | FAIL | INSUFFICIENT
    reason: str


@dataclass
class Rollout:
    min_samples: int = 200
    max_refusal_delta: float = 0.02
    max_p99_ratio: float = 1.2
    history: list[StageResult] = field(default_factory=list)

    def gate(self, base: dict, cand: dict) -> tuple[str, str]:
        if cand["n"] < self.min_samples or base["n"] < self.min_samples:
            return "INSUFFICIENT", f"need >= {self.min_samples} samples per arm"
        d = cand["refusals"] / cand["n"] - base["refusals"] / base["n"]
        if d > self.max_refusal_delta:
            return "FAIL", f"refusal rate +{d:.3f} exceeds {self.max_refusal_delta}"
        if base["p99"] > 0 and cand["p99"] / base["p99"] > self.max_p99_ratio:
            return "FAIL", f"p99 ratio {cand['p99'] / base['p99']:.2f} exceeds {self.max_p99_ratio}"
        return "PASS", "within thresholds"

    def run(self, observe: Callable[[float], tuple[dict, dict]], promote: Callable[[], None],
            rollback: Callable[[], None]) -> str:
        for f in STAGES:
            base, cand = observe(f)
            v, why = self.gate(base, cand)
            self.history.append(StageResult(f, v, why))
            if v != "PASS":
                rollback(); return "ROLLED_BACK"
        promote(); return "PROMOTED"
