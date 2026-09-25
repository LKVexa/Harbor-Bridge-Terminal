"""Canary / staged rollout / rollback machinery (GAP04-C43).

Pure decision logic over fleet health snapshots (the ``health()`` documents of
each node), so it can be driven by any deployment system. Compatibility gates
come from ``COMPAT`` (which state-schema and contract versions each code
version reads/writes); promotion requires every canary node to be ready with
bounded denial/verification-failure rates for a bake period; any gate breach
yields an emergency ROLLBACK decision naming the last good version.
"""
from __future__ import annotations

from dataclasses import dataclass, field

COMPAT = {
    # code version -> (state schema versions readable, written, lease envelope versions, journal version)
    "4.2.0": ({None}, None, set(), None),
    "4.3.0": ({1}, 1, {"PK_SIGNED_LEASE/1"}, "PK_JOURNAL/1"),
}
STAGES = (("canary", 0.01), ("early", 0.10), ("half", 0.50), ("full", 1.0))


def compatible(from_v: str, to_v: str) -> tuple[bool, str]:
    if from_v not in COMPAT or to_v not in COMPAT:
        return False, "unknown version"
    f, t = COMPAT[from_v], COMPAT[to_v]
    if f[1] is not None and f[1] not in t[0]:
        return False, f"{to_v} cannot read state schema {f[1]} written by {from_v}"
    if f[1] is None and t[1] is not None:
        return True, "fresh-state upgrade: 4.2.0 had no durable state; nodes start clean"
    return True, "compatible"


@dataclass
class Gates:
    bake_s: int = 1800
    max_denial_ratio_ppm: int = 50_000
    max_verification_failures: int = 0
    require_ready: bool = True


@dataclass
class Rollout:
    from_version: str
    to_version: str
    gates: Gates = field(default_factory=Gates)
    stage: int = 0
    stage_started: int = 0
    history: list = field(default_factory=list)

    def __post_init__(self):
        ok, why = compatible(self.from_version, self.to_version)
        if not ok:
            raise ValueError(why)

    def evaluate(self, now: int, cohort: list[dict], denials: int = 0, decisions: int = 0,
                 verification_failures: int = 0) -> dict:
        reasons = []
        if not cohort:
            reasons.append("empty cohort")
        for h in cohort:
            if h.get("code_version") != self.to_version:
                reasons.append(f"{h.get('site')}: running {h.get('code_version')}")
            if self.gates.require_ready and not h.get("ready"):
                reasons.append(f"{h.get('site')}: not ready {h.get('not_ready_reasons')}")
            if h.get("quarantine"):
                reasons.append(f"{h.get('site')}: quarantined")
        total = denials + decisions
        if total and denials * 1_000_000 // total > self.gates.max_denial_ratio_ppm:
            reasons.append("denial ratio above gate")
        if verification_failures > self.gates.max_verification_failures:
            reasons.append("verification failures above gate")
        if reasons:
            d = {"action": "ROLLBACK", "to": self.from_version, "stage": STAGES[self.stage][0], "reasons": reasons}
        elif now - self.stage_started < self.gates.bake_s:
            d = {"action": "HOLD", "stage": STAGES[self.stage][0], "remaining_s": self.gates.bake_s - (now - self.stage_started)}
        elif self.stage + 1 < len(STAGES):
            self.stage += 1
            self.stage_started = now
            d = {"action": "PROMOTE", "stage": STAGES[self.stage][0], "fraction": STAGES[self.stage][1]}
        else:
            d = {"action": "COMPLETE", "stage": "full"}
        self.history.append({"at": now, **d})
        return d
