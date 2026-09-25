"""Bounded retry with jitter and a hysteretic circuit breaker (C053, C054).

These apply to *adapters* only.  Local terminal resolution is never retried:
``resolve`` either wins once or raises; repeating it is a caller defect.
Retries of wire resolutions are safe only because every message carries an
idempotency key that the endpoint de-duplicates.
"""
from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

from .errors import FutureError, Rejected, from_exception

T = TypeVar("T")
NON_RETRYABLE_LOCAL = ("resolve", "resolve_error", "abandon", "take", "cancel")


class RetryPolicy:
    def __init__(self, *, max_attempts: int = 3, base_delay_s: float = 0.05, max_delay_s: float = 1.0,
                 max_total_s: float = 5.0, seed: int | None = None, sleep=time.sleep, clock=time.monotonic):
        if max_attempts < 1:
            raise ValueError("max_attempts >= 1")
        self.max_attempts, self.base, self.cap, self.total = max_attempts, base_delay_s, max_delay_s, max_total_s
        self._rng = random.Random(seed)
        self._sleep, self._clock = sleep, clock
        self.attempts_made = 0

    def delay(self, attempt: int) -> float:
        """Full-jitter exponential backoff."""
        return self._rng.uniform(0, min(self.cap, self.base * (2 ** attempt)))

    def call(self, fn: Callable[[], T], *, deadline: float | None = None, cancelled: Callable[[], bool] = lambda: False,
             on_retry: Callable[[int, BaseException], None] | None = None) -> T:
        start = self._clock()
        last: BaseException | None = None
        for attempt in range(self.max_attempts):
            if cancelled():
                raise Rejected("retry cancelled", code="FUTURE_CANCELLED")
            self.attempts_made = attempt + 1
            try:
                return fn()
            except BaseException as exc:  # noqa: BLE001 - classified below
                rec = from_exception(exc)
                if not rec.retryable:
                    raise
                last = exc
                if attempt + 1 >= self.max_attempts:
                    break
                d = self.delay(attempt)
                now = self._clock()
                limit = start + self.total if deadline is None else min(start + self.total, deadline)
                if now + d > limit:
                    break
                if on_retry:
                    on_retry(attempt + 1, exc)
                self._sleep(d)
        raise Rejected("retry budget exhausted", code="DEPENDENCY_UNAVAILABLE",
                       details={"attempts": self.attempts_made}) from last


CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 5, reset_s: float = 1.0, close_successes: int = 2,
                 clock=time.monotonic):
        self.threshold, self.reset_s, self.close_successes = failure_threshold, reset_s, close_successes
        self._clock = clock
        self.state = CLOSED
        self.failures = 0
        self.successes = 0
        self.opened_at = 0.0
        self.transitions: list[str] = []

    def _to(self, s: str) -> None:
        if s != self.state:
            self.transitions.append(f"{self.state}->{s}")
            self.state = s

    def allow(self) -> bool:
        if self.state == OPEN and self._clock() - self.opened_at >= self.reset_s:
            self._to(HALF_OPEN)
            self.successes = 0
        return self.state != OPEN

    def record(self, ok: bool) -> None:
        if ok:
            if self.state == HALF_OPEN:
                self.successes += 1
                if self.successes >= self.close_successes:   # hysteresis
                    self._to(CLOSED)
                    self.failures = 0
            else:
                self.failures = 0
        else:
            if self.state == HALF_OPEN:
                self._to(OPEN)
                self.opened_at = self._clock()
            else:
                self.failures += 1
                if self.failures >= self.threshold:
                    self._to(OPEN)
                    self.opened_at = self._clock()

    def call(self, fn: Callable[[], T]) -> T:
        if not self.allow():
            raise Rejected("circuit open", code="DEPENDENCY_UNAVAILABLE")
        try:
            r = fn()
        except FutureError as exc:
            self.record(not exc.record().retryable)
            raise
        except BaseException:
            self.record(False)
            raise
        self.record(True)
        return r
