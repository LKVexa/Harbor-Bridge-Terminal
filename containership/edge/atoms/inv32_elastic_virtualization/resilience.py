"""Retry/backoff, retry budgets, circuit breaking, admission control and load shedding (WS 9).

Design choices:
* Only ``Retry.RETRYABLE`` errors are retried automatically, and only for operations protected by a
  durable operation ID *and* expected-state fencing.  ``CONDITIONAL`` errors (stale state, quarantine,
  reserve) require the caller to re-read state first; ``TERMINAL`` never retries.
* Backoff: decorrelated-jitter exponential, capped, never past the caller's deadline.
* Admission rejects instead of queuing unboundedly.  ``safety_reserved_slots`` are held back so rollback /
  quarantine / reconciliation (``Priority.SAFETY``) remain serviceable under normal-load saturation.
"""
from __future__ import annotations

from contextlib import contextmanager
from enum import IntEnum
import random
import threading
import time
from typing import Callable, Iterator, TypeVar

from . import errors as E

T = TypeVar("T")


class Priority(IntEnum):
    SAFETY = 0  # rollback, quarantine, reconciliation
    NORMAL = 1
    LOW = 2  # predictive / opportunistic adjustments; shed first


class RetryBudget:
    """Retries may not exceed ``ratio`` x requests over a sliding window (per dependency)."""

    def __init__(self, ratio: float = 0.2, window_s: float = 10.0, min_retries: int = 3, clock=time.monotonic) -> None:
        self.ratio, self.window_s, self.min_retries = ratio, window_s, min_retries
        self._req: list[float] = []
        self._ret: list[float] = []
        self._clock = clock
        self._lock = threading.Lock()

    def _trim(self, now: float) -> None:
        lo = now - self.window_s
        self._req = [t for t in self._req if t >= lo]
        self._ret = [t for t in self._ret if t >= lo]

    def record_request(self) -> None:
        with self._lock:
            now = self._clock()
            self._trim(now)
            self._req.append(now)

    def try_spend(self) -> bool:
        with self._lock:
            now = self._clock()
            self._trim(now)
            if len(self._ret) < max(self.min_retries, int(len(self._req) * self.ratio)):
                self._ret.append(now)
                return True
            return False


class RetryPolicy:
    def __init__(self, *, max_attempts: int = 3, base_delay_s: float = 0.05, max_delay_s: float = 2.0,
                 budget: RetryBudget | None = None, rng: random.Random | None = None,
                 sleep: Callable[[float], None] = time.sleep, clock=time.monotonic, metrics=None,
                 dependency: str = "provider") -> None:
        self.max_attempts, self.base, self.cap = max_attempts, base_delay_s, max_delay_s
        self.budget = budget or RetryBudget()
        self._rng = rng or random.Random()
        self._sleep, self._clock, self._metrics, self.dependency = sleep, clock, metrics, dependency
        self.attempts_made = 0

    def delays(self) -> Iterator[float]:
        prev = self.base
        while True:
            prev = min(self.cap, self._rng.uniform(self.base, prev * 3))
            yield prev

    def run(self, fn: Callable[[], T], *, deadline: float, idempotent: bool) -> T:
        self.budget.record_request()
        delays = self.delays()
        attempt = 0
        while True:
            attempt += 1
            self.attempts_made = attempt
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001 - classification decides
                if not idempotent or E.classify(exc) is not E.Retry.RETRYABLE or attempt >= self.max_attempts:
                    raise
                delay = next(delays)
                if self._clock() + delay >= deadline:
                    raise
                if not self.budget.try_spend():
                    raise
                if self._metrics:
                    self._metrics.inc("inv32_retries_total", dependency=self.dependency)
                self._sleep(delay)


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, name: str, *, failure_threshold: int = 5, reset_s: float = 10.0, jitter: float = 0.2,
                 clock=time.monotonic, rng: random.Random | None = None, on_change=None) -> None:
        self.name, self.threshold, self.reset_s, self.jitter = name, failure_threshold, reset_s, jitter
        self._clock, self._rng = clock, rng or random.Random()
        self.state = self.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._reopen_after = reset_s
        self._probe_inflight = False
        self._lock = threading.Lock()
        self._on_change = on_change or (lambda name, old, new: None)

    def _set(self, new: str) -> None:
        old, self.state = self.state, new
        if old != new:
            self._on_change(self.name, old, new)

    def before(self) -> None:
        with self._lock:
            if self.state == self.OPEN:
                if self._clock() - self._opened_at < self._reopen_after:
                    raise E.CircuitOpen("dependency circuit open", dependency=self.name,
                                        retry_after_s=round(self._reopen_after - (self._clock() - self._opened_at), 3))
                self._set(self.HALF_OPEN)
            if self.state == self.HALF_OPEN:
                if self._probe_inflight:
                    raise E.CircuitOpen("dependency circuit half-open; probe in flight", dependency=self.name)
                self._probe_inflight = True

    def success(self) -> None:
        with self._lock:
            self._failures = 0
            self._probe_inflight = False
            self._set(self.CLOSED)

    def failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._probe_inflight = False
            if self.state == self.HALF_OPEN or self._failures >= self.threshold:
                self._opened_at = self._clock()
                # jitter prevents all controllers probing in lock-step after an outage
                self._reopen_after = self.reset_s * (1 + self._rng.uniform(0, self.jitter))
                self._set(self.OPEN)

    @contextmanager
    def guard(self, *, counts: Callable[[BaseException], bool] | None = None) -> Iterator[None]:
        self.before()
        try:
            yield
        except BaseException as exc:
            if counts is None or counts(exc):
                self.failure()
            else:
                self.success()
            raise
        else:
            self.success()

    def snapshot(self) -> dict:
        return {"name": self.name, "state": self.state, "failures": self._failures}


