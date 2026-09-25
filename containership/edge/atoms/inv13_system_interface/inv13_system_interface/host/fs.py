"""MC-003 -- descriptor/handle-relative filesystem resolver (POSIX hosts).

A preopen is an *already-open directory descriptor*; nothing is ever
re-resolved from a host path string after the grant.  Relative opens walk one
component at a time with ``openat(dirfd, name, O_NOFOLLOW|...)``, so a symlink
anywhere in the chain -- including one swapped in by a racing attacker between
calls -- is refused by the kernel (ELOOP/ENOTDIR) rather than followed.  On
Linux >= 5.6 the whole walk is additionally delegated to ``openat2`` with
``RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS`` (and
``RESOLVE_NO_XDEV`` if requested), which is atomic against rename races.

``..`` is never passed to the kernel; guest paths are rejected lexically if
they contain empty, ``.``-only-escaping or ``..`` components, so the component
walk cannot climb above its descriptor.
"""
from __future__ import annotations

import ctypes
import os
import stat
import struct
import sys
from typing import Any

from .errors import ErrorCode, Inv13Error, from_os_error

MAX_PATH = 4096
MAX_COMPONENT = 255
MAX_DEPTH = 128

RESOLVE_NO_XDEV = 0x01
RESOLVE_NO_MAGICLINKS = 0x02
RESOLVE_NO_SYMLINKS = 0x04
RESOLVE_BENEATH = 0x08
_SYS_OPENAT2 = {"x86_64": 437, "aarch64": 437}.get(os.uname().machine) if hasattr(os, "uname") else None

_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_PATH = getattr(os, "O_PATH", 0)
_O_TMPFILE = getattr(os, "O_TMPFILE", 0)

SUPPORTED = sys.platform != "win32" and bool(_O_NOFOLLOW) and os.open in os.supports_dir_fd


def split_guest_path(path: Any) -> list[str]:
    """Validate a guest path and return its components (no kernel involved)."""
    if not isinstance(path, str):
        raise Inv13Error(ErrorCode.INVALID_ARGUMENT, type(path).__name__)
    if len(path.encode("utf-8", "surrogatepass")) > MAX_PATH:
        raise Inv13Error(ErrorCode.TOO_LONG)
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        raise Inv13Error(ErrorCode.INVALID_ENCODING) from None
    if "\0" in path:
        raise Inv13Error(ErrorCode.PATH_ESCAPE, "nul")
    if path.startswith("/") or path.startswith("\\"):
        raise Inv13Error(ErrorCode.PATH_ESCAPE, "absolute")
    parts = [p for p in path.split("/") if p not in ("", ".")]
    if not parts:
        return []
    if len(parts) > MAX_DEPTH:
        raise Inv13Error(ErrorCode.TOO_LONG, "depth")
    for p in parts:
        if p == "..":
            raise Inv13Error(ErrorCode.PATH_ESCAPE, "dotdot")
        if len(p.encode("utf-8")) > MAX_COMPONENT:
            raise Inv13Error(ErrorCode.TOO_LONG, "component")
    return parts


class _OpenHow(ctypes.Structure):
    _fields_ = [("flags", ctypes.c_uint64), ("mode", ctypes.c_uint64), ("resolve", ctypes.c_uint64)]


_libc = None
_openat2_ok: bool | None = None


def _openat2(dirfd: int, path: str, flags: int, mode: int, resolve: int) -> int:
    global _libc
    if _libc is None:
        _libc = ctypes.CDLL(None, use_errno=True)
    how = _OpenHow(flags | _O_CLOEXEC, mode, resolve)
    fd = _libc.syscall(_SYS_OPENAT2, dirfd, path.encode("utf-8"), ctypes.byref(how), ctypes.sizeof(how))
    if fd < 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    return fd


def openat2_available() -> bool:
    global _openat2_ok
    if _openat2_ok is None:
        _openat2_ok = False
        if sys.platform.startswith("linux") and _SYS_OPENAT2:
            try:
                fd = _openat2(os.open("/", os.O_RDONLY | _O_DIRECTORY), ".", os.O_RDONLY | _O_DIRECTORY, 0,
                              RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS)
                os.close(fd)
                _openat2_ok = True
            except OSError:
                _openat2_ok = False
    return _openat2_ok


