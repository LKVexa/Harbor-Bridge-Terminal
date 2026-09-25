"""MC-25 / MC-24 - Durable revision store with fencing and lifecycle controls.

Layout under ``root``::

    revisions/<tenant>/<environment>/<revision>.json   immutable, content-addressed
    heads/<tenant>/<environment>/<application>.json    current + history (supersession chain)
    control.json                                       fencing epoch, freezes, disable, quarantine

Every write is tmp-file + fsync + ``os.replace`` (atomic on POSIX and NTFS).
Publication requires the caller's fencing epoch to equal the stored epoch, so a
stale controller that lost its lease cannot publish (split-brain protection).
Reads re-verify the content address; a corrupt revision is reported and
auto-quarantined rather than served.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import tempfile
import threading
import time
from typing import Any, Mapping

from .errors import PlaneError
from .resolver import RevisionIntegrityError, verify_revision

_NAME = re.compile(r"^[a-z0-9][a-z0-9._\-]{0,62}$")
_REV = re.compile(r"^[0-9a-f]{64}$")
MAX_HISTORY = 1000


def _atomic_write(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, sort_keys=True, separators=(",", ":"))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _name(v: str, field: str) -> str:
    if not isinstance(v, str) or not _NAME.fullmatch(v):
        raise PlaneError(f"invalid {field}", code="INVALID_APPLICATION", details={"field": field})
    return v


class RevisionStore:
    def __init__(self, root: str | os.PathLike, clock=time.time) -> None:
        self.root = pathlib.Path(root)
        self._clock = clock
        self._lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)
        self.recovery_report = self._recover()

    # ------------------------------------------------------------ control state
    def _control_path(self) -> pathlib.Path:
        return self.root / "control.json"

    def _control(self) -> dict:
        p = self._control_path()
        if not p.exists():
            return {"epoch": 0, "holder": None, "frozen": [], "disabled": False, "quarantined": []}
        return json.loads(p.read_text("utf-8"))

    def _save_control(self, c: dict) -> None:
        _atomic_write(self._control_path(), c)

    def acquire_epoch(self, holder: str) -> int:
        """Take ownership; bumps the fencing epoch so any prior holder is fenced."""
        with self._lock:
            c = self._control()
            c["epoch"] += 1
            c["holder"] = str(holder)[:128]
            self._save_control(c)
            return c["epoch"]

    def _fence(self, epoch: int) -> dict:
        c = self._control()
        if epoch != c["epoch"]:
            raise PlaneError("stale fencing epoch", code="FENCED", details={"held": c["epoch"], "presented": epoch})
        return c

    def freeze(self, scope: str, epoch: int) -> None:
        with self._lock:
            c = self._fence(epoch)
            if scope not in c["frozen"]:
                c["frozen"].append(scope)
            self._save_control(c)

    def unfreeze(self, scope: str, epoch: int) -> None:
        with self._lock:
            c = self._fence(epoch)
            c["frozen"] = [s for s in c["frozen"] if s != scope]
            self._save_control(c)

    def set_disabled(self, disabled: bool, epoch: int) -> None:
        with self._lock:
            c = self._fence(epoch)
            c["disabled"] = bool(disabled)
            self._save_control(c)

    def quarantine(self, revision: str, epoch: int | None = None) -> None:
        with self._lock:
            c = self._control() if epoch is None else self._fence(epoch)
            if revision not in c["quarantined"]:
                c["quarantined"].append(revision)
            self._save_control(c)

    def release(self, revision: str, epoch: int) -> None:
        with self._lock:
            c = self._fence(epoch)
            c["quarantined"] = [r for r in c["quarantined"] if r != revision]
            self._save_control(c)

    def status(self) -> dict:
        c = self._control()
        return {k: c[k] for k in ("epoch", "holder", "frozen", "disabled", "quarantined")}

    def check_writable(self, tenant: str, environment: str) -> None:
        c = self._control()
        if c["disabled"]:
            raise PlaneError("application plane disabled", code="PLANE_DISABLED", details={"scope": "*"})
        for scope in ("*", tenant, f"{tenant}/{environment}"):
            if scope in c["frozen"]:
                raise PlaneError("scope frozen", code="PLANE_FROZEN", details={"scope": scope})

    # ------------------------------------------------------------ revisions
    def _rev_path(self, tenant: str, env: str, rev: str) -> pathlib.Path:
        return self.root / "revisions" / tenant / env / f"{rev}.json"

    def _head_path(self, tenant: str, env: str, app: str) -> pathlib.Path:
        return self.root / "heads" / tenant / env / f"{app}.json"

    def publish(self, *, tenant: str, environment: str, application: str, revision: Mapping[str, Any],
                epoch: int, provenance: Mapping[str, Any] | None = None) -> dict:
        tenant, environment, application = (_name(tenant, "tenant"), _name(environment, "environment"),
                                            _name(application, "application"))
        verify_revision(revision)
        rev = revision["revision"]
        with self._lock:
            self._fence(epoch)
            self.check_writable(tenant, environment)
            if rev in self._control()["quarantined"]:
                raise PlaneError("revision quarantined", code="REVISION_QUARANTINED", details={"revision": rev})
            path = self._rev_path(tenant, environment, rev)
            if path.exists():
                stored = json.loads(path.read_text("utf-8"))
                if stored["revision"] != revision:
                    raise PlaneError("content address collision", code="REVISION_INTEGRITY_ERROR")
            else:
                _atomic_write(path, {"revision": dict(revision), "sealed_at": self._clock(),
                                     "provenance": dict(provenance or {})})
            head_p = self._head_path(tenant, environment, application)
            head = json.loads(head_p.read_text("utf-8")) if head_p.exists() else {"current": None, "history": []}
            if head["current"] != rev:  # idempotent re-publish is a no-op
                if head["current"] is not None:
                    head["history"].append({"revision": head["current"], "superseded_by": rev, "at": self._clock()})
                    head["history"] = head["history"][-MAX_HISTORY:]
                head["current"] = rev
                _atomic_write(head_p, head)
            return {"revision": rev, "application": application, "tenant": tenant, "environment": environment}

    def get(self, tenant: str, environment: str, rev: str) -> dict:
        if not isinstance(rev, str) or not _REV.fullmatch(rev):
            raise PlaneError("revision not found", code="REVISION_NOT_FOUND", details={"revision": str(rev)[:64]})
        path = self._rev_path(_name(tenant, "tenant"), _name(environment, "environment"), rev)
        if not path.exists():
            raise PlaneError("revision not found", code="REVISION_NOT_FOUND", details={"revision": rev})
        if rev in self._control()["quarantined"]:
            raise PlaneError("revision quarantined", code="REVISION_QUARANTINED", details={"revision": rev})
        data = json.loads(path.read_text("utf-8"))["revision"]
        try:
            verify_revision(data)
            if data["revision"] != rev:
                raise RevisionIntegrityError("stored under wrong address")
        except RevisionIntegrityError:
            self.quarantine(rev)
            raise
        return data

    def head(self, tenant: str, environment: str, application: str) -> dict:
        p = self._head_path(_name(tenant, "tenant"), _name(environment, "environment"), _name(application, "application"))
        if not p.exists():
            raise PlaneError("application has no revisions", code="REVISION_NOT_FOUND", details={"revision": None})
        return json.loads(p.read_text("utf-8"))

    def rollback(self, *, tenant: str, environment: str, application: str, epoch: int) -> str:
        """Re-point the head at the previous (non-quarantined) revision."""
        with self._lock:
            self._fence(epoch)
            head = self.head(tenant, environment, application)
            q = set(self._control()["quarantined"])
            for entry in reversed(head["history"]):
                if entry["revision"] not in q:
                    head["history"].append({"revision": head["current"], "superseded_by": entry["revision"],
                                            "at": self._clock(), "rollback": True})
                    head["current"] = entry["revision"]
                    _atomic_write(self._head_path(tenant, environment, application), head)
                    return entry["revision"]
        raise PlaneError("no prior revision to roll back to", code="REVISION_NOT_FOUND", details={"revision": None})

    # ------------------------------------------------------------ recovery / backup
    def _recover(self) -> dict:
        removed, corrupt = 0, []
        for tmp in self.root.rglob(".tmp-*"):
            tmp.unlink(missing_ok=True)
            removed += 1
        for p in (self.root / "revisions").rglob("*.json") if (self.root / "revisions").exists() else []:
            try:
                data = json.loads(p.read_text("utf-8"))["revision"]
                verify_revision(data)
                if data["revision"] != p.stem:
                    raise RevisionIntegrityError("address mismatch")
            except Exception:
                corrupt.append(p.stem)
        if corrupt:
            c = self._control()
            c["quarantined"] = sorted(set(c["quarantined"]) | set(corrupt))
            self._save_control(c)
        return {"tmp_removed": removed, "corrupt_quarantined": corrupt}

    def backup(self, dest: str | os.PathLike) -> pathlib.Path:
        dest = pathlib.Path(dest)
        if dest.exists():
            raise PlaneError("backup destination exists", code="CONFIG_INVALID", details={"field": "dest"})
        with self._lock:
            shutil.copytree(self.root, dest)
        RevisionStore(dest)  # verifies on open
        return dest

    @classmethod
    def restore(cls, backup: str | os.PathLike, root: str | os.PathLike) -> "RevisionStore":
        root = pathlib.Path(root)
        if root.exists() and any(root.iterdir()):
            raise PlaneError("restore target not empty", code="CONFIG_INVALID", details={"field": "root"})
        shutil.copytree(backup, root, dirs_exist_ok=True)
        store = cls(root)
        c = store._control()
        c["epoch"] += 1  # restored store fences every pre-backup holder
        c["holder"] = None
        store._save_control(c)
        return store
