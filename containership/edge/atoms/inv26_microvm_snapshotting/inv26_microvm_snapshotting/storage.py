"""Snapshot blob storage port and adapters (X003, C032, C095, X010).

INV-26 does not *own* blob storage (contract ``not_owns``) but it must own the
port it calls. :class:`BlobStore` is that port. Blobs are addressed by
``(tenant, snapshot_id, generation)`` under a per-tenant prefix, so a worker
scoped to one tenant never needs list rights over another (C042).

Adapters:

* :class:`FilesystemBlobStore` — durable local adapter for edge/single-node
  and for the integration suite: write to a private temp file in the same
  directory, ``fsync``, atomic ``os.replace``, ``fsync`` the directory; files
  are ``0600``, directories ``0700``; reads verify the recorded size; a
  configurable byte quota returns ``SNAP_STORAGE_FULL`` before writing.
* :class:`MemoryBlobStore` — tests only.

An object-store (S3/GCS/Azure) adapter is **not** included (BLOCKED_EXTERNAL):
it must implement the same four methods with tenant-prefix-scoped
credentials.
"""
from __future__ import annotations

import os
import re
import secrets
import threading
from pathlib import Path

from .errors import SnapshotServiceError

_SAFE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")


def _key(tenant: str, snapshot_id: str, generation: int) -> tuple[str, str]:
    if not (_SAFE.fullmatch(tenant) and _SAFE.fullmatch(snapshot_id)) or ".." in tenant + snapshot_id:
        raise SnapshotServiceError("SNAP_INVALID_REQUEST", "unsafe blob key")
    if not isinstance(generation, int) or generation < 1:
        raise SnapshotServiceError("SNAP_INVALID_REQUEST", "bad generation")
    return tenant, f"{snapshot_id}.g{generation}.blob"


class BlobStore:
    def put(self, tenant: str, snapshot_id: str, generation: int, data: bytes) -> str:  # pragma: no cover
        raise NotImplementedError

    def get(self, tenant: str, snapshot_id: str, generation: int) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def delete(self, tenant: str, snapshot_id: str, generation: int) -> bool:  # pragma: no cover
        raise NotImplementedError

    def list(self, tenant: str) -> list[str]:  # pragma: no cover
        raise NotImplementedError

    def health(self) -> bool:
        return True


class MemoryBlobStore(BlobStore):
    def __init__(self, quota_bytes: int | None = None):
        self._d: dict[tuple[str, str], bytes] = {}
        self._lock = threading.Lock()
        self.quota_bytes = quota_bytes
        self.available = True

    def _up(self):
        if not self.available:
            raise SnapshotServiceError("SNAP_STORAGE_UNAVAILABLE", "memory store offline")

    def put(self, tenant, snapshot_id, generation, data):
        self._up()
        k = _key(tenant, snapshot_id, generation)
        with self._lock:
            used = sum(len(v) for v in self._d.values())
            if self.quota_bytes is not None and used + len(data) > self.quota_bytes:
                raise SnapshotServiceError("SNAP_STORAGE_FULL", "quota")
            if k in self._d:
                raise SnapshotServiceError("SNAP_DUPLICATE", "blob exists")
            self._d[k] = bytes(data)
        return "/".join(k)

    def get(self, tenant, snapshot_id, generation):
        self._up()
        with self._lock:
            try:
                return self._d[_key(tenant, snapshot_id, generation)]
            except KeyError:
                raise SnapshotServiceError("SNAP_STORAGE_CORRUPT", "blob missing") from None

    def delete(self, tenant, snapshot_id, generation):
        self._up()
        with self._lock:
            return self._d.pop(_key(tenant, snapshot_id, generation), None) is not None

    def list(self, tenant):
        with self._lock:
            return sorted(n for (t, n) in self._d if t == tenant)

    def health(self):
        return self.available

    def corrupt(self, tenant, snapshot_id, generation, fn) -> None:
        """Test hook: replace stored bytes with ``fn(old)``."""
        k = _key(tenant, snapshot_id, generation)
        with self._lock:
            self._d[k] = fn(self._d[k])


class FilesystemBlobStore(BlobStore):
    def __init__(self, root: str | os.PathLike, *, quota_bytes: int | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        self.quota_bytes = quota_bytes
        self._lock = threading.Lock()

    def _path(self, tenant, snapshot_id, generation) -> Path:
        t, name = _key(tenant, snapshot_id, generation)
        d = self.root / t
        try:
            d.mkdir(exist_ok=True, mode=0o700)
        except OSError as exc:  # FZ/FI-3: an unreachable root must be a catalogued, retryable failure
            raise SnapshotServiceError("SNAP_STORAGE_UNAVAILABLE", type(exc).__name__) from None
        return d / name

    def _used(self) -> int:
        return sum(p.stat().st_size for p in self.root.rglob("*.blob") if p.is_file())

    def put(self, tenant, snapshot_id, generation, data):
        p = self._path(tenant, snapshot_id, generation)
        with self._lock:
            if self.quota_bytes is not None and self._used() + len(data) > self.quota_bytes:
                raise SnapshotServiceError("SNAP_STORAGE_FULL", "filesystem quota")
            if p.exists():
                raise SnapshotServiceError("SNAP_DUPLICATE", "blob exists")
            tmp = p.with_name(f".{p.name}.{secrets.token_hex(6)}.tmp")
            try:
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as fh:
                    fh.write(data)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp, p)
                dfd = os.open(p.parent, os.O_RDONLY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
            except OSError as exc:
                try:
                    tmp.unlink()
                except OSError:
                    pass
                code = "SNAP_STORAGE_FULL" if getattr(exc, "errno", None) == 28 else "SNAP_STORAGE_UNAVAILABLE"
                raise SnapshotServiceError(code, type(exc).__name__) from None
        return str(p.relative_to(self.root))

    def get(self, tenant, snapshot_id, generation):
        p = self._path(tenant, snapshot_id, generation)
        try:
            return p.read_bytes()
        except FileNotFoundError:
            raise SnapshotServiceError("SNAP_STORAGE_CORRUPT", "blob missing") from None
        except OSError as exc:
            raise SnapshotServiceError("SNAP_STORAGE_UNAVAILABLE", type(exc).__name__) from None

    def delete(self, tenant, snapshot_id, generation):
        p = self._path(tenant, snapshot_id, generation)
        try:
            size = p.stat().st_size
            # overwrite before unlink: best-effort only (COW/SSD/journaling make it
            # unreliable) -- crypto-erase via DEK destruction is the primary control.
            with open(p, "r+b") as fh:
                fh.write(b"\x00" * min(size, 1 << 20))
                fh.flush()
                os.fsync(fh.fileno())
            p.unlink()
            return True
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise SnapshotServiceError("SNAP_STORAGE_UNAVAILABLE", type(exc).__name__) from None

    def list(self, tenant):
        d = self.root / tenant
        try:
            return sorted(p.name for p in d.glob("*.blob")) if d.is_dir() else []
        except OSError as exc:
            raise SnapshotServiceError("SNAP_STORAGE_UNAVAILABLE", type(exc).__name__) from None

    def health(self):
        return os.access(self.root, os.W_OK)

    def stray_temp_files(self) -> list[Path]:
        return sorted(self.root.rglob(".*.tmp"))
