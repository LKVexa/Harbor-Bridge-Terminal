"""Components 15 and 16 - workload-class-aware shedding and the
constraint-precedence engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import floor

# ------------------------------------------------------------ 15 shedding
DEFAULT_CLASS_ORDER = ("best-effort", "batch", "standard", "latency-critical", "system")


@dataclass(frozen=True)
class SheddingPolicy:
    """Classes earlier in ``order`` are shed first. ``protected_share`` reserves
    part of the ceiling for a class. No class may exceed the node ceiling and
    every class drops to zero under emergency exclusion (no bypass)."""
    order: tuple[str, ...] = DEFAULT_CLASS_ORDER
    protected_share: dict = field(default_factory=lambda: {"system": 0.10})

    def allocate(self, ceiling: int, demand: dict[str, int], excluded: bool) -> dict[str, int]:
        unknown = set(demand) - set(self.order)
        if unknown:
            raise ValueError(f"unknown workload classes {sorted(unknown)}")
        if excluded or ceiling <= 0:
            return {c: 0 for c in demand}
        alloc = {c: 0 for c in demand}
        remaining = ceiling
        # protected shares first (floor - never round up)
        for c in reversed(self.order):
            if c in demand:
                grant = min(demand[c], floor(ceiling * self.protected_share.get(c, 0.0)), remaining)
                alloc[c] += grant
                remaining -= grant
        # then highest priority first; lowest priority is shed first
        for c in reversed(self.order):
            if c in demand and remaining > 0:
                grant = min(demand[c] - alloc[c], remaining)
                alloc[c] += grant
                remaining -= grant
        if sum(alloc.values()) > ceiling:  # defensive, survives python -O
            raise RuntimeError("allocation exceeded ceiling")
        return alloc

    def shed_order(self) -> tuple[str, ...]:
        return self.order


# ------------------------------------------------------------ 16 precedence
PRECEDENCE = (
    "thermal-safety",        # physical safety always wins
    "emergency-operator",    # authenticated operator restriction (can only restrict)
    "security",
    "residency",
    "maintenance",
    "slo",
    "cost",
)


@dataclass(frozen=True)
class Constraint:
    source: str
    max_fraction: float        # upper bound on capacity fraction this source allows
    reason: str
    wants_increase: bool = False  # e.g. SLO pressure asking for more capacity


def resolve(constraints: list[Constraint]) -> tuple[float, list[dict]]:
    """Return (effective_fraction, explanation).

    Every constraint is an upper bound; the result is the minimum. Sources may
    request *more* capacity (SLO, cost), but a request can never raise the
    result above any higher-precedence bound. Unknown sources are rejected."""
    rank = {s: i for i, s in enumerate(PRECEDENCE)}
    for c in constraints:
        if c.source not in rank:
            raise ValueError(f"unknown constraint source {c.source}")
        if not 0.0 <= c.max_fraction <= 1.0:
            raise ValueError("max_fraction must be within [0,1]")
    ordered = sorted(constraints, key=lambda c: rank[c.source])
    effective = 1.0
    trail = []
    for c in ordered:
        before = effective
        effective = min(effective, c.max_fraction)
        trail.append({"rank": rank[c.source], "source": c.source, "bound": c.max_fraction,
                      "applied": effective < before, "ignored_increase": c.wants_increase and c.max_fraction > before,
                      "reason": c.reason})
    return effective, trail
