"""Admission policy: deadlines, cancellation, idempotency, retry, quotas, shedding.

Covers INV-35-C017 (tenant quota/fairness beyond local queue depth), C025
(timeout/cancellation/retry/idempotency/backpressure contract), C053 (bounded
retry with backoff and jitter, only for retryable outcomes) and C054 (circuit
breaker/load shedding beyond simple queue refusal).
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
import random
from threading import RLock
import time
from typing import Callable, TypeVar

from .errors import Inv35Error

T = TypeVar("T")


class CancelToken:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


@dataclass(frozen=True, slots=True)
class Deadline:
    at: float

    @classmethod
    def after(cls, seconds: float, clock: Callable[[], float] = time.monotonic) -> "Deadline":
        return cls(clock() + seconds)

    def check(self, clock: Callable[[], float] = time.monotonic) -> None:
        if clock() > self.at:
            raise Inv35Error("INV35-E203")


@dataclass
class RetryPolicy:
    """Full-jitter exponential backoff with a hard attempt and time budget."""

    max_attempts: int = 4
    base_delay: float = 0.002
    max_delay: float = 0.100
    budget: float = 0.500
    rng: random.Random = field(default_factory=lambda: random.Random(0x1235))

    def __post_init__(self) -> None:
        if not (1 <= self.max_attempts <= 10) or self.base_delay <= 0 or self.max_delay < self.base_delay:
            raise Inv35Error("INV35-E500", "retry policy out of bounds")

    def delays(self) -> list[float]:
        return [self.rng.uniform(0, min(self.max_delay, self.base_delay * 2 ** i)) for i in range(self.max_attempts - 1)]

    def run(self, op: Callable[[], T], *, sleep: Callable[[float], None] = time.sleep,
            cancel: CancelToken | None = None) -> T:
        spent = 0.0
        delays = self.delays()
        for attempt in range(self.max_attempts):
            if cancel is not None and cancel.cancelled:
                raise Inv35Error("INV35-E204")
            try:
                return op()
            except Inv35Error as exc:
                if not exc.retryable or attempt == self.max_attempts - 1:
                    raise
                delay = delays[attempt]
                if spent + delay > self.budget:
                    raise
                spent += delay
                sleep(delay)
        raise AssertionError("unreachable")  # pragma: no cover


class IdempotencyCache:
    """Remembers terminal results per (tenant, key) so a retried submit is not applied twice."""

    def __init__(self, capacity: int = 4096) -> None:
        self._data: OrderedDict[tuple[str, str], dict[str, object]] = OrderedDict()
        self.capacity = capacity
        self._lock = RLock()

    def get(self, tenant: str, key: str) -> dict[str, object] | None:
        with self._lock:
            hit = self._data.get((tenant, key))
            if hit is not None:
                self._data.move_to_end((tenant, key))
            return hit

    def put(self, tenant: str, key: str, result: dict[str, object]) -> None:
        with self._lock:
            self._data[(tenant, key)] = result
            while len(self._data) > self.capacity:
                self._data.popitem(last=False)


class TokenBucket:
    def __init__(self, rate: float, burst: float, clock: Callable[[], float] = time.monotonic) -> None:
        if rate <= 0 or burst <= 0:
            raise Inv35Error("INV35-E500", "quota rate/burst must be positive")
        self.rate, self.burst, self.clock = rate, burst, clock
        self.tokens = burst
        self.stamp = clock()

    def take(self, n: float = 1.0) -> bool:
        now = self.clock()
        self.tokens = min(self.burst, self.tokens + (now - self.stamp) * self.rate)
        self.stamp = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


class QuotaManager:
    """Per-tenant rate quota plus a per-tenant share of host-wide descriptor capacity."""

    def __init__(self, *, host_descriptor_capacity: int, tenant_share: float, rate: float, burst: float,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if not (0 < tenant_share <= 1):
            raise Inv35Error("INV35-E500", "tenant_share must be in (0, 1]")
        self.capacity = host_descriptor_capacity
        self.per_tenant_cap = max(1, int(host_descriptor_capacity * tenant_share))
        self.rate, self.burst, self.clock = rate, burst, clock
        self.buckets: dict[str, TokenBucket] = {}
        self.used: dict[str, int] = {}
        self._lock = RLock()

    def admit(self, tenant: str, descriptors: int) -> None:
        with self._lock:
            bucket = self.buckets.setdefault(tenant, TokenBucket(self.rate, self.burst, self.clock))
            if self.used.get(tenant, 0) + descriptors > self.per_tenant_cap:
                raise Inv35Error("INV35-E201", f"{tenant} descriptor share exhausted")
            if sum(self.used.values()) + descriptors > self.capacity:
                raise Inv35Error("INV35-E201", "host descriptor capacity exhausted")
            if not bucket.take():
                raise Inv35Error("INV35-E201", f"{tenant} submit rate exhausted")
            self.used[tenant] = self.used.get(tenant, 0) + descriptors

    def release(self, tenant: str, descriptors: int) -> None:
        with self._lock:
            self.used[tenant] = max(0, self.used.get(tenant, 0) - descriptors)

    def saturation(self) -> float:
        with self._lock:
            return sum(self.used.values()) / self.capacity


class CircuitBreaker:
    """Opens after ``threshold`` consecutive backend failures; half-opens after ``cooldown``."""

    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, threshold: int = 5, cooldown: float = 1.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.threshold, self.cooldown, self.clock = threshold, cooldown, clock
        self.state = self.CLOSED
        self.failures = 0
        self.opened_at = 0.0
        self._lock = RLock()

    def before(self) -> None:
        with self._lock:
            if self.state == self.OPEN:
                if self.clock() - self.opened_at >= self.cooldown:
                    self.state = self.HALF_OPEN
                else:
                    raise Inv35Error("INV35-E202")

    def record(self, ok: bool) -> None:
        with self._lock:
            if ok:
                self.failures = 0
                self.state = self.CLOSED
                return
            self.failures += 1
            if self.state == self.HALF_OPEN or self.failures >= self.threshold:
                self.state = self.OPEN
                self.opened_at = self.clock()
