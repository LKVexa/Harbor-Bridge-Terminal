"""GAP11-P0-01 Durable lease-state store + GAP11-P0-02 storage-side fencing.

Design (see docs/DESIGN_RECORDS.md#GAP11-P0-01):

* One append-only write-ahead log (JSON lines). Each committed transaction is one
  line ``{"rev", "ops", "pre", "fence", "prov", "sum"}`` where ``sum`` is the
  SHA-256 of the canonical body. A transaction is committed iff its full line is
  on disk and fsync returned — that is the single atomic boundary.
* All writes are multi-key compare-and-swap: ``pre`` maps key -> expected
  revision (0 = must be absent). Any mismatch rejects the whole transaction.
* Storage-side fencing: a transaction may carry ``fence=(resource, token)``; the
  store keeps the highest token seen per resource and rejects lower tokens, so a
  deposed controller cannot write even if it still believes it leads.
* Recovery rebuilds every index exclusively from the snapshot + WAL. A torn final
  line (crash mid-write) is uncommitted and discarded; a bad line anywhere else is
  corruption and the store refuses to open (fail closed).

Crash points (``fault`` hook): before_write, mid_write, after_write_before_fsync,
after_fsync_before_apply, before_ack. Only a crash after fsync yields a committed
transaction; the caller may not have seen the ack, which is why every mutation is
paired with an idempotency key (see ``idempotency.py``).
"""
from __future__ import annotations

import copy
import errno
import json
import os
import threading
from dataclasses import dataclass
from typing import Any, Callable

from .common import ControlError, canonical, digest, utc_iso, SystemClock

WAL_NAME = "wal.jsonl"
SNAP_NAME = "snapshot.json"
FENCE_PREFIX = "__fence__/"


class SimulatedCrash(BaseException):
    """Raised by a fault hook to model process death at a write point."""


