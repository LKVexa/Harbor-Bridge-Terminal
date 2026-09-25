"""Retry/backoff/jitter + circuit breaker (M15), fairness/capacity (M16), bounded queue/backpressure (M45)."""
from __future__ import annotations

import random
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Mapping, TypeVar

from .errors import PlaneError

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_s: float = 0.05
    cap_s: float = 2.0
    budget_s: float = 10.0

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 20 or self.base_s <= 0 or self.cap_s < self.base_s or self.budget_s <= 0:
            raise ValueError("invalid retry policy")

    def delay(self, attempt: int, rng: random.Random) -> float:
        """AWS 'full jitter': uniform(0, min(cap, base * 2**attempt))."""
        return rng.uniform(0, min(self.cap_s, self.base_s * (2 ** attempt)))


def retry(fn: Callable[[], T], policy: RetryPolicy, *, sleep: Callable[[float], None] = time.sleep,
          clock: Callable[[], float] = time.monotonic, rng: random.Random | None = None,
          on_retry: Callable[[int, PlaneError], None] | None = None) -> T:
    """Retry only errors whose *code* is retryable, within attempt and time budgets."""
    rng = rng or random.Random()
    started = clock()
    attempt = 0
    while True:
        try:
            return fn()
        except PlaneError as exc:
            attempt += 1
            if not exc.retryable or attempt >= policy.max_attempts:
                raise
            wait = exc.retry_after_s if exc.retry_after_s is not None else policy.delay(attempt, rng)
            if clock() - started + wait > policy.budget_s:
                raise
            if on_retry:
                on_retry(attempt, exc)
            sleep(wait)


