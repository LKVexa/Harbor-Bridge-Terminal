"""Durable transactional rollout-state store (component 1) and backup/restore (component 24).

``FileStateStore`` is a reference backend with the semantics GAP-08 requires of
any production backend (GAP-05 or a selected database):

* **compare-and-swap** on ``state_revision`` — exactly one writer wins for a
  given expected revision; the rest get ``StaleRevision``;
* **fencing** — every commit carries the controller's fencing token; a token
  lower than the highest one ever committed, or one the lease service reports
  as not current, is refused with ``StaleFence``;
* **atomic, durable writes** — write temp file, ``fsync``, ``os.replace``,
  ``fsync`` the directory; a crash leaves either the old or the new record,
  never a torn one;
* **integrity** — each record carries ``state_digest``; reads verify it;
* **immutability guards** — ``pinned_target`` and the audit-log prefix can never
  be rewritten by a later commit;
* **no secrets** — records pass ``assert_no_secrets`` before persisting.

Commit point: a transition is *accepted* when ``commit`` returns; it is
*recoverable* from that moment (fsync'd); it is *externally visible* once the
audit sink has sealed the matching event (see ``audit_sink``).
"""
from __future__ import annotations

import fcntl
import json
import os
import shutil
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Protocol

from .common import Clock, SystemClock, canonical_json, digest_of, sha256_hex
from .errors import Conflict, IntegrityFailure, StaleFence, StaleRevision, ValidationFailed
from .secrets_boundary import assert_no_secrets

RECORD_SCHEMA = "PK_STORE_RECORD/1"
BACKUP_SCHEMA = "PK_STORE_BACKUP/1"
_ID_OK = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")

FenceCheck = Callable[[str, int], None]  # raises StaleFence if token not current


@dataclass(frozen=True)
class Record:
    rollout_id: str
    revision: int
    fence: int
    state: dict[str, Any]
    state_digest: str
    created_at: float
    updated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {"schema": RECORD_SCHEMA, "rollout_id": self.rollout_id, "revision": self.revision,
                "fence": self.fence, "state": self.state, "state_digest": self.state_digest,
                "created_at": self.created_at, "updated_at": self.updated_at}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Record":
        if not isinstance(raw, Mapping) or raw.get("schema") != RECORD_SCHEMA:
            raise IntegrityFailure("unsupported store record schema")
        state = raw.get("state")
        if not isinstance(state, dict) or digest_of(state) != raw.get("state_digest"):
            raise IntegrityFailure("store record digest mismatch", resource=str(raw.get("rollout_id")))
        return cls(str(raw["rollout_id"]), int(raw["revision"]), int(raw["fence"]), dict(state),
                   str(raw["state_digest"]), float(raw["created_at"]), float(raw["updated_at"]))


class StateStore(Protocol):
    def create(self, rollout_id: str, state: Mapping[str, Any], *, fence: int) -> Record: ...
    def load(self, rollout_id: str) -> Record: ...
    def commit(self, rollout_id: str, state: Mapping[str, Any], *, expected_revision: int, fence: int) -> Record: ...
    def list_ids(self) -> list[str]: ...


def _check_id(rollout_id: str) -> str:
    if not isinstance(rollout_id, str) or not rollout_id or len(rollout_id) > 128 or not set(rollout_id) <= _ID_OK \
            or rollout_id.startswith("."):
        raise ValidationFailed(f"invalid rollout id {rollout_id!r}")
    return rollout_id


def _guard_transition(old: Record, new_state: Mapping[str, Any]) -> None:
    old_pin = old.state.get("pinned_target")
    if old_pin is not None and new_state.get("pinned_target") != old_pin:
        raise IntegrityFailure("pinned_target is immutable after first commit", resource=old.rollout_id)
    old_log = old.state.get("audit_log") or []
    new_log = new_state.get("audit_log") or []
    if len(new_log) < len(old_log) or [e.get("event_hash") for e in new_log[: len(old_log)]] != \
            [e.get("event_hash") for e in old_log]:
        raise IntegrityFailure("audit log prefix may not be rewritten", resource=old.rollout_id)
    if new_state.get("rollout_id") not in (None, old.rollout_id):
        raise IntegrityFailure("rollout_id may not change", resource=old.rollout_id)


class _Base:
    def __init__(self, *, fence_check: FenceCheck | None = None, clock: Clock | None = None) -> None:
        self.fence_check = fence_check
        self.clock = clock or SystemClock()

    def _prepare(self, rollout_id: str, state: Mapping[str, Any], fence: int) -> dict[str, Any]:
        _check_id(rollout_id)
        if not isinstance(fence, int) or fence < 1:
            raise ValidationFailed("fence must be a positive integer")
        state = dict(state)
        try:
            canonical_json(state)
        except (TypeError, ValueError) as exc:
            raise ValidationFailed("state must be finite JSON", cause=exc) from exc
        assert_no_secrets(state, where="state store")
        if self.fence_check is not None:
            self.fence_check(rollout_id, fence)
        return state


