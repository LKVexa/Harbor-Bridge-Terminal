"""Durable replay protection (03), write-ahead buffer (11), persistent state /
reconstruction (38), backup/restore (43).

On-disk record format (both replay log and WAL), one per line:
    <crc32 hex 8>\t<canonical JSON>\n
A line whose CRC does not match, or a final line without ``\\n``, is a torn
write: recovery truncates to the last good record and reports how many bytes
were dropped (never silently).  A bad CRC *before* the tail is corruption and
raises -- a mid-file hole is not something to "recover" past.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import zlib
from collections import OrderedDict
from typing import Any, Iterator

from ..runtime import ReplayDetected, Sample, SignalStore
from .canonical import canonicalize
from .errors import Corrupted, QuotaExceeded


def _encode(obj: Any) -> bytes:
    body = canonicalize(obj).encode("utf-8")
    return b"%08x\t" % zlib.crc32(body) + body + b"\n"


def _scan(path: str) -> tuple[list[Any], int, int]:
    """Return (records, good_bytes, dropped_bytes)."""
    if not os.path.exists(path):
        return [], 0, 0
    with open(path, "rb") as fh:
        data = fh.read()
    recs, pos = [], 0
    lines = data.split(b"\n")
    for idx, line in enumerate(lines):
        is_last = idx == len(lines) - 1
        if is_last:
            break  # remainder after final newline (empty, or a torn tail)
        ok = len(line) > 9 and line[8:9] == b"\t"
        if ok:
            try:
                ok = int(line[:8], 16) == zlib.crc32(line[9:])
            except ValueError:
                ok = False
        if not ok:
            # tolerate only if every later line is also unterminated/garbage? No: only final
            if idx == len(lines) - 2 and lines[-1] == b"":
                break  # final complete line is torn/garbled -> tail truncation
            raise Corrupted("record checksum failure before log tail", path=os.path.basename(path), record=idx)
        recs.append(json.loads(line[9:]))
        pos += len(line) + 1
    return recs, pos, len(data) - pos


class _AppendLog:
    def __init__(self, path: str, *, max_bytes: int) -> None:
        self.path = path
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        recs, good, dropped = _scan(path)
        self.recovered_dropped_bytes = dropped
        if dropped:
            with open(path, "r+b") as fh:
                fh.truncate(good)
        self._records = recs
        self._size = good

    def _append(self, obj: Any) -> None:
        line = _encode(obj)
        if self._size + len(line) > self.max_bytes:
            raise QuotaExceeded("durable log at its disk bound", path=os.path.basename(self.path))
        with open(self.path, "ab") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        self._size += len(line)
        self._records.append(obj)


class DurableReplayGuard(_AppendLog):
    """Persisted (reporter, submission_id) set with a time window.

    Semantics: a submission id is remembered for ``window`` seconds after its
    ``issued_at``.  Submissions with ``issued_at <= now - window`` are refused
    outright as *too old to judge* -- that is what makes eviction safe: an id
    can only be forgotten once nothing carrying it could still be accepted.
    """

    def __init__(self, path: str, *, window: int, max_bytes: int = 64 << 20) -> None:
        if window <= 0:
            raise ValueError("window must be positive")
        super().__init__(path, max_bytes=max_bytes)
        self.window = window
        self._seen: OrderedDict[tuple[str, str], int] = OrderedDict()
        for r in self._records:
            self._seen[(r["r"], r["s"])] = r["t"]

    def check_and_record(self, reporter: str, submission_id: str, issued_at: int, now: int) -> None:
        with self._lock:
            if issued_at <= now - self.window:
                raise ReplayDetected("submission older than the replay window", reporter=reporter)
            self._evict(now)
            key = (reporter, submission_id)
            if key in self._seen:
                raise ReplayDetected("submission id already accepted (durable)", reporter=reporter)
            self._append({"r": reporter, "s": submission_id, "t": issued_at})
            self._seen[key] = issued_at

    def _evict(self, now: int) -> None:
        cutoff = now - self.window
        stale = [k for k, t in self._seen.items() if t <= cutoff]
        for k in stale:
            del self._seen[k]

    def compact(self, now: int) -> int:
        """Rewrite the log keeping only live ids (atomic replace)."""
        with self._lock:
            self._evict(now)
            tmp = self.path + ".tmp"
            with open(tmp, "wb") as fh:
                for (r, s), t in self._seen.items():
                    fh.write(_encode({"r": r, "s": s, "t": t}))
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
            self._size = os.path.getsize(self.path)
            return len(self._seen)

    def __len__(self) -> int:
        return len(self._seen)


class WriteAheadBuffer(_AppendLog):
    """Durable local buffer for disconnected sites.

    ``append`` persists a submission before acknowledging; ``pending`` yields
    entries not yet acked by upstream; ``ack(seq)`` persists an ack marker.
    Resume after crash replays exactly the un-acked entries in order.
    """

    def __init__(self, path: str, *, max_bytes: int = 256 << 20) -> None:
        super().__init__(path, max_bytes=max_bytes)
        self._next = 0
        self._acked: set[int] = set()
        self._data: dict[int, Any] = {}
        for r in self._records:
            if r["k"] == "d":
                self._data[r["n"]] = r["v"]
                self._next = max(self._next, r["n"] + 1)
            else:
                self._acked.add(r["n"])

    def append(self, value: Any) -> int:
        with self._lock:
            n = self._next
            self._append({"k": "d", "n": n, "v": value})
            self._data[n] = value
            self._next += 1
            return n

    def ack(self, n: int) -> None:
        with self._lock:
            if n not in self._data or n in self._acked:
                return
            self._append({"k": "a", "n": n})
            self._acked.add(n)

    def pending(self) -> list[tuple[int, Any]]:
        with self._lock:
            return [(n, self._data[n]) for n in sorted(self._data) if n not in self._acked]

    @property
    def used_bytes(self) -> int:
        return self._size


# ---------------------------------------------------------------- state (38/43)

def snapshot_store(store: SignalStore) -> dict:
    """Serialisable reconstruction contract for the reference store."""
    latest = []
    for key, st in sorted(store.latest.items()):
        s = st.sample
        latest.append({"signal": s.signal, "value": s.value, "tenant": s.tenant, "environment": s.environment,
                       "site": s.site, "workload": s.workload, "at": s.at, "reporter": st.reporter,
                       "received_at": st.received_at, "submission_id": st.submission_id})
    return {"format": "GAP09-SNAPSHOT/1", "latest": latest,
            "last_submission": dict(sorted(store.last_submission.items()))}


def restore_store(snap: dict, **store_kwargs) -> SignalStore:
    from ..runtime import StoredSample
    if snap.get("format") != "GAP09-SNAPSHOT/1":
        raise Corrupted("unknown snapshot format")
    st = SignalStore(**store_kwargs)
    with st._lock:  # reconstruction is the one sanctioned internal write
        for r in snap["latest"]:
            s = Sample(r["signal"], r["value"], r["tenant"], r["environment"], r["site"], r["workload"], r["at"])
            st._latest[(s.tenant, s.environment, s.site, s.workload, s.signal)] = StoredSample(
                s, r["reporter"], r["received_at"], r["submission_id"])
        st._last_submission.update(snap["last_submission"])
    return st


def write_snapshot(path: str, snap: dict) -> str:
    body = canonicalize(snap).encode()
    digest = hashlib.sha256(body).hexdigest()
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(body)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    with open(path + ".sha256", "w", encoding="ascii") as fh:
        fh.write(digest + "\n")
    return digest


def read_snapshot(path: str) -> dict:
    with open(path, "rb") as fh:
        body = fh.read()
    with open(path + ".sha256", "r", encoding="ascii") as fh:
        want = fh.read().strip()
    if hashlib.sha256(body).hexdigest() != want:
        raise Corrupted("snapshot digest mismatch")
    return json.loads(body)


def backup(src_dir: str, dest_dir: str) -> dict:
    """Copy every state file with a manifest; restore verifies before use."""
    os.makedirs(dest_dir, exist_ok=True)
    manifest = {}
    for name in sorted(os.listdir(src_dir)):
        p = os.path.join(src_dir, name)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(dest_dir, name))
            with open(p, "rb") as fh:
                manifest[name] = hashlib.sha256(fh.read()).hexdigest()
    with open(os.path.join(dest_dir, "BACKUP_MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump({"format": "GAP09-BACKUP/1", "files": manifest}, fh, sort_keys=True, indent=1)
    return manifest


def restore(backup_dir: str, dest_dir: str) -> dict:
    with open(os.path.join(backup_dir, "BACKUP_MANIFEST.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    for name, digest in man["files"].items():
        with open(os.path.join(backup_dir, name), "rb") as fh:
            if hashlib.sha256(fh.read()).hexdigest() != digest:
                raise Corrupted("backup file digest mismatch; restore refused", file=name)
    os.makedirs(dest_dir, exist_ok=True)
    for name in man["files"]:
        shutil.copy2(os.path.join(backup_dir, name), os.path.join(dest_dir, name))
    return man["files"]
