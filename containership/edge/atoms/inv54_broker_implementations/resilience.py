"""Timeouts, cancellation, retry/backoff/jitter, idempotency, circuit breaking and
admission control (components 21, 53, 54, 68).

All primitives take an injectable clock/sleep/rng so behaviour is deterministic under test.
Every buffer is bounded by configuration *and* a hard ceiling (``HARD_*``).
"""
from __future__ import annotations

import random
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Event, RLock
from typing import Any, Callable, TypeVar

from .errors import (CANCELLED, CIRCUIT_OPEN, DEADLINE_EXCEEDED, INVALID_ARGUMENT, OVERLOADED,
                     BrokerError, classify)

T = TypeVar("T")
Clock = Callable[[], float]

HARD_MAX_RETRIES = 20
HARD_MAX_IDEMPOTENCY_KEYS = 1_000_000
HARD_MAX_INFLIGHT = 100_000


class CancelToken:
    def __init__(self) -> None:
        self._ev = Event()
        self.reason = ""

    def cancel(self, reason: str = "cancelled") -> None:
        self.reason = reason
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()


@dataclass
class Deadline:
    """Absolute deadline; ``check()`` raises before any effect is attempted."""

    expires_at: float
    clock: Clock = time.monotonic
    token: CancelToken | None = None

    @classmethod
    def after(cls, seconds: float, clock: Clock = time.monotonic, token: CancelToken | None = None) -> "Deadline":
        if seconds <= 0:
            raise BrokerError(INVALID_ARGUMENT, "timeout must be > 0")
        return cls(clock() + seconds, clock, token)

    def remaining(self) -> float:
        return self.expires_at - self.clock()

    def check(self) -> None:
        if self.token is not None and self.token.cancelled:
            raise BrokerError(CANCELLED, self.token.reason)
        if self.remaining() <= 0:
            raise BrokerError(DEADLINE_EXCEEDED)


@dataclass
class RetryPolicy:
    """Bounded exponential backoff with full jitter (AWS architecture-blog formulation)."""

    max_attempts: int = 5
    base_delay: float = 0.05
    max_delay: float = 5.0
    rng: random.Random = field(default_factory=lambda: random.Random(0x1554))

    def __post_init__(self) -> None:
        if not (1 <= self.max_attempts <= HARD_MAX_RETRIES):
            raise BrokerError(INVALID_ARGUMENT, f"max_attempts must be 1..{HARD_MAX_RETRIES}")
        if self.base_delay < 0 or self.max_delay < self.base_delay:
            raise BrokerError(INVALID_ARGUMENT, "0 <= base_delay <= max_delay required")

    def delay(self, attempt: int) -> float:
        cap = min(self.max_delay, self.base_delay * (2 ** attempt))
        return self.rng.uniform(0, cap)

    def run(self, fn: Callable[[], T], *, deadline: Deadline | None = None,
            sleep: Callable[[float], None] = time.sleep,
            on_retry: Callable[[int, BrokerError, float], None] | None = None) -> T:
        last: BrokerError | None = None
        for attempt in range(self.max_attempts):
            if deadline:
                deadline.check()
            try:
                return fn()
            except Exception as exc:  # classified; non-retryable re-raised immediately
                err = classify(exc)
                if not err.retryable:
                    raise err from exc
                last = err
                if attempt + 1 >= self.max_attempts:
                    break
                d = self.delay(attempt)
                if deadline and d >= deadline.remaining():
                    raise BrokerError(DEADLINE_EXCEEDED, "retry budget exceeds deadline") from exc
                if on_retry:
                    on_retry(attempt, err, d)
                sleep(d)
        assert last is not None
        raise last


class IdempotencyCache:
    """Bounded LRU of idempotency-key -> first result; duplicate requests return the cached result."""

    def __init__(self, capacity: int = 10_000) -> None:
        if not (1 <= capacity <= HARD_MAX_IDEMPOTENCY_KEYS):
            raise BrokerError(INVALID_ARGUMENT, "idempotency capacity out of range")
        self.capacity = capacity
        self._d: OrderedDict[str, Any] = OrderedDict()
        self._lock = RLock()

    def get_or_run(self, key: str | None, fn: Callable[[], T]) -> tuple[T, bool]:
        if key is None:
            return fn(), False
        with self._lock:
            if key in self._d:
                self._d.move_to_end(key)
                return self._d[key], True
            result = fn()
            self._d[key] = result
            if len(self._d) > self.capacity:
                self._d.popitem(last=False)
            return result, False

    def __len__(self) -> int:
        return len(self._d)


class CircuitBreaker:
    """closed -> open after ``failure_threshold`` consecutive failures; half-open after ``reset_after``."""

    def __init__(self, failure_threshold: int = 5, reset_after: float = 30.0, clock: Clock = time.monotonic) -> None:
        self.failure_threshold = failure_threshold
        self.reset_after = reset_after
        self.clock = clock
        self.state = "closed"
        self.failures = 0
        self.opened_at = 0.0
        self._lock = RLock()

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.reset_after:
                    self.state = "half_open"
                else:
                    raise BrokerError(CIRCUIT_OPEN)
        try:
            result = fn()
        except Exception:
            with self._lock:
                self.failures += 1
                if self.state == "half_open" or self.failures >= self.failure_threshold:
                    self.state, self.opened_at = "open", self.clock()
            raise
        with self._lock:
            self.failures, self.state = 0, "closed"
        return result


class TokenBucket:
    def __init__(self, rate: float, burst: float, clock: Clock = time.monotonic) -> None:
        if rate <= 0 or burst <= 0:
            raise BrokerError(INVALID_ARGUMENT, "rate and burst must be > 0")
        self.rate, self.burst, self.clock = rate, burst, clock
        self.tokens = burst
        self.last = clock()
        self._lock = RLock()

    def try_take(self, n: float = 1.0) -> bool:
        with self._lock:
            now = self.clock()
            self.tokens = min(self.burst, self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False


class AdmissionController:
    """Global in-flight ceiling + priority-aware shedding.

    Requests at priority < ``shed_below_priority`` are shed once utilisation passes
    ``shed_ratio``; everything is shed at the ceiling.  Always explicit, never silent.
    """

    def __init__(self, max_inflight: int = 1024, shed_ratio: float = 0.8, shed_below_priority: int = 5) -> None:
        if not (1 <= max_inflight <= HARD_MAX_INFLIGHT):
            raise BrokerError(INVALID_ARGUMENT, "max_inflight out of range")
        self.max_inflight, self.shed_ratio, self.shed_below = max_inflight, shed_ratio, shed_below_priority
        self.inflight = 0
        self.shed_count = 0
        self._lock = RLock()

    def acquire(self, priority: int = 5) -> None:
        with self._lock:
            util = self.inflight / self.max_inflight
            if self.inflight >= self.max_inflight or (util >= self.shed_ratio and priority < self.shed_below):
                self.shed_count += 1
                raise BrokerError(OVERLOADED, inflight=self.inflight, priority=priority)
            self.inflight += 1

    def release(self) -> None:
        with self._lock:
            self.inflight = max(0, self.inflight - 1)
