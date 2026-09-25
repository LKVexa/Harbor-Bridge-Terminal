"""Shared durable file storage for cross-process providers.

Layout inside the state directory (created 0700, verified owned by this user and not a
symlink):  ``<resource>.lock`` (OS lock target), ``<resource>.json`` (ownership record),
``<resource>.gen`` (fencing generation floor), ``quarantine/`` (repaired records).
Writes are atomic: temp file (O_EXCL|O_NOFOLLOW, 0600) -> fsync -> os.replace -> fsync(dir).
"""

from __future__ import annotations

import json
import os
import stat
import sys
import time
from contextlib import contextmanager
from typing import Optional

from .base import ClaimProvider, OwnershipCorrupt, validate_resource

NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
CLOEXEC = getattr(os, "O_CLOEXEC", 0)
BINARY = getattr(os, "O_BINARY", 0)
MAX_RECORD_BYTES = 64 * 1024


def default_state_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "inv23", "claims")
    base = os.environ.get("XDG_RUNTIME_DIR")
    if base and os.path.isdir(base):
        return os.path.join(base, "inv23")
    return os.path.join(os.path.expanduser("~"), ".cache", "inv23", "claims")


class InsecureStateDir(OwnershipCorrupt):
    code = "insecure_state_dir"


def ensure_secure_dir(path: str, *, allow_group: bool = False) -> str:
    path = os.path.abspath(path)
    os.makedirs(path, mode=0o770 if allow_group else 0o700, exist_ok=True)
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise InsecureStateDir(f"{path} is not a real directory")
    if sys.platform != "win32":
        if st.st_uid != os.getuid():
            raise InsecureStateDir(f"{path} is not owned by uid {os.getuid()}")
        forbidden = 0o007 if allow_group else 0o077
        if st.st_mode & forbidden:
            raise InsecureStateDir(f"{path} permissions {oct(st.st_mode & 0o777)} are too open")
    return path


class FileClaimProvider(ClaimProvider):
    def __init__(self, state_dir: Optional[str] = None, *, allow_group: bool = False, **kw) -> None:
        super().__init__(**kw)
        self.state_dir = ensure_secure_dir(state_dir or default_state_dir(), allow_group=allow_group)
        self._mode = 0o660 if allow_group else 0o600

    def _path(self, resource: str, suffix: str) -> str:
        return os.path.join(self.state_dir, validate_resource(resource) + suffix)

    # OS lock hooks
    def _os_lock(self, fd: int) -> None:
        raise NotImplementedError

    def _os_unlock(self, fd: int) -> None:
        raise NotImplementedError

    @contextmanager
    def _critical(self, resource):
        fd = os.open(self._path(resource, ".lock"), os.O_RDWR | os.O_CREAT | NOFOLLOW | CLOEXEC | BINARY, self._mode)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                raise InsecureStateDir("lock target is not a regular file")
            self._os_lock(fd)
            try:
                yield
            finally:
                self._os_unlock(fd)
        finally:
            os.close(fd)

    def _read_bytes(self, path: str) -> Optional[bytes]:
        try:
            fd = os.open(path, os.O_RDONLY | NOFOLLOW | CLOEXEC | BINARY)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise OwnershipCorrupt(f"cannot open {os.path.basename(path)}: {exc}") from exc
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise OwnershipCorrupt("record is not a regular file")
            data = os.read(fd, MAX_RECORD_BYTES + 1)
        finally:
            os.close(fd)
        if len(data) > MAX_RECORD_BYTES:
            raise OwnershipCorrupt("record too large")
        return data

    def _atomic_write(self, path: str, data: bytes) -> None:
        tmp = f"{path}.{os.getpid()}.{time.monotonic_ns()}.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW | CLOEXEC | BINARY, self._mode)
        try:
            view = memoryview(data)
            while view:
                n = os.write(fd, view)
                view = view[n:]
            os.fsync(fd)
        except BaseException:
            os.close(fd)
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        os.close(fd)
        os.replace(tmp, path)
        if sys.platform != "win32":
            dfd = os.open(self.state_dir, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)

    def _load(self, resource):
        raw = self._read_bytes(self._path(resource, ".json"))
        if raw is None:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise OwnershipCorrupt(f"record is not valid JSON (partial write?): {exc}") from exc

    def _store(self, resource, rec):
        self._atomic_write(self._path(resource, ".json"), json.dumps(rec, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    def _load_generation(self, resource):
        raw = self._read_bytes(self._path(resource, ".gen"))
        if raw is None:
            return 0
        try:
            g = int(raw.decode("ascii").strip())
        except (UnicodeDecodeError, ValueError) as exc:
            raise OwnershipCorrupt("generation file corrupt") from exc
        if g < 0:
            raise OwnershipCorrupt("negative generation")
        return g

    def _store_generation(self, resource, gen):
        self._atomic_write(self._path(resource, ".gen"), str(int(gen)).encode("ascii"))

    def _quarantine(self, resource):
        q = ensure_secure_dir(os.path.join(self.state_dir, "quarantine"))
        src = self._path(resource, ".json")
        if os.path.lexists(src):
            os.replace(src, os.path.join(q, f"{resource}.{int(time.time())}.json"))
        gen = self._path(resource, ".gen")
        try:
            self._load_generation(resource)
        except OwnershipCorrupt:
            os.replace(gen, os.path.join(q, f"{resource}.{int(time.time())}.gen"))
