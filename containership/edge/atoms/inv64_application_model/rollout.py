"""Canary / staged rollout controller and rollback drill (MC-40; C092).

Stages (ops/ROLLOUT_POLICY.json is the source of truth; these are the defaults)::

    preprod -> canary-node -> canary-cohort (<=5% tenants) -> expanded (<=25%) -> full

* cohorts are chosen deterministically: SHA-256(rollout_id, target) ranked,
  so re-running a rollout picks the same targets and never all at once;
* the candidate (artifact digest + config digest) is fixed at start; a change
  requires a new rollout (``rollout.candidate_changed``);
* promotion requires every gate signal present and within threshold; a missing
  signal blocks promotion (``rollout.signal_missing``) unless an *emergency*
  policy with an approver is supplied;
* skipping stages is impossible through :meth:`promote`; ``emergency_full``
  requires an approver and is recorded as such;
* a threshold breach aborts and rolls back every target already on the
  candidate to the recorded known-good revision via the same ConfigStore
  mechanism used in production; every transition is appended to ``history``.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Callable, Mapping

from .errors import Inv64Error

DEFAULT_STAGES = (
    {"name": "preprod", "max_fraction": 0.0, "fixed": 1, "observe_s": 600, "auto_rollback": True},
    {"name": "canary-node", "max_fraction": 0.0, "fixed": 1, "observe_s": 1800, "auto_rollback": True},
    {"name": "canary-cohort", "max_fraction": 0.05, "fixed": 0, "observe_s": 3600, "auto_rollback": True},
    {"name": "expanded", "max_fraction": 0.25, "fixed": 0, "observe_s": 7200, "auto_rollback": True},
    {"name": "full", "max_fraction": 1.0, "fixed": 0, "observe_s": 0, "auto_rollback": False},
)
# signal -> (comparison, threshold)
DEFAULT_GATES: Mapping[str, tuple[str, float]] = {
    "validation_error_rate": ("<=", 0.01),
    "internal_error_rate": ("<=", 0.001),
    "p99_latency_ms": ("<=", 5.0),
    "readiness_ratio": (">=", 0.999),
    "dependency_error_rate": ("<=", 0.01),
    "auth_anomaly_rate": ("<=", 0.001),
    "saturation": ("<=", 0.8),
    "audit_integrity": (">=", 1.0),
}


@dataclass
class Rollout:
    rollout_id: str
    candidate: dict                 # {"artifact_digest", "config_digest"}
    targets: list[str]              # every node/site/tenant target in scope
    apply: Callable[[str], None]    # activate candidate on one target
    revert: Callable[[str], None]   # roll one target back to known-good
    stages: tuple = DEFAULT_STAGES
    gates: Mapping = field(default_factory=lambda: dict(DEFAULT_GATES))
    clock: Callable[[], float] = time.time
    stage_index: int = -1
    exposed: list = field(default_factory=list)
    history: list = field(default_factory=list)
    state: str = "pending"

    def _rank(self) -> list[str]:
        return sorted(self.targets, key=lambda t: hashlib.sha256(f"{self.rollout_id}\x00{t}".encode()).hexdigest())

    def _cohort_size(self, stage: dict) -> int:
        n = len(self.targets)
        return min(n, max(stage["fixed"], int(n * stage["max_fraction"]) or (1 if stage["max_fraction"] else 0)))

    def _log(self, event: str, **info) -> None:
        self.history.append({"ts": self.clock(), "rollout": self.rollout_id, "event": event,
                             "stage": self.stages[self.stage_index]["name"] if self.stage_index >= 0 else None,
                             "candidate": dict(self.candidate), "exposed": len(self.exposed), **info})

    def evaluate(self, signals: Mapping[str, float]) -> list[str]:
        breaches = []
        for name, (op, thr) in self.gates.items():
            if name not in signals or signals[name] is None:
                breaches.append(f"rollout.signal_missing:{name}")
                continue
            v = signals[name]
            if (op == "<=" and v > thr) or (op == ">=" and v < thr):
                breaches.append(f"rollout.threshold:{name}")
        return breaches

    def promote(self, signals: Mapping[str, float] | None, *, actor: str, candidate: dict | None = None) -> dict:
        if self.state in ("aborted", "complete"):
            raise Inv64Error("activation.state", details={"rollout": self.state})
        if candidate is not None and candidate != self.candidate:
            raise Inv64Error("activation.state", details={"reason": "rollout.candidate_changed"})
        if self.stage_index >= 0:
            breaches = self.evaluate(signals or {})
            if breaches:
                return self.abort(actor=actor, reasons=breaches)
        if self.stage_index + 1 >= len(self.stages):
            self.state = "complete"
            self._log("complete", actor=actor)
            return {"state": self.state}
        self.stage_index += 1
        stage = self.stages[self.stage_index]
        want = self._cohort_size(stage) if stage["name"] != "full" else len(self.targets)
        ranked = [t for t in self._rank() if t not in self.exposed]
        for t in ranked[: max(0, want - len(self.exposed))]:
            self.apply(t)
            self.exposed.append(t)
        self.state = "complete" if stage["name"] == "full" else "in_progress"
        self._log("promote", actor=actor, signals=dict(signals or {}))
        return {"state": self.state, "stage": stage["name"], "exposed": len(self.exposed)}

    def abort(self, *, actor: str, reasons: list[str]) -> dict:
        for t in reversed(self.exposed):
            self.revert(t)
        self._log("abort-rollback", actor=actor, reasons=reasons, reverted=len(self.exposed))
        self.exposed = []
        self.state = "aborted"
        return {"state": self.state, "reasons": reasons}

    def emergency_full(self, *, actor: str, approver: str, reason: str) -> dict:
        if not approver or approver == actor:
            raise Inv64Error("authz.denied", details={"reason": "emergency full rollout needs an independent approver"})
        for t in self._rank():
            if t not in self.exposed:
                self.apply(t)
                self.exposed.append(t)
        self.stage_index = len(self.stages) - 1
        self.state = "complete"
        self._log("emergency-full", actor=actor, approver=approver, reason=reason)
        return {"state": self.state}


def rollback_drill(make_store: Callable[[], object], *, candidate_effective: dict, known_good_effective: dict,
                   validator, clock=time.time) -> dict:
    """Exercise the production rollback path end to end and return machine-readable evidence."""
    store = make_store()
    t0 = clock()
    r1 = store.propose(known_good_effective, actor="drill-operator", release="drill", validator=validator)
    store.activate(r1, actor="drill-operator", expected_active=store.state["active"])
    r2 = store.propose(candidate_effective, actor="drill-operator", release="drill", validator=validator)
    auto = store.activate(r2, actor="drill-operator", expected_active=r1, health_probe=lambda eff: False)
    auto_ok = auto["result"] == "rolled_back" and store.state["active"] == r1
    # manual path: re-approve, activate healthy, then operator rollback
    store.reapprove(candidate_effective["digest"], approver="drill-approver")
    r3 = store.propose(candidate_effective, actor="drill-operator", release="drill", validator=validator)
    store.activate(r3, actor="drill-operator", expected_active=r1)
    manual = store.rollback(actor="drill-operator", reason="drill")
    manual_ok = manual["active"] == r1
    again = store.rollback(actor="drill-operator", reason="drill-idempotency", to=r1)
    return {"schema": "PK_APP_ROLLBACK_DRILL/1", "auto_rollback": auto_ok, "manual_rollback": manual_ok,
            "idempotent": again["result"] == "noop", "known_good": r1,
            "restored_digest": store.status()["active_digest"], "elapsed_s": round(clock() - t0, 6),
            "objective_s": 60, "result": "PASS" if (auto_ok and manual_ok and again["result"] == "noop") else "FAIL"}
