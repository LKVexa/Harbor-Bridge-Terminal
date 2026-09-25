"""Constraint precedence engine and capacity/headroom predictor (MC-030, MC-048).

SPDX-License-Identifier: NOASSERTION

Each constraint returns ALLOW / DENY / UNKNOWN with a reason.  Evaluation
walks the configured precedence order; the first DENY wins, and any UNKNOWN on
a mandatory (safety) constraint fails closed.  The full trace is returned so
the explain surface (MC-055) can show every input and outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

CONSTRAINTS = ("security", "capacity", "residency", "slo", "cost")
MANDATORY = frozenset({"security", "capacity", "residency"})


@dataclass(frozen=True)
class Verdict:
    constraint: str
    decision: str      # ALLOW | DENY | UNKNOWN
    reason: str


@dataclass
class Decision:
    allowed: bool
    deciding: str | None
    trace: list[Verdict] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "deciding_constraint": self.deciding,
                "trace": [v.__dict__ for v in self.trace]}


Evaluator = Callable[[dict], Verdict]


def evaluate(order: list[str], evaluators: dict[str, Evaluator], ctx: dict) -> Decision:
    if sorted(order) != sorted(CONSTRAINTS):
        raise ValueError("precedence order must list every constraint once")
    trace = []
    for name in order:
        ev = evaluators.get(name)
        v = ev(ctx) if ev else Verdict(name, "UNKNOWN", "no evaluator configured")
        trace.append(v)
        if v.decision == "DENY":
            return Decision(False, name, trace)
        if v.decision == "UNKNOWN" and name in MANDATORY:
            return Decision(False, name, trace)
    return Decision(True, None, trace)


def capacity_evaluator(ctx: dict) -> Verdict:
    need, free = ctx.get("add_vcpus"), ctx.get("host_free_vcpus")
    if need is None or free is None:
        return Verdict("capacity", "UNKNOWN", "capacity inputs missing")
    return (Verdict("capacity", "ALLOW", f"{need} <= free {free}") if need <= free
            else Verdict("capacity", "DENY", f"{need} > free {free}"))


def security_evaluator(ctx: dict) -> Verdict:
    s = ctx.get("security_state")
    if s is None:
        return Verdict("security", "UNKNOWN", "mandatory security state unknown")
    return Verdict("security", "ALLOW" if s == "ok" else "DENY", f"security_state={s}")


def residency_evaluator(ctx: dict) -> Verdict:
    allowed, site = ctx.get("allowed_sites"), ctx.get("site")
    if allowed is None or site is None:
        return Verdict("residency", "UNKNOWN", "residency inputs missing")
    return Verdict("residency", "ALLOW" if site in allowed else "DENY", f"site {site}")


def slo_evaluator(ctx: dict) -> Verdict:
    burn = ctx.get("error_budget_burn")
    if burn is None:
        return Verdict("slo", "ALLOW", "no SLO signal; advisory constraint")
    return Verdict("slo", "DENY" if burn > 1.0 else "ALLOW", f"burn={burn}")


def cost_evaluator(ctx: dict) -> Verdict:
    cap, cost = ctx.get("cost_cap"), ctx.get("cost_after")
    if cap is None or cost is None:
        return Verdict("cost", "ALLOW", "no cost cap; advisory constraint")
    return Verdict("cost", "DENY" if cost > cap else "ALLOW", f"{cost} vs cap {cap}")


DEFAULT_EVALUATORS: dict[str, Evaluator] = {
    "security": security_evaluator, "capacity": capacity_evaluator, "residency": residency_evaluator,
    "slo": slo_evaluator, "cost": cost_evaluator,
}


def headroom_forecast(samples: list[tuple[float, int]], capacity: int, horizon_s: float) -> dict:
    """Least-squares trend over (t, committed_vcpus) samples -> projected headroom and
    time-to-saturation.  Reports INSUFFICIENT_DATA below 3 samples instead of guessing."""
    if len(samples) < 3:
        return {"status": "INSUFFICIENT_DATA", "samples": len(samples)}
    n = len(samples)
    mt = sum(t for t, _ in samples) / n
    mu = sum(u for _, u in samples) / n
    var = sum((t - mt) ** 2 for t, _ in samples)
    slope = 0.0 if var == 0 else sum((t - mt) * (u - mu) for t, u in samples) / var
    t_last, u_last = samples[-1]
    projected = u_last + slope * horizon_s
    tts = None if slope <= 0 else max(0.0, (capacity - u_last) / slope)
    return {"status": "OK", "slope_vcpus_per_s": slope, "current_headroom": capacity - u_last,
            "projected_headroom": capacity - projected, "time_to_saturation_s": tts,
            "saturating_within_horizon": tts is not None and tts <= horizon_s}
