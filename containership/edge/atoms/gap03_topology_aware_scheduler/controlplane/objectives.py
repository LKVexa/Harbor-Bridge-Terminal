"""MC-029 - Multi-objective score composition (formula gap03-score/2).

Objective vector (each normalised to an integer 0..1000, lower is better):
  locality (static class, or measured refinement), gravity (GAP-14),
  demand (PLN-05 advisory: 0 unless the tenant has pending demand AND the
  candidate's domain is already used by that tenant), spread (0/1000).
Composite = sum(weight_ppm * value) // 1000 (integer; deterministic).
Hard gates (fairness, entitlement, physical capacity, hardware predicates,
hard residency, freeze) are evaluated *before* and *outside* the sum.
Missing-signal policy: latency->static fallback, gravity->neutral 0,
demand->neutral 0.  Ordering: strict spreading is lexicographic (a used failure domain always sorts
behind an unused one - v4.2.0 semantics preserved), then (composite, locality, node id).
"""
from __future__ import annotations

from dataclasses import dataclass

FORMULA_VERSION = "gap03-score/2"
MISSING_POLICY = {"latency": "static_fallback", "gravity": "neutral", "demand": "neutral"}
MAX_WEIGHT = 10_000


@dataclass(frozen=True)
class Composite:
    node: str
    total: int
    components: tuple
    weights: tuple
    feasible: bool
    hard_failures: tuple


def normalise_locality(cost_milli: int) -> int:
    return min(1000, cost_milli * 1000 // 101_000)


def validate_weights(w: dict) -> dict:
    out = {}
    for k in ("locality", "gravity", "demand", "spread"):
        v = w.get(k, 0)
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= MAX_WEIGHT:
            raise ValueError(f"weight {k} must be an integer in [0, {MAX_WEIGHT}]")
        out[k] = v
    if sum(out.values()) == 0:
        raise ValueError("all weights zero")
    return out


def compose(nodes, *, weights: dict, locality, gravity=None, demand=None, spread=None, hard=None) -> list[Composite]:
    """locality/gravity/demand/spread: callables node -> int 0..1000 (or None when missing);
    hard: callable node -> tuple of failure reasons (empty = feasible)."""
    w = validate_weights(weights)
    out = []
    for n in nodes:
        fails = tuple(hard(n)) if hard else ()
        comp = {"locality": locality(n), "gravity": gravity(n) if gravity else None,
                "demand": demand(n) if demand else None, "spread": spread(n) if spread else 0}
        for k in ("gravity", "demand"):
            if comp[k] is None:
                comp[k] = 0  # neutral
        for k, v in comp.items():
            if not isinstance(v, int) or not 0 <= v <= 1000:
                raise ValueError(f"component {k} for {n} out of range")
        total = sum(w[k] * comp[k] for k in w) // 1000
        out.append(Composite(n, total, tuple(sorted(comp.items())), tuple(sorted(w.items())), not fails, fails))
    feasible = sorted((c for c in out if c.feasible),
                      key=lambda c: (dict(c.components)["spread"], c.total, dict(c.components)["locality"], c.node))
    infeasible = sorted((c for c in out if not c.feasible), key=lambda c: c.node)
    return feasible + infeasible


def sensitivity(nodes, *, weights, locality, gravity, perturb: int = 5) -> dict:
    """Fraction of +-perturb unit input perturbations that change the top choice."""
    base = compose(nodes, weights=weights, locality=locality, gravity=gravity)
    top = base[0].node if base else None
    flips = trials = 0
    for n in nodes:
        for d in (-perturb, perturb):
            def g2(x, n=n, d=d):
                v = gravity(x)
                return max(0, min(1000, v + d)) if x == n and v is not None else v
            r = compose(nodes, weights=weights, locality=locality, gravity=g2)
            trials += 1
            flips += (r[0].node != top) if r else 0
    return {"trials": trials, "top_changes": flips, "instability": round(flips / trials, 4) if trials else 0.0}
