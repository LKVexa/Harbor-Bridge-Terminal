"""MC-05 - Capacity, quota, fairness and dynamic admission control.

Admission happens *before* parsing large inputs: payload byte limit, per-tenant
token-bucket rate quota, per-tenant and global concurrency limits (fair share),
and load shedding when the global in-flight count crosses the shed threshold.
A per-dependency circuit breaker protects catalogue/provider calls.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import threading
import time
from typing import Callable, Iterator

from .errors import PlaneError


@dataclass(frozen=True)
class AdmissionPolicy:
    max_payload_bytes: int = 1_048_576
    tenant_rate_per_second: float = 50.0
    tenant_burst: int = 100
    tenant_max_concurrency: int = 8
    global_max_concurrency: int = 64
    shed_threshold: float = 0.9  # fraction of global concurrency where non-priority work is shed
    max_tenants_tracked: int = 10_000


class _Bucket:
    __slots__ = ("tokens", "stamp")

    def __init__(self, burst: int, now: float) -> None:
        self.tokens = float(burst)
        self.stamp = now


class AdmissionController:
    def __init__(self, policy: AdmissionPolicy | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        self.policy = policy or AdmissionPolicy()
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[str, _Bucket] = {}
        self._inflight: dict[str, int] = {}
        self._global = 0
        self.stats = {"admitted": 0, "rejected_quota": 0, "rejected_concurrency": 0, "shed": 0, "rejected_payload": 0}

    def check_payload(self, size: int) -> None:
        if size > self.policy.max_payload_bytes:
            self.stats["rejected_payload"] += 1
            raise PlaneError("request payload too large", code="PAYLOAD_TOO_LARGE",
                             details={"limit": self.policy.max_payload_bytes, "actual": size})

    @contextmanager
    def admit(self, tenant: str, *, priority: bool = False) -> Iterator[None]:
        p = self.policy
        with self._lock:
            now = self._clock()
            b = self._buckets.get(tenant)
            if b is None:
                if len(self._buckets) >= p.max_tenants_tracked:
                    # evict the fullest (least recently constrained) bucket to bound memory
                    victim = max(self._buckets, key=lambda k: self._buckets[k].tokens)
                    del self._buckets[victim]
                b = self._buckets[tenant] = _Bucket(p.tenant_burst, now)
            b.tokens = min(p.tenant_burst, b.tokens + (now - b.stamp) * p.tenant_rate_per_second)
            b.stamp = now
            if b.tokens < 1.0:
                self.stats["rejected_quota"] += 1
                raise PlaneError("tenant request quota exceeded", code="QUOTA_EXCEEDED",
                                 details={"tenant": tenant, "limit": p.tenant_rate_per_second})
            if self._global >= p.global_max_concurrency:
                self.stats["rejected_concurrency"] += 1
                raise PlaneError("plane at global concurrency limit", code="OVERLOADED", details={"reason": "global_concurrency"})
            if not priority and self._global >= p.shed_threshold * p.global_max_concurrency:
                self.stats["shed"] += 1
                raise PlaneError("load shed", code="OVERLOADED", details={"reason": "load_shed"})
            if self._inflight.get(tenant, 0) >= p.tenant_max_concurrency:
                self.stats["rejected_concurrency"] += 1
                raise PlaneError("tenant concurrency limit", code="QUOTA_EXCEEDED",
                                 details={"tenant": tenant, "limit": p.tenant_max_concurrency})
            b.tokens -= 1.0
            self._inflight[tenant] = self._inflight.get(tenant, 0) + 1
            self._global += 1
            self.stats["admitted"] += 1
        try:
            yield
        finally:
            with self._lock:
                self._global -= 1
                left = self._inflight[tenant] - 1
                if left:
                    self._inflight[tenant] = left
                else:
                    del self._inflight[tenant]

    def saturation(self) -> float:
        return self._global / self.policy.global_max_concurrency


class CircuitBreaker:
    """Closed -> open after N consecutive failures; half-open after cool-down."""

    def __init__(self, name: str, *, failure_threshold: int = 5, reset_after: float = 10.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_after = reset_after
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if self._clock() - self._opened_at >= self.reset_after:
            return "half_open"
        return "open"

    def call(self, fn: Callable[[], object]) -> object:
        with self._lock:
            if self.state == "open":
                raise PlaneError(f"circuit open for {self.name}", code="CIRCUIT_OPEN", details={"dependency": self.name})
        try:
            result = fn()
        except Exception:
            with self._lock:
                self._failures += 1
                if self._failures >= self.failure_threshold or self._opened_at is not None:
                    self._opened_at = self._clock()
            raise
        with self._lock:
            self._failures = 0
            self._opened_at = None
        return result
