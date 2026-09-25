"""Component 41 - health / stall detection.

Contract ``PK_DYN_HEALTH/1``: every check returns ``Check(name, status,
detail, remediation)`` with status HEALTHY | DEGRADED | UNHEALTHY; aggregation
is worst-of, and every non-HEALTHY check carries a concrete remediation.

* Heartbeat: component beats on the injected clock; age <= interval ->
  HEALTHY, <= interval*miss_threshold -> DEGRADED (suspect), beyond -> UNHEALTHY
  (dead); never beaten -> UNHEALTHY.
* Stuck ops: PENDING journal ops older than ``threshold`` seconds.
* Dependency: sliding-window error rate per dependency plus circuit state.
* Lease store: ping (UNHEALTHY if unavailable) and write lag (time since the
  last durable write vs ``max_lag``; only meaningful while a leader renews).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable

from .core import Inv08Error

HEALTHY, DEGRADED, UNHEALTHY = "HEALTHY", "DEGRADED", "UNHEALTHY"
_RANK = {HEALTHY: 0, DEGRADED: 1, UNHEALTHY: 2}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    remediation: str = ""


class Heartbeats:
    def __init__(self, clock: Callable[[], float], *, interval: float = 10.0, miss_threshold: int = 3) -> None:
        if interval <= 0 or miss_threshold < 1:
            raise ValueError("interval > 0 and miss_threshold >= 1")
        self.clock, self.interval, self.miss = clock, interval, miss_threshold
        self.last: dict[str, float] = {}

    def beat(self, component: str) -> None:
        self.last[component] = self.clock()

    def check(self, component: str) -> Check:
        if component not in self.last:
            return Check(f"heartbeat:{component}", UNHEALTHY, "no heartbeat ever received",
                         "start the component / check it is scheduled")
        age = self.clock() - self.last[component]
        if age <= self.interval:
            return Check(f"heartbeat:{component}", HEALTHY, f"age {age:.1f}s")
        if age <= self.interval * self.miss:
            return Check(f"heartbeat:{component}", DEGRADED, f"late heartbeat, age {age:.1f}s",
                         "check controller loop latency / CPU starvation")
        return Check(f"heartbeat:{component}", UNHEALTHY, f"heartbeat missing for {age:.1f}s",
                     "controller presumed dead: standby takes over after leader ttl; restart it")


def stuck_ops(journal, now: float, threshold: float) -> Check:
    stuck = sorted(k for k, v in journal.pending().items() if now - v["started"] > threshold)
    if not stuck:
        return Check("stuck_ops", HEALTHY, "no stuck operations")
    return Check("stuck_ops", UNHEALTHY, f"{len(stuck)} ops pending > {threshold}s: {stuck[:5]}",
                 "run a reconcile round (restart reconciliation resolves or times them out); "
                 "if they persist, inspect provider for the node ids listed")


class DependencyHealth:
    def __init__(self, window: int = 20, degraded_rate: float = 0.2, unhealthy_rate: float = 0.5) -> None:
        if not 0 < degraded_rate < unhealthy_rate <= 1 or window < 1:
            raise ValueError("invalid thresholds")
        self.window, self.dr, self.ur = window, degraded_rate, unhealthy_rate
        self.samples: dict[str, deque] = {}

    def record(self, dep: str, ok: bool) -> None:
        self.samples.setdefault(dep, deque(maxlen=self.window)).append(bool(ok))

    def check(self, dep: str, breaker=None) -> Check:
        s = self.samples.get(dep, ())
        rate = (s.count(False) / len(s)) if s else 0.0
        state = breaker.current_state() if breaker is not None else "CLOSED"
        if state == "OPEN" or rate >= self.ur:
            return Check(f"dependency:{dep}", UNHEALTHY, f"error rate {rate:.0%}, circuit {state}",
                         f"check {dep} status; controller sheds calls until the circuit closes")
        if state == "HALF_OPEN" or rate >= self.dr:
            return Check(f"dependency:{dep}", DEGRADED, f"error rate {rate:.0%}, circuit {state}",
                         f"watch {dep}; retries are absorbing failures")
        return Check(f"dependency:{dep}", HEALTHY, f"error rate {rate:.0%}")


def lease_store_health(store, now: float, max_lag: float) -> Check:
    try:
        store.ping()
    except Inv08Error as exc:
        return Check("lease_store", UNHEALTHY, exc.code,
                     "lease store unreachable: leader will lose lease at ttl; restore store availability")
    if store.last_write_ts is None:
        return Check("lease_store", DEGRADED, "no durable write observed yet",
                     "verify a leader is renewing its lease")
    lag = now - store.last_write_ts
    if lag > max_lag:
        return Check("lease_store", DEGRADED, f"write lag {lag:.1f}s > {max_lag}s",
                     "leader not renewing: check controller heartbeat and store latency")
    return Check("lease_store", HEALTHY, f"write lag {lag:.1f}s")


def aggregate(checks: list[Check]) -> dict:
    if not checks:
        return {"status": UNHEALTHY, "checks": [], "remediation": ["no health checks ran"]}
    worst = max(checks, key=lambda c: _RANK[c.status]).status
    return {"status": worst,
            "checks": [c.__dict__ for c in checks],
            "remediation": [f"{c.name}: {c.remediation}" for c in checks if c.status != HEALTHY]}
