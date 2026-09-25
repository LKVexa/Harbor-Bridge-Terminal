"""Admission control, circuit breaking and retry policy.

GAP-008 (bounded retry, idempotency, backpressure), GAP-009 (admission,
load-shedding, circuit breaker), GAP-023 (saturation signals).

* :class:`AdmissionController` -- global and per-tenant in-flight caps plus a
  per-tenant token bucket. Admission never queues unboundedly: over the cap the
  call is shed immediately with ``Overloaded`` (retry_after_ms hint).
* :class:`CircuitBreaker` -- closed/open/half-open per remote callee, bounded
  number of tracked callees.
* :class:`RetryPolicy` -- retries only retriable categories, only for
  idempotent operations or calls carrying an idempotency key, with capped
  exponential backoff + jitter, and never past the deadline.
"""
from __future__ import annotations

import random
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

from .errors import ChainError, CircuitOpen, Overloaded

IDEMPOTENT_OPERATIONS = frozenset({"get", "read", "query", "head", "list"})


@dataclass
class TokenBucket:
    rate: float
    burst: float
    tokens: float = field(init=False)
    stamp: float = field(init=False)

    def __post_init__(self):
        self.tokens = self.burst
        self.stamp = time.monotonic()

    def take(self) -> bool:
        now = time.monotonic()
        self.tokens = min(self.burst, self.tokens + (now - self.stamp) * self.rate)
        self.stamp = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class AdmissionController:
    def __init__(self, *, max_in_flight: int = 1024, max_in_flight_per_tenant: int = 256,
                 tenant_rate: Optional[float] = None, tenant_burst: Optional[float] = None,
                 max_tenants: int = 4096) -> None:
        if not 1 <= max_in_flight <= 1_000_000 or not 1 <= max_in_flight_per_tenant <= max_in_flight:
            raise ValueError("admission limits out of range")
        self.max_in_flight = max_in_flight
        self.max_per_tenant = max_in_flight_per_tenant
        self.tenant_rate = tenant_rate
        self.tenant_burst = tenant_burst or (tenant_rate or 0)
        self.max_tenants = max_tenants
        self._lock = threading.Lock()
        self.in_flight = 0
        self._per_tenant: dict = {}
        self._buckets: "OrderedDict[str, TokenBucket]" = OrderedDict()
        self.shed = 0
        self.admitted = 0
        self.peak_in_flight = 0

    def utilization(self) -> float:
        with self._lock:
            return self.in_flight / self.max_in_flight

    def _try_enter(self, tenant: str) -> Optional[str]:
        with self._lock:
            if self.in_flight >= self.max_in_flight:
                return "global_concurrency"
            if self._per_tenant.get(tenant, 0) >= self.max_per_tenant:
                return "tenant_concurrency"
            if self.tenant_rate:
                b = self._buckets.get(tenant)
                if b is None:
                    b = self._buckets[tenant] = TokenBucket(self.tenant_rate, self.tenant_burst)
                    while len(self._buckets) > self.max_tenants:
                        self._buckets.popitem(last=False)
                if not b.take():
                    return "tenant_rate"
            self.in_flight += 1
            self._per_tenant[tenant] = self._per_tenant.get(tenant, 0) + 1
            self.admitted += 1
            self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
            return None

    def _exit(self, tenant: str) -> None:
        with self._lock:
            self.in_flight -= 1
            n = self._per_tenant.get(tenant, 1) - 1
            if n <= 0:
                self._per_tenant.pop(tenant, None)
            else:
                self._per_tenant[tenant] = n

    @contextmanager
    def admit(self, tenant: str, *, reentrant: bool = False):
        """Nested hops of an already admitted call are ``reentrant`` and never
        shed (shedding mid-chain would deadlock/partial-fail the parent)."""
        if reentrant:
            yield
            return
        why = self._try_enter(tenant)
        if why is not None:
            with self._lock:
                self.shed += 1
            raise Overloaded("admission refused", reason=why, tenant=tenant, retry_after_ms=50)
        try:
            yield
        finally:
            self._exit(tenant)

    def snapshot(self) -> dict:
        with self._lock:
            return {"in_flight": self.in_flight, "max_in_flight": self.max_in_flight,
                    "tenants_in_flight": len(self._per_tenant), "shed": self.shed,
                    "admitted": self.admitted, "peak_in_flight": self.peak_in_flight}


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 5, reset_after_s: float = 5.0,
                 half_open_max: int = 1, max_keys: int = 4096) -> None:
        if failure_threshold < 1 or reset_after_s <= 0:
            raise ValueError("breaker parameters out of range")
        self.failure_threshold = failure_threshold
        self.reset_after_s = reset_after_s
        self.half_open_max = half_open_max
        self.max_keys = max_keys
        self._lock = threading.Lock()
        self._state: "OrderedDict[str, list]" = OrderedDict()  # key -> [state, failures, opened_at, probes]

    def state(self, key: str) -> str:
        with self._lock:
            s = self._state.get(key)
            if s is None:
                return "closed"
            if s[0] == "open" and time.monotonic() - s[2] >= self.reset_after_s:
                return "half_open"
            return s[0]

    def before(self, key: str) -> None:
        with self._lock:
            s = self._state.get(key)
            if s is None:
                return
            if s[0] == "open":
                if time.monotonic() - s[2] < self.reset_after_s:
                    raise CircuitOpen("circuit open", callee=key, retry_after_ms=int(self.reset_after_s * 1000))
                s[0], s[3] = "half_open", 0
            if s[0] == "half_open":
                if s[3] >= self.half_open_max:
                    raise CircuitOpen("circuit half-open probe in flight", callee=key)
                s[3] += 1

    def success(self, key: str) -> None:
        with self._lock:
            self._state.pop(key, None)

    def failure(self, key: str) -> None:
        with self._lock:
            s = self._state.get(key)
            if s is None:
                s = self._state[key] = ["closed", 0, 0.0, 0]
                while len(self._state) > self.max_keys:
                    self._state.popitem(last=False)
            s[1] += 1
            if s[0] == "half_open" or s[1] >= self.failure_threshold:
                s[0], s[2], s[3] = "open", time.monotonic(), 0

    def open_circuits(self) -> list:
        with self._lock:
            return sorted(k for k, s in self._state.items() if s[0] != "closed")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    base_backoff_s: float = 0.01
    max_backoff_s: float = 0.2
    jitter: float = 0.5

    def __post_init__(self):
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("max_attempts must be within [1, 5]")
        if not 0 <= self.base_backoff_s <= self.max_backoff_s <= 5:
            raise ValueError("backoff out of range")

    @staticmethod
    def retry_safe(operation: str, idempotency_key: Optional[str]) -> bool:
        return operation in IDEMPOTENT_OPERATIONS or idempotency_key is not None

    def should_retry(self, err: ChainError, attempt: int, operation: str,
                     idempotency_key: Optional[str], remaining_s: Optional[float]) -> Optional[float]:
        """Return backoff seconds, or None to stop."""
        if attempt >= self.max_attempts or not err.is_retriable:
            return None
        if isinstance(err, (Overloaded,)) and err.details.get("reason") != "global_concurrency":
            return None  # do not amplify tenant-scoped shedding
        if not self.retry_safe(operation, idempotency_key):
            return None
        back = min(self.max_backoff_s, self.base_backoff_s * (2 ** (attempt - 1)))
        back *= 1 - self.jitter * random.random()
        if remaining_s is not None and back >= remaining_s:
            return None
        return back
