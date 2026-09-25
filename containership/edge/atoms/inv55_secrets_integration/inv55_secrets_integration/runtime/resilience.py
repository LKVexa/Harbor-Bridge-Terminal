"""Retry / backoff / deadline / circuit breaker / admission control (checklist #20, #53, #54).

Only ``RETRYABLE`` outcomes are retried; ``DENIED`` and ``TERMINAL`` are
returned immediately.  Retries are bounded by attempts AND the caller's
deadline, with full-jitter exponential backoff.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass

from .errors import INV55Error, Outcome


@dataclass
class Deadline:
    expires_at: float
    clock: object = time.monotonic

    @classmethod
    def after(cls, seconds: float, clock=time.monotonic):
        return cls(clock() + seconds, clock)

    def remaining(self) -> float:
        return max(0.0, self.expires_at - self.clock())

    def check(self):
        if self.remaining() <= 0:
            raise INV55Error("INV55-E-DEADLINE")


def retry(fn, *, attempts: int = 3, base_s: float = 0.05, cap_s: float = 1.0, deadline: Deadline,
          rng: random.Random | None = None, sleep=time.sleep, on_retry=None):
    rng = rng or random.Random()
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last = None
    for i in range(attempts):
        deadline.check()
        try:
            return fn(deadline.remaining())
        except INV55Error as e:
            if e.outcome is not Outcome.RETRYABLE or e.code == "INV55-E-CIRCUIT-OPEN":
                raise
            last = e
            if i == attempts - 1:
                break
            delay = rng.uniform(0, min(cap_s, base_s * (2 ** i)))
            if delay >= deadline.remaining():
                break
            if on_retry:
                on_retry(i + 1, e.code)
            sleep(delay)
    raise last


class CircuitBreaker:
    """closed -> open after ``threshold`` consecutive retryable failures;
    open -> half_open after ``cooldown_s``; one probe decides."""

    def __init__(self, threshold: int = 5, cooldown_s: float = 10.0, clock=time.monotonic):
        self.threshold, self.cooldown_s, self.clock = threshold, cooldown_s, clock
        self.state, self.failures, self.opened_at = "closed", 0, 0.0
        self._probe = False
        self._lock = threading.Lock()

    def call(self, fn, *a, **kw):
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at < self.cooldown_s:
                    raise INV55Error("INV55-E-CIRCUIT-OPEN")
                self.state = "half_open"
            if self.state == "half_open":
                if self._probe:
                    raise INV55Error("INV55-E-CIRCUIT-OPEN")
                self._probe = True
        try:
            r = fn(*a, **kw)
        except INV55Error as e:
            with self._lock:
                self._probe = False
                if e.outcome is Outcome.RETRYABLE:
                    self.failures += 1
                    if self.state == "half_open" or self.failures >= self.threshold:
                        self.state, self.opened_at = "open", self.clock()
            raise
        with self._lock:
            self._probe = False
            self.state, self.failures = "closed", 0
        return r


class Bulkhead:
    """Bounded concurrency; refuses instead of queueing unboundedly."""

    def __init__(self, max_inflight: int):
        self._sem = threading.BoundedSemaphore(max_inflight)
        self.max_inflight = max_inflight

    def __enter__(self):
        if not self._sem.acquire(blocking=False):
            raise INV55Error("INV55-E-OVERLOADED")
        return self

    def __exit__(self, *exc):
        self._sem.release()


class TokenBucketQuota:
    """Per-(tenant, app) quota with a hard cap on tracked keys (checklist #9, #43, #67)."""

    def __init__(self, rate_per_s: float, burst: int, *, max_keys: int = 10_000, clock=time.monotonic):
        self.rate, self.burst, self.max_keys, self.clock = rate_per_s, burst, max_keys, clock
        self._b: dict[tuple, list[float]] = {}
        self._lock = threading.Lock()

    def take(self, key: tuple) -> None:
        with self._lock:
            now = self.clock()
            b = self._b.get(key)
            if b is None:
                if len(self._b) >= self.max_keys:
                    raise INV55Error("INV55-E-OVERLOADED", "quota table full")
                b = self._b[key] = [float(self.burst), now]
            elapsed = now - b[1]
            if elapsed < 0:   # clock rollback must never mint or destroy tokens
                raise INV55Error("INV55-E-CLOCK", "quota clock moved backwards")
            b[0] = min(self.burst, b[0] + elapsed * self.rate)
            b[1] = now
            if b[0] < 1:
                raise INV55Error("INV55-E-QUOTA")
            b[0] -= 1
