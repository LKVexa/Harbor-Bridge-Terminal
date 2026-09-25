"""Resilience primitives (checklist #20, #53, #54, #9, #56, #59, #67).

All primitives take an injected monotonic clock so behavior is deterministic in tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import random
import threading
from typing import Callable, TypeVar

from .errors import ErrorCode, Inv55Error, error
from .providers.base import ProviderError

T = TypeVar("T")


@dataclass(frozen=True)
class Deadline:
    """Absolute deadline + cooperative cancellation token."""
    expires_at: float
    clock: Callable[[], float]
    cancelled: threading.Event = field(default_factory=threading.Event)

    @classmethod
    def after(cls, seconds: float, clock: Callable[[], float]) -> "Deadline":
        return cls(clock() + seconds, clock)

    def remaining(self) -> float:
        return self.expires_at - self.clock()

    def check(self) -> None:
        if self.cancelled.is_set():
            raise error(ErrorCode.CANCELLED)
        if self.remaining() <= 0:
            raise error(ErrorCode.DEADLINE_EXCEEDED)


@dataclass
class RetryPolicy:
    """Capped exponential backoff with full jitter; retries only retryable errors."""
    max_attempts: int = 3
    base_s: float = 0.05
    cap_s: float = 1.0
    rng: random.Random = field(default_factory=lambda: random.Random(0))
    sleep: Callable[[float], None] = lambda s: None

    def __post_init__(self) -> None:
        if not (1 <= self.max_attempts <= 10):
            raise ValueError("max_attempts must be in [1, 10]")

    def backoff(self, attempt: int) -> float:
        return self.rng.uniform(0, min(self.cap_s, self.base_s * (2 ** attempt)))

    def run(self, fn: Callable[[], T], deadline: Deadline | None = None) -> T:
        last: Exception | None = None
        for attempt in range(self.max_attempts):
            if deadline:
                deadline.check()
            try:
                return fn()
            except ProviderError as exc:
                if not exc.retryable:
                    raise
                last = exc
            delay = self.backoff(attempt)
            if deadline and delay >= deadline.remaining():
                break
            if attempt + 1 < self.max_attempts:
                self.sleep(delay)
        assert last is not None or deadline is not None
        if last is None:
            raise error(ErrorCode.DEADLINE_EXCEEDED)
        raise last


class CircuitOpen(Inv55Error):
    code = ErrorCode.PROVIDER_UNAVAILABLE


@dataclass
class CircuitBreaker:
    """closed -> open after N consecutive failures; half-open probe after cooldown."""
    clock: Callable[[], float]
    failure_threshold: int = 5
    cooldown_s: float = 5.0
    state: str = "closed"
    _failures: int = 0
    _opened_at: float = 0.0
    _probe_in_flight: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state == "open":
                if self.clock() - self._opened_at >= self.cooldown_s and not self._probe_in_flight:
                    self.state = "half_open"
                    self._probe_in_flight = True
                else:
                    raise CircuitOpen()
            elif self.state == "half_open":
                if self._probe_in_flight:
                    raise CircuitOpen()
                self._probe_in_flight = True
        try:
            result = fn()
        except ProviderError as exc:
            with self._lock:
                self._probe_in_flight = False
                if exc.retryable:
                    self._failures += 1
                    if self.state == "half_open" or self._failures >= self.failure_threshold:
                        self.state, self._opened_at = "open", self.clock()
            raise
        with self._lock:
            self._probe_in_flight = False
            self._failures = 0
            self.state = "closed"
        return result


@dataclass
class TokenBucket:
    rate_per_s: float
    burst: float
    clock: Callable[[], float]
    _tokens: float = -1.0
    _last: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def take(self, n: float = 1.0) -> bool:
        with self._lock:
            now = self.clock()
            if self._tokens < 0:
                self._tokens, self._last = self.burst, now
            self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate_per_s)
            self._last = now
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False


@dataclass
class AdmissionController:
    """Global concurrency cap (load shedding) + per-tenant/per-workload token buckets (fairness)."""
    clock: Callable[[], float]
    max_in_flight: int = 256
    tenant_rate: float = 200.0
    tenant_burst: float = 400.0
    workload_rate: float = 50.0
    workload_burst: float = 100.0
    max_tracked_keys: int = 10_000
    _in_flight: int = 0
    _buckets: dict[str, TokenBucket] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _bucket(self, key: str, rate: float, burst: float) -> TokenBucket:
        b = self._buckets.get(key)
        if b is None:
            if len(self._buckets) >= self.max_tracked_keys:
                raise error(ErrorCode.OVERLOADED)
            b = self._buckets[key] = TokenBucket(rate, burst, self.clock)
        return b

    def admit(self) -> None:
        """Global load shedding, applied before authentication."""
        with self._lock:
            if self._in_flight >= self.max_in_flight:
                raise error(ErrorCode.OVERLOADED)
            self._in_flight += 1

    def charge(self, tenant: str, workload: str) -> None:
        """Per-tenant/per-workload fairness, applied to the *authenticated* principal."""
        with self._lock:
            t = self._bucket("t:" + tenant, self.tenant_rate, self.tenant_burst)
            w = self._bucket(f"w:{tenant}/{workload}", self.workload_rate, self.workload_burst)
        if not w.take() or not t.take():
            raise error(ErrorCode.QUOTA_EXCEEDED)

    def release(self) -> None:
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)

    @property
    def in_flight(self) -> int:
        return self._in_flight
