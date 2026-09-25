"""Durable state (M11), ownership fencing (M12) and backup/restore/migration (M31).

``FileStateStore`` is a single-writer, crash-consistent key/value store:
every mutation is a checksummed write-ahead-log record fsync'd before the
call returns; ``compact()`` writes an atomic snapshot (write temp, fsync,
``os.replace``) and truncates the log.  On open, a torn *final* WAL record is
discarded (it was never acknowledged); a corrupt *complete* record is a
hard ``PLN04-STATE-003``.  Every key carries a monotonic version and all
writes are compare-and-swap.  An exclusive ``flock`` on POSIX prevents two
controllers from opening the same store.

``LeaseManager`` issues ownership leases with a monotonically increasing
fencing epoch per key, persisted in the store.  Providers reject commands
carrying an older epoch (see ``providers.ExecutionProvider._fence``).

Honest boundary: a single file is not a *distributed* linearizable store.
Multi-controller deployments must implement ``StateStore`` over etcd /
FoundationDB / Spanner-class storage; the lease and fencing logic is written
against the interface and is reused unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Iterator

from .errors import PlaneError

STATE_FORMAT = "PK_PLN04_STATE/2"


def _sha(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class StateStore:
    """Interface.  Values are JSON-compatible objects."""

    def get(self, key: str) -> tuple[int, object] | None: ...
    def cas(self, key: str, expected_version: int, value: object) -> int: ...
    def delete(self, key: str, expected_version: int) -> None: ...
    def items(self, prefix: str = "") -> Iterator[tuple[str, int, object]]: ...
    def healthy(self) -> bool: ...


class MemoryStateStore(StateStore):
    def __init__(self) -> None:
        self._data: dict[str, tuple[int, object]] = {}
        self._lock = threading.RLock()
        self.fail_writes = False  # fault injection

    def get(self, key):
        with self._lock:
            entry = self._data.get(key)
            return None if entry is None else (entry[0], json.loads(json.dumps(entry[1])))

    def _apply(self, key: str, expected_version: int, value: object, delete: bool = False) -> int:
        with self._lock:
            if self.fail_writes:
                raise PlaneError("PLN04-DEP-001", details={"dependency": "state-store"})
            current = self._data.get(key)
            cur_ver = 0 if current is None else current[0]
            if cur_ver != expected_version:
                raise PlaneError("PLN04-STATE-001", details={"reason": f"version {cur_ver} != expected {expected_version}"})
            if delete:
                self._data.pop(key, None)
                return 0
            self._data[key] = (cur_ver + 1, json.loads(json.dumps(value)))
            return cur_ver + 1

    def cas(self, key, expected_version, value):
        return self._apply(key, expected_version, value)

    def delete(self, key, expected_version):
        self._apply(key, expected_version, None, delete=True)

    def items(self, prefix=""):
        with self._lock:
            snap = [(k, v, d) for k, (v, d) in self._data.items() if k.startswith(prefix)]
        for k, v, d in sorted(snap):
            yield k, v, json.loads(json.dumps(d))

    def healthy(self):
        return not self.fail_writes


# --------------------------------------------------------------------------- migrations

def _migrate_1_to_2(doc: dict) -> dict:
    """v1 snapshots were a bare ``{key: value}`` mapping without versions."""
    return {"format": STATE_FORMAT, "data": {k: [1, v] for k, v in doc.items()}}


MIGRATIONS: dict[str, Callable[[dict], dict]] = {"PK_PLN04_STATE/1": _migrate_1_to_2}


def migrate(doc: dict) -> dict:
    fmt = doc.get("format", "PK_PLN04_STATE/1") if isinstance(doc, dict) else None
    if fmt == STATE_FORMAT:
        return doc
    if fmt == "PK_PLN04_STATE/1":
        body = {k: v for k, v in doc.items() if k != "format"}
        return MIGRATIONS[fmt](body)
    raise PlaneError("PLN04-STATE-003", details={"reason": f"unsupported state format {fmt!r}"})


class FileStateStore(MemoryStateStore):
    def __init__(self, directory: str, *, fsync: bool = True) -> None:
        super().__init__()
        self._dir = directory
        self._fsync = fsync
        os.makedirs(directory, mode=0o700, exist_ok=True)
        self._snap = os.path.join(directory, "state.snapshot.json")
        self._wal_path = os.path.join(directory, "state.wal.jsonl")
        self._lockfh = open(os.path.join(directory, ".lock"), "a+")
        try:
            import fcntl
            fcntl.flock(self._lockfh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:  # pragma: no cover - non-POSIX
            pass
        except OSError:
            self._lockfh.close()
            raise PlaneError("PLN04-DEP-001", details={"dependency": "state-store", "reason": "store locked by another controller"}) from None
        self.recovered_torn_record = False
        self._load()
        self._wal = open(self._wal_path, "a", encoding="utf-8")

    def _load(self) -> None:
        if os.path.exists(self._snap):
            try:
                with open(self._snap, encoding="utf-8") as fh:
                    doc = migrate(json.load(fh))
            except ValueError:
                raise PlaneError("PLN04-STATE-003", details={"reason": "snapshot unreadable"}) from None
            if doc.get("sha256") is not None and doc["sha256"] != _sha(doc["data"]):
                raise PlaneError("PLN04-STATE-003", details={"reason": "snapshot checksum mismatch"})
            self._data = {k: (int(v[0]), v[1]) for k, v in doc["data"].items()}
        if not os.path.exists(self._wal_path):
            return
        with open(self._wal_path, "rb") as fh:
            raw = fh.read()
        # A torn write is an *unterminated* final record (every acknowledged record ends
        # with a newline after fsync).  A complete record that fails its checksum is
        # corruption of acknowledged data, never silently discarded.
        tail_torn = bool(raw) and not raw.endswith(b"\n")
        lines = raw.split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()
        good_bytes = 0
        for i, line in enumerate(lines):
            try:
                rec = json.loads(line.decode("utf-8"))  # UnicodeDecodeError is a ValueError
                body = {k: rec[k] for k in ("key", "ver", "value", "op")}
                if rec["sha"] != _sha(body):
                    raise ValueError("checksum")
            except (ValueError, KeyError, TypeError):
                if i == len(lines) - 1 and tail_torn:
                    self.recovered_torn_record = True
                    with open(self._wal_path, "r+b") as fh:
                        fh.truncate(good_bytes)
                    break
                raise PlaneError("PLN04-STATE-003", details={"reason": f"WAL record {i + 1} corrupt"}) from None
            if rec["op"] == "del":
                self._data.pop(rec["key"], None)
            else:
                self._data[rec["key"]] = (int(rec["ver"]), rec["value"])
            good_bytes += len(line) + 1

    def _apply(self, key, expected_version, value, delete=False):
        with self._lock:
            new_ver = super()._apply(key, expected_version, value, delete)
            body = {"key": key, "ver": new_ver, "value": None if delete else value, "op": "del" if delete else "put"}
            try:
                self._wal.write(json.dumps({**body, "sha": _sha(body)}, separators=(",", ":")) + "\n")
                self._wal.flush()
                if self._fsync:
                    os.fsync(self._wal.fileno())
            except OSError as exc:
                raise PlaneError("PLN04-DEP-001", details={"dependency": "state-store"}, cause=exc) from None
            return new_ver

    def compact(self) -> None:
        with self._lock:
            data = {k: [v, d] for k, (v, d) in self._data.items()}
            doc = {"format": STATE_FORMAT, "written_ns": time.time_ns(), "data": data, "sha256": _sha(data)}
            tmp = self._snap + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self._snap)
            self._wal.close()
            self._wal = open(self._wal_path, "w", encoding="utf-8")

    def backup(self, destination: str) -> dict:
        """Write a self-verifying backup file; returns its manifest."""
        with self._lock:
            data = {k: [v, d] for k, (v, d) in self._data.items()}
        doc = {"format": STATE_FORMAT, "written_ns": time.time_ns(), "data": data, "sha256": _sha(data)}
        tmp = destination + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, destination)
        return {"path": destination, "records": len(data), "sha256": doc["sha256"]}

    def restore(self, source: str) -> int:
        """Replace state with a verified backup (the store must be quiesced)."""
        with open(source, encoding="utf-8") as fh:
            doc = migrate(json.load(fh))
        if doc.get("sha256") != _sha(doc["data"]):
            raise PlaneError("PLN04-STATE-003", details={"reason": "backup checksum mismatch"})
        with self._lock:
            self._data = {k: (int(v[0]), v[1]) for k, v in doc["data"].items()}
            self.compact()
            return len(self._data)

    def close(self) -> None:
        try:
            self._wal.close()
        finally:
            self._lockfh.close()

    def healthy(self):
        return not self.fail_writes and not self._wal.closed


# --------------------------------------------------------------------------- leases / fencing (M12)

@dataclass(frozen=True, slots=True)
class Lease:
    key: str
    owner: str
    epoch: int
    expires_at: float


class LeaseManager:
    def __init__(self, store: StateStore, *, clock: Callable[[], float] = time.monotonic,
                 on_split_brain: Callable[[str, str, str], None] | None = None) -> None:
        self._store = store
        self._clock = clock
        self._on_split = on_split_brain

    def _next_epoch(self) -> int:
        """Global monotonic fencing counter: every epoch ever issued is larger than all before it,
        so released lease records can be deleted without an epoch ever being reused."""
        while True:
            entry = self._store.get("lease-epoch/counter")
            version, value = (0, 0) if entry is None else entry
            try:
                self._store.cas("lease-epoch/counter", version, int(value) + 1)
                return int(value) + 1
            except PlaneError as exc:
                if exc.code != "PLN04-STATE-001":
                    raise

    def acquire(self, key: str, owner: str, ttl_s: float) -> Lease:
        if ttl_s <= 0 or ttl_s > 3600:
            raise ValueError("ttl_s must be in (0, 3600]")
        skey = f"lease/{key}"
        entry = self._store.get(skey)
        now = self._clock()
        version, rec = (0, None) if entry is None else entry
        if rec is not None and rec["expires_at"] > now and rec["owner"] != owner:
            if self._on_split:
                self._on_split(key, rec["owner"], owner)
            raise PlaneError("PLN04-STATE-002", details={"epoch": rec["epoch"], "reason": "held by another owner"})
        epoch = self._next_epoch()
        new = {"owner": owner, "epoch": epoch, "expires_at": now + ttl_s}
        self._store.cas(skey, version, new)  # CAS: a concurrent acquirer gets STATE-001
        return Lease(key, owner, epoch, now + ttl_s)

    def renew(self, lease: Lease, ttl_s: float) -> Lease:
        skey = f"lease/{lease.key}"
        entry = self._store.get(skey)
        now = self._clock()
        if entry is None or entry[1]["owner"] != lease.owner or entry[1]["epoch"] != lease.epoch or entry[1]["expires_at"] < now:
            raise PlaneError("PLN04-STATE-002", details={"epoch": lease.epoch, "reason": "lease lost"})
        self._store.cas(skey, entry[0], {**entry[1], "expires_at": now + ttl_s})
        return Lease(lease.key, lease.owner, lease.epoch, now + ttl_s)

    def validate(self, lease: Lease) -> None:
        entry = self._store.get(f"lease/{lease.key}")
        if entry is None or entry[1]["epoch"] != lease.epoch or entry[1]["owner"] != lease.owner or entry[1]["expires_at"] < self._clock():
            raise PlaneError("PLN04-STATE-002", details={"epoch": lease.epoch, "reason": "lease no longer valid"})

    def release(self, lease: Lease) -> None:
        skey = f"lease/{lease.key}"
        entry = self._store.get(skey)
        if entry is not None and entry[1]["owner"] == lease.owner and entry[1]["epoch"] == lease.epoch:
            # safe to delete: the global counter guarantees the next epoch is larger
            self._store.delete(skey, entry[0])
