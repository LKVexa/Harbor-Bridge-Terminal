"""MC13 / MC04 / MC09 — layer unpack pipeline, snapshotter and rootfs policy.

``apply_layer`` streams an OCI layer (tar, tar+gzip; zstd is detected and refused
with a stable error because the stdlib has no decoder) into a directory, enforcing:

* no absolute paths, ``..`` components, or writes through symlinks (every parent is
  resolved with ``O_NOFOLLOW``-equivalent checks relative to the root);
* hardlinks must target an already-extracted path inside the root;
* device/FIFO nodes are refused unless explicitly allowed; setuid/setgid bits are
  stripped unless allowed;
* entry-count and uncompressed-byte ceilings (decompression-bomb defence);
* OCI whiteouts (``.wh.<name>``) and opaque directories (``.wh..wh..opq``);
* the uncompressed stream digest must equal the config ``diff_id``.

``Snapshotter`` materialises layer chains as directories keyed by OCI ``ChainID`` with a
prepare → commit lifecycle; it is a copy-based snapshotter (no privileges required).
"""
from __future__ import annotations

import gzip
import hashlib
import io
import os
import shutil
import stat
import tarfile
import threading
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .registry import IntegrityError, LimitExceeded, ValidationError

WHITEOUT_PREFIX = ".wh."
OPAQUE = ".wh..wh..opq"


class UnsafeLayer(IntegrityError):
    code = "LAYER_UNSAFE"


class UnsupportedCompression(IntegrityError):
    code = "LAYER_UNSUPPORTED_COMPRESSION"


@dataclass(frozen=True)
class UnpackPolicy:
    max_entries: int = 500_000
    max_uncompressed_bytes: int = 32 * 1024**3
    max_path_len: int = 4096
    allow_devices: bool = False
    allow_setuid: bool = False
    preserve_owner: bool = False  # requires privilege; rootless unpack maps to caller


class _HashingReader(io.RawIOBase):
    def __init__(self, inner, limit: int) -> None:
        self.inner, self.limit = inner, limit
        self.h = hashlib.sha256()
        self.n = 0

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:
        data = self.inner.read(len(b))
        self.n += len(data)
        if self.n > self.limit:
            raise LimitExceeded("layer exceeds uncompressed byte limit")
        self.h.update(data)
        b[: len(data)] = data
        return len(data)


def _open_decompressed(blob: bytes):
    if blob[:4] == b"\x28\xb5\x2f\xfd":
        raise UnsupportedCompression("zstd layers require an external decompressor")
    if blob[:2] == b"\x1f\x8b":
        return gzip.GzipFile(fileobj=io.BytesIO(blob))
    return io.BytesIO(blob)


def _clean(name: str, max_len: int) -> PurePosixPath:
    if len(name) > max_len or "\x00" in name:
        raise UnsafeLayer(f"path too long or contains NUL: {name[:80]!r}")
    if name.startswith("/"):
        raise UnsafeLayer(f"absolute path in layer: {name!r}")
    while name.startswith("./"):
        name = name[2:]
    p = PurePosixPath(name)
    if p.is_absolute():
        raise UnsafeLayer(f"absolute path in layer: {name!r}")
    if any(part == ".." for part in p.parts):
        raise UnsafeLayer(f"parent traversal in layer: {name!r}")
    return p


