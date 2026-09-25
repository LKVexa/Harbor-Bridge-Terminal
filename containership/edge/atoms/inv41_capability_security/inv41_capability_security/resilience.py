"""Bounded retry, circuit breaker, admission control and fault injection
(Section 14, REQ-RES-*).  Retries apply only to dependency calls, never to
authorization denials, invalid input or revocation.
"""
from __future__ import annotations

import random
import threading
import time
from typing import Callable, Final

from .capabilities import CapabilityError
from .errors import Overloaded, ServiceError, Unavailable

TERMINAL: Final[tuple] = (CapabilityError, ValueError, TypeError)


class RetryBudget:
    """Global token bucket so retries cannot become a storm."""

    def __init__(self, capacity: int = 100, refill_per_s: float = 10.0, clock=time.monotonic) -> None:
        self.capacity, self.refill, self.clock = capacity, refill_per_s, clock
        self.tokens = float(capacity)
        self.t = clock()
        self._lock = threading.Lock()

    def take(self) -> bool:
        with self._lock:
            now = self.clock()
            self.tokens = min(self.capacity, self.tokens + (now - self.t) * self.refill)
            self.t = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


def retry(fn: Callable, *, attempts: int = 3, base: float = 0.01, cap: float = 0.5, budget: RetryBudget | None = None,
          sleep=time.sleep, rng: random.Random | None = None, retry_on: tuple = (Unavailable, TimeoutError, ConnectionError)):
    """Full-jitter exponential backoff.  Terminal outcomes are never retried."""
    rng = rng or random.Random()
    last = None
    for i in range(max(1, attempts)):
        try:
            return fn()
        except TERMINAL as exc:
            if isinstance(exc, retry_on):
                last = exc
            else:
                raise
        except retry_on as exc:
            last = exc
        if i == attempts - 1 or (budget is not None and not budget.take()):
            break
        sleep(rng.uniform(0, min(cap, base * (2 ** i))))
    raise Unavailable("dependency unavailable after bounded retries") from last


class CircuitBreaker:
    """closed -> open after N failures; half-open after cooldown; hysteresis via success threshold."""

    def __init__(self, failure_threshold: int = 5, cooldown_s: float = 5.0, success_threshold: int = 2, clock=time.monotonic):
        self.ft, self.cd, self.st, self.clock = failure_threshold, cooldown_s, success_threshold, clock
        self.state, self.failures, self.successes, self.opened_at = "closed", 0, 0, 0.0
        self._lock = threading.Lock()

    def call(self, fn: Callable):
        with self._lock:
            if self.state == "open":
                if self.clock() - self.opened_at >= self.cd:
                    self.state, self.successes = "half-open", 0
                else:
                    raise Unavailable("circuit open")
        try:
            result = fn()
        except Exception as exc:
            if isinstance(exc, TERMINAL) and not isinstance(exc, ServiceError):
                raise  # denials / invalid input are not dependency failures
            with self._lock:
                self.failures += 1
                if self.state == "half-open" or self.failures >= self.ft:
                    self.state, self.opened_at = "open", self.clock()
            raise
        with self._lock:
            if self.state == "half-open":
                self.successes += 1
                if self.successes >= self.st:
                    self.state, self.failures = "closed", 0
            else:
                self.failures = 0
        return result


class Admission:
    """Bounded concurrency + bounded queue; excess is rejected early (never queued unboundedly).

    Priority lane: revoke/control operations bypass the normal limit up to a reserve.
    """

    def __init__(self, max_concurrent: int, max_queue: int, *, priority_reserve: int = 4, wait_s: float = 0.05):
        self.max_concurrent, self.max_queue, self.reserve, self.wait_s = max_concurrent, max_queue, priority_reserve, wait_s
        self.in_flight = 0
        self.waiting = 0
        self._cv = threading.Condition()
        self.rejected = 0

    def __call__(self, priority: bool = False):
        adm = self

        class _Slot:
            def __enter__(self_inner):
                limit = adm.max_concurrent + (adm.reserve if priority else 0)
                with adm._cv:
                    if adm.in_flight >= limit:
                        if adm.waiting >= adm.max_queue:
                            adm.rejected += 1
                            raise Overloaded("admission queue full")
                        adm.waiting += 1
                        try:
                            ok = adm._cv.wait_for(lambda: adm.in_flight < limit, timeout=adm.wait_s)
                        finally:
                            adm.waiting -= 1
                        if not ok:
                            adm.rejected += 1
                            raise Overloaded("admission wait timed out")
                    adm.in_flight += 1
                return self_inner

            def __exit__(self_inner, *exc):
                with adm._cv:
                    adm.in_flight -= 1
                    adm._cv.notify()
                return False
        return _Slot()


class FaultInjector:
    """Deterministic fault injection keyed by dependency name."""

    KINDS: Final[tuple] = ("timeout", "unavailable", "crash", "clock_skew", "exhaustion", "partition")

    def __init__(self) -> None:
        self.active: dict = {}

    def set(self, dependency: str, kind: str | None) -> None:
        if kind is None:
            self.active.pop(dependency, None)
        elif kind not in self.KINDS:
            raise ValueError(kind)
        else:
            self.active[dependency] = kind

    def check(self, dependency: str) -> None:
        kind = self.active.get(dependency)
        if kind in ("timeout",):
            raise TimeoutError(f"{dependency}: injected timeout")
        if kind in ("unavailable", "partition"):
            raise Unavailable(f"{dependency}: injected {kind}")
        if kind == "crash":
            raise RuntimeError(f"{dependency}: injected crash")
        if kind == "exhaustion":
            raise MemoryError(f"{dependency}: injected exhaustion")
