"""Trusted-time integration for PLN-07 (MC-12).

The verifier never reads the wall clock itself.  ``TrustedClock`` wraps one or
more time sources, enforces monotonicity, detects rollback, bounds disagreement
between sources and fails closed when trustworthy time is unavailable.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Sequence

from .grants import SecurityPlaneError

TimeSource = Callable[[], int]


class TimeUnavailable(SecurityPlaneError):
    code = "time.unavailable"


class TimeRollback(SecurityPlaneError):
    code = "time.rollback"


def system_seconds() -> int:
    """Reference source: integer UNIX seconds from the host clock."""
    return int(time.time())


@dataclass
class TrustedClock:
    """Quorum-of-sources monotonic clock.

    * ``sources`` - callables returning integer seconds; at least ``quorum`` must
      answer for ``now()`` to succeed.
    * ``max_disagreement`` - the answering sources must agree within this many
      seconds, otherwise time is treated as untrustworthy.
    * ``max_rollback`` - a reading earlier than the last issued value by more
      than this raises :class:`TimeRollback`; smaller regressions are clamped
      (monotonic output).
    """

    sources: Sequence[TimeSource] = field(default_factory=lambda: (system_seconds,))
    quorum: int = 1
    max_disagreement: int = 5
    max_rollback: int = 2
    _last: int = field(default=-1, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("at least one time source is required")
        if not 1 <= self.quorum <= len(self.sources):
            raise ValueError("quorum must be between 1 and the number of sources")
        if self.max_disagreement < 0 or self.max_rollback < 0:
            raise ValueError("tolerances must be non-negative")

    def _read(self) -> list[int]:
        readings: list[int] = []
        for source in self.sources:
            try:
                value = source()
            except Exception:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                continue
            readings.append(value)
        return readings

    def now(self) -> int:
        readings = self._read()
        if len(readings) < self.quorum:
            raise TimeUnavailable(
                "trusted time unavailable", details={"answered": len(readings), "quorum": self.quorum}
            )
        if max(readings) - min(readings) > self.max_disagreement:
            raise TimeUnavailable(
                "time sources disagree", details={"spread": max(readings) - min(readings)}
            )
        readings.sort()
        median = readings[len(readings) // 2]
        with self._lock:
            if self._last >= 0 and median < self._last:
                if self._last - median > self.max_rollback:
                    raise TimeRollback(
                        "clock rolled back", details={"last": self._last, "observed": median}
                    )
                median = self._last
            self._last = median
            return median

    def status(self) -> dict:
        try:
            return {"state": "ok", "now": self.now()}
        except SecurityPlaneError as exc:
            return {"state": "unavailable", **exc.as_dict()}
