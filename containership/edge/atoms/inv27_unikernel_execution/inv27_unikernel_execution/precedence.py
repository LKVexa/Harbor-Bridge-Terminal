"""Security / residency / SLO / cost precedence (MC-020; C019) and disconnected-mode rules (MC-019; C018).

``resolve`` takes candidate actions, each scored on the four axes, and returns the chosen one with
the reason.  Order is strict and lexicographic: an action that violates a security invariant is never
chosen whatever it saves; residency beats SLO; SLO beats cost.  No weights, so no trade that lets
cost buy back security.

``disconnected_decision`` encodes the intermittent-network rules: a site that cannot refresh its
trust root keeps running *already admitted* instances, but admits nothing new once the cached trust
root is older than its max age (fail closed for admission, fail static for execution).
"""
from __future__ import annotations

from dataclasses import dataclass

ORDER = ("security", "residency", "slo", "cost")


@dataclass(frozen=True)
class Candidate:
    name: str
    security_ok: bool
    residency_ok: bool
    slo_ok: bool
    cost: float


def resolve(cands: list[Candidate]) -> tuple[Candidate | None, str]:
    if not cands:
        return None, "no candidates"
    pool = [c for c in cands if c.security_ok]
    if not pool:
        return None, "every candidate violates a security invariant; refuse"
    res = [c for c in pool if c.residency_ok]
    if not res:
        return None, "no candidate satisfies residency; refuse rather than move data"
    slo = [c for c in res if c.slo_ok] or res
    why = "cheapest among SLO-meeting, resident, secure candidates" if any(c.slo_ok for c in res) else \
        "no candidate meets the SLO; cheapest resident secure candidate chosen and flagged degraded"
    best = min(slo, key=lambda c: (c.cost, c.name))
    return best, why


def disconnected_decision(*, trust_age_s: float, max_age_s: float, action: str) -> tuple[bool, str]:
    if action in ("stop", "quarantine", "status"):
        return True, "always permitted offline (reduces exposure)"
    if action == "keep_running":
        return True, "fail static: admitted instances keep their verified seal"
    if action == "admit":
        if trust_age_s > max_age_s:
            return False, "UK_TRUST_UNAVAILABLE: cached trust root too old; admission fails closed"
        return True, "cached trust root within max age"
    return False, f"unknown action {action!r}"
