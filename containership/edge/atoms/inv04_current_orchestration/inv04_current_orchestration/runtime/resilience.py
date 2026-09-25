"""Deadlines, cancellation, retry/backoff/jitter, rate limiting, circuit
breakers and stall detection (components 33, 34, 35, 51, 53).

All primitives take an injectable clock so behaviour is deterministic under
test and in simulation.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from .errors import Cancelled, CircuitOpen, DeadlineExceeded, Throttled, is_retryable

T = TypeVar("T")
Clock = Callable[[], float]


class Context:
    """Deadline + cancellation token propagated through every dependency call."""

    def __init__(self, *, timeout: float | None = None, clock: Clock = time.monotonic, parent: "Context | None" = None):
        self.clock = clock
        own = None if timeout is None else clock() + timeout
        pdl = parent.deadline if parent else None
        bounds = [x for x in (own, pdl) if x is not None]
        self.deadline: float | None = min(bounds) if bounds else None
        self._cancelled = threading.Event()
        self.reason = ""
        self.parent = parent

    def child(self, timeout: float | None = None) -> "Context":
        return Context(timeout=timeout, clock=self.clock, parent=self)

    def cancel(self, reason: str = "cancelled") -> None:
        self.reason = reason
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set() or (self.parent.cancelled if self.parent else False)

    def remaining(self) -> float | None:
        return None if self.deadline is None else self.deadline - self.clock()

    def check(self, what: str = "operation") -> None:
        if self.cancelled:
            raise Cancelled(f"{what} cancelled: {self.reason or (self.parent.reason if self.parent else '')}")
        rem = self.remaining()
        if rem is not None and rem <= 0:
            raise DeadlineExceeded(f"{what} exceeded its deadline")


@dataclass
class Backoff:
    base: float = 0.1
    cap: float = 30.0
    factor: float = 2.0
    jitter: float = 1.0  # 1.0 = full jitter, 0 = none
    rng: random.Random = field(default_factory=lambda: random.Random(0x1404))

    def delay(self, attempt: int) -> float:
        raw = min(self.cap, self.base * (self.factor ** max(0, attempt)))
        if self.jitter <= 0:
            return raw
        return raw * (1 - self.jitter) + self.rng.uniform(0, raw * self.jitter)


class RetryBudget:
    """Caps retries to a fraction of recent requests so retries cannot amplify outages."""

    def __init__(self, ratio: float = 0.2, min_per_window: int = 10):
        self.ratio = ratio
        self.min = min_per_window
        self.requests = 0
        self.retries = 0
        self._lock = threading.Lock()

    def record_request(self) -> None:
        with self._lock:
            self.requests += 1

    def try_spend(self) -> bool:
        with self._lock:
            allowed = max(self.min, int(self.requests * self.ratio))
            if self.retries >= allowed:
                return False
            self.retries += 1
            return True


def retry_call(fn: Callable[[], T], *, ctx: Context | None = None, attempts: int = 5, backoff: Backoff | None = None,
               budget: RetryBudget | None = None, sleep: Callable[[float], None] = time.sleep,
               classify: Callable[[BaseException], bool] = is_retryable,
               on_retry: Callable[[int, BaseException], None] | None = None) -> T:
    """Call ``fn`` retrying only retryable faults, within deadline and budget."""
    bo = backoff or Backoff()
    ctx = ctx or Context()
    if budget:
        budget.record_request()
    last: BaseException | None = None
    for attempt in range(attempts):
        ctx.check("retry_call")
        try:
            return fn()
        except BaseException as exc:  # noqa: BLE001
            last = exc
            if not classify(exc) or attempt == attempts - 1:
                raise
            if budget and not budget.try_spend():
                raise
            d = bo.delay(attempt)
            rem = ctx.remaining()
            if rem is not None and d >= rem:
                raise DeadlineExceeded("retry backoff would exceed deadline") from exc
            if on_retry:
                on_retry(attempt + 1, exc)
            sleep(d)
    raise last if last is not None else RuntimeError("retry_call made no attempts")


class TokenBucket:
    """QPS/burst limiter (client-side API limits, per-tenant limits)."""

    def __init__(self, qps: float, burst: int, *, clock: Clock = time.monotonic):
        if qps <= 0 or burst <= 0:
            raise ValueError("qps and burst must be positive")
        self.qps, self.burst, self.clock = qps, burst, clock
        self.tokens = float(burst)
        self.stamp = clock()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = self.clock()
        self.tokens = min(self.burst, self.tokens + (now - self.stamp) * self.qps)
        self.stamp = now

    def try_acquire(self, n: int = 1) -> bool:
        with self._lock:
            self._refill()
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False

    def acquire(self, n: int = 1, *, what: str = "request") -> None:
        if not self.try_acquire(n):
            raise Throttled(f"{what} rate limited", details={"qps": self.qps, "burst": self.burst})


class CircuitBreaker:
    """closed -> open after ``threshold`` consecutive failures; half-open after ``reset``."""

    def __init__(self, name: str, *, threshold: int = 5, reset: float = 30.0, clock: Clock = time.monotonic,
                 classify: Callable[[BaseException], bool] = is_retryable):
        self.name, self.threshold, self.reset, self.clock, self.classify = name, threshold, reset, clock, classify
        self.state = "closed"
        self.failures = 0
        self.opened_at = 0.0
        self._lock = threading.Lock()
        self.transitions: list[tuple[str, str]] = []

    def _set(self, state: str) -> None:
        if state != self.state:
            self.transitions.append((self.state, state))
            self.state = state

    def call(self, fn: Callable[[], T]) -> T:
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.reset:
                    self._set("half_open")
                else:
                    raise CircuitOpen(f"{self.name} circuit open", details={"dependency": self.name})
        try:
            out = fn()
        except BaseException as exc:
            with self._lock:
                if self.classify(exc):
                    self.failures += 1
                    if self.state == "half_open" or self.failures >= self.threshold:
                        self._set("open")
                        self.opened_at = self.clock()
            raise
        with self._lock:
            self.failures = 0
            self._set("closed")
        return out


class StallDetector:
    """Detect work items with no progress, repeated conflicts or stuck processing (51)."""

    def __init__(self, *, max_age: float, max_conflicts: int = 5, clock: Clock = time.monotonic):
        self.max_age, self.max_conflicts, self.clock = max_age, max_conflicts, clock
        self.started: dict[str, float] = {}
        self.progress: dict[str, float] = {}
        self.conflicts: dict[str, int] = {}

    def begin(self, key: str) -> None:
        now = self.clock()
        self.started.setdefault(key, now)
        self.progress[key] = now

    def mark_progress(self, key: str) -> None:
        self.progress[key] = self.clock()
        self.conflicts.pop(key, None)

    def conflict(self, key: str) -> None:
        self.conflicts[key] = self.conflicts.get(key, 0) + 1

    def finish(self, key: str) -> None:
        for d in (self.started, self.progress, self.conflicts):
            d.pop(key, None)

    def stalled(self) -> list[dict]:
        now = self.clock()
        out = []
        for key in sorted(self.started):
            age = now - self.progress.get(key, self.started[key])
            reasons = []
            if age > self.max_age:
                reasons.append("no_progress")
            if self.conflicts.get(key, 0) >= self.max_conflicts:
                reasons.append("repeated_conflicts")
            if reasons:
                out.append({"key": key, "idle_seconds": round(age, 3), "reasons": reasons})
        return out
