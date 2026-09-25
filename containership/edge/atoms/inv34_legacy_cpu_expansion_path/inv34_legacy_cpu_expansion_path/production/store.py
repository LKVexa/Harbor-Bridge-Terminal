"""Durable file-backed state store (MC-019, MC-020, MC-021, MC-026, MC-065).

SPDX-License-Identifier: NOASSERTION

One JSON document per VM, written atomically (temp file + fsync + os.replace
+ directory fsync).  Every write is a compare-and-swap on ``revision``;
a writer holding a stale revision gets ``CasConflict`` and must re-read.

The document holds: CPU state, the durable idempotency table, the lease
(owner, fence token, expiry) and the operation journal used to rebuild
pending work after a crash.  A POSIX advisory lock (fcntl) serialises
read-modify-write across processes on one host.

Scope statement: this is a single-host durable store.  It gives restart
durability and multi-process safety on one node; it is NOT a replicated
fleet database, and cross-host replica races remain a production integration
(see governance/BLOCKERS.json, MC-019/MC-037).
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]

STORE_SCHEMA = "INV34_VM_STORE/1"
STORE_SCHEMA_VERSIONS = ("INV34_VM_STORE/1",)
MAX_IDEMPOTENCY_ENTRIES = 4096
MAX_JOURNAL_ENTRIES = 1024


class StoreError(RuntimeError):
    code = "STORE_ERROR"


class CasConflict(StoreError):
    code = "STORE_CAS_CONFLICT"


class LeaseHeld(StoreError):
    code = "LEASE_HELD"


class LeaseLost(StoreError):
    code = "LEASE_LOST"


class CorruptDocument(StoreError):
    code = "STORE_CORRUPT"


def _digest(doc: dict) -> str:
    body = {k: v for k, v in doc.items() if k != "digest"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class FileStateStore:
    def __init__(self, root: str | os.PathLike, clock: Callable[[], float] = time.time) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    def _path(self, vm_id: str) -> Path:
        safe = hashlib.sha256(vm_id.encode()).hexdigest()[:32]
        return self.root / f"vm-{safe}.json"

    @contextlib.contextmanager
    def _locked(self, vm_id: str) -> Iterator[None]:
        lock_path = self._path(vm_id).with_suffix(".lock")
        with open(lock_path, "a+") as fh:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

    # -- raw document I/O ----------------------------------------------
    def load(self, vm_id: str) -> dict[str, Any] | None:
        p = self._path(vm_id)
        if not p.exists():
            return None
        try:
            doc = json.loads(p.read_text())
        except ValueError as exc:
            raise CorruptDocument(f"{p.name} is not valid JSON") from exc
        if doc.get("schema") not in STORE_SCHEMA_VERSIONS:
            raise CorruptDocument(f"unsupported store schema {doc.get('schema')!r}")
        if doc.get("digest") != _digest(doc):
            raise CorruptDocument(f"{p.name} digest mismatch (torn or tampered write)")
        if doc.get("vm_id") != vm_id:
            raise CorruptDocument("document vm_id does not match key")
        return doc

    def _write(self, vm_id: str, doc: dict) -> None:
        doc["digest"] = _digest(doc)
        p = self._path(vm_id)
        fd, tmp = tempfile.mkstemp(dir=self.root, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w") as fh:
                json.dump(doc, fh, sort_keys=True, indent=1)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, p)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp)
            raise
        with contextlib.suppress(OSError):
            dfd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)

    def create(self, vm_id: str, cpu_state: dict[str, Any]) -> dict[str, Any]:
        with self._locked(vm_id):
            if self._path(vm_id).exists():
                raise CasConflict("VM document already exists")
            doc = {"schema": STORE_SCHEMA, "vm_id": vm_id, "revision": 1, "cpu": dict(cpu_state),
                   "idempotency": {}, "idempotency_order": [], "lease": None, "fence_counter": 0,
                   "journal": [], "created_at": self._clock()}
            self._write(vm_id, doc)
            return copy.deepcopy(doc)

    def update(self, vm_id: str, expected_revision: int,
               mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Compare-and-swap: apply ``mutate`` only if the revision still matches."""
        with self._locked(vm_id):
            doc = self.load(vm_id)
            if doc is None:
                raise StoreError("VM document does not exist")
            if doc["revision"] != expected_revision:
                raise CasConflict(f"revision {expected_revision} is stale; current {doc['revision']}")
            new = copy.deepcopy(doc)
            mutate(new)
            new["revision"] = doc["revision"] + 1
            self._trim(new)
            self._write(vm_id, new)
            return copy.deepcopy(new)

    @staticmethod
    def _trim(doc: dict) -> None:
        order = doc["idempotency_order"]
        while len(order) > MAX_IDEMPOTENCY_ENTRIES:
            doc["idempotency"].pop(order.pop(0), None)
        # keep all non-terminal journal entries; trim oldest terminal ones
        j = doc["journal"]
        while len(j) > MAX_JOURNAL_ENTRIES:
            for i, e in enumerate(j):
                if e.get("state") in ("done", "failed", "abandoned"):
                    del j[i]
                    break
            else:
                break

    # -- lease / fencing (MC-021) --------------------------------------
    def acquire_lease(self, vm_id: str, owner: str, ttl_s: float) -> tuple[int, dict]:
        with self._locked(vm_id):
            doc = self.load(vm_id)
            if doc is None:
                raise StoreError("VM document does not exist")
            now = self._clock()
            lease = doc.get("lease")
            if lease and lease["owner"] != owner and lease["expires_at"] > now:
                raise LeaseHeld(f"lease held by {lease['owner']} until {lease['expires_at']:.0f}")
            new = copy.deepcopy(doc)
            new["fence_counter"] += 1
            new["lease"] = {"owner": owner, "fence": new["fence_counter"], "expires_at": now + ttl_s}
            new["revision"] += 1
            self._write(vm_id, new)
            return new["fence_counter"], copy.deepcopy(new)

    def check_lease(self, doc: dict, owner: str, fence: int) -> None:
        lease = doc.get("lease")
        if not lease or lease["owner"] != owner or lease["fence"] != fence or lease["expires_at"] <= self._clock():
            raise LeaseLost("lease not held with this fence token")

    # -- backup / restore / migrate (MC-065) ---------------------------
    def backup(self, dest: str | os.PathLike) -> dict[str, Any]:
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        entries = []
        for p in sorted(self.root.glob("vm-*.json")):
            data = p.read_bytes()
            doc = json.loads(data)
            if doc.get("digest") != _digest(doc):
                raise CorruptDocument(f"refusing to back up corrupt {p.name}")
            (dest / p.name).write_bytes(data)
            entries.append({"file": p.name, "sha256": hashlib.sha256(data).hexdigest(),
                            "vm_id": doc["vm_id"], "revision": doc["revision"]})
        manifest = {"schema": "INV34_STORE_BACKUP/1", "taken_at": self._clock(), "entries": entries}
        (dest / "BACKUP_MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
        return manifest

    @classmethod
    def restore(cls, backup_dir: str | os.PathLike, root: str | os.PathLike) -> "FileStateStore":
        """Restore verifies every file; restored state is marked ``needs_reconcile`` so
        it is never trusted until reconciled against live hypervisor/guest state."""
        backup_dir, store = Path(backup_dir), cls(root)
        manifest = json.loads((backup_dir / "BACKUP_MANIFEST.json").read_text())
        for e in manifest["entries"]:
            data = (backup_dir / e["file"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != e["sha256"]:
                raise CorruptDocument(f"backup file {e['file']} fails its manifest digest")
            doc = json.loads(data)
            doc["needs_reconcile"] = True
            doc["lease"] = None
            doc["revision"] += 1
            store._write(doc["vm_id"], doc)
        return store

    def vm_ids(self) -> list[str]:
        out = []
        for p in sorted(self.root.glob("vm-*.json")):
            with contextlib.suppress(ValueError, KeyError):
                out.append(json.loads(p.read_text())["vm_id"])
        return out


def migrate_document(doc: dict) -> dict:
    """Schema migration entry point. Only /1 exists; unknown versions are refused."""
    if doc.get("schema") == STORE_SCHEMA:
        return doc
    raise CorruptDocument(f"no migration path from {doc.get('schema')!r}")
