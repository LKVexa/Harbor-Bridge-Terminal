"""Replication/failover primitive (39): lease + fencing epochs.

Only one writer per partition may hold the lease; every write carries the
epoch it was granted, and the replica refuses any write with an epoch lower
than the highest it has seen.  This is the split-brain guard the real
multi-site replication must build on; the multi-node consensus itself is NOT
implemented here (component 39 integration stays BLOCKED).
"""
from __future__ import annotations

import threading

from .errors import Unauthorized


class LeaseAuthority:
    def __init__(self, ttl: int) -> None:
        self.ttl = ttl
        self._lock = threading.Lock()
        self._holder: dict[str, tuple[str, int, int]] = {}  # partition -> (node, epoch, expires)
        self._epoch: dict[str, int] = {}

    def acquire(self, partition: str, node: str, now: int) -> int:
        with self._lock:
            h = self._holder.get(partition)
            if h and h[0] != node and now < h[2]:
                raise Unauthorized("lease held by another node", holder=h[0])
            if h and h[0] == node and now < h[2]:
                self._holder[partition] = (node, h[1], now + self.ttl)
                return h[1]
            e = self._epoch.get(partition, 0) + 1
            self._epoch[partition] = e
            self._holder[partition] = (node, e, now + self.ttl)
            return e


class FencedReplica:
    def __init__(self) -> None:
        self._high: dict[str, int] = {}
        self.data: dict[tuple, object] = {}
        self._lock = threading.Lock()

    def write(self, partition: str, epoch: int, key, value) -> None:
        with self._lock:
            if epoch < self._high.get(partition, 0):
                raise Unauthorized("stale fencing epoch refused", epoch=epoch)
            self._high[partition] = epoch
            self.data[(partition, key)] = value
