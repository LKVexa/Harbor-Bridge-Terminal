"""MC03 / MC15 / MC34 / MC35 / MC36 / MC37 / MC38 / MC30 / MC52 — durable local store.

A crash-safe, filesystem-backed content-addressable store and metadata database:

* ``blobs/sha256/<hex>``          immutable content, written via temp file + fsync + rename
* ``ingest/<ref>.part`` + ``.json`` resumable partial uploads with running hash state checks
* ``meta.json``                   tags, leases, quarantine, schema version; replaced atomically
* ``LOCK``                        advisory ``fcntl`` lock (single-host); leases carry expiry

Every read re-hashes content; corruption is detected, reported by :meth:`fsck`, and
moved aside by :meth:`repair`.  The store is stdlib-only and POSIX-oriented.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import secrets
import shutil
import tarfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from .registry import IntegrityError, LimitExceeded, QuarantinedDigest, UnknownReference, ValidationError
from .timeutil import Clock, SystemClock

SCHEMA_VERSION = 2
_HEX_RE = re.compile(r"[0-9a-f]{64}\Z")
_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_TAGKEY_RE = re.compile(r"[^\s@]{1,1024}:[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}\Z")

try:  # POSIX advisory locking; Windows falls back to an in-process lock only.
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore


class ConflictError(IntegrityError):
    """Compare-and-swap precondition failed (MC34)."""
    code = "STORE_CONFLICT"


class LockTimeout(TimeoutError):
    code = "STORE_LOCK_TIMEOUT"


class SchemaError(IntegrityError):
    code = "STORE_SCHEMA_UNSUPPORTED"


def _hex(d: str) -> str:
    if not isinstance(d, str) or not d.startswith("sha256:") or not _HEX_RE.fullmatch(d[7:]):
        raise ValidationError(f"invalid digest: {d!r}")
    return d[7:]


def _fsync_dir(path: Path) -> None:
    with contextlib.suppress(OSError):
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


@dataclass(frozen=True)
class StoreLimits:
    max_blob_bytes: int = 8 * 1024**3
    max_total_bytes: int = 256 * 1024**3
    max_ingests: int = 256
    lock_timeout_s: float = 10.0


@dataclass(frozen=True)
class Lease:
    lease_id: str
    digests: tuple[str, ...]
    expires_at: float
    holder: str


class ContentStore:
    """Durable CAS + metadata database.  Safe across threads and (on POSIX) processes."""

    def __init__(self, root: str | os.PathLike, *, limits: StoreLimits | None = None,
                 clock: Clock | None = None, audit: "Callable[[str, dict], None] | None" = None) -> None:
        self.root = Path(root)
        self.limits = limits or StoreLimits()
        self.clock = clock or SystemClock()
        self._audit = audit or (lambda event, fields: None)
        self._tlock = threading.RLock()
        for sub in ("blobs/sha256", "ingest", "corrupt"):
            (self.root / sub).mkdir(parents=True, exist_ok=True, mode=0o700)
        self._lockfile = self.root / "LOCK"
        self._lockfile.touch(mode=0o600, exist_ok=True)
        with self._locked():
            meta = self._read_meta_unlocked()
            if meta is None:
                self._write_meta_unlocked(self._empty_meta())

    # -- locking (MC35) -------------------------------------------------------------
    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        with self._tlock:
            if fcntl is None:
                yield
                return
            fd = os.open(self._lockfile, os.O_RDWR)
            try:
                deadline = time.monotonic() + self.limits.lock_timeout_s
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            raise LockTimeout("store lock not acquired within timeout")
                        time.sleep(0.005)
                try:
                    yield
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    # -- metadata (MC15) ------------------------------------------------------------
    @staticmethod
    def _empty_meta() -> dict:
        return {"schema": SCHEMA_VERSION, "generation": 0, "tags": {}, "leases": {}, "quarantine": {}}

    def _read_meta_unlocked(self) -> dict | None:
        p = self.root / "meta.json"
        if not p.exists():
            return None
        try:
            meta = json.loads(p.read_bytes())
        except (OSError, ValueError) as exc:
            raise IntegrityError("metadata database is unreadable; restore from backup") from exc
        from .migrations import migrate_store_meta

        meta = migrate_store_meta(meta, SCHEMA_VERSION)
        return meta

    def _write_meta_unlocked(self, meta: dict) -> None:
        meta["generation"] = int(meta.get("generation", 0)) + 1
        atomic_write(self.root / "meta.json", json.dumps(meta, sort_keys=True, indent=1).encode())

    @contextlib.contextmanager
    def _txn(self) -> Iterator[dict]:
        with self._locked():
            meta = self._read_meta_unlocked() or self._empty_meta()
            yield meta
            self._write_meta_unlocked(meta)

    def snapshot_meta(self) -> dict:
        with self._locked():
            return json.loads(json.dumps(self._read_meta_unlocked()))

    # -- blobs (MC03) ---------------------------------------------------------------
    def _blob_path(self, d: str) -> Path:
        return self.root / "blobs" / "sha256" / _hex(d)

    def has(self, d: str) -> bool:
        return self._blob_path(d).is_file()

    def put(self, data: bytes, *, expected: str | None = None) -> str:
        data = bytes(data)
        if len(data) > self.limits.max_blob_bytes:
            raise LimitExceeded("blob exceeds max_blob_bytes")
        d = "sha256:" + hashlib.sha256(data).hexdigest()
        if expected is not None and expected != d:
            raise IntegrityError(f"content digest {d} != expected {expected}")
        with self._locked():
            p = self._blob_path(d)
            if p.is_file() and self._hash_file(p) == d:
                return d
            if self.total_bytes() + len(data) > self.limits.max_total_bytes:
                raise LimitExceeded("store capacity exceeded")
            atomic_write(p, data, 0o444)
        self._audit("blob.put", {"digest": d, "size": len(data)})
        return d

    @staticmethod
    def _hash_file(p: Path) -> str:
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return "sha256:" + h.hexdigest()

    def get(self, d: str, *, allow_quarantined: bool = False) -> bytes:
        p = self._blob_path(d)
        if not allow_quarantined and self.is_quarantined(d):
            raise QuarantinedDigest(f"{d}: quarantined")
        try:
            data = p.read_bytes()
        except FileNotFoundError:
            raise UnknownReference(f"{d}: not in store") from None
        if "sha256:" + hashlib.sha256(data).hexdigest() != d:
            self._audit("blob.corrupt", {"digest": d})
            raise IntegrityError(f"{d}: stored content is corrupt")
        return data

    def total_bytes(self) -> int:
        base = self.root / "blobs" / "sha256"
        return sum(p.stat().st_size for p in base.iterdir() if p.is_file())

    def digests(self) -> list[str]:
        base = self.root / "blobs" / "sha256"
        return sorted("sha256:" + p.name for p in base.iterdir() if p.is_file() and _HEX_RE.fullmatch(p.name))

    # -- resumable ingest (MC36) ----------------------------------------------------
    def ingest_open(self, ref: str, expected: str, expected_size: int) -> int:
        """Open or resume an ingest; returns the committed offset to resume from."""
        if not _REF_RE.fullmatch(ref):
            raise ValidationError("invalid ingest ref")
        _hex(expected)
        if not isinstance(expected_size, int) or expected_size < 0 or expected_size > self.limits.max_blob_bytes:
            raise LimitExceeded("expected_size outside limits")
        part = self.root / "ingest" / f"{ref}.part"
        info = self.root / "ingest" / f"{ref}.json"
        with self._locked():
            if info.exists():
                st = json.loads(info.read_text())
                if st["expected"] != expected or st["size"] != expected_size:
                    raise ConflictError("ingest ref reused for different content")
                return part.stat().st_size if part.exists() else 0
            if len(list((self.root / "ingest").glob("*.json"))) >= self.limits.max_ingests:
                raise LimitExceeded("too many concurrent ingests")
            atomic_write(info, json.dumps({"expected": expected, "size": expected_size,
                                           "started": self.clock.now()}).encode())
            part.touch(mode=0o600)
            return 0

    def ingest_write(self, ref: str, offset: int, chunk: bytes) -> int:
        part = self.root / "ingest" / f"{ref}.part"
        info = self.root / "ingest" / f"{ref}.json"
        with self._locked():
            if not info.exists():
                raise UnknownReference("no such ingest")
            st = json.loads(info.read_text())
            cur = part.stat().st_size
            if offset != cur:
                raise ConflictError(f"offset {offset} != committed {cur}")
            if cur + len(chunk) > st["size"]:
                raise IntegrityError("ingest exceeds declared size")
            with open(part, "ab") as fh:
                fh.write(chunk)
                fh.flush()
                os.fsync(fh.fileno())
            return cur + len(chunk)

    def ingest_commit(self, ref: str) -> str:
        part = self.root / "ingest" / f"{ref}.part"
        info = self.root / "ingest" / f"{ref}.json"
        with self._locked():
            st = json.loads(info.read_text())
            if part.stat().st_size != st["size"]:
                raise IntegrityError("ingest incomplete")
            got = self._hash_file(part)
            if got != st["expected"]:
                part.unlink()
                info.unlink()
                raise IntegrityError(f"ingest digest mismatch: {got} != {st['expected']}")
            dest = self._blob_path(got)
            os.chmod(part, 0o444)
            os.replace(part, dest)
            _fsync_dir(dest.parent)
            info.unlink()
        self._audit("blob.ingest", {"digest": got, "size": st["size"]})
        return got

    def ingest_abort(self, ref: str) -> None:
        with self._locked():
            for suffix in (".part", ".json"):
                with contextlib.suppress(FileNotFoundError):
                    (self.root / "ingest" / f"{ref}{suffix}").unlink()

    # -- tags with compare-and-swap (MC34) -----------------------------------------
    def get_tag(self, key: str) -> str | None:
        return self.snapshot_meta()["tags"].get(key, {}).get("digest")

    def set_tag(self, key: str, new_digest: str, *, expected: str | None | object = ...,
                actor: str = "system") -> int:
        """Atomically move ``key`` to ``new_digest``.  When ``expected`` is given, the
        update applies only if the current value equals it (``None`` = must not exist)."""
        if not _TAGKEY_RE.fullmatch(key):
            raise ValidationError(f"invalid tag key {key!r}")
        _hex(new_digest)
        if not self.has(new_digest):
            raise UnknownReference(f"{new_digest}: tag target not in store")
        with self._txn() as meta:
            cur = meta["tags"].get(key)
            cur_d = cur["digest"] if cur else None
            if expected is not ... and expected != cur_d:
                raise ConflictError(f"{key}: expected {expected}, found {cur_d}")
            version = (cur["version"] + 1) if cur else 1
            meta["tags"][key] = {"digest": new_digest, "version": version, "previous": cur_d,
                                 "actor": actor, "at": self.clock.now()}
        self._audit("tag.set", {"tag": key, "digest": new_digest, "previous": cur_d, "actor": actor})
        return version

    def delete_tag(self, key: str, *, expected: str | None = None) -> None:
        with self._txn() as meta:
            cur = meta["tags"].get(key)
            if cur is None:
                raise UnknownReference(key)
            if expected is not None and cur["digest"] != expected:
                raise ConflictError(f"{key}: expected {expected}")
            del meta["tags"][key]
        self._audit("tag.delete", {"tag": key})

    # -- durable quarantine (MC30) -------------------------------------------------
    def quarantine(self, d: str, reason: str, *, actor: str, expires_at: float | None = None) -> None:
        _hex(d)
        if not reason.strip() or len(reason) > 1024:
            raise ValidationError("quarantine reason required (<=1024 chars)")
        with self._txn() as meta:
            meta["quarantine"][d] = {"reason": reason.strip(), "actor": actor,
                                     "at": self.clock.now(), "expires_at": expires_at}
        self._audit("quarantine.add", {"digest": d, "reason": reason, "actor": actor})

    def release(self, d: str, *, actor: str, approver: str) -> None:
        if actor == approver:
            raise ValidationError("quarantine release requires a second approver")
        with self._txn() as meta:
            if meta["quarantine"].pop(d, None) is None:
                raise UnknownReference(f"{d} not quarantined")
        self._audit("quarantine.release", {"digest": d, "actor": actor, "approver": approver})

    def is_quarantined(self, d: str) -> bool:
        q = self.snapshot_meta()["quarantine"].get(d)
        if q is None:
            return False
        # Quarantine never silently lapses; an expiry only flags it for review.
        return True

    # -- leases & GC (MC37) --------------------------------------------------------
    def lease(self, digests: list[str], ttl_s: float, holder: str) -> Lease:
        if ttl_s <= 0 or ttl_s > 7 * 86400:
            raise ValidationError("lease ttl must be in (0, 7d]")
        for d in digests:
            _hex(d)
        lid = secrets.token_hex(12)
        exp = self.clock.now() + ttl_s
        with self._txn() as meta:
            meta["leases"][lid] = {"digests": list(digests), "expires_at": exp, "holder": holder}
        return Lease(lid, tuple(digests), exp, holder)

    def release_lease(self, lease_id: str) -> None:
        with self._txn() as meta:
            meta["leases"].pop(lease_id, None)

    def roots(self, meta: dict, extra_refs: Callable[[bytes], list[str]] | None) -> set[str]:
        now = self.clock.now()
        live: set[str] = {t["digest"] for t in meta["tags"].values()}
        live |= set(meta["quarantine"])  # keep evidence
        for lease in meta["leases"].values():
            if lease["expires_at"] > now:
                live |= set(lease["digests"])
        # Mark: follow references from manifests/indexes.
        stack, seen = list(live), set()
        while stack:
            d = stack.pop()
            if d in seen:
                continue
            seen.add(d)
            if extra_refs and self.has(d):
                with contextlib.suppress(Exception):
                    stack.extend(extra_refs(self.get(d, allow_quarantined=True)))
        return seen

    def gc(self, *, dry_run: bool = False, grace_s: float = 3600.0,
           refs: Callable[[bytes], list[str]] | None = None) -> dict:
        """Mark-and-sweep.  Blobs younger than ``grace_s`` are never swept, which
        protects content between ingest and tag/lease creation."""
        refs = refs or default_refs
        with self._locked():
            meta = self._read_meta_unlocked()
            now = self.clock.now()
            for lid in [k for k, v in meta["leases"].items() if v["expires_at"] <= now]:
                del meta["leases"][lid]
            live = self.roots(meta, refs)
            swept, kept = [], 0
            for d in self.digests():
                p = self._blob_path(d)
                if d in live or (time.time() - p.stat().st_mtime) < grace_s:
                    kept += 1
                    continue
                swept.append(d)
                if not dry_run:
                    p.unlink()
            if not dry_run:
                self._write_meta_unlocked(meta)
        self._audit("gc.run", {"swept": len(swept), "kept": kept, "dry_run": dry_run})
        return {"swept": swept, "kept": kept, "dry_run": dry_run}

    # -- verification & repair (MC38) ---------------------------------------------
    def fsck(self) -> dict:
        corrupt, dangling, stale_ingest = [], [], []
        for d in self.digests():
            if self._hash_file(self._blob_path(d)) != d:
                corrupt.append(d)
        meta = self.snapshot_meta()
        for key, t in meta["tags"].items():
            if not self.has(t["digest"]):
                dangling.append(key)
        for info in (self.root / "ingest").glob("*.json"):
            st = json.loads(info.read_text())
            if self.clock.now() - st.get("started", 0) > 86400:
                stale_ingest.append(info.stem)
        return {"corrupt": corrupt, "dangling_tags": dangling, "stale_ingests": stale_ingest,
                "ok": not (corrupt or dangling)}

    def repair(self, fetch: Callable[[str], bytes] | None = None) -> dict:
        """Move corrupt blobs to ``corrupt/`` (evidence preserved), quarantine them, and
        optionally re-fetch verified replacements from a trusted source."""
        report = self.fsck()
        repaired, moved = [], []
        for d in report["corrupt"]:
            src = self._blob_path(d)
            dest = self.root / "corrupt" / f"{_hex(d)}.{int(self.clock.now())}"
            os.replace(src, dest)
            moved.append(d)
            if fetch is not None:
                try:
                    self.put(fetch(d), expected=d)
                    repaired.append(d)
                    continue
                except Exception:  # replacement unavailable: fail closed
                    pass
            self.quarantine(d, "fsck: content corrupt, no verified replacement", actor="repair")
        for ref in report["stale_ingests"]:
            self.ingest_abort(ref)
        self._audit("store.repair", {"moved": moved, "repaired": repaired})
        return {"moved": moved, "repaired": repaired, "stale_ingests_aborted": report["stale_ingests"]}

    # -- backup / restore (MC52) --------------------------------------------------
    def backup(self, dest: str | os.PathLike) -> str:
        """Write a consistent tar backup (taken under the store lock) and return its digest."""
        dest = Path(dest)
        with self._locked():
            with tarfile.open(dest, "w") as tar:
                tar.add(self.root / "meta.json", arcname="meta.json")
                for d in self.digests():
                    tar.add(self._blob_path(d), arcname=f"blobs/sha256/{_hex(d)}")
        return self._hash_file(dest)

    @classmethod
    def restore(cls, backup: str | os.PathLike, root: str | os.PathLike, *,
                expected_digest: str | None = None, **kw) -> "ContentStore":
        backup, root = Path(backup), Path(root)
        if expected_digest and cls._hash_file(backup) != expected_digest:
            raise IntegrityError("backup archive digest mismatch")
        if root.exists() and any(root.iterdir()):
            raise ValidationError("restore target must be empty")
        root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(backup, "r") as tar:
            for m in tar.getmembers():
                ok = m.isfile() and (m.name == "meta.json" or re.fullmatch(r"blobs/sha256/[0-9a-f]{64}", m.name))
                if not ok:
                    raise IntegrityError(f"unexpected member in backup: {m.name!r}")
                (root / m.name).parent.mkdir(parents=True, exist_ok=True)
                fh = tar.extractfile(m)
                assert fh is not None
                (root / m.name).write_bytes(fh.read())
        store = cls(root, **kw)
        bad = store.fsck()
        if not bad["ok"]:
            raise IntegrityError(f"restored store failed fsck: {bad}")
        return store


def default_refs(doc: bytes) -> list[str]:
    """Extract child digests from an OCI manifest/index (used by GC marking)."""
    try:
        obj = json.loads(doc)
    except Exception:
        return []
    out: list[str] = []
    if isinstance(obj, dict):
        for key in ("config", "subject"):
            v = obj.get(key)
            if isinstance(v, dict) and isinstance(v.get("digest"), str):
                out.append(v["digest"])
        for key in ("layers", "manifests"):
            for v in obj.get(key, []) or []:
                if isinstance(v, dict) and isinstance(v.get("digest"), str):
                    out.append(v["digest"])
                elif isinstance(v, str):
                    out.append(v)
    return [d for d in out if isinstance(d, str) and d.startswith("sha256:")]
