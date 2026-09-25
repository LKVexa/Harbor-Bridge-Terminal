"""Durable, tamper-evident audit journal: the authoritative source of truth.

Covers MC-005 (source of truth), MC-035 (anchoring), MC-038 (crash recovery /
replay), MC-039 (single-writer fencing), MC-046 (bounded retention), MC-070
(archival/export).

Layout of a store directory::

    journal.jsonl        active segment, one PK_ECP_AUDIT/1 event per line
    archive/seg-<first>-<last>.jsonl  sealed, read-only segments (retention)
    snapshot.json        reducer state + chain head at the last compaction
    anchors.jsonl        HMAC-signed chain-head checkpoints
    lease.json           leader lease: holder, epoch, expiry (fencing token)

Consistency model: single writer per store (lease holder), linearizable
appends; an append is acknowledged only after ``fsync``.  Readers replay
``snapshot + journal``.  Every record binds sequence, previous hash and the
writer's lease epoch, so a fenced (stale) leader cannot append.
"""
from __future__ import annotations

import json
import os
import pathlib
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Iterator, Protocol

from .canonical import canonical_json, consteq, hmac_hex, sha256_hex
from .errors import fail

AUDIT_SCHEMA = "PK_ECP_AUDIT/1"
DOMAIN = b"PK_ECP_AUDIT/1\0"
ANCHOR_DOMAIN = b"PK_ECP_ANCHOR/1\0"
ZERO = "0" * 64


def record_hash(sequence: int, previous: str, epoch: int, entry: dict) -> str:
    return sha256_hex(DOMAIN + canonical_json({"sequence": sequence, "previous_hash": previous,
                                               "epoch": epoch, "entry": entry}))


def verify_chain(records: Iterable[dict], start_seq: int = 1, start_prev: str = ZERO) -> tuple[bool, str, int]:
    """Return (ok, head_hash, last_sequence)."""
    prev, seq = start_prev, start_seq - 1
    for r in records:
        seq += 1
        try:
            if r.get("schema") != AUDIT_SCHEMA or r.get("sequence") != seq or r.get("previous_hash") != prev:
                return False, prev, seq - 1
            if not isinstance(r.get("epoch"), int) or not isinstance(r.get("entry"), dict):
                return False, prev, seq - 1
            h = record_hash(seq, prev, r["epoch"], r["entry"])
            if r.get("hash") != h:
                return False, prev, seq - 1
            prev = h
        except (TypeError, ValueError, AttributeError):
            return False, prev, seq - 1
    return True, prev, seq


class AnchorSink(Protocol):
    """External WORM/transparency anchor (object-lock bucket, TSA, ledger)."""

    def publish(self, anchor: dict) -> None: ...


class StoreFault(Protocol):
    def __call__(self, op: str) -> None: ...


@dataclass
class Lease:
    holder: str
    epoch: int
    expires_at: float


