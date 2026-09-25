"""Local-operator safety primitives. These are NOT an OS sandbox.

Archive limits apply before decompression. Logical ZIP names are retained in a
map while bytes are staged under opaque names, so NTFS cannot silently merge
case-colliding cargo. Cooperating CLI/API writers use an OS-released file lock.
"""
from __future__ import annotations

import contextlib
import functools
import json
import math
import ntpath
import os
import re
import stat
import tempfile
import threading
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from . import Refusal

NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z", re.ASCII)
RESERVED = {"CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"} | {
    f"{prefix}{n}" for prefix in ("COM", "LPT") for n in "123456789¹²³"
}


def portable_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def windows_unsafe(value: str) -> bool:
    return any(not p or p[-1:] in (" ", ".") or p.split(".")[0].upper() in RESERVED
               or any(ord(c) < 32 or c in '<>:"\\|?*' for c in p)
               for p in value.split("/"))


def validate_name(name: str) -> str:
    if not isinstance(name, str) or not NAME_RE.fullmatch(name) or windows_unsafe(name):
        raise Refusal("invalid berth/container name: use 1-64 ASCII letters, digits, dot, dash or underscore; "
                      "start with a letter; no Windows device names or trailing dots", {"name": name})
    return name


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise Refusal("empty or overlong relative path", {"path": value})
    if ntpath.splitdrive(value)[0] or value.startswith(("/", "\\")) or "\\" in value:
        raise Refusal("absolute, drive-qualified or backslash path refused", {"path": value})
    if any(p in ("", ".", "..") for p in value.split("/")) or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise Refusal("non-canonical or control-character path refused", {"path": value})
    return value


def reject_link(path: str) -> None:
    if not os.path.lexists(path):
        return
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise Refusal("symlink or reparse point refused", {"path": path})


def contained_path(root: str, relative: str) -> str:
    relative_path(relative)
    root = os.path.abspath(root)
    reject_link(root)
    dest = os.path.abspath(os.path.join(root, *relative.split("/")))
    try:
        if os.path.commonpath((os.path.realpath(root), os.path.realpath(dest))) != os.path.realpath(root):
            raise Refusal("path escapes its permitted root", {"path": relative})
    except ValueError as exc:
        raise Refusal("path is on another drive", {"path": relative}) from exc
    cur = root
    for part in relative.split("/"):
        cur = os.path.join(cur, part)
        reject_link(cur)
    return dest


def atomic_write(path: str, data: bytes | str, mode: int | None = None) -> None:
    """Same-directory replace with data fsync; no claim of multi-file atomicity."""
    path = os.path.abspath(path)
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    reject_link(path)
    reject_link(parent)
    if isinstance(data, str):
        data = data.encode("utf-8")
    fd, tmp = tempfile.mkstemp(prefix=".uc-tmp-", dir=parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        elif os.path.isfile(path):
            os.chmod(tmp, stat.S_IMODE(os.stat(path).st_mode))
        os.replace(tmp, path)
        if os.name != "nt":
            dfd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_json(path: str, obj: Any) -> None:
    atomic_write(path, json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str, allow_nan=False) + "\n")


@dataclass(frozen=True)
class ArchiveLimits:
    entries: int = 50000
    member_bytes: int = 64 * 1024 * 1024
    total_bytes: int = 1024 * 1024 * 1024
    ratio: int = 1000


DEFAULT_LIMITS = ArchiveLimits()


