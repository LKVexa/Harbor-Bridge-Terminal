"""Deadlines, bounded retry, circuit breakers and admission control
(C017, C025, C053, C054, C067).

* :class:`Deadline` — an end-to-end budget; every dependency call receives
  ``remaining()`` and the service checks it between lifecycle steps, so
  cancellation/expiry is observed before the next side effect.
* :func:`retry` — retries only errors whose catalog entry is ``retryable``,
  with full-jitter exponential backoff, a per-call attempt cap and a shared
  :class:`RetryBudget` (at most ``ratio`` extra attempts per first attempt,
  so a dependency outage cannot turn into a retry storm). Policy/integrity
  failures are never retried.
* :class:`CircuitBreaker` — closed -> open after ``threshold`` consecutive
  failures; half-open admits one probe after ``cooldown_s``.
* :class:`Admission` — rejects *before* any expensive work: global in-flight
  ceiling, bounded wait queue, per-tenant concurrency (fairness: one tenant
  can hold at most ``per_tenant`` of the slots), and a per-tenant token bucket
  for request rate. Rejections carry ``retry_after_s``.
"""
from __future__ import annotations

import random
import threading
import time
from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

from .errors import SnapshotServiceError

T = TypeVar("T")


class Deadline:
    def __init__(self, budget_s: float, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self.expires = clock() + budget_s
        self.cancelled = False

    def remaining(self) -> float:
        return self.expires - self.clock()

    def cancel(self) -> None:
        self.cancelled = True

    def check(self, stage: str) -> None:
        if self.cancelled:
            raise SnapshotServiceError("SNAP_CANCELLED", f"cancelled before {stage}")
        if self.remaining() <= 0:
            raise SnapshotServiceError("SNAP_TIMEOUT", f"deadline exceeded before {stage}")


class RetryBudget:
    def __init__(self, ratio: float = 0.2, min_tokens: float = 10.0):
        self.ratio, self.tokens, self.max = ratio, min_tokens, min_tokens * 10
        self._lock = threading.Lock()

    def on_first_attempt(self) -> None:
        with self._lock:
            self.tokens = min(self.max, self.tokens + self.ratio)

    def take(self) -> bool:
        with self._lock:
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


def retry(fn: Callable[[], T], *, attempts: int = 3, base_s: float = 0.01, cap_s: float = 0.5,
          deadline: Deadline | None = None, budget: RetryBudget | None = None,
          sleep: Callable[[float], None] = time.sleep, rng: random.Random | None = None,
          on_retry: Callable[[SnapshotServiceError, int], None] | None = None) -> T:
    rng = rng or random.Random()
    if budget:
        budget.on_first_attempt()
    for i in range(attempts):
        try:
            return fn()
        except SnapshotServiceError as exc:
            last = i == attempts - 1
            if not exc.retryable or last or (budget and not budget.take()):
                raise
            delay = rng.uniform(0, min(cap_s, base_s * (2 ** i)))
            if deadline is not None and deadline.remaining() <= delay:
                raise
            if on_retry:
                on_retry(exc, i + 1)
            sleep(delay)
    raise AssertionError("unreachable")  # pragma: no cover


class CircuitBreaker:
    def __init__(self, name: str, *, threshold: int = 5, cooldown_s: float = 5.0,
                 clock: Callable[[], float] = time.monotonic):
        self.name, self.threshold, self.cooldown, self.clock = name, threshold, cooldown_s, clock
        self.failures = 0
        self.state = "closed"
        self.opened_at = 0.0
        self._probe = False
        self._lock = threading.Lock()

    def before(self) -> None:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.cooldown and not self._probe:
                    self.state, self._probe = "half_open", True
                    return
                raise SnapshotServiceError("SNAP_CIRCUIT_OPEN", self.name,
                                           retry_after_s=max(0.0, self.cooldown - (self.clock() - self.opened_at)))
            if self.state == "half_open" and self._probe:
                raise SnapshotServiceError("SNAP_CIRCUIT_OPEN", f"{self.name} probing", retry_after_s=self.cooldown)

    def success(self) -> None:
        with self._lock:
            self.failures, self.state, self._probe = 0, "closed", False

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.state == "half_open" or self.failures >= self.threshold:
                self.state, self.opened_at, self._probe = "open", self.clock(), False

    def call(self, fn: Callable[[], T]) -> T:
        self.before()
        try:
            out = fn()
        except SnapshotServiceError as exc:
            if exc.retryable:  # only dependency faults trip the breaker, not policy rejections
                self.failure()
            else:
                self.success()
            raise
        self.success()
        return out


class TokenBucket:
    def __init__(self, rate_per_s: float, burst: float, clock: Callable[[], float] = time.monotonic):
        self.rate, self.burst, self.clock = rate_per_s, burst, clock
        self.tokens, self.t = burst, clock()

    def take(self) -> float:
        """Return 0 when admitted, else seconds until a token is available."""
        now = self.clock()
        self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate)
        self.t = now
        if self.tokens >= 1:
            self.tokens -= 1
            return 0.0
        return (1 - self.tokens) / self.rate


