"""INV-38-C019 — Constraint precedence resolution.

Deterministic lattice: security > isolation > residency > correctness >
availability/SLO > performance > cost.  Given two competing constraints the
higher-priority one wins; the loser is recorded with a stable reason code so an
operator can tell policy rejection from resource failure.
"""
from __future__ import annotations

LATTICE = ["SECURITY", "ISOLATION", "RESIDENCY", "CORRECTNESS",
           "AVAILABILITY", "PERFORMANCE", "COST"]
_RANK = {name: i for i, name in enumerate(LATTICE)}


class PrecedenceError(ValueError):
    code = "PK_BYPASS_POLICY_REJECTED"


def resolve(constraints: list[str]) -> tuple[str, str]:
    """Return (winner, reason_code). Lower rank index wins."""
    unknown = [c for c in constraints if c not in _RANK]
    if unknown:
        raise PrecedenceError(f"unknown constraints {unknown}")
    if not constraints:
        raise PrecedenceError("no constraints supplied")
    winner = min(constraints, key=lambda c: _RANK[c])
    return winner, f"PK_BYPASS_PRECEDENCE_{winner}"


def security_beats_performance() -> bool:
    return _RANK["SECURITY"] < _RANK["PERFORMANCE"]
