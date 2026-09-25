"""Component 50 - edge power/thermal model (``PK_DYN_POWER/1``).

Telemetry records (supplied by a caller; no real sensors are read here - BLOCKED on
node sensor access such as RAPL/IPMI/hwmon):

  power:   {"node": str, "ts": number, "watts": 0..5000, "source": "rapl|ipmi|pdu|sim"}
  thermal: {"node": str, "ts": number, "sensor": str, "celsius": -40..150}

Budget model: node draw = idle_w + busy * (peak_w - idle_w); site limit =
budget_w * (1 - margin).  Derating: per-node hottest reading T -> factor 1 below
``throttle_c``, linear to 0 at ``shutdown_c``; the pool is capped by clamping the
demand passed to ``Pool.tick`` (reducing ``Pool.max_nodes`` below the current size
raises ``PoolInvariantError`` in the model, so the cap is applied via demand).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .core import Inv08Error

SCHEMA = "PK_DYN_POWER/1"
POWER_SOURCES = ("rapl", "ipmi", "pdu", "sim")


def _bad(msg: str) -> Inv08Error:
    return Inv08Error("INV08.POWER.BAD_TELEMETRY", msg)


def _fin(v, lo, hi, name):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
        raise _bad(f"{name}={v!r} outside [{lo},{hi}]")
    return float(v)


def validate_power(rec: dict, *, now: float, max_age: float = 60.0) -> dict:
    if not isinstance(rec, dict) or not isinstance(rec.get("node"), str) or rec.get("source") not in POWER_SOURCES:
        raise _bad("malformed power sample")
    ts = _fin(rec.get("ts"), -1e18, 1e18, "ts")
    if now - ts > max_age or ts > now + 5:
        raise _bad(f"stale or future power sample for {rec['node']}")
    return {"node": rec["node"], "ts": ts, "watts": _fin(rec.get("watts"), 0, 5000, "watts"), "source": rec["source"]}


def validate_thermal(rec: dict, *, now: float, max_age: float = 60.0) -> dict:
    if not isinstance(rec, dict) or not isinstance(rec.get("node"), str) or not isinstance(rec.get("sensor"), str):
        raise _bad("malformed thermal sample")
    ts = _fin(rec.get("ts"), -1e18, 1e18, "ts")
    if now - ts > max_age or ts > now + 5:
        raise _bad(f"stale or future thermal sample for {rec['node']}")
    return {"node": rec["node"], "ts": ts, "sensor": rec["sensor"], "celsius": _fin(rec.get("celsius"), -40, 150, "celsius")}


@dataclass(frozen=True)
class PowerBudget:
    budget_w: float
    idle_w: float
    peak_w: float
    margin: float = 0.1

    def __post_init__(self) -> None:
        if not (0 < self.idle_w <= self.peak_w and self.budget_w > 0 and 0 <= self.margin < 1):
            raise Inv08Error("INV08.POWER.BAD_BUDGET", "need 0 < idle <= peak, budget > 0, 0 <= margin < 1")

    def node_draw(self, busy: bool) -> float:
        return self.peak_w if busy else self.idle_w

    def max_nodes(self) -> int:
        """Worst case: every node at peak."""
        return int(self.budget_w * (1 - self.margin) // self.peak_w)

    def check(self, nodes: dict) -> dict:
        draw = sum(self.node_draw(s["busy"]) for s in nodes.values())
        limit = self.budget_w * (1 - self.margin)
        return {"modelled_w": draw, "limit_w": limit, "over_budget": draw > limit}


@dataclass(frozen=True)
class ThermalPolicy:
    throttle_c: float = 80.0
    shutdown_c: float = 95.0

    def __post_init__(self) -> None:
        if not self.throttle_c < self.shutdown_c:
            raise Inv08Error("INV08.POWER.BAD_POLICY", "throttle_c must be < shutdown_c")

    def factor(self, celsius: float) -> float:
        if celsius <= self.throttle_c:
            return 1.0
        if celsius >= self.shutdown_c:
            return 0.0
        return 1.0 - (celsius - self.throttle_c) / (self.shutdown_c - self.throttle_c)


def derate(pool, budget: PowerBudget, thermal: ThermalPolicy, samples: list[dict], *, now: float) -> dict:
    """Return the capped node count and per-node actions from validated thermal samples.
    A node with no valid (fresh, in-range) sample fails safe to factor 0.5 -> DERATE.
    ``min_nodes`` is a hard floor and wins over the thermal cap; busy nodes are never
    reclaimed by the model, so SHED is advisory to the node drain path."""
    hottest: dict[str, float] = {}
    invalid: list[str] = []
    for s in samples:
        try:
            v = validate_thermal(s, now=now)
        except Inv08Error:
            invalid.append(s.get("node", "?") if isinstance(s, dict) else "?")
            continue
        hottest[v["node"]] = max(hottest.get(v["node"], -math.inf), v["celsius"])
    actions, effective = {}, 0.0
    for n in pool.nodes:
        if n in hottest:
            f = thermal.factor(hottest[n])
        else:
            f = 0.5  # no valid telemetry: conservative
        actions[n] = "NORMAL" if f == 1.0 else "SHED" if f == 0.0 else "DERATE"
        effective += f
    cap = min(pool.max_nodes, budget.max_nodes(), math.floor(effective) + (pool.max_nodes - len(pool.nodes)))
    return {"cap_nodes": max(pool.min_nodes, cap), "actions": actions, "invalid_samples": invalid}


def capped_tick(pool, now, demand, cap_nodes: int, **kw):
    """Apply a derating cap by clamping demand; never mutates pool limits."""
    return pool.tick(now, min(demand, cap_nodes * pool.per_node), **kw)


def energy_efficiency(power_samples: list[dict], work_units: float, *, now: float, interval_s: float) -> dict:
    """Joules per unit of served demand over one interval from supplied telemetry."""
    if work_units <= 0 or interval_s <= 0:
        raise Inv08Error("INV08.POWER.BAD_INPUT", "work and interval must be positive")
    per_node: dict[str, float] = {}
    for s in power_samples:
        v = validate_power(s, now=now)
        per_node[v["node"]] = v["watts"]  # latest wins
    joules = sum(per_node.values()) * interval_s
    return {"joules": joules, "joules_per_unit": joules / work_units, "nodes": len(per_node)}
