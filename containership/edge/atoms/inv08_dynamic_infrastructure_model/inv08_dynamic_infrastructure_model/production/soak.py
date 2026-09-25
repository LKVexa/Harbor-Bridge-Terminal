"""Component 59 - compressed-time soak / burst / churn / fleet harness (PK_DYN_SOAK/1).

Time is simulated: one tick == ``tick_hours`` of wall time, so a "72 h" profile
runs as 72/tick_hours ticks in-process in well under a second.  Real multi-hour
or multi-day soak runs on live infrastructure are NOT_RUN.

Per tick invariants (violations are recorded with tick and pool index):
  I1 min(target) bound: size >= min_nodes;  I2 size <= max_nodes
  I3 no busy node reclaimed;  I4 node ids unique and all leased (expires > now or busy renewed)
Leak detection: the profile runs ``epochs`` times; each epoch ends by releasing
work and converging to min_nodes, so live state is identical at each boundary and
tracemalloc growth between the first and last boundary must stay below
``leak_budget_bytes``; open fd count (Linux
/proc/self/fd) must not grow.  Convergence: after load stops, every pool must
reach min_nodes within ``lease_ttl + 1`` ticks.
"""
from __future__ import annotations

import math
import os
import random
import tracemalloc
from dataclasses import dataclass

from ..model import Pool

PROFILES = {
    "soak_72h": {"hours": 72, "pattern": "diurnal"},
    "soak_7d": {"hours": 168, "pattern": "diurnal"},
    "burst": {"hours": 24, "pattern": "burst"},
    "churn": {"hours": 24, "pattern": "churn"},
}


def demand_at(pattern: str, t: int, rng: random.Random, cap: int) -> float:
    if pattern == "diurnal":
        return max(0.0, cap * 0.5 * (1 + math.sin(2 * math.pi * t / 24)) + rng.uniform(-1, 1))
    if pattern == "burst":
        return cap * 3 if rng.random() < 0.1 else rng.uniform(0, cap * 0.2)
    if pattern == "churn":
        return rng.choice([0, cap, cap // 2, cap * 2])
    raise ValueError(f"unknown pattern {pattern}")


def _fd_count() -> int | None:
    try:
        return len(os.listdir("/proc/self/fd"))
    except OSError:
        return None


@dataclass
class SoakResult:
    ticks: int
    pools: int
    violations: list
    mem_growth_bytes: int
    fd_growth: int | None
    converged: bool
    convergence_ticks: int
    max_size_seen: int


def run(profile: str, *, pools: int = 10, min_nodes: int = 1, max_nodes: int = 20, per_node: int = 4,
        lease_ttl: int = 3, tick_hours: float = 1.0, seed: int = 0, busy_prob: float = 0.2,
        leak_budget_bytes: int = 64 * 1024, epochs: int = 2, pool_factory=Pool) -> SoakResult:
    """Run ``epochs`` repetitions of the profile; after each epoch all work is
    released and the fleet converges to min_nodes, so live state is identical at
    every epoch boundary and any retained-memory growth between boundaries is a leak."""
    prof = PROFILES[profile]
    rng = random.Random(seed)
    fleet = [pool_factory(min_nodes=min_nodes, max_nodes=max_nodes, per_node=per_node, lease_ttl=lease_ttl)
             for _ in range(pools)]
    ticks = int(prof["hours"] / tick_hours)
    violations: list = []
    cap = max_nodes * per_node
    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()
    fd0 = _fd_count()
    boundary_mem: list[int] = []
    max_seen = 0
    t = 0
    converged, conv = True, 0
    for _epoch in range(max(1, epochs)):
        for _ in range(ticks):
            for i, p in enumerate(fleet):
                busy_before = {n for n, s in p.nodes.items() if s["busy"]}
                res = p.tick(t, demand_at(prof["pattern"], t, rng, cap), elapsed_hours=tick_hours)
                size = res["size"]
                max_seen = max(max_seen, size)
                if size < min_nodes:
                    violations.append((t, i, "I1"))
                if size > max_nodes:
                    violations.append((t, i, "I2"))
                if busy_before & set(res["reclaimed"]):
                    violations.append((t, i, "I3"))
                if any(not (s["expires"] > t) for s in p.nodes.values()):
                    violations.append((t, i, "I4"))
                for n in list(p.nodes):
                    if rng.random() < busy_prob:
                        p.set_busy(n, not p.nodes[n]["busy"])
            t += 1
        for p in fleet:                      # release all work, zero demand
            for n in list(p.nodes):
                p.set_busy(n, False)
        conv = 0
        while conv <= lease_ttl + 1 and any(len(p.nodes) != min_nodes for p in fleet):
            for p in fleet:
                p.tick(t, 0, elapsed_hours=tick_hours)
            t += 1
            conv += 1
        converged = converged and all(len(p.nodes) == min_nodes for p in fleet)
        boundary_mem.append(tracemalloc.get_traced_memory()[0])
    if not was_tracing:
        tracemalloc.stop()
    growth = boundary_mem[-1] - boundary_mem[0] if len(boundary_mem) > 1 else 0
    fd1 = _fd_count()
    if growth > leak_budget_bytes:
        violations.append((t, -1, f"memory growth {growth} > budget {leak_budget_bytes}"))
    if not converged:
        violations.append((t, -1, "no convergence to min_nodes"))
    return SoakResult(ticks * max(1, epochs), pools, violations, growth,
                      None if fd0 is None or fd1 is None else fd1 - fd0, converged, conv, max_seen)
