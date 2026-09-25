"""Controller ownership, leases and fencing tokens (WS 7).

Unit of exclusive ownership: **the host** (one writer per host).  Ownership is a lease in an
authoritative lease store; every acquisition increments a monotonically increasing ``epoch`` which is the
fencing token.  The token is sent on every provider mutation; providers that cannot enforce it are
fronted by the controller's own per-host single-writer check (``validate`` immediately before the
provider call and again before commit).

``FileLeaseStore`` gives a correct single-node/shared-filesystem implementation using ``fcntl.flock`` for
atomic compare-and-swap.  A multi-site deployment requires a consensus store (etcd/ZooKeeper/Consul);
that integration is BLOCKED (WS7-CONSENSUS) pending the ADR-0003 decision -- the ``LeaseStore`` protocol
is the seam.

Partition policy: when the lease cannot be renewed or validated the controller enters FROZEN_WRITE mode
(reads/audit continue, no mutations) -- isolation and reserve are preferred over availability.
"""
from __future__ import annotations

import fcntl
import json
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol

from . import errors as E


@dataclass(frozen=True)
class Lease:
    resource: str
    owner: str
    epoch: int
    expires_at: float


class LeaseStore(Protocol):
    def acquire(self, resource: str, owner: str, duration_s: float) -> Lease: ...
    def renew(self, lease: Lease, duration_s: float) -> Lease: ...
    def release(self, lease: Lease) -> None: ...
    def current(self, resource: str) -> Lease | None: ...


class FileLeaseStore:
    def __init__(self, directory: str | os.PathLike, *, clock=time.time) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self.available = True  # tests flip this to simulate partition from the lease store

    @contextmanager
    def _locked(self, resource: str) -> Iterator[Path]:
        if not self.available:
            raise E.NotOwner("lease store unreachable")
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in resource)[:128]
        path = self.dir / f"{safe}.lease"
        with open(self.dir / f"{safe}.lock", "a+") as lk:
            fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
            try:
                yield path
            finally:
                fcntl.flock(lk.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _read(path: Path) -> dict | None:
        if not path.exists():
            return None
        return json.loads(path.read_text())

    @staticmethod
    def _write(path: Path, doc: dict) -> None:
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w") as fh:
            json.dump(doc, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    def acquire(self, resource: str, owner: str, duration_s: float) -> Lease:
        with self._locked(resource) as path:
            doc = self._read(path) or {"epoch": 0, "owner": None, "expires_at": 0.0}
            now = self._clock()
            if doc["owner"] not in (None, owner) and doc["expires_at"] > now:
                raise E.NotOwner("resource is owned by another controller", resource=resource)
            doc = {"epoch": doc["epoch"] + 1, "owner": owner, "expires_at": now + duration_s}
            self._write(path, doc)
            return Lease(resource, owner, doc["epoch"], doc["expires_at"])

    def renew(self, lease: Lease, duration_s: float) -> Lease:
        with self._locked(lease.resource) as path:
            doc = self._read(path)
            now = self._clock()
            if not doc or doc["owner"] != lease.owner or doc["epoch"] != lease.epoch or doc["expires_at"] <= now:
                raise E.NotOwner("lease lost", resource=lease.resource, epoch=lease.epoch)
            doc["expires_at"] = now + duration_s
            self._write(path, doc)
            return Lease(lease.resource, lease.owner, lease.epoch, doc["expires_at"])

    def release(self, lease: Lease) -> None:
        with self._locked(lease.resource) as path:
            doc = self._read(path)
            if doc and doc["owner"] == lease.owner and doc["epoch"] == lease.epoch:
                doc["owner"], doc["expires_at"] = None, 0.0
                self._write(path, doc)

    def current(self, resource: str) -> Lease | None:
        with self._locked(resource) as path:
            doc = self._read(path)
            if not doc or doc["owner"] is None:
                return None
            return Lease(resource, doc["owner"], doc["epoch"], doc["expires_at"])


class Ownership:
    """Holds and validates this controller's lease for one host."""

    def __init__(self, store: LeaseStore, resource: str, controller_id: str, *, duration_s: float = 15.0,
                 clock=time.time, audit=None) -> None:
        self.store = store
        self.resource = resource
        self.controller_id = controller_id
        self.duration_s = duration_s
        self._clock = clock
        self._audit = audit or (lambda e: None)
        self.lease: Lease | None = None

    def acquire(self) -> Lease:
        self.lease = self.store.acquire(self.resource, self.controller_id, self.duration_s)
        self._audit({"kind": "ownership_acquired", "owner": self.controller_id, "epoch": self.lease.epoch})
        return self.lease

    def renew(self) -> Lease:
        if self.lease is None:
            raise E.NotOwner("no lease held")
        try:
            self.lease = self.store.renew(self.lease, self.duration_s)
        except E.NotOwner:
            self._audit({"kind": "ownership_renew_failed", "owner": self.controller_id,
                         "epoch": self.lease.epoch})
            self.lease = None
            raise
        return self.lease

    def release(self) -> None:
        if self.lease is not None:
            self.store.release(self.lease)
            self._audit({"kind": "ownership_released", "owner": self.controller_id, "epoch": self.lease.epoch})
            self.lease = None

    def validate(self) -> int:
        """Return the fencing token if ownership is provably current; raise otherwise."""
        lease = self.lease
        if lease is None or lease.expires_at <= self._clock():
            raise E.NotOwner("lease absent or expired")
        cur = self.store.current(self.resource)
        if cur is None or cur.owner != self.controller_id or cur.epoch != lease.epoch:
            self._audit({"kind": "stale_write_rejected", "owner": self.controller_id, "epoch": lease.epoch})
            raise E.FencingRejected("a newer controller owns this host", epoch=lease.epoch)
        return lease.epoch

    @property
    def epoch(self) -> int | None:
        return self.lease.epoch if self.lease else None

    def age_s(self) -> float:
        return 0.0 if self.lease is None else max(0.0, self.duration_s - (self.lease.expires_at - self._clock()))


class GuestLocks:
    """Per-guest serialization: conflicting mutations on one guest never run concurrently."""

    def __init__(self) -> None:
        self._locks: dict[str, threading.Lock] = {}
        self._meta = threading.Lock()

    @contextmanager
    def hold(self, guest: str, *, timeout: float = 0.0) -> Iterator[None]:
        with self._meta:
            lock = self._locks.setdefault(guest, threading.Lock())
        acquired = lock.acquire(timeout=timeout) if timeout > 0 else lock.acquire(blocking=False)
        if not acquired:
            raise E.GuestBusy("another mutation is in flight for this guest", guest=guest)
        try:
            yield
        finally:
            lock.release()