@dataclass(frozen=True)
class Provenance:
    request_id: str
    actor: str
    controller_epoch: int
    reason: str

    def validate(self) -> None:
        for name in ("request_id", "actor", "reason"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v.strip():
                raise ControlError("SCHEMA_INVALID", f"provenance.{name} required")
        if not isinstance(self.controller_epoch, int) or self.controller_epoch < 0:
            raise ControlError("SCHEMA_INVALID", "provenance.controller_epoch must be >= 0")


class LeaseStore:
    def __init__(self, directory: str, *, clock: Any | None = None,
                 fault: Callable[[str], None] | None = None, fsync: bool = True) -> None:
        self.dir = directory
        os.makedirs(directory, exist_ok=True)
        self.clock = clock or SystemClock()
        self.fault = fault or (lambda point: None)
        self.fsync = fsync
        self._lock = threading.RLock()
        self.data: dict[str, tuple[int, Any]] = {}   # key -> (revision, value)
        self.revision = 0
        self.history: list[dict[str, Any]] = []      # provenance of mutations since open
        self.read_only = False
        self._recover()

    # ------------------------------------------------------------------ recovery
    def _recover(self) -> None:
        snap = os.path.join(self.dir, SNAP_NAME)
        if os.path.exists(snap):
            with open(snap, "rb") as fh:
                body = json.loads(fh.read())
            if digest(body["state"]) != body["sum"]:
                raise ControlError("STORE_CORRUPT", "snapshot checksum mismatch")
            self.revision = body["state"]["revision"]
            self.data = {k: (r, v) for k, (r, v) in body["state"]["data"].items()}
        wal = os.path.join(self.dir, WAL_NAME)
        if not os.path.exists(wal):
            return
        with open(wal, "rb") as fh:
            raw = fh.read()
        lines = raw.split(b"\n")
        good_bytes = 0
        for idx, line in enumerate(lines):
            last = idx == len(lines) - 1
            if not line:
                if not last:
                    raise ControlError("STORE_CORRUPT", "empty WAL line inside log", line=idx)
                continue
            try:
                rec = json.loads(line)
                body = {k: rec[k] for k in ("rev", "ops", "pre", "fence", "prov")}
                ok = digest(body) == rec["sum"]
            except Exception:
                ok = False
            if not ok:
                if last:  # torn tail: the crash happened before this commit finished
                    break
                raise ControlError("STORE_CORRUPT", "WAL record failed checksum", line=idx)
            good_bytes += len(line) + 1
            if rec["rev"] <= self.revision:
                continue
            if rec["rev"] != self.revision + 1:
                raise ControlError("STORE_CORRUPT", "WAL revision gap", expected=self.revision + 1, got=rec["rev"])
            self._apply(rec)
        if good_bytes < len(raw):
            with open(wal, "r+b") as fh:  # drop the torn tail so the next append is clean
                fh.truncate(good_bytes)
                fh.flush()
                if self.fsync:
                    os.fsync(fh.fileno())

    def _apply(self, rec: dict[str, Any]) -> None:
        rev = rec["rev"]
        for op in rec["ops"]:
            if op["op"] == "put":
                self.data[op["key"]] = (rev, op["value"])
            elif op["op"] == "delete":
                self.data.pop(op["key"], None)
        if rec["fence"]:
            res, tok = rec["fence"]
            self.data[FENCE_PREFIX + res] = (rev, tok)
        self.revision = rev
        self.history.append({"rev": rev, **rec["prov"]})

    # ------------------------------------------------------------------ reads
    def get(self, key: str) -> tuple[int, Any] | None:
        with self._lock:
            item = self.data.get(key)
            return None if item is None else (item[0], copy.deepcopy(item[1]))

    def scan(self, prefix: str) -> dict[str, tuple[int, Any]]:
        with self._lock:
            return {k: (r, copy.deepcopy(v)) for k, (r, v) in self.data.items() if k.startswith(prefix)}

    def fence_token(self, resource: str) -> int:
        item = self.get(FENCE_PREFIX + resource)
        return 0 if item is None else int(item[1])

    # ------------------------------------------------------------------ writes
    def commit(self, ops: list[dict[str, Any]], *, pre: dict[str, int], prov: Provenance,
               fence: tuple[str, int] | None = None) -> int:
        prov.validate()
        for op in ops:
            if op.get("op") not in ("put", "delete") or not isinstance(op.get("key"), str):
                raise ControlError("SCHEMA_INVALID", "bad op", op=op)
            if op["key"].startswith(FENCE_PREFIX):
                raise ControlError("ILLEGAL_TRANSITION", "fence keys are store-managed")
        with self._lock:
            if self.read_only:
                raise ControlError("STORE_UNAVAILABLE", "store is in read-only degraded mode")
            for key, expected in pre.items():
                cur = self.data.get(key)
                cur_rev = 0 if cur is None else cur[0]
                if cur_rev != expected:
                    raise ControlError("STALE_REVISION", key=key, expected=expected, actual=cur_rev)
            if fence is not None:
                res, tok = fence
                if not isinstance(tok, int) or tok < self.fence_token(res):
                    raise ControlError("STALE_FENCE", resource=res, token=tok, current=self.fence_token(res))
            body = {
                "rev": self.revision + 1,
                "ops": ops,
                "pre": pre,
                "fence": list(fence) if fence else None,
                "prov": {"request_id": prov.request_id, "actor": prov.actor,
                         "controller_epoch": prov.controller_epoch, "reason": prov.reason,
                         "prev_revision": self.revision, "new_revision": self.revision + 1,
                         "ts": utc_iso(self.clock.wall())},
            }
            line = json.dumps({**body, "sum": digest(body)}, sort_keys=True, separators=(",", ":")).encode() + b"\n"
            self.fault("before_write")
            path = os.path.join(self.dir, WAL_NAME)
            with open(path, "ab") as fh:
                start = fh.tell()
                try:
                    half = len(line) // 2
                    fh.write(line[:half])
                    fh.flush()
                    self.fault("mid_write")          # crash here leaves a torn tail on disk
                    fh.write(line[half:])
                    fh.flush()
                    self.fault("after_write_before_fsync")
                    if self.fsync:
                        os.fsync(fh.fileno())
                except OSError as exc:
                    fh.truncate(start)  # e.g. ENOSPC: roll the partial append back
                    code = "STORE_UNAVAILABLE"
                    raise ControlError(code, f"WAL append failed: {errno.errorcode.get(exc.errno, exc)}") from exc
            self.fault("after_fsync_before_apply")
            self._apply(json.loads(line))
            self.fault("before_ack")
            return self.revision

    # ------------------------------------------------------------------ maintenance
    def snapshot(self) -> None:
        """Compact: write snapshot atomically (tmp + fsync + rename), then reset WAL."""
        with self._lock:
            state = {"revision": self.revision, "data": {k: [r, v] for k, (r, v) in self.data.items()}}
            tmp = os.path.join(self.dir, SNAP_NAME + ".tmp")
            with open(tmp, "wb") as fh:
                fh.write(canonical({"state": state, "sum": digest(state)}))
                fh.flush()
                if self.fsync:
                    os.fsync(fh.fileno())
            os.replace(tmp, os.path.join(self.dir, SNAP_NAME))
            # WAL records <= snapshot revision are skipped on replay, so truncation
            # after the rename is safe even if we crash between the two steps.
            with open(os.path.join(self.dir, WAL_NAME), "wb") as fh:
                fh.flush()
                if self.fsync:
                    os.fsync(fh.fileno())

    def verify(self) -> dict[str, Any]:
        """Re-open from disk into a scratch instance and compare state digests."""
        other = LeaseStore(self.dir, clock=self.clock, fsync=False)
        mine = digest({k: [r, v] for k, (r, v) in self.data.items()})
        theirs = digest({k: [r, v] for k, (r, v) in other.data.items()})
        return {"revision": self.revision, "disk_revision": other.revision, "consistent": mine == theirs and self.revision == other.revision}
