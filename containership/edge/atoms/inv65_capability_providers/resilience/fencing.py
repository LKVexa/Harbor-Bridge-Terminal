"""Lease/epoch fencing (M17).  A ``LeaseManager`` grants a time-bounded lease
with a monotonically increasing epoch per slot.  Every state-mutating action
must present the current epoch; a stale controller (old epoch, or expired
lease) is fenced with PK_PROVIDER_FENCED, preventing split-brain double
ownership even if the old owner is still running."""
from __future__ import annotations

import threading
import time

from ..errors.mapping import ProviderFault


class LeaseManager:
    def __init__(self, ttl_s: float = 10.0, *, clock=time.monotonic):
        self.ttl, self._clock = ttl_s, clock
        self._slots: dict[str, tuple[str, int, float]] = {}
        self._lock = threading.Lock()

    def acquire(self, slot: str, holder: str) -> int:
        with self._lock:
            cur = self._slots.get(slot)
            now = self._clock()
            if cur and cur[0] != holder and cur[2] > now:
                raise ProviderFault("PK_PROVIDER_FENCED", f"{slot} leased by another holder")
            epoch = (cur[1] + 1) if cur else 1
            if cur and cur[0] == holder and cur[2] > now:
                epoch = cur[1]
            self._slots[slot] = (holder, epoch, now + self.ttl)
            return epoch

    def renew(self, slot: str, holder: str, epoch: int) -> None:
        self.validate(slot, holder, epoch)
        with self._lock:
            self._slots[slot] = (holder, epoch, self._clock() + self.ttl)

    def validate(self, slot: str, holder: str, epoch: int) -> None:
        with self._lock:
            cur = self._slots.get(slot)
            if not cur or cur[0] != holder or cur[1] != epoch or cur[2] <= self._clock():
                raise ProviderFault("PK_PROVIDER_FENCED", f"stale or expired lease on {slot}")

    def release(self, slot: str, holder: str, epoch: int) -> None:
        with self._lock:
            cur = self._slots.get(slot)
            if cur and cur[0] == holder and cur[1] == epoch:
                self._slots[slot] = (holder, epoch, 0.0)  # keep epoch so next owner increments
