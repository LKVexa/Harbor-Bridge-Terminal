"""Canary / staged rollout evaluation with automated rollback (GAP-033).

A rollout moves through stages (default 1% -> 10% -> 50% -> 100%). At each
stage the canary cohort's signals are compared with the baseline cohort; any
breached criterion triggers ``rollback`` through the ConfigStore (config
rollouts) or returns a ``rollback`` verdict for the deployment system (binary
rollouts). Criteria are explicit, versioned and recorded with the verdict.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

STAGES = (1, 10, 50, 100)


@dataclass(frozen=True)
class Criteria:
    max_error_rate_delta: float = 0.005        # absolute (0.5 percentage points)
    max_p99_ratio: float = 1.25                # canary p99 / baseline p99
    max_refusal_rate_delta: float = 0.01       # unexpected policy/isolation refusals
    min_requests: int = 500                    # evidence floor per stage
    zero_tolerance_codes: tuple = ("PK_CHAIN_CROSS_TENANT_ALLOWED", "PK_CHAIN_INTERNAL")
    version: str = "ROLLOUT_CRITERIA/1"


@dataclass(frozen=True)
class CohortSignals:
    requests: int
    errors: int
    refusals: int
    p99_us: float
    codes: dict = field(default_factory=dict)

    @property
    def error_rate(self) -> float:
        return self.errors / self.requests if self.requests else 0.0

    @property
    def refusal_rate(self) -> float:
        return self.refusals / self.requests if self.requests else 0.0


def evaluate(stage: int, canary: CohortSignals, baseline: CohortSignals, c: Criteria = Criteria()) -> dict:
    reasons = []
    if canary.requests < c.min_requests:
        return {"stage": stage, "verdict": "hold", "reasons": ["insufficient_evidence"], "criteria": asdict(c)}
    if canary.error_rate - baseline.error_rate > c.max_error_rate_delta:
        reasons.append("error_rate")
    if baseline.p99_us and canary.p99_us / baseline.p99_us > c.max_p99_ratio:
        reasons.append("latency_p99")
    if canary.refusal_rate - baseline.refusal_rate > c.max_refusal_rate_delta:
        reasons.append("refusal_rate")
    if any(canary.codes.get(k) for k in c.zero_tolerance_codes):
        reasons.append("zero_tolerance_code")
    if reasons:
        return {"stage": stage, "verdict": "rollback", "reasons": reasons, "criteria": asdict(c)}
    nxt = next((s for s in STAGES if s > stage), None)
    return {"stage": stage, "verdict": "promote" if nxt else "complete", "next_stage": nxt,
            "reasons": [], "criteria": asdict(c)}


def apply_verdict(verdict: dict, store=None, *, author: str = "rollout-controller") -> Optional[object]:
    """Automated rollback for configuration rollouts."""
    if verdict["verdict"] == "rollback" and store is not None:
        return store.rollback(author=author)
    return None