class CircuitBreaker:
    """closed -> open after ``threshold`` consecutive failures; half-open after ``reset_s`` admits one probe."""

    def __init__(self, name: str, *, threshold: int = 5, reset_s: float = 30.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.name = name
        self._threshold = threshold
        self._reset = reset_s
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._probe_in_flight = False
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state_locked()

    def _state_locked(self) -> str:
        if self._opened_at is None:
            return "closed"
        return "half_open" if self._clock() - self._opened_at >= self._reset else "open"

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            state = self._state_locked()
            if state == "open" or (state == "half_open" and self._probe_in_flight):
                raise PlaneError("PLN04-DEP-001", details={"dependency": self.name, "reason": "circuit open"},
                                 retry_after_s=max(0.0, self._reset - (self._clock() - (self._opened_at or 0))))
            if state == "half_open":
                self._probe_in_flight = True
        try:
            result = fn()
        except PlaneError as exc:
            with self._lock:
                self._probe_in_flight = False
                if exc.spec.category in ("provider", "dependency", "timeout"):
                    self._failures += 1
                    if self._failures >= self._threshold or self._opened_at is not None:
                        self._opened_at = self._clock()
            raise
        with self._lock:
            self._failures = 0
            self._opened_at = None
            self._probe_in_flight = False
        return result


class FairShare:
    """M16 - weighted tenant shares over node resources.

    A tenant may always use its guaranteed share
    ``capacity * (1 - headroom) * weight / sum(weights)``; above that it may borrow idle
    capacity only while total usage stays below ``capacity * (1 - headroom)``,
    so a noisy tenant cannot consume the reserve needed by others.
    """

    def __init__(self, *, cpu_milli: int, memory_mib: int, weights: Mapping[str, int] | None = None,
                 default_weight: int = 1, headroom: float = 0.1) -> None:
        if cpu_milli < 1 or memory_mib < 1 or not 0 <= headroom < 1:
            raise ValueError("invalid capacity model")
        self.capacity = {"cpu_milli": cpu_milli, "memory_mib": memory_mib}
        self._weights = dict(weights or {})
        self._default = default_weight
        self._headroom = headroom
        self._used: dict[str, dict[str, int]] = {}
        self._lock = threading.Lock()

    def _share(self, tenant: str, dim: str) -> float:
        tenants = set(self._used) | set(self._weights) | {tenant}
        total_w = sum(self._weights.get(t, self._default) for t in tenants)
        return self.capacity[dim] * (1 - self._headroom) * self._weights.get(tenant, self._default) / total_w

    def reserve(self, tenant: str, cpu_milli: int, memory_mib: int) -> None:
        req = {"cpu_milli": cpu_milli, "memory_mib": memory_mib}
        with self._lock:
            mine = self._used.get(tenant, {"cpu_milli": 0, "memory_mib": 0})
            for dim, amount in req.items():
                total = sum(u[dim] for u in self._used.values())
                if total + amount > self.capacity[dim]:
                    raise PlaneError("PLN04-CAP-001", details={"tenant": tenant, "reason": f"node {dim} exhausted"}, retry_after_s=1.0)
                if mine[dim] + amount > self._share(tenant, dim) and total + amount > self.capacity[dim] * (1 - self._headroom):
                    raise PlaneError("PLN04-CAP-001", details={"tenant": tenant, "reason": f"tenant over fair share of {dim}"}, retry_after_s=1.0)
            self._used[tenant] = {d: mine[d] + req[d] for d in req}

    def release(self, tenant: str, cpu_milli: int, memory_mib: int) -> None:
        with self._lock:
            mine = self._used.get(tenant)
            if mine is None:
                return
            mine["cpu_milli"] = max(0, mine["cpu_milli"] - cpu_milli)
            mine["memory_mib"] = max(0, mine["memory_mib"] - memory_mib)
            if not any(mine.values()):
                del self._used[tenant]

    def usage(self) -> dict[str, dict[str, int]]:
        with self._lock:
            return {t: dict(u) for t, u in self._used.items()}


class AdmissionGate:
    """M45 - bounded concurrent admissions with a bounded, per-tenant-fair wait queue.

    ``max_inflight`` admissions run at once; up to ``max_queue`` wait (round-robin
    across tenants, at most ``per_tenant_queue`` each); anything more is refused
    immediately with ``PLN04-CAP-002`` (explicit backpressure, never unbounded
    buffering).  Waiters give up at their deadline with ``PLN04-TIME-001``.
    """

    def __init__(self, *, max_inflight: int = 32, max_queue: int = 256, per_tenant_queue: int = 32) -> None:
        self._max_inflight = max_inflight
        self._max_queue = max_queue
        self._per_tenant = per_tenant_queue
        self._inflight = 0
        self._queues: dict[str, deque] = {}
        self._rr: deque[str] = deque()
        self._cv = threading.Condition()

    def depth(self) -> int:
        with self._cv:
            return sum(len(q) for q in self._queues.values())

    def _next_ticket(self):
        while self._rr:
            tenant = self._rr[0]
            q = self._queues.get(tenant)
            if q:
                return q[0]
            self._rr.popleft()
            self._queues.pop(tenant, None)
        return None

    def acquire(self, tenant: str, deadline: float, clock: Callable[[], float] = time.monotonic) -> None:
        with self._cv:
            if self._inflight < self._max_inflight and self._next_ticket() is None:
                self._inflight += 1
                return
            depth = sum(len(q) for q in self._queues.values())
            q = self._queues.setdefault(tenant, deque())
            if depth >= self._max_queue or len(q) >= self._per_tenant:
                raise PlaneError("PLN04-CAP-002", details={"tenant": tenant, "queue_depth": depth}, retry_after_s=0.5)
            ticket = object()
            q.append(ticket)
            if tenant not in self._rr:
                self._rr.append(tenant)
            try:
                while not (self._inflight < self._max_inflight and self._next_ticket() is ticket):
                    remaining = deadline - clock()
                    if remaining <= 0:
                        raise PlaneError("PLN04-TIME-001", details={"tenant": tenant, "reason": "queued past deadline"})
                    self._cv.wait(timeout=min(remaining, 0.05))
                self._inflight += 1
                # rotate so the next tenant goes first (round-robin fairness)
                self._rr.rotate(-1)
            finally:
                if ticket in q:
                    q.remove(ticket)
                self._cv.notify_all()

    def release(self) -> None:
        with self._cv:
            self._inflight = max(0, self._inflight - 1)
            self._cv.notify_all()