class MemoryStateStore(_Base):
    """Thread-safe in-memory backend with identical semantics (tests, simulation)."""

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self._data: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, rollout_id, state, *, fence):
        state = self._prepare(rollout_id, state, fence)
        with self._lock:
            if rollout_id in self._data:
                raise Conflict(f"rollout {rollout_id} already exists", resource=rollout_id)
            t = self.clock.now()
            rec = Record(rollout_id, 1, fence, state, digest_of(state), t, t)
            self._data[rollout_id] = json.loads(json.dumps(rec.to_dict()))
            return rec

    def load(self, rollout_id):
        with self._lock:
            raw = self._data.get(_check_id(rollout_id))
        if raw is None:
            raise ValidationFailed(f"unknown rollout {rollout_id}", resource=rollout_id)
        return Record.from_dict(json.loads(json.dumps(raw)))

    def commit(self, rollout_id, state, *, expected_revision, fence):
        state = self._prepare(rollout_id, state, fence)
        with self._lock:
            raw = self._data.get(rollout_id)
            if raw is None:
                raise ValidationFailed(f"unknown rollout {rollout_id}", resource=rollout_id)
            old = Record.from_dict(raw)
            if fence < old.fence:
                raise StaleFence(f"fence {fence} < committed fence {old.fence}", resource=rollout_id)
            if old.revision != expected_revision:
                raise StaleRevision(f"expected revision {expected_revision}, store has {old.revision}",
                                    resource=rollout_id)
            _guard_transition(old, state)
            rec = Record(rollout_id, old.revision + 1, fence, state, digest_of(state), old.created_at,
                         self.clock.now())
            self._data[rollout_id] = json.loads(json.dumps(rec.to_dict()))
            return rec

    def list_ids(self):
        with self._lock:
            return sorted(self._data)


class FileStateStore(_Base):
    """Crash-safe single-host durable backend (reference for the GAP-05 contract)."""

    def __init__(self, root: str | os.PathLike[str], **kw: Any) -> None:
        super().__init__(**kw)
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self._tlock = threading.Lock()

    def _path(self, rollout_id: str) -> Path:
        return self.root / f"{_check_id(rollout_id)}.json"

    @contextmanager
    def _locked(self) -> Iterator[None]:
        # Thread lock + inter-process advisory lock.
        with self._tlock:
            fd = os.open(self.root / ".lock", os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

    def _write_atomic(self, path: Path, data: bytes) -> None:
        tmp = path.with_suffix(f".tmp.{os.getpid()}.{threading.get_ident()}")
        fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, path)
        dfd = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    def _read(self, rollout_id: str) -> Record | None:
        p = self._path(rollout_id)
        if not p.exists():
            return None
        try:
            raw = json.loads(p.read_bytes())
        except json.JSONDecodeError as exc:
            raise IntegrityFailure("torn or corrupt store record", resource=rollout_id, cause=exc) from exc
        return Record.from_dict(raw)

    def create(self, rollout_id, state, *, fence):
        state = self._prepare(rollout_id, state, fence)
        with self._locked():
            if self._path(rollout_id).exists():
                raise Conflict(f"rollout {rollout_id} already exists", resource=rollout_id)
            t = self.clock.now()
            rec = Record(rollout_id, 1, fence, state, digest_of(state), t, t)
            self._write_atomic(self._path(rollout_id), canonical_json(rec.to_dict()))
            return rec

    def load(self, rollout_id):
        rec = self._read(rollout_id)
        if rec is None:
            raise ValidationFailed(f"unknown rollout {rollout_id}", resource=rollout_id)
        return rec

    def commit(self, rollout_id, state, *, expected_revision, fence):
        state = self._prepare(rollout_id, state, fence)
        with self._locked():
            old = self._read(rollout_id)
            if old is None:
                raise ValidationFailed(f"unknown rollout {rollout_id}", resource=rollout_id)
            if fence < old.fence:
                raise StaleFence(f"fence {fence} < committed fence {old.fence}", resource=rollout_id)
            if old.revision != expected_revision:
                raise StaleRevision(f"expected revision {expected_revision}, store has {old.revision}",
                                    resource=rollout_id)
            _guard_transition(old, state)
            rec = Record(rollout_id, old.revision + 1, fence, state, digest_of(state), old.created_at,
                         self.clock.now())
            self._write_atomic(self._path(rollout_id), canonical_json(rec.to_dict()))
            return rec

    def list_ids(self):
        return sorted(p.stem for p in self.root.glob("*.json"))

    # ---- component 24: backup / restore -------------------------------------------------------
    def backup(self, dest: str | os.PathLike[str]) -> dict[str, Any]:
        """Consistent point-in-time copy (taken under the store lock) plus a digest manifest."""
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=False)
        with self._locked():
            files = {}
            for p in sorted(self.root.glob("*.json")):
                data = p.read_bytes()
                Record.from_dict(json.loads(data))  # refuse to back up corrupt state
                (dest / p.name).write_bytes(data)
                files[p.name] = sha256_hex(data)
        manifest = {"schema": BACKUP_SCHEMA, "taken_at": self.clock.now(), "files": files}
        manifest["manifest_digest"] = digest_of({k: v for k, v in manifest.items()})
        (dest / "BACKUP_MANIFEST.json").write_bytes(canonical_json(manifest))
        return manifest

    @classmethod
    def restore(cls, backup_dir: str | os.PathLike[str], target: str | os.PathLike[str], **kw: Any) -> "FileStateStore":
        """Restore into an *empty* target after verifying every digest; never merges."""
        backup_dir, target = Path(backup_dir), Path(target)
        manifest = json.loads((backup_dir / "BACKUP_MANIFEST.json").read_bytes())
        recorded = manifest.pop("manifest_digest", None)
        if manifest.get("schema") != BACKUP_SCHEMA or digest_of(manifest) != recorded:
            raise IntegrityFailure("backup manifest failed verification")
        if target.exists() and any(target.glob("*.json")):
            raise Conflict("restore target is not empty", resource=str(target))
        staging = target.with_name(target.name + ".restoring")
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        for name, digest in manifest["files"].items():
            data = (backup_dir / name).read_bytes()
            if sha256_hex(data) != digest:
                raise IntegrityFailure(f"backup file {name} digest mismatch")
            Record.from_dict(json.loads(data))
            (staging / name).write_bytes(data)
        if target.exists():
            target.rmdir()
        os.replace(staging, target)
        return cls(target, **kw)