def inspect_zip(z: zipfile.ZipFile, limits: ArchiveLimits = DEFAULT_LIMITS) -> list[zipfile.ZipInfo]:
    infos = z.infolist()
    if len(infos) > limits.entries:
        raise Refusal("archive has too many entries", {"limit": limits.entries})
    total = 0
    seen: set[str] = set()
    files: set[str] = set()
    dirs: set[str] = set()
    for info in infos:
        raw = info.orig_filename
        if raw != info.filename:
            raise Refusal("archive filename was truncated by ZIP parser", {"path": raw})
        name = raw[:-1] if info.is_dir() else raw
        relative_path(name)
        if name in seen:
            raise Refusal("duplicate ZIP member", {"path": name})
        seen.add(name)
        kind = stat.S_IFMT(info.external_attr >> 16)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or (kind == stat.S_IFDIR and not info.is_dir()):
            raise Refusal("archive link or special file refused", {"path": name})
        if info.flag_bits & 1:
            raise Refusal("encrypted ZIP members are unsupported", {"path": name})
        total += info.file_size
        if info.file_size > limits.member_bytes or total > limits.total_bytes:
            raise Refusal("archive exceeds expanded-size budget", {"path": name, "total_bytes": total})
        if info.file_size > 1024 * 1024 and info.file_size > max(1, info.compress_size) * limits.ratio:
            raise Refusal("archive compression ratio exceeds budget", {"path": name, "ratio_limit": limits.ratio})
        (dirs if info.is_dir() else files).add(name)
        dirs.update("/".join(name.split("/")[:i]) for i in range(1, len(name.split("/"))))
    if files & dirs:
        raise Refusal("ZIP file/directory name conflict", {"paths": sorted(files & dirs)[:10]})
    return infos


def stage_zip(z: zipfile.ZipFile, dest: str, limits: ArchiveLimits = DEFAULT_LIMITS) -> tuple[dict[str, str], str | None]:
    infos = inspect_zip(z, limits)
    members = [i for i in infos if not i.is_dir()]
    first = {i.filename.split("/")[0] for i in members}
    prefix = next(iter(first)) if len(first) == 1 and all("/" in i.filename for i in members) else None
    mapping: dict[str, str] = {}
    os.makedirs(dest, exist_ok=True)
    total = 0
    for index, info in enumerate(members):
        logical = info.filename[len(prefix) + 1:] if prefix else info.filename
        path = os.path.join(dest, f"{index:08x}.blob")
        count = 0
        with z.open(info) as src, open(path, "xb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                total += len(chunk)
                if count > limits.member_bytes or total > limits.total_bytes:
                    raise Refusal("expanded ZIP stream exceeds budget", {"path": logical})
                dst.write(chunk)
        if count != info.file_size:
            raise Refusal("ZIP expanded size mismatch", {"path": logical})
        mapping[logical] = path
    return mapping, prefix


_MUTEX = threading.RLock()
_LOCAL = threading.local()


@contextlib.contextmanager
def ship_lock(root: str) -> Iterator[None]:
    """Serialize cooperating operations. Lock survives as a file, never as a stale lock."""
    if not _MUTEX.acquire(blocking=False):
        raise Refusal("ship is busy in another thread")
    root = os.path.realpath(root)
    held = getattr(_LOCAL, "held", {})
    if root in held:
        try:
            yield
        finally:
            _MUTEX.release()
        return
    fh = None
    locked = False
    try:
        path = contained_path(root, "_runs/ship.lock")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags, 0o600)
        fh = os.fdopen(fd, "r+b", buffering=0)
        if os.fstat(fd).st_size == 0:
            fh.write(b"0")
        fh.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise Refusal("ship is busy in another process; retry after its operation finishes") from exc
        locked = True
        _LOCAL.held = {**held, root: True}
        yield
    finally:
        _LOCAL.held = held
        if fh is not None:
            if locked:
                fh.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            fh.close()
        _MUTEX.release()


def serialized(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        from . import engines as E
        with ship_lock(E.ship_root()):
            return fn(*args, **kwargs)
    return wrapped


def finite_number(value: float, low: float, high: float, label: str) -> float:
    if not math.isfinite(value) or not low <= value <= high:
        raise Refusal(f"{label} must be finite and between {low} and {high}", {label: value if math.isfinite(value) else str(value)})
    return value
