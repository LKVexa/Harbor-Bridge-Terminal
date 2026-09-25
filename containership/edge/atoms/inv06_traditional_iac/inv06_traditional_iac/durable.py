"""Durable state backend, crash-safe journal, rollback and backup tooling.

Package-local reference implementations for MC-010, MC-012, MC-013 and MC-014.

* ``FileStateBackend`` persists ``PK_IAC_STATE/1`` snapshots as immutable,
  digest-sealed revision files and moves a ``HEAD`` pointer with an atomic
  ``os.replace`` after ``fsync``.  Writes are compare-and-swap on the serial,
  so a writer holding an older serial can never commit.
* A write-ahead intent journal (``journal.jsonl``) records ``intent`` before a
  revision is published and ``commit`` after; ``recover()`` resolves any
  interrupted apply deterministically on restart.
* ``rollback_to()`` republishes an earlier revision as a *new* serial (history
  is never rewritten), with preconditions and an audit record.
* ``backup()`` / ``restore()`` produce and verify a self-describing archive;
  ``migrate_snapshot()`` is the format-migration hook.

This is a single-host backend.  It is durable against process crash on a
POSIX filesystem with working ``fsync``; it is not replicated and does not
replace a managed remote-state service (see ``governance/SUPPORT_MATRIX.md``).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import tarfile
import tempfile
import threading
import time
from collections.abc import Mapping
from typing import Any

from .state import STATE_SCHEMA, IacError, IacState, InvalidState, _canonical_bytes

REVISION_SCHEMA = "PK_IAC_REVISION/1"
JOURNAL_SCHEMA = "PK_IAC_JOURNAL/1"
BACKUP_SCHEMA = "PK_IAC_BACKUP/1"

DEFAULT_MAX_STATE_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_REVISIONS = 1000


class StateConflict(IacError):
    code = "PK_IAC_STATE_CONFLICT"


class StateCorrupt(IacError):
    code = "PK_IAC_STATE_CORRUPT"


class StateTooLarge(IacError):
    code = "PK_IAC_STATE_TOO_LARGE"


class RollbackRefused(IacError):
    code = "PK_IAC_ROLLBACK_REFUSED"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_dir(path: pathlib.Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:  # pragma: no cover - platforms without directory fds
        return
    try:
        os.fsync(fd)
    except OSError:  # pragma: no cover
        pass
    finally:
        os.close(fd)


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    """Write ``data`` to ``path`` so readers see either old or new bytes, never a mix."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def seal_snapshot(snapshot: Mapping[str, Any], *, parent_digest: str | None, meta: Mapping[str, Any] | None = None) -> dict[str, Any]:
    body = {
        "schema": REVISION_SCHEMA,
        "state": dict(snapshot),
        "parent_digest": parent_digest,
        "meta": dict(meta or {}),
    }
    return {**body, "digest": _sha256(_canonical_bytes(body))}


