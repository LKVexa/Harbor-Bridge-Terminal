"""Leader election with fencing tokens and split-brain protection (item 33).

Lease semantics follow coordination.k8s.io/v1 Lease: holder, renewTime,
duration, and a monotonically increasing transitions counter used as the
fencing token. The downstream adapter rejects writes carrying a stale fencing
token, so a paused ex-leader that wakes up cannot launch or cancel anything.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class Lease:
    holder: str = ""
    renew: float = 0.0
    duration: float = 15.0
    transitions: int = 0
    version: int = 0


class LeaseStore:
    """CAS store standing in for the API server's Lease object."""

    def __init__(self):
        self._lock = threading.Lock()
        self.lease = Lease()
        self.down = False

    def read(self) -> Lease:
        if self.down:
            raise ConnectionError("lease store unreachable")
        with self._lock:
            return Lease(**vars(self.lease))

    def cas(self, expected_version: int, new: Lease) -> bool:
        if self.down:
            raise ConnectionError("lease store unreachable")
        with self._lock:
            if self.lease.version != expected_version:
                return False
            new.version = expected_version + 1
            self.lease = new
            return True


class Elector:
    def __init__(self, store: LeaseStore, identity: str, duration: float = 15.0, clock=time.monotonic):
        self.store, self.id, self.duration, self.clock = store, identity, duration, clock
        self.token: int | None = None
        self.valid_until = 0.0

    def try_acquire_or_renew(self) -> bool:
        now = self.clock()
        try:
            cur = self.store.read()
        except ConnectionError:
            return self._lose_if_expired(now)
        if cur.holder == self.id or cur.holder == "" or now - cur.renew > cur.duration:
            transitions = cur.transitions if cur.holder == self.id else cur.transitions + 1
            new = Lease(self.id, now, self.duration, transitions)
            try:
                ok = self.store.cas(cur.version, new)
            except ConnectionError:
                return self._lose_if_expired(now)
            if ok:
                self.token, self.valid_until = transitions, now + self.duration * 0.8
                return True
        self.token = None
        return False

    def _lose_if_expired(self, now) -> bool:
        # Renewal failed: keep leadership only inside our own safety margin.
        if self.token is not None and now < self.valid_until:
            return True
        self.token = None
        return False

    def is_leader(self) -> bool:
        return self.token is not None and self.clock() < self.valid_until

    def release(self):
        try:
            cur = self.store.read()
            if cur.holder == self.id:
                self.store.cas(cur.version, Lease("", 0.0, self.duration, cur.transitions))
        except ConnectionError:
            pass
        self.token = None


class FenceGuard:
    """Downstream-side guard: highest fencing token seen wins."""

    def __init__(self):
        self.highest = -1
        self._lock = threading.Lock()

    def admit(self, token: int | None) -> bool:
        with self._lock:
            if token is None or token < self.highest:
                return False
            self.highest = token
            return True
