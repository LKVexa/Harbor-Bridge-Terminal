"""Retry/backoff/jitter engine and circuit breaker (component 16).

Retries are permitted only for operations declared idempotent (``Idempotent``
marker or a deduplicated command id).  Every retry loop has both an attempt cap
and a total deadline; delays use *full jitter* (``uniform(0, min(cap, base*2^n))``)
so a reconnect storm does not synchronise.  ``CircuitBreaker`` is keyed per
node/site cohort so one failing site cannot consume the whole retry budget.
"""
from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from .common import Clock, SystemClock
from .errors import CircuitOpen, Gap08Error, Retry, Timeout, ValidationFailed

T = TypeVar("T")


@dataclass(frozen=True)
class BackoffPolicy:
    base_s: float = 0.5
    cap_s: float = 30.0
    max_attempts: int = 5
    deadline_s: float = 120.0

    def __post_init__(self) -> None:
        if not (0 < self.base_s <= self.cap_s) or self.max_attempts < 1 or self.deadline_s <= 0:
            raise ValidationFailed("invalid backoff policy")

    def delay(self, attempt: int, rng: random.Random) -> float:
        return rng.uniform(0, min(self.cap_s, self.base_s * (2 ** attempt)))


def retry_call(fn: Callable[[], T], *, idempotent: bool, policy: BackoffPolicy = BackoffPolicy(),
               clock: Clock | None = None, sleep: Callable[[float], None] | None = None,
               rng: random.Random | None = None, breaker: "CircuitBreaker | None" = None,
               cohort: str = "default") -> T:
    if not idempotent:
        policy = BackoffPolicy(policy.base_s, policy.cap_s, 1, policy.deadline_s)
    clock = clock or SystemClock()
    rng = rng or random.Random()
    sleep = sleep or (lambda s: None)
    start = clock.monotonic()
    last: BaseException | None = None
    for attempt in range(policy.max_attempts):
        if breaker is not None:
            breaker.before(cohort)
        try:
            result = fn()
        except Gap08Error as exc:
            last = exc
            if breaker is not None:
                breaker.failure(cohort)
            if exc.spec.retry not in (Retry.SAFE, Retry.UNKNOWN_OUTCOME):
                raise
        else:
            if breaker is not None:
                breaker.success(cohort)
            return result
        d = policy.delay(attempt, rng)
        if clock.monotonic() - start + d > policy.deadline_s:
            break
        sleep(d)
        if hasattr(clock, "advance"):
            clock.advance(d)  # FakeClock support
    raise Timeout(f"gave up after {policy.max_attempts} attempts / {policy.deadline_s}s", cause=last)


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    reset_timeout_s: float = 60.0
    clock: Clock = field(default_factory=SystemClock)
    _state: dict[str, tuple[str, int, float]] = field(default_factory=dict)  # cohort -> (state, failures, opened_at)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def state(self, cohort: str) -> str:
        with self._lock:
            st, _, opened = self._state.get(cohort, ("closed", 0, 0.0))
            if st == "open" and self.clock.monotonic() - opened >= self.reset_timeout_s:
                return "half_open"
            return st

    def before(self, cohort: str) -> None:
        st = self.state(cohort)
        if st == "open":
            raise CircuitOpen(f"circuit open for cohort {cohort}", resource=cohort)
        if st == "half_open":
            with self._lock:
                _, f, _ = self._state[cohort]
                self._state[cohort] = ("half_open", f, self.clock.monotonic())

    def failure(self, cohort: str) -> None:
        with self._lock:
            st, f, opened = self._state.get(cohort, ("closed", 0, 0.0))
            f += 1
            if st == "half_open" or f >= self.failure_threshold:
                self._state[cohort] = ("open", f, self.clock.monotonic())
            else:
                self._state[cohort] = (st, f, opened)

    def success(self, cohort: str) -> None:
        with self._lock:
            self._state[cohort] = ("closed", 0, 0.0)
