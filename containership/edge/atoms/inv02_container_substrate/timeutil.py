"""MC44 — time and deadline abstraction.

All components take a :class:`Clock` so tests can inject :class:`FakeClock`, and all
blocking work takes a :class:`Deadline` derived from monotonic time (wall-clock jumps
never shorten or extend a timeout).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass


class Clock:
    def now(self) -> float:  # wall clock, seconds since epoch (for records)
        raise NotImplementedError

    def monotonic(self) -> float:  # for durations
        raise NotImplementedError

    def sleep(self, seconds: float) -> None:
        raise NotImplementedError


class SystemClock(Clock):
    def now(self) -> float:
        return time.time()

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


class FakeClock(Clock):
    """Deterministic clock for tests; ``sleep`` advances time instantly."""

    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self._t = start
        self._m = 0.0
        self._lock = threading.Lock()

    def now(self) -> float:
        with self._lock:
            return self._t

    def monotonic(self) -> float:
        with self._lock:
            return self._m

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._t += seconds
            self._m += seconds

    def sleep(self, seconds: float) -> None:
        self.advance(max(0.0, seconds))


class DeadlineExceeded(TimeoutError):
    code = "DEADLINE_EXCEEDED"


@dataclass(frozen=True)
class Deadline:
    expires_mono: float
    clock: Clock

    @classmethod
    def after(cls, seconds: float, clock: Clock | None = None) -> "Deadline":
        if seconds <= 0:
            raise ValueError("deadline must be positive")
        c = clock or SystemClock()
        return cls(c.monotonic() + seconds, c)

    def remaining(self) -> float:
        return max(0.0, self.expires_mono - self.clock.monotonic())

    def expired(self) -> bool:
        return self.remaining() <= 0.0

    def check(self, what: str = "operation") -> None:
        if self.expired():
            raise DeadlineExceeded(f"{what}: deadline exceeded")

    def child(self, seconds: float) -> "Deadline":
        """A sub-deadline that can never outlive its parent."""
        return Deadline(min(self.expires_mono, self.clock.monotonic() + seconds), self.clock)
