"""Bounded retry, backoff/jitter, admission control and circuit breaking (MC-38, MC-07, MC-13).

Retry is only ever applied to *pre-dispatch* failures classified retryable
``after_backoff`` by the error model.  Anything ``after_reconcile`` (ambiguous
commit, in-doubt effect, deadline) is never retried here, so retries cannot
convert an ambiguous commit into a duplicate append or duplicate effect.
"""
from __future__ import annotations

import random
import threading
import time
from typing import Any, Callable

from .errors import Overloaded, spec_for


class RetryPolicy:
    def __init__(self, *, max_attempts: int = 3, base: float = 0.2, cap: float = 10.0,
                 seed: int | None = None, sleep: Callable[[float], None] = time.sleep) -> None:
        if max_attempts < 1 or base <= 0 or cap < base:
            raise ValueError("invalid retry policy")
        self.max_attempts, self.base, self.cap = max_attempts, base, cap
        self._rng = random.Random(seed)
        self._sleep = sleep

    def delay(self, attempt: int) -> float:
        """Full jitter: uniform(0, min(cap, base * 2**attempt))."""
        return self._rng.uniform(0, min(self.cap, self.base * (2 ** attempt)))

    def call(self, fn: Callable[[], Any]) -> Any:
        for attempt in range(self.max_attempts):
            try:
                return fn()
            except Exception as exc:
                if spec_for(exc).retryable != "after_backoff" or attempt + 1 == self.max_attempts:
                    raise
                self._sleep(self.delay(attempt))
        raise AssertionError("unreachable")


class CircuitBreaker:
    def __init__(self, *, threshold: int = 5, reset_seconds: float = 30.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.threshold, self.reset, self.clock = threshold, reset_seconds, clock
        self.failures, self.opened_at, self._lock = 0, None, threading.Lock()

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        return "half_open" if self.clock() - self.opened_at >= self.reset else "open"

    def call(self, fn: Callable[[], Any]) -> Any:
        with self._lock:
            if self.state == "open":
                raise Overloaded("circuit open")
        try:
            result = fn()
        except Exception:
            with self._lock:
                self.failures += 1
                if self.failures >= self.threshold or self.opened_at is not None:
                    self.opened_at = self.clock()
            raise
        with self._lock:
            self.failures, self.opened_at = 0, None
        return result


class AdmissionController:
    """Global and per-tenant in-flight bounds; refuses (sheds) instead of queueing unboundedly."""

    def __init__(self, *, max_inflight: int, per_tenant: int) -> None:
        self.max_inflight, self.per_tenant = max_inflight, per_tenant
        self._total, self._by_tenant = 0, {}
        self._lock = threading.Lock()
        self.shed = 0

    def acquire(self, tenant: str) -> None:
        with self._lock:
            if self._total >= self.max_inflight or self._by_tenant.get(tenant, 0) >= self.per_tenant:
                self.shed += 1
                raise Overloaded("admission refused")
            self._total += 1
            self._by_tenant[tenant] = self._by_tenant.get(tenant, 0) + 1

    def release(self, tenant: str) -> None:
        with self._lock:
            if self._by_tenant.get(tenant, 0) <= 0:
                raise ValueError("release without acquire")
            self._total -= 1
            self._by_tenant[tenant] -= 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"inflight": self._total, "tenants": len([v for v in self._by_tenant.values() if v]),
                    "shed_total": self.shed, "max_inflight": self.max_inflight}
