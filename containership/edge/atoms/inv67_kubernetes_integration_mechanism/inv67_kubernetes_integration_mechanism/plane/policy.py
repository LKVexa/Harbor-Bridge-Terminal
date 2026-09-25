"""Constraint-precedence policy (item 8).

Deterministic resolution when constraints conflict. Order (highest first):
security > tenancy/residency > safety (freeze/quarantine) > compatibility >
quota/capacity > SLO > cost > user placement preference. A lower-precedence
constraint can never override a refusal from a higher one; ties at one level
resolve to the *more restrictive* outcome.
"""
from __future__ import annotations

PRECEDENCE = ["security", "residency", "safety", "compatibility", "capacity", "slo", "cost", "preference"]


def resolve(verdicts: dict[str, str]) -> tuple[str, str]:
    """verdicts: level -> 'allow' | 'deny' | 'defer'. Returns (decision, deciding level).
    Unknown levels are refused (fail closed)."""
    unknown = set(verdicts) - set(PRECEDENCE)
    if unknown:
        return "deny", f"unknown-constraint:{sorted(unknown)[0]}"
    for level in PRECEDENCE:
        v = verdicts.get(level)
        if v == "deny":
            return "deny", level
        if v not in (None, "allow", "defer"):
            return "deny", f"invalid-verdict:{level}"
    for level in PRECEDENCE:
        if verdicts.get(level) == "defer":
            return "defer", level
    return "allow", "all"
