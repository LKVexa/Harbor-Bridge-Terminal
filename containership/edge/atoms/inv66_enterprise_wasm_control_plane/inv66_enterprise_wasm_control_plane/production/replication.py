"""Single-writer leadership with leases and fencing epochs (MC-039; C055, C058).

Model: N control-plane replicas share one durable journal directory (shared
storage — a replicated volume or NFS with POSIX locks).  Exactly one replica, the
*leader*, may append.  Leadership is a lease in ``<root>/lease.json`` taken under
an exclusive ``fcntl.flock`` on ``<root>/lease.lock``:

* ``acquire`` succeeds if the lease is free, expired, or already ours; a change
  of holder increments the **epoch** (fencing token).
* ``fenced_append`` re-reads the lease *under the same lock* immediately before
  the journal write and refuses with ``ECP_NOT_LEADER`` unless we still hold it at
  our epoch and it has not expired.  A paused old leader that wakes after its
  lease was taken therefore cannot write (no split brain on the journal).
* followers serve reads by re-opening the journal (``Service.refresh``).

Not provided: multi-site consensus (Raft/Paxos) or cross-region replication of
the journal itself.  That is recorded as OPEN_EXTERNAL / waiver W-04; the lease
design depends on the storage layer's lock and fsync guarantees.
"""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from .errors import EcpError
from .util import atomic_write, canonical_json, now


class LeaseManager:
    def __init__(self, root: Path, node_id: str, *, ttl_s: float = 10.0, clock: Callable[[], float] = now):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.node = node_id
        self.ttl = ttl_s
        self.clock = clock
        self.epoch = 0

    @contextmanager
    def _locked(self) -> Iterator[None]:
        fd = os.open(str(self.root / "lease.lock"), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _read(self) -> dict[str, Any]:
        p = self.root / "lease.json"
        return json.loads(p.read_bytes()) if p.exists() else {"holder": None, "epoch": 0, "expires": 0.0}

    def acquire(self) -> bool:
        with self._locked():
            lease = self._read()
            t = self.clock()
            if lease["holder"] not in (None, self.node) and lease["expires"] > t:
                return False
            epoch = lease["epoch"] if lease["holder"] == self.node and lease["expires"] > t else lease["epoch"] + 1
            atomic_write(self.root / "lease.json",
                         canonical_json({"holder": self.node, "epoch": epoch, "expires": t + self.ttl}))
            self.epoch = epoch
            return True

    def renew(self) -> bool:
        return self.acquire()

    def release(self) -> None:
        with self._locked():
            lease = self._read()
            if lease["holder"] == self.node:
                atomic_write(self.root / "lease.json",
                             canonical_json({"holder": None, "epoch": lease["epoch"], "expires": 0.0}))

    def status(self) -> dict[str, Any]:
        lease = self._read()
        t = self.clock()
        role = "leader" if lease["holder"] == self.node and lease["expires"] > t and lease["epoch"] == self.epoch \
            else "follower"
        return {"role": role, "holder": lease["holder"], "epoch": lease["epoch"], "our_epoch": self.epoch,
                "expires_in_s": round(lease["expires"] - t, 3)}

    def fenced(self, fn: Callable[[], Any]) -> Any:
        with self._locked():
            lease = self._read()
            if lease["holder"] != self.node or lease["epoch"] != self.epoch or lease["expires"] <= self.clock():
                raise EcpError("ECP_NOT_LEADER", "not the current leader", epoch=self.epoch,
                               leader=str(lease["holder"])[:128])
            return fn()


class FencedJournal:
    """Journal wrapper whose appends are fenced by the lease (drop-in for Journal)."""

    def __init__(self, journal, lease: LeaseManager):
        self._j = journal
        self.lease = lease

    def append(self, kind: str, body: dict[str, Any]) -> dict[str, Any]:
        def _do():
            self._j.reload_tail()
            return self._j.append(kind, {**body, "_epoch": self.lease.epoch})
        return self.lease.fenced(_do)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._j, name)
