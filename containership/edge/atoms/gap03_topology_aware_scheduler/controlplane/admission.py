"""MC-025 - Admission control, load shedding and circuit breakers.

Independent limits: ingress rate (global + per tenant token buckets), candidate
fan-out, concurrent scoring, concurrent commits, queue depth, per-dependency
concurrency.  Control-plane operations (health, freeze, release, rollback,
reconciliation) draw from a *reserved* pool that new placements cannot use.
Shedding order is deterministic by priority class.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time

from .errors import SchedulerError

PRIORITY = {"system-critical": 0, "production": 1, "batch": 2, "best-effort": 3}
CONTROL_OPS = frozenset({"health", "freeze", "release", "rollback", "reconcile"})


class TokenBucket:
    def __init__(self, rate: float, burst: float, *, clock=time.monotonic):
        if rate <= 0 or burst <= 0:
            raise ValueError("rate and burst must be positive")
        self.rate, self.burst, self.clock = rate, burst, clock
        self.tokens, self.t = burst, clock()
        self._lock = threading.Lock()

    def take(self, n: float = 1.0) -> float:
        """Take n tokens; return 0 on success or seconds until available."""
        with self._lock:
            now = self.clock()
            self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate)
            self.t = now
            if self.tokens >= n:
                self.tokens -= n
                return 0.0
            return (n - self.tokens) / self.rate


@dataclass
class Limits:
    global_rps: float = 2000.0
    global_burst: float = 4000.0
    tenant_rps: float = 200.0
    tenant_burst: float = 400.0
    max_candidates: int = 10_000
    max_concurrent_scoring: int = 64
    max_concurrent_commits: int = 16
    max_queue: int = 256
    reserved_control_slots: int = 4
    max_tenants_tracked: int = 10_000
    shed_threshold: dict = field(default_factory=lambda: {"best-effort": 0.5, "batch": 0.75, "production": 0.95,
                                                            "system-critical": 1.01})


class Admission:
    def __init__(self, limits: Limits | None = None, *, clock=time.monotonic, metrics=None):
        self.l = limits or Limits()
        self.clock, self.metrics = clock, metrics
        self.global_bucket = TokenBucket(self.l.global_rps, self.l.global_burst, clock=clock)
        self.tenants: dict[str, TokenBucket] = {}
        self.inflight = {"score": 0, "commit": 0, "control": 0}
        self.queued = 0
        self._lock = threading.Lock()
        self.rejected: dict[str, int] = {}

    def _count(self, reason: str):
        self.rejected[reason] = self.rejected.get(reason, 0) + 1
        if self.metrics:
            self.metrics.inc("gap03_admission_rejected_total", reason=reason)

    def utilization(self) -> float:
        return max(self.inflight["score"] / self.l.max_concurrent_scoring, self.inflight["commit"] / self.l.max_concurrent_commits,
                   self.queued / self.l.max_queue)

    def admit(self, *, kind: str, tenant: str = "", priority: str = "production", candidates: int = 0):
        """Return a release callable, or raise OVERLOADED with retry-after."""
        if priority not in PRIORITY:
            raise SchedulerError("INVALID_ARGUMENT", "unknown priority class")
        with self._lock:
            if kind in CONTROL_OPS:
                if self.inflight["control"] >= self.l.reserved_control_slots:
                    self._count("control_saturated")
                    raise SchedulerError("OVERLOADED", "control pool saturated", detail={"retry_after_s": 1})
                self.inflight["control"] += 1
                return self._releaser("control")
            if candidates > self.l.max_candidates:
                self._count("fanout")
                raise SchedulerError("PAYLOAD_TOO_LARGE", "candidate fan-out exceeds limit")
            if self.utilization() >= self.l.shed_threshold[priority]:
                self._count(f"shed_{priority}")
                raise SchedulerError("OVERLOADED", f"shedding {priority}", detail={"retry_after_s": 1})
            wait = self.global_bucket.take()
            if wait:
                self._count("global_rate")
                raise SchedulerError("OVERLOADED", "global rate", detail={"retry_after_s": round(wait, 3)})
            if tenant:
                bucket = self.tenants.get(tenant)
                if bucket is None:
                    if len(self.tenants) >= self.l.max_tenants_tracked:
                        self._evict_idle()
                    if len(self.tenants) >= self.l.max_tenants_tracked:
                        self._count("tenant_table_full")
                        raise SchedulerError("OVERLOADED", "tenant table full")
                    bucket = self.tenants[tenant] = TokenBucket(self.l.tenant_rps, self.l.tenant_burst, clock=self.clock)
                wait = bucket.take()
                if wait:
                    self._count("tenant_rate")
                    raise SchedulerError("OVERLOADED", "tenant rate", detail={"retry_after_s": round(wait, 3)})
            if self.metrics:
                self.metrics.set("gap03_admission_utilization_ratio", round(self.utilization(), 4))
            slot = "commit" if kind == "commit" else "score"
            cap = self.l.max_concurrent_commits if slot == "commit" else self.l.max_concurrent_scoring
            if self.inflight[slot] >= cap:
                self._count(f"{slot}_concurrency")
                raise SchedulerError("OVERLOADED", f"{slot} concurrency", detail={"retry_after_s": 0.1})
            self.inflight[slot] += 1
            return self._releaser(slot)

    def _evict_idle(self):
        """Drop tenant buckets that have fully refilled (idle): keeps memory bounded without locking new tenants out
        forever (defect DEF-06: a full table used to reject every new tenant permanently)."""
        now = self.clock()
        idle = [t for t, b in self.tenants.items() if b.tokens + (now - b.t) * b.rate >= b.burst]
        for t in idle:
            del self.tenants[t]

    def _releaser(self, slot):
        done = [False]

        def release():
            with self._lock:
                if not done[0]:
                    done[0] = True
                    self.inflight[slot] -= 1
        return release


class CircuitBreaker:
    """closed -> open after ``threshold`` consecutive failures; half-open after ``cooldown``
    admits ``probes`` trial calls; ``successes`` successes close it."""

    def __init__(self, name: str, *, threshold: int = 5, cooldown: float = 10.0, probes: int = 1, successes: int = 2,
                 clock=time.monotonic, metrics=None):
        self.name, self.threshold, self.cooldown, self.probes, self.successes = name, threshold, cooldown, probes, successes
        self.clock, self.metrics = clock, metrics
        self.state, self.failures, self.opened_at, self.probe_inflight, self.half_ok = "closed", 0, 0.0, 0, 0
        self._lock = threading.Lock()

    def _set(self, st):
        self.state = st
        if self.metrics:
            self.metrics.set("gap03_breaker_state", {"closed": 0, "half_open": 1, "open": 2}[st], dependency=self.name)

    def call(self, fn, *args, **kwargs):
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.cooldown:
                    self._set("half_open")
                    self.half_ok = 0
                else:
                    raise SchedulerError("DEPENDENCY_UNAVAILABLE", f"breaker open: {self.name}")
            if self.state == "half_open":
                if self.probe_inflight >= self.probes:
                    raise SchedulerError("DEPENDENCY_UNAVAILABLE", f"breaker half-open: {self.name}")
                self.probe_inflight += 1
            probing = self.state == "half_open"
        t0 = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
        except Exception:
            if self.metrics:
                self.metrics.observe("gap03_dependency_latency_ms", (time.perf_counter() - t0) * 1000, dependency=self.name)
            with self._lock:
                if probing:
                    self.probe_inflight -= 1
                self.failures += 1
                if probing or self.failures >= self.threshold:
                    self._set("open")
                    self.opened_at = self.clock()
            raise
        if self.metrics:
            self.metrics.observe("gap03_dependency_latency_ms", (time.perf_counter() - t0) * 1000, dependency=self.name)
        with self._lock:
            if probing:
                self.probe_inflight -= 1
                self.half_ok += 1
                if self.half_ok >= self.successes:
                    self._set("closed")
                    self.failures = 0
            else:
                self.failures = 0
        return result