def _safe_parent(root: Path, rel: PurePosixPath) -> Path:
    """Create/validate every parent directory without following symlinks."""
    cur = root
    for part in rel.parts[:-1]:
        cur = cur / part
        if cur.is_symlink():
            raise UnsafeLayer(f"layer writes through symlink at {cur.relative_to(root)}")
        if cur.exists() and not cur.is_dir():
            cur.unlink()
        cur.mkdir(exist_ok=True, mode=0o755)
    return cur / rel.parts[-1]


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def apply_layer(root: str | os.PathLike, blob: bytes, *, diff_id: str | None = None,
                policy: UnpackPolicy | None = None) -> dict:
    policy = policy or UnpackPolicy()
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    reader = _HashingReader(_open_decompressed(blob), policy.max_uncompressed_bytes)
    stats = {"files": 0, "dirs": 0, "links": 0, "whiteouts": 0, "bytes": 0}
    opaque_dirs_this_layer: set[Path] = set()
    try:
        with tarfile.open(fileobj=io.BufferedReader(reader, 1 << 16), mode="r|") as tar:
            for count, m in enumerate(tar, 1):
                if count > policy.max_entries:
                    raise LimitExceeded("layer exceeds entry-count limit")
                rel = _clean(m.name, policy.max_path_len)
                if not rel.parts:
                    continue
                base = rel.name
                if base == OPAQUE:
                    d = root.joinpath(*rel.parts[:-1])
                    if d.is_symlink():
                        raise UnsafeLayer("opaque whiteout on symlink")
                    if d.is_dir():
                        for child in d.iterdir():
                            _remove(child)
                    opaque_dirs_this_layer.add(d)
                    stats["whiteouts"] += 1
                    continue
                if base.startswith(WHITEOUT_PREFIX):
                    target = _safe_parent(root, rel.with_name(base[len(WHITEOUT_PREFIX):]))
                    if target.exists() or target.is_symlink():
                        _remove(target)
                    stats["whiteouts"] += 1
                    continue
                dest = _safe_parent(root, rel)
                mode = m.mode & 0o7777
                if not policy.allow_setuid:
                    mode &= ~(stat.S_ISUID | stat.S_ISGID)
                if dest.is_symlink() or (dest.exists() and not (m.isdir() and dest.is_dir())):
                    _remove(dest)
                if m.isdir():
                    dest.mkdir(exist_ok=True)
                    os.chmod(dest, mode | 0o700)
                    stats["dirs"] += 1
                elif m.isreg():
                    fh = tar.extractfile(m)
                    assert fh is not None
                    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
                    with os.fdopen(fd, "wb") as out:
                        shutil.copyfileobj(fh, out, 1 << 16)
                    os.chmod(dest, mode)
                    stats["files"] += 1
                    stats["bytes"] += m.size
                elif m.issym():
                    # Symlink targets may point anywhere *as data*; containment is enforced
                    # on later writes (_safe_parent) and at runtime by the mount namespace.
                    os.symlink(m.linkname, dest)
                    stats["links"] += 1
                elif m.islnk():
                    src = root / _clean(m.linkname, policy.max_path_len)
                    if src.is_symlink() or not src.is_file() or root not in src.resolve().parents:
                        raise UnsafeLayer(f"hardlink target outside root or missing: {m.linkname!r}")
                    os.link(src, dest)
                    stats["links"] += 1
                elif m.ischr() or m.isblk() or m.isfifo():
                    if not policy.allow_devices:
                        raise UnsafeLayer(f"device/fifo node refused: {m.name!r}")
                    os.mknod(dest, mode | (stat.S_IFCHR if m.ischr() else stat.S_IFBLK if m.isblk() else stat.S_IFIFO),
                             os.makedev(m.devmajor, m.devminor))
                else:
                    raise UnsafeLayer(f"unsupported tar entry type for {m.name!r}")
            # drain trailing padding so the digest covers the full stream
            while reader.read(1 << 16):
                pass
    except tarfile.TarError as exc:
        raise UnsafeLayer(f"malformed layer tar: {exc}") from exc
    except (EOFError, OSError, gzip.BadGzipFile) as exc:
        if isinstance(exc, (UnsafeLayer, LimitExceeded)):
            raise
        raise UnsafeLayer(f"layer stream error: {exc}") from exc
    got = "sha256:" + reader.h.hexdigest()
    if diff_id is not None and got != diff_id:
        raise IntegrityError(f"layer diff_id mismatch: {got} != {diff_id}")
    stats["diff_id"] = got
    return stats


def chain_ids(diff_ids: list[str]) -> list[str]:
    out: list[str] = []
    for d in diff_ids:
        out.append(d if not out else "sha256:" + hashlib.sha256(f"{out[-1]} {d}".encode()).hexdigest())
    return out


