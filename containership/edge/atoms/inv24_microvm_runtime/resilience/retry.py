"""Deadlines, cancellation, bounded retry with jittered backoff (MC-028)."""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from ..errors import Inv24Error

T = TypeVar("T")


class CancelToken:
    def __init__(self) -> None:
        self._ev = threading.Event()
        self.reason = ""

    def cancel(self, reason: str = "cancelled") -> None:
        self.reason = reason
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()

    def wait(self, seconds: float) -> bool:
        return self._ev.wait(seconds)


@dataclass(frozen=True, slots=True)
class Deadline:
    expires_at: float

    @classmethod
    def after_ms(cls, ms: int, clock=time.monotonic) -> "Deadline":
        if isinstance(ms, bool) or not isinstance(ms, int) or not 0 < ms <= 600_000:
            raise Inv24Error("CONFIG_REJECTED", "deadline must be 1..600000 ms")
        return cls(clock() + ms / 1000)

    def remaining(self, clock=time.monotonic) -> float:
        return self.expires_at - clock()

    def check(self, clock=time.monotonic) -> None:
        if self.remaining(clock) <= 0:
            raise Inv24Error("TIMEOUT", "deadline elapsed")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 4
    base_s: float = 0.05
    cap_s: float = 2.0

    def delay(self, attempt: int, rng: random.Random) -> float:
        # "full jitter": uniform(0, min(cap, base*2^attempt))
        return rng.uniform(0, min(self.cap_s, self.base_s * (2 ** attempt)))


def retry(fn: Callable[[], T], *, policy: RetryPolicy = RetryPolicy(), deadline: Deadline | None = None,
          cancel: CancelToken | None = None, rng: random.Random | None = None,
          on_retry: Callable[[int, Inv24Error], None] | None = None) -> T:
    """Retry only errors whose code is declared retryable; never past the deadline."""
    rng = rng or random.Random()
    cancel = cancel or CancelToken()
    for attempt in range(policy.max_attempts):
        if cancel.cancelled:
            raise Inv24Error("CANCELLED", cancel.reason)
        if deadline:
            deadline.check()
        try:
            return fn()
        except Inv24Error as exc:
            if not exc.retryable or attempt == policy.max_attempts - 1:
                raise
            wait = policy.delay(attempt, rng)
            if deadline and wait >= deadline.remaining():
                raise Inv24Error("TIMEOUT", f"retry budget exhausted after {attempt + 1} attempts: {exc.code}") from exc
            if on_retry:
                on_retry(attempt + 1, exc)
            if cancel.wait(wait):
                raise Inv24Error("CANCELLED", cancel.reason) from exc
    raise Inv24Error("TIMEOUT", "retry loop exhausted")  # pragma: no cover
