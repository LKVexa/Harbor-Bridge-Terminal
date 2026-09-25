"""Component 60 - canary / staged rollout with health gates and rollback (PK_DYN_ROLLOUT/1).

All execution targets a ``SimFleet`` double (no real deployer exists): each
member has id, site, version and a health function.  The algorithm is real:

* ``select_canary``: deterministic (sha256 of salt+id) ordering, at least one
  member per site when the cohort size allows, never more than ``max_fraction``.
* ``STAGES``: cumulative fractions 0.01 -> 0.10 -> 0.50 -> 1.00 (cohort >= 1).
* health gate: error_rate <= threshold AND pool invariants hold for every
  upgraded member; evaluated after each stage.
* rollback: automatic on gate failure, or manual via ``abort``; restores the
  previous version on every touched member, then ``verify_rollback`` checks all
  members are on the previous version and healthy.  Every action is appended to
  the audit log (``production/audit.py``).
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Callable

STAGES = (0.01, 0.10, 0.50, 1.00)


@dataclass
class Member:
    id: str
    site: str
    version: str
    metrics: dict = field(default_factory=dict)


class SimFleet:
    """Test double for a real deployer; ``health`` maps (member, version) -> metrics."""

    def __init__(self, members: list[Member], health: Callable[[Member, str], dict]) -> None:
        self.members = {m.id: m for m in members}
        self._health = health

    def deploy(self, member_id: str, version: str) -> None:
        m = self.members[member_id]
        m.version = version
        m.metrics = self._health(m, version)


def _rank(salt: str, mid: str) -> str:
    return hashlib.sha256(f"{salt}:{mid}".encode()).hexdigest()


def select_canary(members: list[Member], fraction: float, *, salt: str, max_fraction: float = 0.1) -> list[str]:
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    n = max(1, math.ceil(len(members) * min(fraction, max_fraction)))
    ordered = sorted(members, key=lambda m: _rank(salt, m.id))
    chosen, sites = [], set()
    for m in ordered:              # one per site first
        if len(chosen) < n and m.site not in sites:
            chosen.append(m.id)
            sites.add(m.site)
    for m in ordered:
        if len(chosen) < n and m.id not in chosen:
            chosen.append(m.id)
    return chosen


def stage_plan(members: list[Member], *, salt: str) -> list[list[str]]:
    ordered = [m.id for m in sorted(members, key=lambda m: _rank(salt, m.id))]
    canary = select_canary(members, STAGES[0], salt=salt)
    rest = [i for i in ordered if i not in canary]
    order = canary + rest
    plan, done = [], 0
    for f in STAGES:
        upto = max(len(canary), math.ceil(len(order) * f))
        plan.append(order[done:upto])
        done = upto
    return [s for s in plan if s]


def gate(metrics: list[dict], *, max_error_rate: float = 0.01) -> tuple[bool, list[str]]:
    reasons = []
    for m in metrics:
        if m.get("error_rate", 1.0) > max_error_rate:
            reasons.append(f"error_rate {m.get('error_rate')} > {max_error_rate}")
        if not m.get("invariants_ok", False):
            reasons.append("pool invariants failed")
    return not reasons, reasons


@dataclass
class RolloutResult:
    status: str            # COMPLETED | ROLLED_BACK
    stages_completed: int
    touched: list
    reasons: list
    verified: bool | None = None


def rollout(fleet: SimFleet, new_version: str, *, salt: str, audit=None, abort: Callable[[int], bool] | None = None,
            max_error_rate: float = 0.01) -> RolloutResult:
    prev = {mid: m.version for mid, m in fleet.members.items()}
    plan = stage_plan(list(fleet.members.values()), salt=salt)
    touched: list[str] = []

    def log(action, outcome, **d):
        if audit is not None:
            audit.append("rollout-controller", action, f"fleet:{new_version}", outcome, d)

    for i, stage in enumerate(plan):
        for mid in stage:
            fleet.deploy(mid, new_version)
            touched.append(mid)
        ok, reasons = gate([fleet.members[m].metrics for m in touched], max_error_rate=max_error_rate)
        manual = abort(i) if abort else False
        log("stage", "SUCCESS" if ok and not manual else "TERMINAL_FAILURE", stage=i, members=len(stage))
        if not ok or manual:
            if manual:
                reasons = reasons + ["manual abort"]
            for mid in reversed(touched):
                fleet.deploy(mid, prev[mid])
            verified = verify_rollback(fleet, prev, max_error_rate=max_error_rate)
            log("rollback", "SUCCESS" if verified else "OPERATOR_REQUIRED", touched=len(touched))
            return RolloutResult("ROLLED_BACK", i, touched, reasons, verified)
    log("complete", "SUCCESS", members=len(touched))
    return RolloutResult("COMPLETED", len(plan), touched, [])


def verify_rollback(fleet: SimFleet, prev: dict, *, max_error_rate: float = 0.01) -> bool:
    if any(fleet.members[m].version != v for m, v in prev.items()):
        return False
    ok, _ = gate([m.metrics for m in fleet.members.values() if m.metrics], max_error_rate=max_error_rate)
    return ok
