"""Component 49 - fleet-scale capacity model (``PK_DYN_CAPACITY/1``).

Inputs are explicit, versioned dicts; every probability comes from a seeded
``random.Random`` Monte Carlo so results are reproducible.

* ``ChurnModel``: per-hour demand as a bounded random walk plus Poisson burst
  arrivals, driven through the *real* ``model.Pool`` to count adds/reclaims.
* ``LatencyDistribution``: empirical provisioning/deprovisioning latency samples.
  ``source`` must be ``"measured"`` (with provenance) or ``"assumed"``; no measured
  provider data exists in this overlay, so shipped defaults are ``assumed`` and the
  sub-part is PARTIAL (BLOCKED on provider measurements).
* ``QuotaModel``: provider instance cap and create-rate limit (token bucket).
* ``saturation_probability``: P(required nodes > usable nodes) given demand
  distribution, per-node failure probability and quota.
* ``headroom_policy``: smallest ``max_nodes`` meeting a saturation target, plus
  headroom fraction (targets PROPOSED; approver UNASSIGNED).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from ..model import Pool
from .core import Inv08Error

SCHEMA = "PK_DYN_CAPACITY/1"
HEADROOM_TARGETS = {"max_saturation_probability": 0.01, "min_headroom_fraction": 0.15,
                    "status": "PROPOSED", "approver": "UNASSIGNED"}


def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 50:  # normal approximation keeps this O(1)
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


@dataclass
class ChurnModel:
    base_demand: float
    walk_sigma: float = 0.05          # relative per-hour drift
    burst_rate: float = 0.1           # bursts per hour
    burst_size: float = 0.5           # relative size of a burst
    busy_fraction: float = 0.5

    def __post_init__(self) -> None:
        for n in ("base_demand", "walk_sigma", "burst_rate", "burst_size", "busy_fraction"):
            v = getattr(self, n)
            if not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                raise Inv08Error("INV08.CAPACITY.BAD_INPUT", f"{n}={v!r}")
        if self.busy_fraction > 1:
            raise Inv08Error("INV08.CAPACITY.BAD_INPUT", "busy_fraction > 1")

    def demand_series(self, hours: int, rng: random.Random) -> list[float]:
        d, out = self.base_demand, []
        for _ in range(hours):
            d = max(0.0, d * (1 + rng.gauss(0, self.walk_sigma)))
            burst = _poisson(rng, self.burst_rate) * self.burst_size * self.base_demand
            out.append(d + burst)
        return out

    def simulate(self, pool: Pool, hours: int, rng: random.Random) -> dict:
        if not 0 < hours <= 100_000:
            raise Inv08Error("INV08.CAPACITY.BAD_INPUT", "hours out of range")
        added = reclaimed = peak = 0
        at_cap = 0
        for t, dem in enumerate(self.demand_series(hours, rng), 1):
            for n in pool.nodes:
                pool.set_busy(n, rng.random() < self.busy_fraction)
            r = pool.tick(t, dem)
            added += r["added"]
            reclaimed += len(r["reclaimed"])
            peak = max(peak, r["size"])
            at_cap += r["target"] == pool.max_nodes
        return {"hours": hours, "adds_per_hour": added / hours, "reclaims_per_hour": reclaimed / hours,
                "peak_nodes": peak, "hours_at_max": at_cap, "node_hours": pool.node_hours}


@dataclass
class LatencyDistribution:
    samples: list[float]
    source: str = "assumed"
    provenance: str | None = None

    def __post_init__(self) -> None:
        if self.source not in ("measured", "assumed"):
            raise Inv08Error("INV08.CAPACITY.BAD_INPUT", "source must be measured|assumed")
        if self.source == "measured" and not self.provenance:
            raise Inv08Error("INV08.CAPACITY.BAD_INPUT", "measured latency needs provenance")
        if not self.samples or any((not math.isfinite(s)) or s < 0 for s in self.samples):
            raise Inv08Error("INV08.CAPACITY.BAD_INPUT", "latency samples must be finite and >= 0")
        self._s = sorted(self.samples)

    def quantile(self, q: float) -> float:
        return self._s[min(len(self._s) - 1, max(0, math.ceil(q * len(self._s)) - 1))]

    def sample(self, rng: random.Random) -> float:
        return rng.choice(self._s)


ASSUMED_PROVISION = LatencyDistribution([45, 60, 75, 90, 120, 180, 300], "assumed")   # seconds, not measured
ASSUMED_DEPROVISION = LatencyDistribution([5, 10, 15, 30, 60], "assumed")


@dataclass
class QuotaModel:
    max_instances: int
    creates_per_minute: float
    _tokens: float = field(default=-1.0, repr=False)
    _last: float | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.max_instances < 0 or self.creates_per_minute <= 0:
            raise Inv08Error("INV08.CAPACITY.BAD_INPUT", "quota must be non-negative / rate positive")
        self._tokens = self.creates_per_minute

    def admit(self, current: int, requested: int, now_minutes: float) -> dict:
        """How many of ``requested`` creates the provider would accept now."""
        if requested < 0 or current < 0:
            raise Inv08Error("INV08.CAPACITY.BAD_INPUT", "negative request")
        if self._last is not None:
            if now_minutes < self._last:
                raise Inv08Error("INV08.CAPACITY.CLOCK_REGRESSION", "time went backwards")
            self._tokens = min(self.creates_per_minute,
                               self._tokens + (now_minutes - self._last) * self.creates_per_minute)
        self._last = now_minutes
        room = max(0, self.max_instances - current)
        ok = min(requested, room, int(self._tokens))
        self._tokens -= ok
        return {"admitted": ok, "quota_denied": max(0, requested - room),
                "rate_limited": requested - ok - max(0, requested - room)}


def saturation_probability(*, max_nodes: int, per_node: int, demand_mean: float, demand_sd: float,
                           node_failure_p: float, quota: int | None = None, trials: int = 5000,
                           rng: random.Random) -> float:
    if not (0 <= node_failure_p <= 1) or trials < 1 or trials > 1_000_000 or per_node < 1:
        raise Inv08Error("INV08.CAPACITY.BAD_INPUT", "bad saturation inputs")
    cap = min(max_nodes, quota) if quota is not None else max_nodes
    sat = 0
    for _ in range(trials):
        need = math.ceil(max(0.0, rng.gauss(demand_mean, demand_sd)) / per_node)
        failed = sum(1 for _ in range(cap) if rng.random() < node_failure_p) if node_failure_p else 0
        if need > cap - failed:
            sat += 1
    return sat / trials


def headroom_policy(*, per_node: int, demand_mean: float, demand_sd: float, node_failure_p: float,
                    quota: int | None, rng_seed: int = 0, trials: int = 2000,
                    targets: dict = HEADROOM_TARGETS, limit: int = 100_000) -> dict:
    base = math.ceil(demand_mean / per_node)
    lo = max(1, math.ceil(base * (1 + targets["min_headroom_fraction"])))
    n = lo
    while n <= limit:
        p = saturation_probability(max_nodes=n, per_node=per_node, demand_mean=demand_mean,
                                   demand_sd=demand_sd, node_failure_p=node_failure_p, quota=None,
                                   trials=trials, rng=random.Random(rng_seed))
        if p <= targets["max_saturation_probability"]:
            break
        n = max(n + 1, int(n * 1.05))
    else:
        raise Inv08Error("INV08.CAPACITY.NO_SOLUTION", "no max_nodes meets the target")
    quota_ok = quota is None or n <= quota
    return {"recommended_max_nodes": n, "mean_nodes": base, "headroom_fraction": (n - base) / max(base, 1),
            "saturation_probability": p, "quota_ok": quota_ok, "status": targets["status"],
            "action": "ok" if quota_ok else "request provider quota increase"}
