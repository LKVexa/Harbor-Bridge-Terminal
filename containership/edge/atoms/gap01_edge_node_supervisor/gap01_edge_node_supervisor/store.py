"""Durable supervisor state store (4), idempotency journal (15),
power-loss recovery (23), backup/reconstruction (38), migration engine (39).

Layout under ``state_dir`` (mode 0700)::

    state.json        latest checkpoint {schema_version, generation, body, sha256}
    state.json.prev   previous checkpoint (rollback / corruption fallback)
    journal.jsonl     write-ahead journal; each line carries its own sha256
    requests.jsonl    idempotency completion records (bounded window)

Writes are atomic: temp file -> fsync -> rename -> fsync(dir).  A torn or
corrupt checkpoint is detected by checksum and the store falls back to the
previous checkpoint and replays the journal tail.  A torn final journal line
(power loss mid-append) is discarded; a corrupt line *before* the tail is
treated as corruption and fails closed.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import tarfile
import threading
from collections import OrderedDict
from typing import Any
from collections.abc import Callable

from .errors import SupervisorError

STATE_SCHEMA_VERSION = 2


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _fsync_dir(path: pathlib.Path) -> None:
    if os.name != "posix":
        return
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    _fsync_dir(path.parent)


# --- migration engine (39) -------------------------------------------------
def _migrate_1_to_2(body: dict) -> dict:
    """v4.x state (schema 1) had no generation-scoped drain intent or cordon ack."""
    body = dict(body)
    body.setdefault("drain_intent", None)
    body.setdefault("cordon_ack", None)
    body.setdefault("emergency", None)
    return body


MIGRATIONS: dict[int, Callable[[dict], dict]] = {1: _migrate_1_to_2}


def migrate(body: dict, from_version: int) -> dict:
    if from_version > STATE_SCHEMA_VERSION:
        raise SupervisorError("E_MIGRATION", f"state schema {from_version} is newer than "
                              f"supported {STATE_SCHEMA_VERSION}; downgrade is not supported")
    v = from_version
    while v < STATE_SCHEMA_VERSION:
        if v not in MIGRATIONS:
            raise SupervisorError("E_MIGRATION", f"no migration from schema {v}")
        body = MIGRATIONS[v](body)
        v += 1
    return body


class StateStore:
    def __init__(self, state_dir: str | os.PathLike, *, replay_window: int = 4096,
                 fsync: bool = True) -> None:
        self.dir = pathlib.Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            os.chmod(self.dir, 0o700)
        self.fsync = fsync
        self.state_path = self.dir / "state.json"
        self.prev_path = self.dir / "state.json.prev"
        self.journal_path = self.dir / "journal.jsonl"
        self.requests_path = self.dir / "requests.jsonl"
        self.replay_window = replay_window
        self.generation = 0
        self._lock = threading.RLock()
        self._requests: OrderedDict[str, dict] = OrderedDict()
        self.recovery_notes: list[str] = []
        self._load_requests()

    # -- checkpoint ------------------------------------------------------
    def checkpoint(self, body: dict) -> int:
        with self._lock:
            self.generation += 1
            doc = {"schema_version": STATE_SCHEMA_VERSION, "generation": self.generation,
                   "body": body}
            doc["sha256"] = _sha(_canon({k: doc[k] for k in ("schema_version", "generation", "body")}))
            try:
                if self.state_path.exists():
                    shutil.copy2(self.state_path, self.prev_path)
                atomic_write(self.state_path, _canon(doc))
                # journal entries up to this generation are now folded in
                atomic_write(self.journal_path, b"")
            except OSError as exc:
                self.generation -= 1
                raise SupervisorError("E_PERSISTENCE", f"checkpoint failed: {exc.strerror}") from None
            return self.generation

    def _read_checkpoint(self, path: pathlib.Path) -> dict | None:
        if not path.exists():
            return None
        try:
            doc = json.loads(path.read_bytes())
            want = _sha(_canon({k: doc[k] for k in ("schema_version", "generation", "body")}))
            if doc.get("sha256") != want:
                raise ValueError("checksum mismatch")
            return doc
        except (ValueError, KeyError, TypeError) as exc:
            self.recovery_notes.append(f"{path.name}: rejected ({exc})")
            return None

    def load(self) -> tuple[dict | None, list[dict]]:
        """Return (checkpoint body or None, journal entries after it)."""
        with self._lock:
            doc = self._read_checkpoint(self.state_path)
            if doc is None and self.state_path.exists():
                doc = self._read_checkpoint(self.prev_path)
                if doc is None:
                    raise SupervisorError("E_STATE_CORRUPT", "current and previous checkpoints invalid")
                self.recovery_notes.append("fell back to previous checkpoint")
            body = None
            if doc is not None:
                self.generation = int(doc["generation"])
                body = migrate(doc["body"], int(doc["schema_version"]))
                if int(doc["schema_version"]) != STATE_SCHEMA_VERSION:
                    self.recovery_notes.append(
                        f"migrated state schema {doc['schema_version']} -> {STATE_SCHEMA_VERSION}")
            return body, self._read_journal()

    # -- write-ahead journal ---------------------------------------------
    def append_journal(self, entry: dict) -> None:
        with self._lock:
            payload = _canon(entry)
            line = _canon({"e": entry, "sha256": _sha(payload)}) + b"\n"
            try:
                with open(self.journal_path, "ab") as fh:
                    fh.write(line)
                    fh.flush()
                    if self.fsync:
                        os.fsync(fh.fileno())
            except OSError as exc:
                raise SupervisorError("E_PERSISTENCE", f"journal append failed: {exc.strerror}") from None

    def _read_journal(self) -> list[dict]:
        if not self.journal_path.exists():
            return []
        lines = self.journal_path.read_bytes().split(b"\n")
        out: list[dict] = []
        body_lines = [ln for ln in lines if ln.strip()]
        for i, ln in enumerate(body_lines):
            try:
                rec = json.loads(ln)
                if rec["sha256"] != _sha(_canon(rec["e"])):
                    raise ValueError("checksum")
                out.append(rec["e"])
            except (ValueError, KeyError, TypeError):
                if i == len(body_lines) - 1:
                    self.recovery_notes.append("discarded torn journal tail")
                    break
                raise SupervisorError("E_STATE_CORRUPT", f"journal record {i} corrupt") from None
        return out

    # -- idempotency / request journal (15) ------------------------------
    def _load_requests(self) -> None:
        if not self.requests_path.exists():
            return
        for ln in self.requests_path.read_bytes().split(b"\n"):
            if not ln.strip():
                continue
            try:
                rec = json.loads(ln)
                self._requests[rec["key"]] = rec["response"]
            except (ValueError, KeyError, TypeError):
                self.recovery_notes.append("discarded torn request record")
        while len(self._requests) > self.replay_window:
            self._requests.popitem(last=False)

    def completed(self, key: str) -> dict | None:
        with self._lock:
            return self._requests.get(key)

    def record_completion(self, key: str, response: dict) -> None:
        with self._lock:
            self._requests[key] = response
            while len(self._requests) > self.replay_window:
                self._requests.popitem(last=False)
            line = _canon({"key": key, "response": response}) + b"\n"
            try:
                with open(self.requests_path, "ab") as fh:
                    fh.write(line)
                    if self.fsync:
                        os.fsync(fh.fileno())
                if self.requests_path.stat().st_size > 4 * 1024 * 1024:
                    self._compact_requests()
            except OSError as exc:
                raise SupervisorError("E_PERSISTENCE", f"request record failed: {exc.strerror}") from None

    def _compact_requests(self) -> None:
        data = b"".join(_canon({"key": k, "response": v}) + b"\n" for k, v in self._requests.items())
        atomic_write(self.requests_path, data)

    # -- backup / reconstruction (38) ------------------------------------
    def backup(self, dest: str | os.PathLike) -> pathlib.Path:
        dest = pathlib.Path(dest)
        with self._lock, tarfile.open(dest, "w:gz") as tar:
            for p in (self.state_path, self.prev_path, self.journal_path, self.requests_path):
                if p.exists():
                    tar.add(p, arcname=p.name)
        return dest

    @staticmethod
    def restore(archive: str | os.PathLike, state_dir: str | os.PathLike) -> pathlib.Path:
        target = pathlib.Path(state_dir)
        target.mkdir(parents=True, exist_ok=True)
        allowed = {"state.json", "state.json.prev", "journal.jsonl", "requests.jsonl"}
        with tarfile.open(archive, "r:gz") as tar:
            for m in tar.getmembers():
                if m.name not in allowed or not m.isfile():
                    raise SupervisorError("E_STATE_CORRUPT", f"unexpected backup member {m.name!r}")
                data = tar.extractfile(m).read()  # type: ignore[union-attr]
                atomic_write(target / m.name, data)
        return target


class AuditLog:
    """Tamper-evident append-only audit log (26): each record chains the
    previous record's hash; ``verify`` detects edits, deletions, reordering."""

    GENESIS = "0" * 64

    def __init__(self, path: str | os.PathLike, *, retention: int = 100_000, fsync: bool = True) -> None:
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.retention = retention
        self.fsync = fsync
        self._lock = threading.Lock()
        self.head = self.GENESIS
        self.count = 0
        if self.path.exists():
            ok, head, n = self.verify(self.path)
            if not ok:
                raise SupervisorError("E_STATE_CORRUPT", "audit log chain broken")
            self.head, self.count = head, n

    def append(self, event: dict) -> str:
        with self._lock:
            rec = {"seq": self.count, "prev": self.head, "event": event}
            h = _sha(_canon(rec))
            rec["hash"] = h
            with open(self.path, "ab") as fh:
                fh.write(_canon(rec) + b"\n")
                if self.fsync:
                    os.fsync(fh.fileno())
            self.head, self.count = h, self.count + 1
            return h

    @staticmethod
    def verify(path: str | os.PathLike) -> tuple[bool, str, int]:
        head, n = AuditLog.GENESIS, 0
        first = True
        for ln in pathlib.Path(path).read_bytes().split(b"\n"):
            if not ln.strip():
                continue
            try:
                rec = json.loads(ln)
                h = rec.pop("hash")
                if first and rec["seq"] != 0:
                    head = rec["prev"]  # rotated log: trust anchor is first prev
                    n = rec["seq"]
                first = False
                if rec["prev"] != head or rec["seq"] != n or _sha(_canon(rec)) != h:
                    return False, head, n
                head, n = h, n + 1
            except (ValueError, KeyError, TypeError):
                return False, head, n
        return True, head, n
