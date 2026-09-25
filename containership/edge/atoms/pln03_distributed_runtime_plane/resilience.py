"""Deadlines, cancellation, bounded retry, admission control, quotas and circuit
breaking (MC-008, MC-014, MC-017, MC-037, MC-038).

All structures are bounded; every limit lives in ``Limits`` and is set from
validated configuration (config.py).
"""
from __future__ import annotations

import random
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, TypeVar

from .envelope import CODES, Outcome
from .runtime import RuntimePlaneError

T = TypeVar("T")


class DeadlineExceeded(RuntimePlaneError):
    code = "PK_DEADLINE_EXCEEDED"


class Cancelled(RuntimePlaneError):
    code = "PK_CANCELLED"


class RateLimited(RuntimePlaneError):
    code = "PK_RATE_LIMITED"


class QuotaExceeded(RuntimePlaneError):
    code = "PK_QUOTA_EXCEEDED"


class CircuitOpen(RuntimePlaneError):
    code = "PK_CIRCUIT_OPEN"


@dataclass(frozen=True)
class Limits:
    """Complete interface resource-limit specification (MC-017).  Defaults are conservative."""

    max_inline_bytes: int = 1024 * 1024
    max_key_chars: int = 1024
    max_transaction_ops: int = 128
    max_concurrency_global: int = 256
    max_concurrency_per_tenant: int = 32
    rate_per_tenant_per_s: float = 500.0
    burst_per_tenant: int = 1000
    max_tenants_tracked: int = 10_000
    max_offline_buffer_msgs: int = 10_000
    max_offline_buffer_bytes: int = 64 * 1024 * 1024
    max_audit_events_in_memory: int = 100_000
    default_deadline_s: float = 2.0
    max_deadline_s: float = 30.0
    retry_max_attempts: int = 4
    retry_base_s: float = 0.02
    retry_cap_s: float = 1.0
    retry_budget_ratio: float = 0.2      # retries may add at most 20% load
    breaker_failure_threshold: int = 5
    breaker_reset_s: float = 5.0
    state_quota_bytes_per_tenant: int = 256 * 1024 * 1024


class Deadline:
    """Absolute deadline + cooperative cancellation token (MC-014)."""

    def __init__(self, seconds: float, clock: Callable[[], float] = time.monotonic):
        if not 0 < seconds:
            raise ValueError("deadline must be positive")
        self.clock = clock
        self.expires = clock() + seconds
        self._cancel = threading.Event()
        self.reason = ""

    def cancel(self, reason: str = "cancelled") -> None:
        self.reason = reason
        self._cancel.set()

    def remaining(self) -> float:
        return self.expires - self.clock()

    def check(self) -> None:
        if self._cancel.is_set():
            raise Cancelled(self.reason or "cancelled")
        if self.remaining() <= 0:
            raise DeadlineExceeded("deadline exceeded")


def is_retryable(exc: BaseException) -> bool:
    spec = CODES.get(getattr(exc, "code", ""), None)
    return spec is not None and spec.outcome is Outcome.RETRYABLE


class RetryBudget:
    """Token budget: each first attempt deposits ``ratio`` tokens, each retry withdraws 1 (bounded)."""

    def __init__(self, ratio: float, cap: float = 100.0):
        self.ratio, self.cap, self.tokens = ratio, cap, cap / 10
        self._lock = threading.Lock()

    def deposit(self) -> None:
        with self._lock:
            self.tokens = min(self.cap, self.tokens + self.ratio)

    def withdraw(self) -> bool:
        with self._lock:
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


def retry_call(fn: Callable[[], T], *, limits: Limits, deadline: Deadline, budget: RetryBudget,
               sleep: Callable[[float], None] = time.sleep, rng: random.Random | None = None,
               on_retry: Callable[[int, BaseException], None] | None = None) -> T:
    """Bounded retry with exponential backoff and full jitter.  Only RETRYABLE codes are retried,
    and only while deadline, attempt limit and retry budget all allow it (MC-037)."""
    rng = rng or random.Random()
    budget.deposit()
    attempt = 0
    while True:
        deadline.check()
        try:
            return fn()
        except BaseException as exc:  # noqa: BLE001 - classified below
            attempt += 1
            if not is_retryable(exc) or attempt >= limits.retry_max_attempts or not budget.withdraw():
                raise
            backoff = rng.uniform(0, min(limits.retry_cap_s, limits.retry_base_s * (2 ** attempt)))
            if backoff >= deadline.remaining():
                raise DeadlineExceeded("retry backoff would exceed deadline", attempts=attempt) from exc
            if on_retry:
                on_retry(attempt, exc)
            sleep(backoff)


class TokenBucket:
    def __init__(self, rate: float, burst: int, clock: Callable[[], float] = time.monotonic):
        self.rate, self.burst, self.clock = rate, burst, clock
        self.tokens, self.t = float(burst), clock()

    def take(self) -> bool:
        now = self.clock()
        self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate)
        self.t = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class CircuitBreaker:
    """closed -> open after N consecutive retryable failures; half-open probe after reset_s."""

    def __init__(self, threshold: int, reset_s: float, clock: Callable[[], float] = time.monotonic):
        self.threshold, self.reset_s, self.clock = threshold, reset_s, clock
        self.failures, self.opened_at, self.state = 0, 0.0, "closed"
        self._lock = threading.Lock()

    def before(self, name: str) -> None:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.reset_s:
                    self.state = "half_open"
                else:
                    raise CircuitOpen(f"circuit open for {name}", dependency=name)

    def record(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self.failures, self.state = 0, "closed"
            else:
                self.failures += 1
                if self.state == "half_open" or self.failures >= self.threshold:
                    self.state, self.opened_at = "open", self.clock()


class Admission:
    """Per-tenant fairness + global concurrency ceiling + rate limiting (MC-008, MC-038).

    Fairness: each tenant is capped at ``max_concurrency_per_tenant`` so one tenant can hold at most
    that share of the global pool; rate buckets are per tenant; tracked-tenant count is bounded.
    """

    def __init__(self, limits: Limits, clock: Callable[[], float] = time.monotonic):
        self.limits, self.clock = limits, clock
        self._global = 0
        self._per: dict[str, int] = defaultdict(int)
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def acquire(self, tenant: str) -> None:
        with self._lock:
            b = self._buckets.get(tenant)
            if b is None:
                if len(self._buckets) >= self.limits.max_tenants_tracked:
                    raise QuotaExceeded("tenant tracking ceiling reached", limit=self.limits.max_tenants_tracked)
                b = self._buckets[tenant] = TokenBucket(self.limits.rate_per_tenant_per_s,
                                                        self.limits.burst_per_tenant, self.clock)
            # concurrency checks first so a refused request never consumes a rate token
            if self._global >= self.limits.max_concurrency_global:
                raise RateLimited("global concurrency ceiling reached (load shed)")
            if self._per.get(tenant, 0) >= self.limits.max_concurrency_per_tenant:
                raise QuotaExceeded("tenant concurrency quota exceeded", tenant=tenant)
            if not b.take():
                raise RateLimited("tenant rate limit exceeded", tenant=tenant)
            self._global += 1
            self._per[tenant] += 1

    def release(self, tenant: str) -> None:
        with self._lock:
            self._global -= 1
            self._per[tenant] -= 1
            if self._per[tenant] <= 0:
                del self._per[tenant]

    @property
    def in_flight(self) -> int:
        return self._global
