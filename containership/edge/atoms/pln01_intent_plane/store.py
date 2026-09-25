"""Durable persistence, crash consistency, audit sealing, backup/restore,
migration (MC-027, MC-022) and single-writer lease with fencing (MC-028).

Layout of ``state_dir``::

    FORMAT            on-disk format version (migrations keyed on it)
    snapshot.json     atomic (write-temp + fsync + rename) full state + chain head
    wal.jsonl         hash-chained, MAC-sealed commit records after the snapshot
    audit.jsonl       hash-chained, MAC-sealed audit records (append-only)
    LEASE             owner + expiry + fencing token

Recovery loads the snapshot, replays WAL records with a version greater than
the snapshot, verifies every hash and MAC, and tolerates exactly one torn
trailing record (a crash mid-append).  Corruption anywhere else raises
``StoreIntegrityError`` (fail-stop, never silent repair).

This is a single-host durable store.  Replicated consensus across hosts is an
external dependency documented in docs/ADR-0002-state-and-consensus.md.
"""
from __future__ import annotations

import json
import os
import shutil
import tarfile
import threading
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

from .errors import LeaseError, StoreIntegrityError
from .graph import IntentGraph, _canonical_json
from .trust import KeyProvider

FORMAT_VERSION = 2
GENESIS = "0" * 64


def _k(key) -> str:
    return "\x1f".join(key)


def _unk(s: str) -> tuple[str, str, str]:
    parts = tuple(s.split("\x1f"))
    if len(parts) != 3:
        raise StoreIntegrityError("malformed node key in store")
    return parts  # type: ignore[return-value]


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write(path: Path, data: bytes, fsync: bool = True) -> None:
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}-{threading.get_ident()}")
    with open(tmp, "wb") as handle:
        handle.write(data)
        handle.flush()
        if fsync:
            os.fsync(handle.fileno())
    os.replace(tmp, path)
    if fsync:
        _fsync_dir(path.parent)


