"""#21 / #57 end-to-end payload integrity: chunked digests, manifests, verification, quarantine."""
from __future__ import annotations

import hashlib
import threading
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .data_plane import _StructuredError

DEFAULT_CHUNK = 1024 * 1024
MAX_CHUNKS = 1 << 20


class IntegrityMismatch(_StructuredError, RuntimeError):
    code = "PK_PAYLOAD_INTEGRITY_MISMATCH"


@dataclass(frozen=True)
class Manifest:
    """Chunk manifest bound to a transfer ID.  ``root`` covers the whole payload."""

    transfer_id: str
    size: int
    chunk_size: int
    chunks: tuple[str, ...]
    root: str

    def as_dict(self) -> dict[str, object]:
        return {"schema": "PK_PAYLOAD_MANIFEST/1", "transfer_id": self.transfer_id, "size": self.size,
                "chunk_size": self.chunk_size, "chunks": list(self.chunks), "root": self.root}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def chunks(data: bytes, chunk_size: int = DEFAULT_CHUNK) -> Iterator[bytes]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def build_manifest(transfer_id: str, data: bytes, chunk_size: int = DEFAULT_CHUNK) -> Manifest:
    parts = tuple(sha256_hex(c) for c in chunks(data, chunk_size)) or (sha256_hex(b""),)
    if len(parts) > MAX_CHUNKS:
        raise IntegrityMismatch("payload exceeds maximum chunk count", chunks=len(parts))
    root = sha256_hex(transfer_id.encode() + b"\x00" + "".join(parts).encode())
    return Manifest(transfer_id, len(data), chunk_size, parts, root)


def reassemble(manifest: Manifest, received: Iterable[tuple[int, bytes]]) -> bytes:
    """Reassemble possibly out-of-order chunks, verifying each one and the whole."""
    slots: dict[int, bytes] = {}
    for index, blob in received:
        if not 0 <= index < len(manifest.chunks):
            raise IntegrityMismatch("chunk index out of range", index=index)
        if index in slots:
            raise IntegrityMismatch("duplicate chunk", index=index)
        if sha256_hex(blob) != manifest.chunks[index]:
            raise IntegrityMismatch("chunk digest mismatch", index=index)
        slots[index] = blob
    if manifest.size and len(slots) != len(manifest.chunks):
        raise IntegrityMismatch("missing chunks", missing=sorted(set(range(len(manifest.chunks))) - set(slots)))
    data = b"".join(slots[i] for i in range(len(slots)))
    verify(manifest, data)
    return data


def verify(manifest: Manifest, data: bytes) -> None:
    if len(data) != manifest.size:
        raise IntegrityMismatch("size mismatch", expected=manifest.size, actual=len(data))
    actual = build_manifest(manifest.transfer_id, data, manifest.chunk_size)
    if actual.root != manifest.root:
        raise IntegrityMismatch("payload root digest mismatch", transfer_id=manifest.transfer_id)


class QuarantineStore:
    """Bounded holding area for payloads that failed verification (metadata only by default)."""

    def __init__(self, limit: int = 1024, keep_bytes: bool = False):
        self._limit = limit
        self._keep = keep_bytes
        self._items: dict[str, dict[str, object]] = {}
        self._lock = threading.Lock()

    def put(self, transfer_id: str, reason: str, data: bytes | None = None) -> None:
        with self._lock:
            if len(self._items) >= self._limit and transfer_id not in self._items:
                self._items.pop(next(iter(self._items)))
            self._items[transfer_id] = {"reason": reason, "size": None if data is None else len(data),
                                        "digest": None if data is None else sha256_hex(data),
                                        "bytes": data if self._keep else None}

    def __contains__(self, transfer_id: object) -> bool:
        return transfer_id in self._items

    def list(self) -> dict[str, dict[str, object]]:
        with self._lock:
            return {k: {kk: vv for kk, vv in v.items() if kk != "bytes"} for k, v in self._items.items()}
