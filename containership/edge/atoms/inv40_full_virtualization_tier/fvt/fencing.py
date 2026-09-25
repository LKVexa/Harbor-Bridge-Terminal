"""Controller leases with monotonically increasing fencing epochs
(INV-40-C058, C055).  A controller that lost its lease (partition, GC pause,
failover) holds a stale epoch; every mutating call presents its epoch and the
tier rejects anything older than the highest epoch it has seen, so two
controllers can never both mutate the same guest (no split-brain).

The lease table here is process-local; a multi-node deployment must back it
with a linearizable store (INV-33 virtualization controller holds the lease).
That binding is recorded as blocker DIST-STORE.
"""
from __future__ import annotations

import threading
import time

from .errors import OpError


class LeaseTable:
    def __init__(self, ttl_s: float = 10.0, clock=time.monotonic):
        self.ttl_s, self.clock = ttl_s, clock
        self._lock = threading.Lock()
        self._epoch = 0
        self._holder: tuple[str, int, float] | None = None
        self.highest_seen = 0

    def acquire(self, controller: str) -> int:
        with self._lock:
            now = self.clock()
            if self._holder and self._holder[0] != controller and now < self._holder[2]:
                raise OpError("PK_FULL_VM_STALE_OWNER", "lease held by another controller", holder=self._holder[0])
            if not self._holder or self._holder[0] != controller or now >= self._holder[2]:
                self._epoch += 1
            self._holder = (controller, self._epoch, now + self.ttl_s)
            return self._epoch

    def check(self, controller: str, epoch: int) -> None:
        with self._lock:
            if epoch < self.highest_seen or not self._holder or self._holder[1] != epoch \
                    or self._holder[0] != controller or self.clock() >= self._holder[2]:
                raise OpError("PK_FULL_VM_STALE_OWNER", "stale or expired fencing token",
                              presented=epoch, current=self._holder[1] if self._holder else None)
            self.highest_seen = epoch
