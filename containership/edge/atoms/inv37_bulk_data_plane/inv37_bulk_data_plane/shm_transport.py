"""Shared-memory zero-copy transport and capability probe (INV-37-C010, C011,
C031, C066).

Scope, stated precisely (see ADR-0001):

* Implemented: **intra-host, cross-process** zero-copy via POSIX/Windows shared
  memory (``multiprocessing.shared_memory``, CPython stdlib).  The producer
  writes (or generates) object bytes directly into a region; the receiver
  verifies chunk digests by hashing ``memoryview`` slices of the same pages and
  exposes the verified object as a read-only ``memoryview``.  After the
  producer's write the data plane performs **zero** payload copies.
* Not implemented: host<->guest (VM) shared memory (virtio/vhost-user,
  ivshmem), RDMA, io_uring registered buffers.  ``probe()`` reports
  ``host_guest: False`` and any configuration requiring it fails closed with
  ``unsupported_capability``.

Copy-count contract: a *data-plane copy* is any operation inside this package
that duplicates payload bytes into a new buffer (``bytes()``, ``tobytes()``,
``b"".join``, file read into a new object).  Hashing reads in place and is
not a copy.  The producer's write into the region is the single *unavoidable
ingress copy* unless the producer generates data in place.  ``CopyCounter``
records both classes so benchmarks can prove the property.

Descriptor binding (confused-deputy defence): a region descriptor carries an
HMAC over (name, size, transfer_id, tenant, generation) keyed by the data-plane
key.  ``attach`` refuses descriptors whose binding does not verify or whose
generation was revoked.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import secrets
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Mapping

from .data_plane import _expected_chunk_count, _expected_chunk_length, _require_bytes, validate_manifest, DEFAULT_LIMITS, TransferLimits
from .errors import CodedError, DigestMismatch, TransferIncomplete

TRANSPORT_ABI = "INV37_SHM_DESCRIPTOR/1"
PINNED = {
    "implementation": "cpython-stdlib multiprocessing.shared_memory",
    "abi": TRANSPORT_ABI,
    "min_python": "3.10",
    "posix": "shm_open(3)/mmap(2) via _posixshmem",
    "windows": "CreateFileMapping named section",
}

_revoked: set[str] = set()
_owned: set[str] = set()   # names created by this process (tracker-registered)
_rlock = threading.Lock()


def probe() -> dict[str, Any]:
    """Capability probe distinguishing zero-copy, copy-fallback and unsupported."""
    caps: dict[str, Any] = {"python": sys.version.split()[0], "platform": sys.platform,
                            "machine": platform.machine(), "shared_memory": False, "memfd": hasattr(os, "memfd_create"),
                            "mmap": True, "host_guest": False, "rdma": False, "io_uring": False}
    try:
        from multiprocessing import shared_memory

        s = shared_memory.SharedMemory(create=True, size=4096)
        try:
            s.buf[0] = 1
            caps["shared_memory"] = s.buf[0] == 1
        finally:
            s.close()
            s.unlink()
    except Exception as exc:  # noqa: BLE001 - any failure => capability absent
        caps["shared_memory_error"] = type(exc).__name__
    caps["mode"] = "zero_copy_intra_host" if caps["shared_memory"] else "copy_fallback"
    return caps


def select_transport(mode: str, require_zero_copy: bool, caps: Mapping[str, Any], *, host_guest_required: bool = False) -> str:
    if host_guest_required and not caps.get("host_guest"):
        raise CodedError("unsupported_capability", "host/guest shared memory is not available", capability="host_guest")
    if mode == "shm" or require_zero_copy:
        if not caps.get("shared_memory"):
            raise CodedError("unsupported_capability", "shared memory unavailable", capability="shared_memory")
        return "shm"
    if mode == "copy":
        return "copy"
    return "shm" if caps.get("shared_memory") else "copy"


@dataclass
class CopyCounter:
    data_plane_copies: int = 0
    data_plane_bytes: int = 0
    ingress_copies: int = 0
    ingress_bytes: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def copy(self, n: int) -> None:
        with self._lock:
            self.data_plane_copies += 1
            self.data_plane_bytes += n

    def ingress(self, n: int) -> None:
        with self._lock:
            self.ingress_copies += 1
            self.ingress_bytes += n

    def as_dict(self) -> dict[str, int]:
        return {"data_plane_copies": self.data_plane_copies, "data_plane_bytes": self.data_plane_bytes,
                "ingress_copies": self.ingress_copies, "ingress_bytes": self.ingress_bytes}


def _binding(key: bytes, name: str, size: int, tid: str, tenant: str, gen: str) -> str:
    msg = json.dumps([TRANSPORT_ABI, name, size, tid, tenant, gen], separators=(",", ":")).encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


class SharedRegion:
    """Owner side: creates, describes, and reclaims one region per transfer."""

    def __init__(self, size: int, *, transfer_id: str, tenant: str, key: bytes, max_mapped: int | None = None) -> None:
        from multiprocessing import shared_memory

        if size < 0:
            raise CodedError("invalid_manifest", "negative size")
        if max_mapped is not None and size > max_mapped:
            raise CodedError("quota_exceeded", "region exceeds max_mapped_bytes", limit=max_mapped)
        self._shm = shared_memory.SharedMemory(create=True, size=max(size, 1))
        _owned.add(self._shm._name)  # noqa: SLF001
        self.size = size
        self.transfer_id = transfer_id
        self.tenant = tenant
        self.generation = secrets.token_hex(8)
        self._key = key
        self.closed = False

    @property
    def buf(self) -> memoryview:
        return self._shm.buf[: self.size]

    def descriptor(self) -> dict[str, Any]:
        return {"abi": TRANSPORT_ABI, "name": self._shm.name, "size": self.size, "transfer_id": self.transfer_id,
                "tenant": self.tenant, "generation": self.generation,
                "binding": _binding(self._key, self._shm.name, self.size, self.transfer_id, self.tenant, self.generation)}

    def revoke(self) -> None:
        with _rlock:
            _revoked.add(self.generation)
        self.close()

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            try:
                self._shm.close()
            except BufferError:
                pass  # outstanding views; unlink still reclaims the name
            try:
                self._shm.unlink()
            except FileNotFoundError:
                pass
            _owned.discard(self._shm._name)  # noqa: SLF001


class AttachedRegion:
    def __init__(self, shm: Any, size: int) -> None:
        self._shm = shm
        self.size = size

    @property
    def buf(self) -> memoryview:
        return self._shm.buf[: self.size]

    def close(self) -> None:
        try:
            self._shm.close()
        except BufferError:
            pass


def attach(desc: Mapping[str, Any], *, key: bytes, transfer_id: str, tenant: str) -> AttachedRegion:
    from multiprocessing import shared_memory

    if desc.get("abi") != TRANSPORT_ABI:
        raise CodedError("version_incompatible", "unsupported descriptor ABI", abi=desc.get("abi"))
    if desc.get("transfer_id") != transfer_id or desc.get("tenant") != tenant:
        raise CodedError("authorization_denied", "descriptor not bound to this transfer/tenant")
    with _rlock:
        if desc.get("generation") in _revoked:
            raise CodedError("authorization_denied", "descriptor generation revoked")
    expect = _binding(key, str(desc.get("name")), int(desc.get("size", -1)), transfer_id, tenant, str(desc.get("generation")))
    if not hmac.compare_digest(expect, str(desc.get("binding", ""))):
        raise CodedError("authorization_denied", "descriptor binding invalid")
    try:
        shm = shared_memory.SharedMemory(name=desc["name"], create=False)
    except FileNotFoundError:
        raise CodedError("transfer_closed", "region no longer exists") from None
    _untrack(shm)
    if shm.size < desc["size"]:
        shm.close()
        raise CodedError("invalid_manifest", "region smaller than descriptor")
    return AttachedRegion(shm, int(desc["size"]))


def _untrack(seg: Any) -> None:
    """CPython < 3.13 registers *attached* segments with the attaching process's
    resource tracker, which unlinks the owner's region when the attacher exits
    (ownership violation).  Only the creator may reclaim a region, so attachers
    unregister.  Python 3.13+ exposes ``track=False`` for the same purpose."""
    if os.name != "posix" or seg._name in _owned:  # noqa: SLF001
        return
    try:
        from multiprocessing import resource_tracker

        resource_tracker.unregister(seg._name, "shared_memory")  # noqa: SLF001
    except Exception:  # noqa: BLE001
        pass


class ZeroCopyReceiver:
    """Verifies chunks in place inside a shared region.  No payload copies."""

    def __init__(self, manifest: Mapping[str, Any], region_buf: memoryview, *,
                 limits: TransferLimits = DEFAULT_LIMITS, counter: CopyCounter | None = None) -> None:
        self.m = validate_manifest(manifest, limits=limits)
        if len(region_buf) < self.m["size"]:
            raise CodedError("invalid_manifest", "region smaller than manifest size")
        self.buf = region_buf
        self.verified: set[int] = set()
        self.counter = counter or CopyCounter()
        self._lock = threading.Lock()
        self.failures = 0

    def _span(self, i: int) -> tuple[int, int]:
        c = self.m["chunk_count"]
        off = i * self.m["chunk"]
        return off, off + _expected_chunk_length(self.m["size"], self.m["chunk"], i, c)

    def commit(self, index: int) -> bool:
        """Producer signals chunk ``index`` is in the region; verify in place."""
        if type(index) is not int or not 0 <= index < self.m["chunk_count"]:
            self.failures += 1
            raise DigestMismatch("chunk index is not in the manifest", index=index)
        a, b = self._span(index)
        digest = hashlib.sha256(self.buf[a:b]).hexdigest()   # hashes in place
        if not hmac.compare_digest(digest, self.m["chunks"][index]):
            self.failures += 1
            raise DigestMismatch("chunk does not verify", index=index)
        with self._lock:
            dup = index in self.verified
            self.verified.add(index)
        return not dup

    def missing(self) -> list[int]:
        return [i for i in range(self.m["chunk_count"]) if i not in self.verified]

    def object_view(self) -> memoryview:
        miss = self.missing()
        if miss:
            raise TransferIncomplete("object is incomplete", missing=miss[:1000], missing_count=len(miss))
        # Final end-to-end re-verification over the ordered chunk list, in place.
        digests = []
        for i in range(self.m["chunk_count"]):
            a, b = self._span(i)
            digests.append(hashlib.sha256(self.buf[a:b]).hexdigest())
        if digests != self.m["chunks"] or hashlib.sha256("".join(digests).encode()).hexdigest() != self.m["object"]:
            raise CodedError("object_digest_mismatch", "final verification failed (region mutated after commit?)")
        return self.buf[: self.m["size"]].toreadonly()


def produce_into(region_buf: memoryview, source: Any, counter: CopyCounter) -> None:
    """Producer helper: the single ingress copy from a caller buffer."""
    v = _require_bytes(source)
    region_buf[: len(v)] = v
    counter.ingress(len(v))


def chunk_count(size: int, chunk: int) -> int:
    return _expected_chunk_count(size, chunk)