class _Chain:
    """Append-only hash-chained, MAC-sealed JSONL log."""

    def __init__(self, path: Path, keys: KeyProvider, fsync: bool) -> None:
        self.path, self.keys, self.fsync = path, keys, fsync
        self.head = GENESIS
        self.count = 0

    def seal(self, body: dict[str, Any]) -> dict[str, Any]:
        body = dict(body, prev=self.head)
        h = sha256(_canonical_json(body).encode()).hexdigest()
        return dict(body, hash=h, mac=self.keys.mac(h.encode()))

    def append(self, body: dict[str, Any]) -> dict[str, Any]:
        rec = self.seal(body)
        line = (json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with open(self.path, "ab") as handle:
            handle.write(line)
            handle.flush()
            if self.fsync:
                os.fsync(handle.fileno())
        self.head, self.count = rec["hash"], self.count + 1
        return rec

    def read(self, start_head: str | None = GENESIS, *, repair_tail: bool = True) -> list[dict[str, Any]]:
        """Verify and return records. ``start_head=None`` adopts the first record's
        ``prev`` as the base (the caller must then anchor the chain itself)."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            if start_head is not None:
                self.head = start_head
            return []
        if start_head is None:
            first = self.path.read_bytes().split(b"\n", 1)[0]
            try:
                start_head = json.loads(first)["prev"]
            except (json.JSONDecodeError, KeyError) as exc:
                raise StoreIntegrityError(f"{self.path.name}: unreadable first record") from exc
        raw = self.path.read_bytes()
        lines = raw.split(b"\n")
        records: list[dict[str, Any]] = []
        prev = start_head
        good_bytes = 0
        for i, line in enumerate(lines):
            if not line:
                good_bytes += 1 if i < len(lines) - 1 else 0
                continue
            last = i >= len(lines) - 2 and not any(lines[i + 1:])
            try:
                rec = json.loads(line)
                body = {k: v for k, v in rec.items() if k not in ("hash", "mac")}
                if rec.get("prev") != prev:
                    raise StoreIntegrityError(f"{self.path.name}: chain break at record {i}")
                if sha256(_canonical_json(body).encode()).hexdigest() != rec.get("hash"):
                    raise StoreIntegrityError(f"{self.path.name}: hash mismatch at record {i}")
                if not self.keys.verify_mac(rec["hash"].encode(), rec.get("mac", "")):
                    raise StoreIntegrityError(f"{self.path.name}: MAC seal invalid at record {i}")
            except (json.JSONDecodeError, KeyError, StoreIntegrityError) as exc:
                if last and not raw.endswith(b"\n") and repair_tail:
                    with open(self.path, "r+b") as handle:   # torn trailing append
                        handle.truncate(good_bytes)
                    break
                if isinstance(exc, StoreIntegrityError):
                    raise
                raise StoreIntegrityError(f"{self.path.name}: unreadable record {i}") from exc
            records.append(rec)
            prev = rec["hash"]
            good_bytes += len(line) + 1
        self.head, self.count = prev, len(records)
        return records


class DurableStore:
    """Write-ahead durable store bound to one :class:`IntentGraph`."""

    def __init__(self, state_dir: str | os.PathLike, keys: KeyProvider, *, fsync: bool = True,
                 snapshot_every: int = 256) -> None:
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.keys, self.fsync, self.snapshot_every = keys, fsync, snapshot_every
        self.wal = _Chain(self.dir / "wal.jsonl", keys, fsync)
        self.audit = _Chain(self.dir / "audit.jsonl", keys, fsync)
        self._lock = threading.Lock()
        self.fencing_token: int | None = None
        self._since_snapshot = 0
        self._graph: IntentGraph | None = None
        migrate(self.dir)

    # ------------------------------------------------------------------ open
    def open_graph(self, **graph_kwargs: Any) -> IntentGraph:
        graph = IntentGraph(on_commit=self._on_commit, **graph_kwargs)
        version, nodes, edges, wal_head = self._load_snapshot()
        records = self.wal.read(None)
        if records:
            base = records[0]["prev"]
            if base != wal_head:
                # Crash between snapshot write and WAL compaction: the snapshot's
                # head must appear inside the retained chain at its version.
                anchor = [r for r in records if r["v"] == version]
                if not anchor or anchor[0]["hash"] != wal_head:
                    raise StoreIntegrityError("WAL does not chain to snapshot head")
        else:
            self.wal.head = wal_head
        for rec in records:
            if rec["v"] <= version:
                continue
            if rec["v"] != version + 1:
                raise StoreIntegrityError(f"WAL gap: expected version {version + 1}, found {rec['v']}")
            for k, spec in rec["nodes"].items():
                if spec is None:
                    nodes.pop(_unk(k), None)
                else:
                    nodes[_unk(k)] = spec
            for k, deps in rec["edges"].items():
                if deps is None:
                    edges.pop(_unk(k), None)
                else:
                    edges[_unk(k)] = frozenset(tuple(d) for d in deps)
            version = rec["v"]
        graph._restore_state(version, nodes, edges)
        self.audit.read(self._audit_anchor())
        self._graph = graph
        return graph

    def _audit_anchor(self) -> str:
        snap = self.dir / "snapshot.json"
        if snap.exists():
            return json.loads(snap.read_text()).get("audit_anchor", GENESIS)
        return GENESIS

    def _load_snapshot(self):
        snap = self.dir / "snapshot.json"
        if not snap.exists():
            return 0, {}, {}, GENESIS
        doc = json.loads(snap.read_text())
        body = {k: v for k, v in doc.items() if k != "mac"}
        if not self.keys.verify_mac(_canonical_json(body).encode(), doc.get("mac", "")):
            raise StoreIntegrityError("snapshot MAC seal invalid")
        nodes = {_unk(k): v for k, v in doc["nodes"].items()}
        edges = {_unk(k): frozenset(tuple(d) for d in v) for k, v in doc["edges"].items()}
        return doc["version"], nodes, edges, doc["wal_head"]

    # ---------------------------------------------------------------- writes
    def _on_commit(self, version: int, nodes: dict, edges: dict) -> None:
        with self._lock:
            self.wal.append({
                "v": version, "fence": self.fencing_token, "ts": time.time(),
                "nodes": {_k(k): v for k, v in nodes.items()},
                "edges": {_k(k): (None if v is None else sorted(list(d) for d in v)) for k, v in edges.items()},
            })
            self._since_snapshot += 1

    def maybe_snapshot(self) -> bool:
        if self._since_snapshot >= self.snapshot_every:
            self.snapshot()
            return True
        return False

    def snapshot(self) -> Path:
        if self._graph is None:
            raise StoreIntegrityError("store not opened")
        with self._lock:
            version, nodes, edges = self._graph._planning_state()
            body = {"format": FORMAT_VERSION, "version": version, "wal_head": self.wal.head,
                    "audit_anchor": self._audit_anchor(), "taken_at": time.time(),
                    "nodes": {_k(k): v for k, v in sorted(nodes.items())},
                    "edges": {_k(k): sorted(list(d) for d in v) for k, v in sorted(edges.items())}}
            body["mac"] = self.keys.mac(_canonical_json(body).encode())
            path = self.dir / "snapshot.json"
            atomic_write(path, json.dumps(body, sort_keys=True).encode(), self.fsync)
            atomic_write(self.wal.path, b"", self.fsync)   # compact: snapshot now covers the WAL
            self._since_snapshot = 0
            return path

    def append_audit(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            return self.audit.append(dict(event, fence=self.fencing_token))

    def verify(self) -> dict[str, Any]:
        """Full offline integrity verification (no repair)."""
        version, _, _, wal_head = self._load_snapshot()
        wal = _Chain(self.wal.path, self.keys, False).read(None, repair_tail=False)
        if wal and wal[0]["prev"] != wal_head and not any(r["hash"] == wal_head for r in wal):
            raise StoreIntegrityError("WAL does not chain to snapshot head")
        audit = _Chain(self.audit.path, self.keys, False).read(self._audit_anchor(), repair_tail=False)
        return {"snapshot_version": version, "wal_records": len(wal), "audit_records": len(audit), "ok": True}

    # -------------------------------------------------------- backup/restore
    def backup(self, destination: str | os.PathLike) -> dict[str, Any]:
        self.snapshot()
        dest = Path(destination)
        with tarfile.open(dest, "w:gz") as tar:
            for name in ("FORMAT", "snapshot.json", "wal.jsonl", "audit.jsonl"):
                p = self.dir / name
                if p.exists():
                    tar.add(p, arcname=name)
        digest = sha256(dest.read_bytes()).hexdigest()
        manifest = {"backup": dest.name, "sha256": digest, "graph_version": self._graph.version if self._graph else None,
                    "taken_at": time.time(), "format": FORMAT_VERSION}
        atomic_write(dest.with_suffix(dest.suffix + ".manifest.json"), json.dumps(manifest, indent=2).encode(), self.fsync)
        return manifest

    @staticmethod
    def restore(backup: str | os.PathLike, state_dir: str | os.PathLike, *, expected_sha256: str) -> Path:
        src = Path(backup)
        if sha256(src.read_bytes()).hexdigest() != expected_sha256:
            raise StoreIntegrityError("backup digest mismatch; refusing restore")
        target = Path(state_dir)
        if target.exists() and any(target.iterdir()):
            raise StoreIntegrityError("restore target is not empty")
        target.mkdir(parents=True, exist_ok=True)
        with tarfile.open(src, "r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile() or "/" in member.name or member.name.startswith("."):
                    raise StoreIntegrityError(f"unsafe member in backup: {member.name}")
            tar.extractall(target)  # members validated above
        return target


def migrate(state_dir: Path) -> int:
    """Upgrade on-disk format in place. v1 (no FORMAT file, audit unsealed) -> v2."""
    fmt = state_dir / "FORMAT"
    current = int(fmt.read_text().strip()) if fmt.exists() else (1 if any(state_dir.iterdir()) else FORMAT_VERSION)
    if current > FORMAT_VERSION:
        raise StoreIntegrityError(f"state format {current} is newer than supported {FORMAT_VERSION}; downgrade refused")
    if current == 1:
        legacy = state_dir / "state.json"
        if legacy.exists():
            legacy.rename(state_dir / "state.v1.json.bak")
    if current != FORMAT_VERSION or not fmt.exists():
        atomic_write(fmt, f"{FORMAT_VERSION}\n".encode())
    return FORMAT_VERSION


class FileLease:
    """Single-writer lease with monotonically increasing fencing tokens.

    Guarantees at most one live holder among processes sharing ``path``'s
    filesystem.  Writers stamp their fencing token on every WAL record; a
    holder that lost its lease is refused (split-brain protection at the store
    boundary).  Cross-host leases require an external coordinator.
    """

    def __init__(self, path: str | os.PathLike, owner: str, ttl: float = 15.0,
                 clock=time.time) -> None:
        self.path, self.owner, self.ttl, self._clock = Path(path), owner, ttl, clock
        self.token: int | None = None

    def _read(self) -> dict[str, Any] | None:
        try:
            return json.loads(self.path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def acquire(self) -> int:
        lock = self.path.with_suffix(".lock")
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise LeaseError("lease is being modified concurrently") from exc
        try:
            cur = self._read()
            now = self._clock()
            if cur and cur["owner"] != self.owner and cur["expires"] > now:
                raise LeaseError(f"lease held by {cur['owner']} until {cur['expires']}")
            token = (cur["token"] + 1) if cur else 1
            atomic_write(self.path, json.dumps({"owner": self.owner, "expires": now + self.ttl, "token": token}).encode())
            self.token = token
            return token
        finally:
            os.close(fd)
            os.unlink(lock)

    def renew(self) -> None:
        cur = self._read()
        if not cur or cur["owner"] != self.owner or cur["token"] != self.token:
            raise LeaseError("lease lost; fencing token stale")
        if cur["expires"] <= self._clock():
            raise LeaseError("lease expired before renewal")
        atomic_write(self.path, json.dumps(dict(cur, expires=self._clock() + self.ttl)).encode())

    def check(self) -> int:
        cur = self._read()
        if not cur or cur["owner"] != self.owner or cur["token"] != self.token or cur["expires"] <= self._clock():
            raise LeaseError("not the lease holder; mutation refused (split-brain guard)")
        return self.token  # type: ignore[return-value]

    def release(self) -> None:
        cur = self._read()
        if cur and cur["owner"] == self.owner and cur["token"] == self.token:
            atomic_write(self.path, json.dumps(dict(cur, expires=0)).encode())
        self.token = None
