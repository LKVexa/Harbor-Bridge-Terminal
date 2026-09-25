"""Bounded retry, circuit breaker, deadlines and load shedding (MC-017 / MC-041).

Every outbound adapter call goes through :func:`call_with_policy`, which
combines a per-dependency :class:`CircuitBreaker`, bounded exponential backoff
with full jitter, and the caller's absolute deadline.  Admission concurrency is
bounded by :class:`Bulkhead` (fail-fast ``OVERLOADED`` instead of queueing
unboundedly); per-tenant rate is bounded by :class:`TokenBucket` quotas.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from .errors import ControlPlaneError, fail

T = TypeVar("T")


class Deadline:
    def __init__(self, timeout_s: float, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self.at = clock() + timeout_s

    def remaining(self) -> float:
        return self.at - self.clock()

    def check(self, what: str = "request") -> None:
        if self.remaining() <= 0:
            raise fail("DEADLINE_EXCEEDED", f"{what} exceeded its deadline")


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    reset_after_s: float = 30.0
    clock: Callable[[], float] = time.monotonic
    state: str = "closed"          # closed | open | half-open
    failures: int = 0
    opened_at: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def allow(self) -> bool:
        with self._lock:
            if self.state == "open" and self.clock() - self.opened_at >= self.reset_after_s:
                self.state = "half-open"
            return self.state != "open"

    def success(self) -> None:
        with self._lock:
            self.state, self.failures = "closed", 0

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.state == "half-open" or self.failures >= self.failure_threshold:
                self.state, self.opened_at = "open", self.clock()


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_s: float = 0.05
    cap_s: float = 1.0

    def backoff(self, attempt: int, rng: random.Random) -> float:
        return rng.uniform(0, min(self.cap_s, self.base_s * (2 ** attempt)))


def call_with_policy(fn: Callable[[], T], breaker: CircuitBreaker, retry: RetryPolicy, deadline: Deadline,
                     unavailable_code: str, *, sleep: Callable[[float], None] = time.sleep,
                     rng: random.Random | None = None) -> T:
    rng = rng or random.Random()
    last: Exception | None = None
    for attempt in range(retry.max_attempts):
        deadline.check(breaker.name)
        if not breaker.allow():
            raise fail(unavailable_code, f"{breaker.name} circuit open", dependency=breaker.name)
        try:
            out = fn()
            breaker.success()
            return out
        except ControlPlaneError as exc:
            if not exc.error.retryable:
                breaker.success()          # a definitive answer is not a dependency fault
                raise
            last = exc
        except Exception as exc:           # transport failure
            last = exc
        breaker.failure()
        pause = retry.backoff(attempt, rng)
        if attempt + 1 < retry.max_attempts and pause < deadline.remaining():
            sleep(pause)
    raise fail(unavailable_code, f"{breaker.name} failed after {retry.max_attempts} attempts: {last}",
               dependency=breaker.name)


class Bulkhead:
    def __init__(self, limit: int):
        self.limit = limit
        self._sem = threading.BoundedSemaphore(limit)
        self.inflight = 0
        self._lock = threading.Lock()

    def __enter__(self):
        if not self._sem.acquire(blocking=False):
            raise fail("OVERLOADED", f"more than {self.limit} admissions in flight")
        with self._lock:
            self.inflight += 1
        return self

    def __exit__(self, *exc):
        with self._lock:
            self.inflight -= 1
        self._sem.release()


class TokenBucket:
    """Per-key rate limiter: ``rate`` tokens per 60 s, burst = rate."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, max_keys: int = 100_000):
        self.clock = clock
        self.max_keys = max_keys
        self._b: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def take(self, key: str, per_minute: int) -> bool:
        now = self.clock()
        with self._lock:
            tokens, ts = self._b.get(key, (float(per_minute), now))
            tokens = min(float(per_minute), tokens + (now - ts) * per_minute / 60.0)
            if tokens < 1.0:
                self._b[key] = (tokens, now)
                return False
            if key not in self._b and len(self._b) >= self.max_keys:
                return False
            self._b[key] = (tokens - 1.0, now)
            return True
