"""MC-009 -- wall / monotonic clock providers with precision policy.

Separate providers, each gated by its own capability.  Precision is reduced by
quantising to ``resolution_ns`` (floor) so fine timing side channels are not
exposed; the monotonic provider additionally never goes backwards.  A replay
mode serves a recorded tape and is refused unless the host is started with an
explicit non-production profile.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Iterable

from .errors import ErrorCode, Inv13Error

MIN_RESOLUTION_NS = 1_000  # 1 us floor unless policy asks for coarser


class _Quantised:
    def __init__(self, source: Callable[[], int], resolution_ns: int) -> None:
        if resolution_ns < MIN_RESOLUTION_NS:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT, "resolution below floor")
        self._src, self.resolution_ns = source, resolution_ns

    def _q(self) -> int:
        return (self._src() // self.resolution_ns) * self.resolution_ns


class WallClock(_Quantised):
    def __init__(self, resolution_ns: int = 1_000_000, source: Callable[[], int] = time.time_ns) -> None:
        super().__init__(source, resolution_ns)

    def now(self) -> tuple[int, int]:
        ns = self._q()
        return ns // 1_000_000_000, ns % 1_000_000_000


class MonotonicClock(_Quantised):
    def __init__(self, resolution_ns: int = 1_000_000, source: Callable[[], int] = time.monotonic_ns) -> None:
        super().__init__(source, resolution_ns)
        self._last = 0
        self._lock = threading.Lock()

    def now(self) -> int:
        with self._lock:
            self._last = max(self._last, self._q())
            return self._last


class ReplayClock:
    """Deterministic tape; construction requires profile != 'production'."""

    def __init__(self, tape: Iterable[int], *, profile: str) -> None:
        if profile == "production":
            raise Inv13Error(ErrorCode.POLICY_DENIED, "replay clock disabled in production")
        self._tape, self._last = list(tape), None

    def now(self) -> int:
        if not self._tape:
            raise Inv13Error(ErrorCode.PROVIDER_UNAVAILABLE, "tape exhausted")
        self._last = self._tape.pop(0)
        return self._last