def verify_revision(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("schema") != REVISION_SCHEMA:
        raise StateCorrupt("revision schema missing or unsupported", details={"schema": getattr(record, "get", lambda _k: None)("schema")})
    body = {k: record[k] for k in ("schema", "state", "parent_digest", "meta") if k in record}
    if len(body) != 4:
        raise StateCorrupt("revision is missing required fields")
    actual = _sha256(_canonical_bytes(body))
    if actual != record.get("digest"):
        raise StateCorrupt("revision digest mismatch", details={"expected": actual, "supplied": record.get("digest")})
    state = record["state"]
    if not isinstance(state, Mapping) or state.get("schema") != STATE_SCHEMA:
        raise StateCorrupt("embedded state schema unsupported")
    return dict(record)


def migrate_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Upgrade known older snapshot shapes to ``PK_IAC_STATE/1`` or refuse.

    ``PK_IAC_STATE/0`` (4.1.x: ``resources``/``serial``/``protected`` without a
    schema tag) is accepted and upgraded.  Unknown versions fail closed.
    """
    schema = snapshot.get("schema")
    if schema == STATE_SCHEMA:
        return dict(snapshot)
    if schema in (None, "PK_IAC_STATE/0") and {"resources", "serial"} <= set(snapshot):
        return {
            "schema": STATE_SCHEMA,
            "serial": snapshot["serial"],
            "resources": snapshot["resources"],
            "protected": sorted(snapshot.get("protected", [])),
            "audit_head": "0" * 64,
        }
    raise InvalidState("unsupported state schema version", details={"schema": schema, "supported": [STATE_SCHEMA, "PK_IAC_STATE/0"]})


class FileStateBackend:
    """Transactional file-backed state store with revision history and WAL."""

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        max_state_bytes: int = DEFAULT_MAX_STATE_BYTES,
        max_revisions: int = DEFAULT_MAX_REVISIONS,
    ) -> None:
        self.root = pathlib.Path(root)
        self.revisions = self.root / "revisions"
        self.revisions.mkdir(parents=True, exist_ok=True)
        self.head_path = self.root / "HEAD"
        self.journal_path = self.root / "journal.jsonl"
        self.max_state_bytes = max_state_bytes
        self.max_revisions = max_revisions
        self._lock = threading.RLock()

    # -- journal ---------------------------------------------------------
    def _journal(self, entry: Mapping[str, Any]) -> None:
        line = json.dumps({"schema": JOURNAL_SCHEMA, "time_ns": time.time_ns(), **entry}, sort_keys=True) + "\n"
        with open(self.journal_path, "ab") as fh:
            fh.write(line.encode("utf-8"))
            fh.flush()
            os.fsync(fh.fileno())

    def journal_entries(self) -> list[dict[str, Any]]:
        if not self.journal_path.exists():
            return []
        out = []
        for raw in self.journal_path.read_text("utf-8").splitlines():
            try:
                out.append(json.loads(raw))
            except json.JSONDecodeError:
                # A torn final line from a crash mid-append is ignored; it can
                # only be an intent that was never followed by a commit.
                continue
        return out

    # -- read ------------------------------------------------------------
    def _rev_path(self, serial: int) -> pathlib.Path:
        return self.revisions / f"{serial:012d}.json"

    def head_serial(self) -> int | None:
        if not self.head_path.exists():
            return None
        text = self.head_path.read_text("utf-8").strip()
        try:
            return int(text)
        except ValueError as exc:
            raise StateCorrupt("HEAD pointer is not an integer", details={"head": text[:64]}) from exc

    def read_revision(self, serial: int) -> dict[str, Any]:
        path = self._rev_path(serial)
        if not path.exists():
            raise StateCorrupt("revision file missing", details={"serial": serial})
        try:
            record = json.loads(path.read_bytes())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StateCorrupt("revision file unreadable", details={"serial": serial}) from exc
        record = verify_revision(record)
        if record["state"].get("serial") != serial:
            raise StateCorrupt("revision serial does not match file name", details={"serial": serial})
        return record

    def load(self) -> dict[str, Any] | None:
        """Return the verified HEAD snapshot, or ``None`` for an empty backend."""
        with self._lock:
            self.recover()
            serial = self.head_serial()
            if serial is None:
                return None
            return dict(self.read_revision(serial)["state"])

    def load_state(self) -> IacState:
        snap = self.load()
        if snap is None:
            return IacState()
        return IacState(resources=snap["resources"], serial=snap["serial"], protected=snap.get("protected", []))

    def history(self) -> list[int]:
        return sorted(int(p.stem) for p in self.revisions.glob("*.json") if p.stem.isdigit())

    # -- write -----------------------------------------------------------
    def commit(self, snapshot: Mapping[str, Any], *, expected_serial: int | None, meta: Mapping[str, Any] | None = None) -> int:
        """Compare-and-swap publish of ``snapshot``.

        ``expected_serial`` is the HEAD serial the writer read (``None`` for an
        empty backend).  Any other HEAD refuses the write with ``StateConflict``.
        """
        snap = migrate_snapshot(snapshot)
        new_serial = snap.get("serial")
        if isinstance(new_serial, bool) or not isinstance(new_serial, int) or new_serial < 0:
            raise InvalidState("snapshot serial must be a non-negative integer")
        with self._lock:
            self.recover()
            head = self.head_serial()
            if head != expected_serial:
                raise StateConflict("state HEAD moved; refusing stale writer", details={"expected": expected_serial, "actual": head})
            if head is not None and new_serial <= head:
                raise StateConflict("serial must advance monotonically", details={"head": head, "new": new_serial})
            parent = self.read_revision(head)["digest"] if head is not None else None
            record = seal_snapshot(snap, parent_digest=parent, meta=meta)
            data = _canonical_bytes(record)
            if len(data) > self.max_state_bytes:
                raise StateTooLarge("state exceeds configured maximum", details={"bytes": len(data), "limit": self.max_state_bytes})
            txid = record["digest"][:16]
            self._journal({"op": "intent", "txid": txid, "serial": new_serial, "parent": head, "digest": record["digest"]})
            atomic_write(self._rev_path(new_serial), data)
            atomic_write(self.head_path, str(new_serial).encode())
            self._journal({"op": "commit", "txid": txid, "serial": new_serial})
            self._compact()
            return new_serial

    def commit_state(self, state: IacState, *, expected_serial: int | None, meta: Mapping[str, Any] | None = None) -> int:
        return self.commit(state.snapshot(), expected_serial=expected_serial, meta=meta)

    def _compact(self) -> None:
        revs = self.history()
        head = self.head_serial()
        excess = len(revs) - self.max_revisions
        for serial in revs[: max(0, excess)]:
            if serial != head:
                self._rev_path(serial).unlink(missing_ok=True)

    # -- recovery --------------------------------------------------------
    def recover(self) -> dict[str, Any]:
        """Resolve interrupted transactions left in the journal.

        An ``intent`` without ``commit``: if HEAD already points at the intended
        serial and that revision verifies, the commit is completed (roll
        forward); otherwise the orphan revision file is removed (roll back).
        """
        with self._lock:
            entries = self.journal_entries()
            committed = {e["txid"] for e in entries if e.get("op") in ("commit", "abort")}
            outcome = {"rolled_forward": [], "rolled_back": []}
            for e in entries:
                if e.get("op") != "intent" or e["txid"] in committed:
                    continue
                head = self.head_serial()
                serial = e["serial"]
                ok = False
                if head == serial:
                    try:
                        ok = self.read_revision(serial)["digest"] == e["digest"]
                    except StateCorrupt:
                        ok = False
                if ok:
                    self._journal({"op": "commit", "txid": e["txid"], "serial": serial, "recovered": True})
                    outcome["rolled_forward"].append(serial)
                else:
                    if head != serial:
                        self._rev_path(serial).unlink(missing_ok=True)
                    else:  # HEAD points at a corrupt revision: restore parent pointer
                        parent = e.get("parent")
                        if parent is None:
                            self.head_path.unlink(missing_ok=True)
                        else:
                            atomic_write(self.head_path, str(parent).encode())
                        self._rev_path(serial).unlink(missing_ok=True)
                    self._journal({"op": "abort", "txid": e["txid"], "serial": serial, "recovered": True})
                    outcome["rolled_back"].append(serial)
            return outcome

    # -- rollback --------------------------------------------------------
    def rollback_to(self, target_serial: int, *, expected_serial: int, actor: str, reason: str) -> int:
        """Republish revision ``target_serial`` as a new, higher serial."""
        if not actor or not reason:
            raise RollbackRefused("rollback requires an actor and a reason")
        with self._lock:
            head = self.head_serial()
            if head is None or head != expected_serial:
                raise StateConflict("state HEAD moved; rollback refused", details={"expected": expected_serial, "actual": head})
            if target_serial >= head:
                raise RollbackRefused("rollback target must precede HEAD", details={"target": target_serial, "head": head})
            target = self.read_revision(target_serial)["state"]
            new_snap = dict(target)
            new_snap["serial"] = head + 1
            return self.commit(
                new_snap,
                expected_serial=head,
                meta={"kind": "rollback", "rollback_of": head, "restored_from": target_serial, "actor": actor, "reason": reason},
            )

    # -- backup / restore ------------------------------------------------
    def backup(self, dest: str | os.PathLike[str]) -> dict[str, Any]:
        with self._lock:
            self.recover()
            dest = pathlib.Path(dest)
            revs = self.history()
            manifest = {
                "schema": BACKUP_SCHEMA,
                "created_ns": time.time_ns(),
                "head": self.head_serial(),
                "revisions": {str(s): _sha256(self._rev_path(s).read_bytes()) for s in revs},
            }
            with tarfile.open(dest, "w:gz") as tar:
                for s in revs:
                    tar.add(self._rev_path(s), arcname=f"revisions/{s:012d}.json")
                data = json.dumps(manifest, sort_keys=True).encode()
                info = tarfile.TarInfo("MANIFEST.json")
                info.size = len(data)
                import io

                tar.addfile(info, io.BytesIO(data))
            return manifest

    @classmethod
    def restore(cls, archive: str | os.PathLike[str], root: str | os.PathLike[str], **kwargs: Any) -> "FileStateBackend":
        """Restore into an *empty* directory and verify every revision + chain."""
        root = pathlib.Path(root)
        if root.exists() and any(root.iterdir()):
            raise RollbackRefused("restore target must be empty", details={"root": str(root)})
        with tarfile.open(archive, "r:gz") as tar:
            members = {m.name: m for m in tar.getmembers()}
            for name, m in members.items():
                if not m.isfile() or name.startswith("/") or ".." in pathlib.PurePosixPath(name).parts:
                    raise StateCorrupt("unsafe member in backup archive", details={"member": name})
            manifest = json.loads(tar.extractfile(members["MANIFEST.json"]).read())  # type: ignore[union-attr]
            if manifest.get("schema") != BACKUP_SCHEMA:
                raise StateCorrupt("unsupported backup schema")
            be = cls(root, **kwargs)
            for serial, digest in manifest["revisions"].items():
                data = tar.extractfile(members[f"revisions/{int(serial):012d}.json"]).read()  # type: ignore[union-attr]
                if _sha256(data) != digest:
                    raise StateCorrupt("backup revision digest mismatch", details={"serial": serial})
                verify_revision(json.loads(data))
                atomic_write(be._rev_path(int(serial)), data)
            if manifest["head"] is not None:
                atomic_write(be.head_path, str(manifest["head"]).encode())
        be.verify_chain()
        return be

    def verify_chain(self) -> bool:
        """Verify every retained revision and parent linkage back to the oldest retained one."""
        revs = self.history()
        prev_digest = None
        for i, s in enumerate(revs):
            rec = self.read_revision(s)
            if i > 0 and rec["parent_digest"] != prev_digest:
                raise StateCorrupt("revision chain broken", details={"serial": s})
            prev_digest = rec["digest"]
        return True