class Admission:
    def __init__(self, *, max_inflight: int, max_queue: int, per_tenant: int, tenant_rate: float,
                 tenant_burst: float, queue_timeout_s: float = 0.05,
                 clock: Callable[[], float] = time.monotonic):
        self.max_inflight, self.max_queue, self.per_tenant = max_inflight, max_queue, per_tenant
        self.tenant_rate, self.tenant_burst, self.queue_timeout = tenant_rate, tenant_burst, queue_timeout_s
        self.clock = clock
        self.inflight = 0
        self.queued = 0
        self.by_tenant: dict[str, int] = {}
        self.buckets: dict[str, TokenBucket] = {}
        self.rejected: dict[str, int] = {}
        self._cv = threading.Condition()

    def _reject(self, reason: str, code: str, retry_after: float):
        self.rejected[reason] = self.rejected.get(reason, 0) + 1
        raise SnapshotServiceError(code, reason, retry_after_s=retry_after)

    @contextmanager
    def slot(self, tenant: str) -> Iterator[None]:
        with self._cv:
            if len(self.buckets) > 10_000 and tenant not in self.buckets:  # bound per-tenant state
                self._reject("tenant table full", "SNAP_OVERLOADED", 1.0)
            b = self.buckets.setdefault(tenant, TokenBucket(self.tenant_rate, self.tenant_burst, self.clock))
            wait = b.take()
            if wait:
                self._reject("tenant rate", "SNAP_OVERLOADED", wait)
            if self.by_tenant.get(tenant, 0) >= self.per_tenant:
                self._reject("tenant concurrency", "SNAP_OVERLOADED", 0.1)
            if self.inflight >= self.max_inflight:
                if self.queued >= self.max_queue:
                    self._reject("queue full", "SNAP_OVERLOADED", 0.5)
                self.queued += 1
                try:
                    end = time.monotonic() + self.queue_timeout
                    while self.inflight >= self.max_inflight:
                        left = end - time.monotonic()
                        if left <= 0:
                            self._reject("queue timeout", "SNAP_OVERLOADED", 0.5)
                        self._cv.wait(left)
                finally:
                    self.queued -= 1
                if self.by_tenant.get(tenant, 0) >= self.per_tenant:
                    self._reject("tenant concurrency", "SNAP_OVERLOADED", 0.1)
            self.inflight += 1
            self.by_tenant[tenant] = self.by_tenant.get(tenant, 0) + 1
        try:
            yield
        finally:
            with self._cv:
                self.inflight -= 1
                self.by_tenant[tenant] -= 1
                if not self.by_tenant[tenant]:
                    del self.by_tenant[tenant]
                self._cv.notify()
