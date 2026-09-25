"""Staged (canary) rollout controller with automatic rollback (INV-68 MC-34; C092).

A rollout moves a *configuration or release* through the stages declared in
``ops/ROLLOUT_POLICY.json`` (default: ``canary 1% -> 10% -> 50% -> 100%``).
At each stage the controller reads observed signals for the candidate and the
baseline and applies abort thresholds:

* error-rate delta (candidate - baseline) above ``max_error_rate_delta``;
* p99 latency ratio above ``max_p99_ratio``;
* efficiency ratio (hosts / placeable lower bound) above ``max_efficiency_ratio``;
* **any** memory-overcommit observation (``mem_overcommit_hosts > 0``) -- no budget;
* candidate readiness (``ready`` false) aborts;
* insufficient traffic (``min_requests``) holds the stage rather than promoting.

Abort -> :meth:`RolloutController.abort` rolls the configuration store back
(audited) and records the reason; the emergency path is ``freeze`` on the
service (``RUNBOOK.md`` section 6).  Decisions are pure functions of the signals,
so ``tools/drills.py`` rehearses them deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

DEFAULT_POLICY: Mapping[str, Any] = {
    "schema": "PK_PACK_ROLLOUT_POLICY/1",
    "stages": [{"name": "canary", "traffic": 0.01}, {"name": "early", "traffic": 0.10},
               {"name": "half", "traffic": 0.50}, {"name": "full", "traffic": 1.00}],
    "min_requests": 200,
    "max_error_rate_delta": 0.005,
    "max_p99_ratio": 1.25,
    "max_efficiency_ratio": 1.10,
}


def evaluate_stage(policy: Mapping[str, Any], candidate: Mapping[str, float],
                   baseline: Mapping[str, float]) -> tuple[str, list[str]]:
    """Return ``("promote" | "hold" | "abort", reasons)``."""
    reasons: list[str] = []
    if candidate.get("ready") is False:
        return "abort", ["candidate not ready (health/readiness failed)"]
    if candidate.get("mem_overcommit_hosts", 0) > 0:
        return "abort", ["memory overcommit observed (no error budget)"]
    if candidate.get("requests", 0) < policy["min_requests"]:
        return "hold", [f"only {candidate.get('requests', 0)} requests (< {policy['min_requests']})"]
    err_delta = candidate.get("error_rate", 0.0) - baseline.get("error_rate", 0.0)
    if err_delta > policy["max_error_rate_delta"]:
        reasons.append(f"error-rate delta {err_delta:.4f} > {policy['max_error_rate_delta']}")
    base_p99 = max(baseline.get("p99_ms", 0.0), 1e-9)
    if candidate.get("p99_ms", 0.0) / base_p99 > policy["max_p99_ratio"]:
        reasons.append(f"p99 ratio {candidate['p99_ms'] / base_p99:.2f} > {policy['max_p99_ratio']}")
    if candidate.get("efficiency_ratio", 1.0) > policy["max_efficiency_ratio"]:
        reasons.append(f"efficiency ratio {candidate['efficiency_ratio']:.3f} > {policy['max_efficiency_ratio']}")
    return ("abort", reasons) if reasons else ("promote", [])


@dataclass
class RolloutController:
    policy: Mapping[str, Any]
    store: Any = None           # ConfigStore, for automatic rollback
    actor: str = "rollout-controller"
    epoch: int = 1
    stage_index: int = 0
    state: str = "in_progress"  # in_progress | complete | aborted
    history: list = field(default_factory=list)

    @property
    def stage(self) -> Mapping[str, Any]:
        return self.policy["stages"][self.stage_index]

    def step(self, candidate: Mapping[str, float], baseline: Mapping[str, float]) -> str:
        if self.state != "in_progress":
            return self.state
        decision, reasons = evaluate_stage(self.policy, candidate, baseline)
        self.history.append({"stage": self.stage["name"], "decision": decision, "reasons": reasons})
        if decision == "abort":
            self.abort("; ".join(reasons))
        elif decision == "promote":
            if self.stage_index + 1 >= len(self.policy["stages"]):
                self.state = "complete"
            else:
                self.stage_index += 1
        return self.state

    def abort(self, reason: str) -> None:
        self.state = "aborted"
        if self.store is not None:
            self.store.rollback(actor=self.actor, epoch=self.epoch)
        self.history.append({"stage": self.stage["name"], "decision": "rolled_back", "reasons": [reason]})