class TokenBucket:
    def __init__(self, rate_per_s: float, burst: int, clock=time.monotonic) -> None:
        self.rate, self.burst, self._clock = rate_per_s, burst, clock
        self._tokens = float(burst)
        self._last = clock()
        self._lock = threading.Lock()

    def take(self) -> float | None:
        """Consume one token; return None on success or seconds-until-available."""
        with self._lock:
            now = self._clock()
            self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
            self._last = now
            if self._tokens >= 1:
                self._tokens -= 1
                return None
            return (1 - self._tokens) / self.rate


class AdmissionController:
    """Bounded in-flight admission per host and per tenant, with safety-reserved capacity."""

    def __init__(self, *, max_host: int = 64, max_tenant: int = 16, safety_slots: int = 4,
                 tenant_rate_per_s: float = 50.0, tenant_burst: int = 100, max_tenants: int = 100_000,
                 clock=time.monotonic) -> None:
        self.max_host, self.max_tenant, self.safety_slots = max_host, max_tenant, safety_slots
        self._rate, self._burst, self._clock = tenant_rate_per_s, tenant_burst, clock
        self._host = 0
        self._tenant: dict[str, int] = {}
        self._buckets: dict[str, TokenBucket] = {}
        self._max_tenants = max_tenants
        self._lock = threading.Lock()
        self.saturated_dependency = False  # set by controller when provider/state store saturates

    def inflight(self) -> int:
        return self._host

    @contextmanager
    def admit(self, tenant: str | None, priority: Priority) -> Iterator[None]:
        with self._lock:
            if priority is not Priority.SAFETY:
                if priority is Priority.LOW and self.saturated_dependency:
                    raise E.Overloaded("shedding low-priority adjustments under dependency saturation",
                                       retry_after_s=1.0)
                if self._host >= self.max_host - self.safety_slots:
                    raise E.Overloaded("host mutation capacity exhausted", retry_after_s=0.1)
                if tenant is not None:
                    if self._tenant.get(tenant, 0) >= self.max_tenant:
                        raise E.QuotaExceeded("tenant in-flight limit reached", retry_after_s=0.1)
                    bucket = self._buckets.get(tenant)
                    if bucket is None:
                        if len(self._buckets) >= self._max_tenants:
                            raise E.Overloaded("tenant table full")
                        bucket = self._buckets[tenant] = TokenBucket(self._rate, self._burst, self._clock)
                    wait = bucket.take()
                    if wait is not None:
                        raise E.QuotaExceeded("tenant request rate exceeded", retry_after_s=round(wait, 3))
            elif self._host >= self.max_host:
                raise E.Overloaded("even safety capacity exhausted", retry_after_s=0.05)
            self._host += 1
            if tenant is not None:
                self._tenant[tenant] = self._tenant.get(tenant, 0) + 1
        try:
            yield
        finally:
            with self._lock:
                self._host -= 1
                if tenant is not None:
                    self._tenant[tenant] -= 1
                    if not self._tenant[tenant]:
                        del self._tenant[tenant]
