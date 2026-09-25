"""MC-10: authoritative time.  All security decisions take time from a
``TrustedClock``; when trusted time is unavailable or skew exceeds budget the
clock raises E_TIME_UNTRUSTED and callers fail closed."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from .errors import fail


@dataclass
class TrustedClock:
    """Wall time anchored to an authoritative source plus the local monotonic clock.

    ``sync(authoritative_epoch)`` records an anchor; ``now()`` = anchor + monotonic
    elapsed.  ``now()`` refuses before the first sync, after ``max_unsynced`` seconds,
    and when a new sync disagrees with the local projection by more than
    ``skew_budget`` (the clock is then poisoned until ``reset_after_review``)."""
    skew_budget: float = 2.0
    max_unsynced: float = 3600.0
    monotonic: callable = time.monotonic
    _anchor: tuple | None = None
    _poisoned: bool = False
    _last_issued: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def sync(self, authoritative_epoch: float) -> None:
        with self._lock:
            m = self.monotonic()
            if self._anchor is not None:
                projected = self._anchor[0] + (m - self._anchor[1])
                if abs(projected - authoritative_epoch) > self.skew_budget:
                    self._poisoned = True
                    raise fail("E_TIME_UNTRUSTED", "authoritative time disagrees beyond skew budget")
            self._anchor = (authoritative_epoch, m)

    def reset_after_review(self) -> None:
        with self._lock:
            self._poisoned, self._anchor = False, None

    def now(self) -> float:
        with self._lock:
            if self._poisoned:
                raise fail("E_TIME_UNTRUSTED", "clock poisoned by skew violation")
            if self._anchor is None:
                raise fail("E_TIME_UNTRUSTED", "no authoritative time sync yet")
            m = self.monotonic()
            if m - self._anchor[1] > self.max_unsynced:
                raise fail("E_TIME_UNTRUSTED", "authoritative sync too old")
            t = self._anchor[0] + (m - self._anchor[1])
            t = max(t, self._last_issued)  # never issue a decreasing time
            self._last_issued = t
            return t


class FakeMonotonic:
    """Test helper: controllable monotonic source."""
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt
