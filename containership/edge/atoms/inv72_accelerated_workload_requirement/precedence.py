"""Precedence when INV-72 requirements conflict (C019).

Order, highest first - a lower rule can never override a higher one:

1. ``security``  - tenant isolation, authentication, integrity of inventory (never traded away)
2. ``residency`` - placement constraints on where a workload may run (site/region/node allow-lists)
3. ``correctness`` - strict class and minimum-memory fit ("never place 80 GB on 40 GB")
4. ``slo``       - latency/availability targets (e.g. prefer interconnect, prefer fresh inventory)
5. ``cost``      - packing density, preferring cheaper classes, partition sharing for utilisation

``resolve`` takes the candidate actions each concern proposes and returns the one chosen, plus the
reason, so every conflict decision is explainable.  Used by the service when a cost/SLO preference
(e.g. share a partition to save a device) meets an isolation or residency rule.
"""
from __future__ import annotations

from dataclasses import dataclass

ORDER = ("security", "residency", "correctness", "slo", "cost")
RANK = {k: i for i, k in enumerate(ORDER)}


@dataclass(frozen=True)
class Claim:
    concern: str
    action: str      # "allow" | "deny" | a named preference
    reason: str


def resolve(claims: list[Claim]) -> dict:
    if not claims:
        return {"action": "deny", "by": None, "reason": "no claims: fail closed", "overridden": []}
    for c in claims:
        if c.concern not in RANK:
            return {"action": "deny", "by": c.concern, "reason": f"unknown concern {c.concern!r}: fail closed",
                    "overridden": []}
    # a deny from a concern outranks any allow/preference from an equal-or-lower concern
    ordered = sorted(claims, key=lambda c: (RANK[c.concern], 0 if c.action == "deny" else 1))
    winner = ordered[0]
    return {"action": winner.action, "by": winner.concern, "reason": winner.reason,
            "overridden": [f"{c.concern}:{c.action}" for c in ordered[1:] if c.action != winner.action]}


def residency_allows(allowed_nodes: frozenset | None, node: str) -> bool:
    return allowed_nodes is None or node in allowed_nodes