class Snapshotter:
    """Copy-based snapshotter: ``committed/<chainid-hex>`` are read-only layer chains;
    ``active/<key>`` are writable container rootfs prepared from a parent chain."""

    def __init__(self, root: str | os.PathLike) -> None:
        self.root = Path(root)
        (self.root / "committed").mkdir(parents=True, exist_ok=True)
        (self.root / "active").mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _committed(self, chain_id: str) -> Path:
        return self.root / "committed" / chain_id.split(":", 1)[1]

    def has(self, chain_id: str) -> bool:
        return self._committed(chain_id).is_dir()

    def unpack_image(self, layers: list[bytes], diff_ids: list[str], policy: UnpackPolicy | None = None) -> str:
        if len(layers) != len(diff_ids):
            raise ValidationError("layers and diff_ids length differ")
        cids = chain_ids(diff_ids)
        for i, (blob, did, cid) in enumerate(zip(layers, diff_ids, cids)):
            if self.has(cid):
                continue
            with self._lock:
                work = self.root / "active" / f".unpack-{cid[7:19]}-{os.getpid()}"
                if work.exists():
                    shutil.rmtree(work)
                if i:
                    shutil.copytree(self._committed(cids[i - 1]), work, symlinks=True)
                else:
                    work.mkdir()
                try:
                    apply_layer(work, blob, diff_id=did, policy=policy)
                except BaseException:
                    shutil.rmtree(work, ignore_errors=True)
                    raise
                os.replace(work, self._committed(cid))
        return cids[-1]

    def prepare(self, key: str, parent_chain_id: str) -> Path:
        if not key.replace("-", "").replace("_", "").isalnum():
            raise ValidationError("invalid snapshot key")
        with self._lock:
            dest = self.root / "active" / key
            if dest.exists():
                raise ValidationError(f"snapshot {key} already active")
            shutil.copytree(self._committed(parent_chain_id), dest, symlinks=True)
            return dest

    def remove(self, key: str) -> None:
        with self._lock:
            shutil.rmtree(self.root / "active" / key, ignore_errors=True)

    def usage(self) -> dict:
        def size(p: Path) -> int:
            return sum(f.lstat().st_size for f in p.rglob("*") if not f.is_dir())
        return {"committed": len(list((self.root / "committed").iterdir())),
                "active": len([p for p in (self.root / "active").iterdir() if not p.name.startswith(".")]),
                "bytes": size(self.root)}


# --- MC09 rootfs / mount policy ---------------------------------------------------------
DEFAULT_MOUNTS = [
    {"destination": "/proc", "type": "proc", "source": "proc", "options": ["nosuid", "noexec", "nodev"]},
    {"destination": "/dev", "type": "tmpfs", "source": "tmpfs", "options": ["nosuid", "strictatime", "mode=755", "size=65536k"]},
    {"destination": "/dev/pts", "type": "devpts", "source": "devpts", "options": ["nosuid", "noexec", "newinstance", "ptmxmode=0666", "mode=0620"]},
    {"destination": "/dev/shm", "type": "tmpfs", "source": "shm", "options": ["nosuid", "noexec", "nodev", "mode=1777", "size=65536k"]},
    {"destination": "/dev/mqueue", "type": "mqueue", "source": "mqueue", "options": ["nosuid", "noexec", "nodev"]},
    {"destination": "/sys", "type": "sysfs", "source": "sysfs", "options": ["nosuid", "noexec", "nodev", "ro"]},
]
FORBIDDEN_HOST_SOURCES = ("/", "/proc", "/sys", "/dev", "/etc", "/boot", "/var/run/docker.sock", "/run/containerd",
                          "/var/lib/kubelet", "/root")


def validate_bind_mount(source: str, destination: str, options: list[str], allowed_prefixes: tuple[str, ...]) -> list[str]:
    """Return normalised options for a host bind mount or raise.  Binds are read-only,
    nosuid, nodev by default; sources must sit under an allow-listed prefix."""
    src = os.path.realpath(source)
    if not os.path.isabs(destination) or ".." in PurePosixPath(destination).parts:
        raise ValidationError("bind destination must be absolute without '..'")
    for f in FORBIDDEN_HOST_SOURCES:
        if src == f or (f != "/" and src.startswith(f.rstrip("/") + "/")):
            raise ValidationError(f"bind source {src} is forbidden")
    if not any(src == p or src.startswith(p.rstrip("/") + "/") for p in allowed_prefixes):
        raise ValidationError(f"bind source {src} not under an allowed prefix")
    opts = set(options) | {"rbind", "nosuid", "nodev"}
    if "rw" not in opts:
        opts.add("ro")
    opts.add("rprivate")
    return sorted(opts)