class Preopen:
    """An open directory descriptor acting as a confinement root."""

    __slots__ = ("logical", "fd", "read_only", "no_xdev", "_dev", "_closed")

    def __init__(self, logical: str, host_root: str, *, read_only: bool = False, no_xdev: bool = True) -> None:
        if not SUPPORTED:
            raise Inv13Error(ErrorCode.PROVIDER_UNAVAILABLE, "descriptor-relative fs unsupported on this host")
        # The host root is resolved exactly once, at grant time, by the operator's policy.
        fd = os.open(host_root, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC)
        self.logical, self.fd, self.read_only, self.no_xdev = logical, fd, read_only, no_xdev
        self._dev = os.fstat(fd).st_dev
        self._closed = False

    def close(self) -> None:
        if not self._closed:
            os.close(self.fd)
            self._closed = True

    def __del__(self) -> None:  # pragma: no cover - best effort
        try:
            self.close()
        except Exception:
            pass

    # -- core walk ------------------------------------------------------
    def _walk_parent(self, parts: list[str]) -> int:
        """Return an fd for the directory containing ``parts[-1]`` (caller closes)."""
        fd = os.dup(self.fd)
        try:
            for name in parts[:-1]:
                nfd = os.open(name, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW | _O_CLOEXEC, dir_fd=fd)
                os.close(fd)
                fd = nfd
                if self.no_xdev and os.fstat(fd).st_dev != self._dev:
                    raise OSError(18, "cross-device")  # EXDEV
            return fd
        except BaseException:
            os.close(fd)
            raise

    def open(self, path: str, flags: int = os.O_RDONLY, mode: int = 0o600) -> int:
        """Open ``path`` beneath this preopen; returns a host fd (caller owns it)."""
        if self._closed:
            raise Inv13Error(ErrorCode.STALE_HANDLE)
        parts = split_guest_path(path)
        write = flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | getattr(os, "O_APPEND", 0))
        if self.read_only and write:
            raise Inv13Error(ErrorCode.POLICY_DENIED, "read-only preopen")
        if not parts:
            return os.dup(self.fd)
        try:
            if openat2_available():
                resolve = RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS
                if self.no_xdev:
                    resolve |= RESOLVE_NO_XDEV
                return _openat2(self.fd, "/".join(parts), flags | _O_NOFOLLOW,
                               mode if (flags & os.O_CREAT) or (_O_TMPFILE and flags & _O_TMPFILE == _O_TMPFILE) else 0,
                               resolve)
            dfd = self._walk_parent(parts)
            try:
                fd = os.open(parts[-1], flags | _O_NOFOLLOW | _O_CLOEXEC, mode, dir_fd=dfd)
            finally:
                os.close(dfd)
            st = os.fstat(fd)
            if self.no_xdev and stat.S_ISDIR(st.st_mode) and st.st_dev != self._dev:
                os.close(fd)
                raise OSError(18, "cross-device")
            return fd
        except OSError as exc:
            raise from_os_error(exc) from None

    def read_bytes(self, path: str, limit: int = 1 << 20) -> bytes:
        fd = self.open(path, os.O_RDONLY)
        try:
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise Inv13Error(ErrorCode.IS_A_DIRECTORY)
            out = bytearray()
            while len(out) <= limit:
                chunk = os.read(fd, 65536)
                if not chunk:
                    return bytes(out)
                out += chunk
            raise Inv13Error(ErrorCode.QUOTA_EXCEEDED, "read limit")
        finally:
            os.close(fd)

    def write_bytes(self, path: str, data: bytes, *, exclusive: bool = False) -> int:
        flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
        fd = self.open(path, flags)
        try:
            return os.write(fd, data)
        finally:
            os.close(fd)

    def mkdir(self, path: str, mode: int = 0o700) -> None:
        if self.read_only:
            raise Inv13Error(ErrorCode.POLICY_DENIED, "read-only preopen")
        parts = split_guest_path(path)
        if not parts:
            raise Inv13Error(ErrorCode.ALREADY_EXISTS)
        try:
            dfd = self._walk_parent(parts)
            try:
                os.mkdir(parts[-1], mode, dir_fd=dfd)
            finally:
                os.close(dfd)
        except OSError as exc:
            raise from_os_error(exc) from None

    def listdir(self, path: str = "") -> list[str]:
        fd = self.open(path, os.O_RDONLY | _O_DIRECTORY)
        try:
            return sorted(os.listdir(fd))
        finally:
            os.close(fd)

    def stat(self, path: str) -> dict[str, Any]:
        parts = split_guest_path(path)
        try:
            dfd = self._walk_parent(parts) if parts else os.dup(self.fd)
            try:
                st = os.stat(parts[-1] if parts else ".", dir_fd=dfd, follow_symlinks=False)
            finally:
                os.close(dfd)
        except OSError as exc:
            raise from_os_error(exc) from None
        kind = "dir" if stat.S_ISDIR(st.st_mode) else "file" if stat.S_ISREG(st.st_mode) else \
            "symlink" if stat.S_ISLNK(st.st_mode) else "other"
        return {"type": kind, "size": st.st_size}  # no inode/owner/host path leaks

    def unlink(self, path: str) -> None:
        if self.read_only:
            raise Inv13Error(ErrorCode.POLICY_DENIED, "read-only preopen")
        parts = split_guest_path(path)
        if not parts:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT)
        try:
            dfd = self._walk_parent(parts)
            try:
                os.unlink(parts[-1], dir_fd=dfd)
            finally:
                os.close(dfd)
        except OSError as exc:
            raise from_os_error(exc) from None