class JournalStore:
    def __init__(self, path: str | os.PathLike, node_id: str, *, anchor_key: bytes,
                 lease_ttl_s: float = 10.0, clock: Callable[[], float] = time.time,
                 anchor_sink: AnchorSink | None = None, fault: StoreFault | None = None,
                 fsync: bool = True):
        self.dir = pathlib.Path(path)
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "archive").mkdir(exist_ok=True)
        self.node_id = node_id
        self.anchor_key = anchor_key
        self.lease_ttl_s = lease_ttl_s
        self.clock = clock
        self.anchor_sink = anchor_sink
        self.fault = fault or (lambda op: None)
        self.fsync = fsync
        self._lock = threading.RLock()
        self.epoch = -1
        self.recovered_bytes = 0
        self._open()

    # ------------------------------------------------------------------ lease
    def _lease_path(self) -> pathlib.Path:
        return self.dir / "lease.json"

    def read_lease(self) -> Lease | None:
        try:
            d = json.loads(self._lease_path().read_text())
            return Lease(d["holder"], d["epoch"], d["expires_at"])
        except (OSError, ValueError, KeyError):
            return None

    def acquire(self) -> int:
        """Acquire or renew the leader lease. Returns the fencing epoch."""
        with self._lock:
            lk = self._flock()
            try:
                cur = self.read_lease()
                now = self.clock()
                if cur and cur.holder != self.node_id and cur.expires_at > now:
                    raise fail("NOT_LEADER", f"lease held by {cur.holder} until {cur.expires_at}")
                epoch = cur.epoch if cur and cur.holder == self.node_id and cur.epoch == self.epoch else (cur.epoch + 1 if cur else 1)
                self._atomic_write(self._lease_path(), {"holder": self.node_id, "epoch": epoch,
                                                        "expires_at": now + self.lease_ttl_s})
                self.epoch = epoch
                return epoch
            finally:
                self._funlock(lk)

    def release(self) -> None:
        with self._lock:
            cur = self.read_lease()
            if cur and cur.holder == self.node_id and cur.epoch == self.epoch:
                self._atomic_write(self._lease_path(), {"holder": self.node_id, "epoch": self.epoch, "expires_at": 0})

    def _check_fence(self) -> None:
        cur = self.read_lease()
        if cur is None or cur.holder != self.node_id or cur.epoch != self.epoch or cur.expires_at <= self.clock():
            raise fail("NOT_LEADER", "lease lost or fenced; refusing write")

    def _flock(self):
        import fcntl
        fh = open(self.dir / ".lock", "a+")
        fcntl.flock(fh, fcntl.LOCK_EX)
        return fh

    @staticmethod
    def _funlock(fh) -> None:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()

    def _atomic_write(self, path: pathlib.Path, obj: Any) -> None:
        tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
        with open(tmp, "wb") as fh:
            fh.write(json.dumps(obj, sort_keys=True).encode())
            fh.flush()
            if self.fsync:
                os.fsync(fh.fileno())
        os.replace(tmp, path)

    # ------------------------------------------------------------- open/replay
    def _open(self) -> None:
        snap = self.load_snapshot()
        self.base_seq = snap["head_sequence"] if snap else 0
        self.base_hash = snap["head_hash"] if snap else ZERO
        jp = self.dir / "journal.jsonl"
        jp.touch(exist_ok=True)
        good_offset, recs = 0, []
        with open(jp, "rb") as fh:
            data = fh.read()
        pos = 0
        while pos < len(data):
            nl = data.find(b"\n", pos)
            if nl == -1:            # torn final write (crash mid-append)
                break
            try:
                recs.append(json.loads(data[pos:nl]))
            except ValueError:
                if data.find(b"\n", nl + 1) != -1:
                    raise fail("STORE_UNAVAILABLE", f"journal corrupt at byte {pos} (not a torn tail)")
                break
            pos = nl + 1
            good_offset = pos
        ok, head, last = verify_chain(recs, self.base_seq + 1, self.base_hash)
        if not ok:
            raise fail("STORE_UNAVAILABLE", f"journal hash chain broken after sequence {last}")
        if good_offset != len(data):
            self.recovered_bytes = len(data) - good_offset
            with open(jp, "r+b") as fh:
                fh.truncate(good_offset)
                if self.fsync:
                    os.fsync(fh.fileno())
        self._records = recs
        self.head_hash, self.head_seq = head, last
        self._size = good_offset

    def load_snapshot(self) -> dict | None:
        p = self.dir / "snapshot.json"
        if not p.exists():
            return None
        snap = json.loads(p.read_text())
        body = {k: v for k, v in snap.items() if k != "mac"}
        if not consteq(snap.get("mac", ""), hmac_hex(self.anchor_key, ANCHOR_DOMAIN, body)):
            raise fail("STORE_UNAVAILABLE", "snapshot MAC invalid")
        return snap

    def records(self) -> list[dict]:
        with self._lock:
            return [json.loads(json.dumps(r)) for r in self._records]

    def iter_all(self) -> Iterator[dict]:
        """All retained records: archived segments then the active journal."""
        for seg in sorted(self.dir.glob("archive/seg-*.jsonl"), key=lambda p: int(p.name.split("-")[1])):
            with open(seg) as fh:
                for line in fh:
                    yield json.loads(line)
        yield from self.records()

    # ------------------------------------------------------------------ append
    def _sync_from_disk(self) -> None:
        """Another process may have appended since we last read: re-read if so."""
        size = (self.dir / "journal.jsonl").stat().st_size
        if size != getattr(self, "_size", -1) or self.load_snapshot_head() != (self.base_seq, self.base_hash):
            self._open()

    def load_snapshot_head(self) -> tuple[int, str]:
        p = self.dir / "snapshot.json"
        try:
            st = p.stat()
            sig = (st.st_mtime_ns, st.st_size, st.st_ino)
        except FileNotFoundError:
            return (0, ZERO)
        if getattr(self, "_snap_sig", None) != sig:
            snap = self.load_snapshot()
            self._snap_sig, self._snap_head = sig, (snap["head_sequence"], snap["head_hash"])
        return self._snap_head

    def append(self, entry: dict) -> dict:
        with self._lock:
            lk = self._flock()
            try:
                return self._append_locked(entry)
            finally:
                self._funlock(lk)

    def _append_locked(self, entry: dict) -> dict:
        if True:
            self._sync_from_disk()
            self._check_fence()
            seq = self.head_seq + 1
            entry = json.loads(canonical_json(entry))
            rec = {"schema": AUDIT_SCHEMA, "sequence": seq, "previous_hash": self.head_hash,
                   "epoch": self.epoch, "entry": entry}
            rec["hash"] = record_hash(seq, self.head_hash, self.epoch, entry)
            line = canonical_json(rec) + b"\n"
            try:
                self.fault("append")
                with open(self.dir / "journal.jsonl", "ab") as fh:
                    fh.write(line)
                    fh.flush()
                    self.fault("fsync")
                    if self.fsync:
                        os.fsync(fh.fileno())
            except OSError as exc:
                self._reload_after_failure()
                raise fail("STORE_UNAVAILABLE", f"append failed: {exc.strerror or exc}") from None
            self._records.append(rec)
            self.head_hash, self.head_seq = rec["hash"], seq
            self._size = (self.dir / "journal.jsonl").stat().st_size
            return json.loads(json.dumps(rec))

    def _reload_after_failure(self) -> None:
        # A partial write may be on disk; truncate back to the last good record.
        try:
            self._open()
        except Exception:
            pass

    # ----------------------------------------------------------------- anchors
    def anchor(self) -> dict:
        with self._lock:
            body = {"schema": "PK_ECP_ANCHOR/1", "node": self.node_id, "epoch": self.epoch,
                    "sequence": self.head_seq, "hash": self.head_hash, "ts": self.clock()}
            a = dict(body, mac=hmac_hex(self.anchor_key, ANCHOR_DOMAIN, body))
            with open(self.dir / "anchors.jsonl", "ab") as fh:
                fh.write(canonical_json(a) + b"\n")
                if self.fsync:
                    os.fsync(fh.fileno())
            if self.anchor_sink is not None:
                self.anchor_sink.publish(a)
            return a

    def verify_anchors(self, anchors: Iterable[dict] | None = None) -> tuple[bool, str]:
        """Each anchor MAC must verify and its hash must equal the chain at that sequence."""
        if anchors is None:
            p = self.dir / "anchors.jsonl"
            anchors = [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        by_seq = {r["sequence"]: r["hash"] for r in self.iter_all()}
        by_seq[0] = ZERO
        snap = self.load_snapshot()
        for a in anchors:
            body = {k: v for k, v in a.items() if k != "mac"}
            if not consteq(a.get("mac", ""), hmac_hex(self.anchor_key, ANCHOR_DOMAIN, body)):
                return False, f"anchor at {a.get('sequence')} has invalid MAC"
            seq = a["sequence"]
            if seq in by_seq:
                if by_seq[seq] != a["hash"]:
                    return False, f"chain rewritten: sequence {seq} differs from anchor"
            elif not (snap and seq < snap.get("archive_floor", 0)):
                return False, f"anchored sequence {seq} missing from retained history"
        return True, "ok"

    # --------------------------------------------------------------- retention
    def compact(self, state: dict) -> dict:
        """Seal the active journal into an archive segment and snapshot state.

        ``state`` is the reducer state at ``head_seq`` (caller-supplied)."""
        with self._lock:
            lk = self._flock()
            try:
                return self._compact_locked(state)
            finally:
                self._funlock(lk)

    def _compact_locked(self, state: dict) -> dict:
        if True:
            self._sync_from_disk()
            self._check_fence()
            recs = self._records
            if not recs:
                return {"sealed": 0}
            seal = recs
            first, last = seal[0]["sequence"], seal[-1]["sequence"]
            seg = self.dir / "archive" / f"seg-{first:012d}-{last:012d}.jsonl"
            with open(seg, "wb") as fh:
                for r in seal:
                    fh.write(canonical_json(r) + b"\n")
                if self.fsync:
                    os.fsync(fh.fileno())
            os.chmod(seg, 0o444)
            body = {"schema": "PK_ECP_SNAPSHOT/1", "head_sequence": last, "head_hash": seal[-1]["hash"],
                    "state": state, "segments": sorted(p.name for p in (self.dir / "archive").glob("seg-*.jsonl")),
                    "archive_floor": (self.load_snapshot() or {}).get("archive_floor", 0)}
            snap = dict(body, mac=hmac_hex(self.anchor_key, ANCHOR_DOMAIN, body))
            self._atomic_write(self.dir / "snapshot.json", snap)
            tmp = self.dir / "journal.jsonl.new"
            with open(tmp, "wb") as fh:
                if self.fsync:
                    os.fsync(fh.fileno())
            os.replace(tmp, self.dir / "journal.jsonl")
            self.base_seq, self.base_hash, self._records, self._size = last, seal[-1]["hash"], [], 0
            return {"sealed": len(seal), "segment": seg.name}

    def purge_archives(self, older_than_seq: int, legal_hold: bool) -> list[str]:
        """Delete sealed segments wholly below ``older_than_seq`` unless on legal hold."""
        if legal_hold:
            return []
        removed = []
        for seg in sorted(self.dir.glob("archive/seg-*.jsonl")):
            last = int(seg.name.split("-")[2].split(".")[0])
            if last < older_than_seq:
                os.chmod(seg, 0o644)
                seg.unlink()
                removed.append(seg.name)
        if removed:
            snap = self.load_snapshot()
            if snap:
                body = {k: v for k, v in snap.items() if k != "mac"}
                remaining = [int(p.name.split("-")[1]) for p in (self.dir / "archive").glob("seg-*.jsonl")]
                body["archive_floor"] = min(remaining) if remaining else body["head_sequence"] + 1
                body["segments"] = sorted(p.name for p in (self.dir / "archive").glob("seg-*.jsonl"))
                self._atomic_write(self.dir / "snapshot.json", dict(body, mac=hmac_hex(self.anchor_key, ANCHOR_DOMAIN, body)))
        return removed

    def verify_all(self) -> tuple[bool, str]:
        """Verify archived segments + journal form one unbroken chain."""
        snap = self.load_snapshot()
        floor = snap.get("archive_floor", 0) if snap else 0
        recs = list(self.iter_all())
        if not recs:
            return True, "empty"
        start = recs[0]["sequence"]
        prev = recs[0]["previous_hash"] if start > 1 else ZERO
        if start > 1 and start > max(floor, 1):
            return False, "history missing below retention floor"
        if start > 1 and not snap:
            return False, "history missing and no snapshot"
        ok, head, last = verify_chain(recs, start, prev)
        if not ok:
            return False, f"chain broken after {last}"
        if head != self.head_hash:
            return False, "head mismatch"
        return True, f"verified {len(recs)} records {start}..{last}"
