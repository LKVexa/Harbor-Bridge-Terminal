"""MC-31 durable state + restart/replay, MC-32 fencing, MC-53 backup/restore.

State is an append-only, hash-chained journal of reservation/release events.  Every
record carries the writer's fencing epoch; a writer whose epoch is below the store's
current epoch is refused (FENCED).  The store here is a single file with an exclusive
`O_EXCL` lock file for epoch acquisition - correct for one host.  A multi-host deployment
needs a linearizable store (etcd/raft) behind :class:`FencingAuthority`; that binding is
external (EXT, not present).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Iterator

from .errors import SchedulerError
from .security import canonical

GENESIS = "0" * 64


class FencingAuthority:
    """Monotonic epoch source.  File-backed, compare-and-swap under an exclusive lock."""

    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self._lock = threading.Lock()

    def _with_lock(self, fn):
        lock = self.path.with_suffix(".lock")
        for _ in range(2000):
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                import time; time.sleep(0.001)
        else:
            raise SchedulerError("FENCED", "could not acquire epoch lock")
        try:
            return fn()
        finally:
            os.close(fd); os.unlink(lock)

    def current(self) -> int:
        try:
            return int(self.path.read_text().strip() or 0)
        except FileNotFoundError:
            return 0

    def acquire(self) -> int:
        def bump():
            e = self.current() + 1
            tmp = self.path.with_suffix(".tmp"); tmp.write_text(str(e)); os.replace(tmp, self.path)
            return e
        with self._lock:
            return self._with_lock(bump)

    def check(self, epoch: int) -> None:
        cur = self.current()
        if epoch != cur:
            raise SchedulerError("FENCED", "writer epoch superseded", details={"epoch": epoch, "current": cur})

    def guarded(self, epoch: int, fn):
        """Run fn only while epoch is current, atomically w.r.t. other acquirers."""
        def g():
            self.check(epoch); return fn()
        with self._lock:
            return self._with_lock(g)


class Journal:
    SCHEMA = "PK_SCHEDULER_JOURNAL/1"

    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self.head, self.seq = GENESIS, 0
        self._lock = threading.Lock()
        for rec in self.records():
            self.head, self.seq = rec["hash"], rec["seq"]

    def records(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        prev, seq = GENESIS, 0
        with open(self.path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if not line.endswith("\n"):
                    # torn final write: crash mid-append. Ignore only the torn tail.
                    break
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    raise SchedulerError("STATE_CORRUPT", f"journal line {n} unparsable") from None
                body = {k: rec[k] for k in ("seq", "prev", "epoch", "event")}
                if rec["seq"] != seq + 1 or rec["prev"] != prev or hashlib.sha256(canonical(body)).hexdigest() != rec["hash"]:
                    raise SchedulerError("STATE_CORRUPT", f"journal chain broken at line {n}")
                prev, seq = rec["hash"], rec["seq"]
                yield rec

    def append(self, epoch: int, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            body = {"seq": self.seq + 1, "prev": self.head, "epoch": epoch, "event": event}
            rec = dict(body, hash=hashlib.sha256(canonical(body)).hexdigest())
            self._truncate_torn_tail()
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, sort_keys=True) + "\n"); f.flush(); os.fsync(f.fileno())
            self.head, self.seq = rec["hash"], rec["seq"]
            return rec

    def _truncate_torn_tail(self):
        if not self.path.exists():
            return
        data = self.path.read_bytes()
        if data and not data.endswith(b"\n"):
            with open(self.path, "r+b") as f:
                f.truncate(data.rfind(b"\n") + 1)

    def replay(self) -> dict[str, dict[str, Any]]:
        """Reconstruct lease table: lease_id -> latest lease record."""
        leases: dict[str, dict[str, Any]] = {}
        for rec in self.records():
            ev = rec["event"]
            if ev["type"] == "reserve":
                leases[ev["lease_id"]] = dict(ev["lease"], state="RESERVED")
            elif ev["type"] in ("release", "expire", "revoke", "admit", "run"):
                if ev["lease_id"] in leases:
                    leases[ev["lease_id"]]["state"] = {"release": "RELEASED", "expire": "EXPIRED", "revoke": "REVOKED",
                                                       "admit": "ADMITTED", "run": "RUNNING"}[ev["type"]]
        return leases


def backup(journal: Journal, dest: str | os.PathLike) -> dict[str, Any]:
    """MC-53: consistent copy + manifest (head hash and sha256) for restore verification."""
    dest = Path(dest)
    with journal._lock:
        shutil.copyfile(journal.path, dest)
        head, seq = journal.head, journal.seq
    manifest = {"schema": "PK_SCHEDULER_BACKUP/1", "head": head, "seq": seq,
                "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}
    dest.with_suffix(".manifest.json").write_text(json.dumps(manifest, sort_keys=True))
    return manifest


def restore(src: str | os.PathLike, target: str | os.PathLike) -> Journal:
    src = Path(src)
    m = json.loads(src.with_suffix(".manifest.json").read_text())
    if hashlib.sha256(src.read_bytes()).hexdigest() != m["sha256"]:
        raise SchedulerError("STATE_CORRUPT", "backup digest mismatch")
    shutil.copyfile(src, target)
    j = Journal(target)
    if j.head != m["head"] or j.seq != m["seq"]:
        raise SchedulerError("STATE_CORRUPT", "restored head does not match manifest")
    return j
