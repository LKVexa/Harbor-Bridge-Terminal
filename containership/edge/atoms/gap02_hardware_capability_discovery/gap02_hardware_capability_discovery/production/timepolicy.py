"""GAP02-MC-12 — Trusted time policy.

``TrustedClock`` anchors wall time to the monotonic clock at a trusted sync
point. It refuses to issue time when: never synced, the sync is older than
``max_sync_age``, the source quality is below policy, or wall time has moved
against monotonic time by more than ``skew_tolerance`` (rollback/jump).
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable

from .errors import Code, Gap02Error

QUALITY = {"unsynced": 0, "local-rtc": 1, "ntp": 2, "nts": 3, "ptp": 3, "attested": 4}


@dataclass
class TimePolicy:
    min_quality: str = "ntp"
    skew_tolerance: int = 5          # seconds
    max_sync_age: int = 3600          # seconds of monotonic time since last trusted sync
    signature_skew: int = 30          # accepted future-dating of a signed envelope

    def __post_init__(self) -> None:
        if self.min_quality not in QUALITY:
            raise Gap02Error(Code.CONFIG_INVALID, f"quality {self.min_quality}")


class TrustedClock:
    def __init__(self, policy: TimePolicy | None = None, *,
                 wall: Callable[[], float] = time.time, mono: Callable[[], float] = time.monotonic):
        self.policy = policy or TimePolicy()
        self._wall, self._mono = wall, mono
        self._anchor: tuple[float, float, str] | None = None
        self._last_issued = -1

    def sync(self, trusted_epoch: float, source: str) -> None:
        if source not in QUALITY:
            raise Gap02Error(Code.CONFIG_INVALID, f"time source {source}")
        self._anchor = (float(trusted_epoch), self._mono(), source)

    def now(self) -> int:
        if self._anchor is None:
            raise Gap02Error(Code.CLOCK_UNTRUSTED, "clock never synchronised")
        epoch, m0, src = self._anchor
        if QUALITY[src] < QUALITY[self.policy.min_quality]:
            raise Gap02Error(Code.CLOCK_UNTRUSTED, f"source {src} below {self.policy.min_quality}")
        elapsed = self._mono() - m0
        if elapsed > self.policy.max_sync_age:
            raise Gap02Error(Code.CLOCK_UNTRUSTED, "trusted sync expired")
        derived = epoch + elapsed
        drift = self._wall() - derived
        if abs(drift) > self.policy.skew_tolerance:
            raise Gap02Error(Code.CLOCK_UNTRUSTED, f"wall/monotonic divergence {drift:.1f}s (rollback or jump)")
        t = int(derived)
        if t < self._last_issued:  # never issue a decreasing timestamp
            raise Gap02Error(Code.CLOCK_UNTRUSTED, "issued time would decrease")
        self._last_issued = t
        return t

    def check_signed_at(self, signed_at: int, now: int, max_age: int) -> None:
        if signed_at > now + self.policy.signature_skew:
            raise Gap02Error(Code.CLOCK_UNTRUSTED, "envelope signed in the future")
        if now - signed_at > max_age:
            raise Gap02Error(Code.STALE_DATA, f"envelope age {now - signed_at}s > {max_age}s")
