"""Lease lock with fencing tokens (MC-011 package-local reference).

``FileLeaseLock`` gives cross-process mutual exclusion on one host (or on a
shared filesystem with atomic ``O_EXCL`` create and ``rename`` semantics).
Each acquisition returns a strictly increasing *fencing token*; a
``FencedBackend`` wrapper refuses writes carrying a token older than the
highest one it has seen, so a paused writer whose lease expired cannot commit
after a new holder took over (stale-writer / split-brain protection).

Cross-site consensus (etcd/Consul/DynamoDB-style) remains an estate backend;
``LeaseBackend`` is the protocol such adapters implement.
"""
from __future__ import annotations

import json
import os
import pathlib
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .state import IacError


class LockUnavailable(IacError):
    code = "PK_IAC_LOCK_UNAVAILABLE"


class LeaseLost(IacError):
    code = "PK_IAC_LEASE_LOST"


class FencingViolation(IacError):
    code = "PK_IAC_FENCING_VIOLATION"


@dataclass(frozen=True)
class Lease:
    holder: str
    token: int
    expires_at: float
    lease_id: str


class LeaseBackend(Protocol):
    def acquire(self, holder: str, ttl: float) -> Lease: ...
    def renew(self, lease: Lease, ttl: float) -> Lease: ...
    def release(self, lease: Lease) -> None: ...
    def current(self) -> Lease | None: ...


class FileLeaseLock:
    """File-based lease lock.  ``clock`` is injectable for deterministic tests."""

    def __init__(self, root: str | os.PathLike[str], *, clock: Callable[[], float] = time.time) -> None:
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lease_path = self.root / "LEASE"
        self.guard_path = self.root / "LEASE.guard"
        self.token_path = self.root / "FENCE"
        self.clock = clock

    # A tiny O_EXCL guard serialises read-modify-write of the lease file.
    def _guard(self, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fd = os.open(str(self.guard_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return
            except FileExistsError:
                try:  # break a guard abandoned by a crashed process
                    if time.time() - self.guard_path.stat().st_mtime > timeout:
                        self.guard_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() > deadline:
                    raise LockUnavailable("lease guard busy")
                time.sleep(0.002)

    def _unguard(self) -> None:
        self.guard_path.unlink(missing_ok=True)

    def _read(self) -> Lease | None:
        try:
            d = json.loads(self.lease_path.read_text("utf-8"))
            return Lease(d["holder"], int(d["token"]), float(d["expires_at"]), d["lease_id"])
        except (FileNotFoundError, ValueError, KeyError):
            return None

    def _write(self, lease: Lease | None) -> None:
        from .durable import atomic_write

        if lease is None:
            self.lease_path.unlink(missing_ok=True)
            return
        atomic_write(self.lease_path, json.dumps(lease.__dict__, sort_keys=True).encode())

    def _next_token(self) -> int:
        from .durable import atomic_write

        try:
            tok = int(self.token_path.read_text().strip()) + 1
        except (FileNotFoundError, ValueError):
            tok = 1
        atomic_write(self.token_path, str(tok).encode())
        return tok

    def current(self) -> Lease | None:
        lease = self._read()
        if lease and lease.expires_at <= self.clock():
            return None
        return lease

    def acquire(self, holder: str, ttl: float = 30.0) -> Lease:
        if not holder or ttl <= 0:
            raise LockUnavailable("holder and positive ttl required")
        self._guard()
        try:
            cur = self._read()
            if cur and cur.expires_at > self.clock() and cur.holder != holder:
                raise LockUnavailable("lease held", details={"holder": cur.holder, "expires_at": cur.expires_at})
            lease = Lease(holder, self._next_token(), self.clock() + ttl, uuid.uuid4().hex)
            self._write(lease)
            return lease
        finally:
            self._unguard()

    def renew(self, lease: Lease, ttl: float = 30.0) -> Lease:
        self._guard()
        try:
            cur = self._read()
            if not cur or cur.lease_id != lease.lease_id or cur.expires_at <= self.clock():
                raise LeaseLost("lease expired or taken over", details={"token": lease.token})
            new = Lease(cur.holder, cur.token, self.clock() + ttl, cur.lease_id)
            self._write(new)
            return new
        finally:
            self._unguard()

    def release(self, lease: Lease) -> None:
        self._guard()
        try:
            cur = self._read()
            if cur and cur.lease_id == lease.lease_id:
                self._write(None)
        finally:
            self._unguard()


class FencedBackend:
    """Wraps a ``FileStateBackend``; every commit must present a live, newest fencing token."""

    def __init__(self, backend: Any, lock: FileLeaseLock) -> None:
        self.backend = backend
        self.lock = lock
        self.fence_path = pathlib.Path(backend.root) / "HIGHEST_FENCE"

    def _highest(self) -> int:
        try:
            return int(self.fence_path.read_text().strip())
        except (FileNotFoundError, ValueError):
            return 0

    def commit(self, snapshot: Any, *, lease: Lease, expected_serial: int | None, meta: dict | None = None) -> int:
        from .durable import atomic_write

        cur = self.lock.current()
        if cur is None or cur.lease_id != lease.lease_id:
            raise LeaseLost("writer no longer holds the lease", details={"token": lease.token})
        if lease.token < self._highest():
            raise FencingViolation("stale fencing token", details={"token": lease.token, "highest": self._highest()})
        atomic_write(self.fence_path, str(lease.token).encode())
        return self.backend.commit(snapshot, expected_serial=expected_serial, meta={**(meta or {}), "fence": lease.token, "holder": lease.holder})
