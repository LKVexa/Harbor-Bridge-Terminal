"""Leader election with fencing tokens (component 5).

A ``Lease`` lives in the ``VersionedStore`` (kind ``Lease``) and is updated with
compare-and-swap, so two candidates can never both win the same term.  Every
successful acquisition increments ``fencing_token``; mutating calls carry the
token and ``FencingGuard.check`` rejects any token lower than the highest one
seen, which closes the split-brain window of a paused ex-leader.
"""
from __future__ import annotations

import threading
import time
from typing import Callable

from .errors import AlreadyExists, Conflict, FencedOut, NotFound, NotLeader
from .store import VersionedStore


class LeaderElector:
    def __init__(self, store: VersionedStore, name: str, identity: str, *, lease_seconds: float = 15.0,
                 renew_deadline: float = 10.0, clock: Callable[[], float] = time.time):
        if renew_deadline >= lease_seconds:
            raise ValueError("renew_deadline must be shorter than lease_seconds")
        self.store, self.name, self.identity = store, name, identity
        self.lease_seconds, self.renew_deadline, self.clock = lease_seconds, renew_deadline, clock
        self.token = 0
        self.last_renew = 0.0
        self._lock = threading.Lock()

    def try_acquire_or_renew(self) -> bool:
        now = self.clock()
        with self._lock:
            try:
                rec = self.store.get("Lease", self.name)
            except NotFound:
                spec = {"holder": self.identity, "renew": now, "duration": self.lease_seconds, "token": 1}
                try:
                    self.store.create("Lease", self.name, spec)
                except AlreadyExists:
                    return False
                self.token, self.last_renew = 1, now
                return True
            spec = rec.spec
            held_by_other = spec["holder"] != self.identity
            expired = now - spec["renew"] > spec["duration"]
            if held_by_other and not expired:
                self.token = 0
                return False
            token = spec["token"] + (1 if held_by_other or self.token != spec["token"] else 0)
            new = {"holder": self.identity, "renew": now, "duration": self.lease_seconds, "token": token}
            try:
                self.store.update("Lease", self.name, new, expected_rv=rec.resource_version)
            except Conflict:
                self.token = 0
                return False
            self.token, self.last_renew = token, now
            return True

    def is_leader(self) -> bool:
        """Leader only while within renew_deadline of last successful renewal."""
        return self.token > 0 and (self.clock() - self.last_renew) < self.renew_deadline

    def require_leader(self) -> int:
        if not self.is_leader():
            raise NotLeader(f"{self.identity} is not the active controller for {self.name}")
        return self.token

    def release(self) -> None:
        with self._lock:
            try:
                rec = self.store.get("Lease", self.name)
            except NotFound:
                return
            if rec.spec["holder"] == self.identity:
                spec = dict(rec.spec, renew=0.0)
                try:
                    self.store.update("Lease", self.name, spec, expected_rv=rec.resource_version)
                except Conflict:
                    pass
            self.token = 0


class FencingGuard:
    """Rejects writes carrying a fencing token older than the newest observed."""

    def __init__(self) -> None:
        self.highest = 0
        self._lock = threading.Lock()

    def check(self, token: int) -> None:
        with self._lock:
            if token <= 0 or token < self.highest:
                raise FencedOut(f"fencing token {token} is stale (highest {self.highest})",
                                details={"token": token, "highest": self.highest})
            self.highest = token
