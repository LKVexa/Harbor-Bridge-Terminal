"""Hardened, dependency-free bulk data-plane primitives for INV-37.

The module intentionally contains no network transport.  It owns integrity,
resumption, manifest validation, bounded in-memory receiving, and concurrency
admission.  Transport, placement, storage, and key custody remain external.
"""
from __future__ import annotations

import hashlib
import hmac
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Iterator, Mapping

from .errors import (
    AdmissionRejected,
    DigestMismatch,
    InvalidManifest,
    TransferClosed,
    TransferIncomplete,
)

MANIFEST_SCHEMA = "PK_BULK_MANIFEST/1"
CHUNK_SCHEMA = "PK_BULK_CHUNK/1"
RESUME_SCHEMA = "PK_BULK_RESUME/1"
DIGEST_ALGORITHM = "sha256"
CHUNK = 4096
_HEX_DIGEST_LENGTH = hashlib.sha256().digest_size * 2


@dataclass(frozen=True)
class TransferLimits:
    """Fail-closed resource ceilings for untrusted manifests and payloads."""

    max_object_bytes: int = 1 << 30  # 1 GiB default receiver ceiling.
    max_chunk_bytes: int = 16 << 20  # 16 MiB.
    max_chunks: int = 262_144
    max_concurrent_transfers: int = 8

    def __post_init__(self) -> None:
        for name, value in (
            ("max_object_bytes", self.max_object_bytes),
            ("max_chunk_bytes", self.max_chunk_bytes),
            ("max_chunks", self.max_chunks),
            ("max_concurrent_transfers", self.max_concurrent_transfers),
        ):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


DEFAULT_LIMITS = TransferLimits()


class TransferState(str, Enum):
    RECEIVING = "receiving"
    COMPLETE = "complete"
    CLOSED = "closed"


def _require_bytes(data: Any, name: str = "data") -> memoryview:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"{name} must support the bytes buffer protocol")
    view = memoryview(data)
    if view.ndim != 1 or view.format not in ("B", "b", "c"):
        try:
            view = view.cast("B")
        except (TypeError, ValueError) as exc:
            raise TypeError(f"{name} must be a contiguous one-dimensional byte buffer") from exc
    if not view.contiguous:
        raise TypeError(f"{name} must be contiguous")
    return view.cast("B") if view.format != "B" else view


def _sha256_hex(data: Any) -> str:
    return hashlib.sha256(_require_bytes(data)).hexdigest()


def _object_digest(chunk_digests: Iterable[str]) -> str:
    # Compatibility with v4.1.0: the object digest is SHA-256 over concatenated
    # lowercase hex chunk digests, not over the raw object bytes.
    return hashlib.sha256("".join(chunk_digests).encode("ascii")).hexdigest()


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _HEX_DIGEST_LENGTH:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _expected_chunk_count(size: int, chunk: int) -> int:
    return 0 if size == 0 else (size + chunk - 1) // chunk


def _expected_chunk_length(size: int, chunk: int, index: int, count: int) -> int:
    if count == 0:
        return 0
    if index < count - 1:
        return chunk
    return size - chunk * (count - 1)


def manifest(data: Any, chunk: int = CHUNK, *, limits: TransferLimits = DEFAULT_LIMITS) -> dict[str, Any]:
    """Build a validated v1 manifest without materializing per-chunk copies."""
    view = _require_bytes(data)
    if type(chunk) is not int or chunk <= 0:
        raise ValueError(f"chunk size must be a positive integer, got {chunk!r}")
    if chunk > limits.max_chunk_bytes:
        raise ValueError(f"chunk size {chunk} exceeds limit {limits.max_chunk_bytes}")
    if len(view) > limits.max_object_bytes:
        raise ValueError(f"object size {len(view)} exceeds limit {limits.max_object_bytes}")
    count = _expected_chunk_count(len(view), chunk)
    if count > limits.max_chunks:
        raise ValueError(f"chunk count {count} exceeds limit {limits.max_chunks}")
    chunks = [hashlib.sha256(view[i : i + chunk]).hexdigest() for i in range(0, len(view), chunk)]
    result = {
        "schema": MANIFEST_SCHEMA,
        "algorithm": DIGEST_ALGORITHM,
        "chunk": chunk,
        "size": len(view),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "object": _object_digest(chunks),
    }
    validate_manifest(result, limits=limits)
    return result


def validate_manifest(candidate: Mapping[str, Any], *, limits: TransferLimits = DEFAULT_LIMITS) -> dict[str, Any]:
    """Validate and normalize an untrusted manifest before state is allocated."""
    if not isinstance(candidate, Mapping):
        raise InvalidManifest("manifest must be a mapping")

    schema = candidate.get("schema")
    if schema != MANIFEST_SCHEMA:
        raise InvalidManifest("unsupported manifest schema", schema=schema, supported=MANIFEST_SCHEMA)

    algorithm = candidate.get("algorithm", DIGEST_ALGORITHM)
    if algorithm != DIGEST_ALGORITHM:
        raise InvalidManifest("unsupported digest algorithm", algorithm=algorithm)

    chunk = candidate.get("chunk")
    size = candidate.get("size")
    chunks = candidate.get("chunks")
    object_digest = candidate.get("object")

    if type(chunk) is not int or chunk <= 0:
        raise InvalidManifest("chunk must be a positive integer", chunk=chunk)
    if chunk > limits.max_chunk_bytes:
        raise InvalidManifest("chunk exceeds configured limit", chunk=chunk, limit=limits.max_chunk_bytes)
    if type(size) is not int or size < 0:
        raise InvalidManifest("size must be a non-negative integer", size=size)
    if size > limits.max_object_bytes:
        raise InvalidManifest("object exceeds configured limit", size=size, limit=limits.max_object_bytes)
    if not isinstance(chunks, (list, tuple)):
        raise InvalidManifest("chunks must be an array")
    if len(chunks) > limits.max_chunks:
        raise InvalidManifest("chunk count exceeds configured limit", count=len(chunks), limit=limits.max_chunks)

    expected = _expected_chunk_count(size, chunk)
    if len(chunks) != expected:
        raise InvalidManifest("chunk count does not match size/chunk geometry", expected=expected, actual=len(chunks))

    advertised_count = candidate.get("chunk_count", len(chunks))
    if type(advertised_count) is not int or advertised_count != len(chunks):
        raise InvalidManifest("chunk_count does not match chunks", advertised=advertised_count, actual=len(chunks))

    normalized_chunks: list[str] = []
    for index, digest in enumerate(chunks):
        if not _is_sha256_hex(digest):
            raise InvalidManifest("invalid chunk digest", index=index)
        normalized_chunks.append(digest)

    if not _is_sha256_hex(object_digest):
        raise InvalidManifest("invalid object digest")
    expected_object = _object_digest(normalized_chunks)
    if not hmac.compare_digest(expected_object, object_digest):
        raise InvalidManifest("manifest object digest does not authenticate the chunk list")

    return {
        "schema": MANIFEST_SCHEMA,
        "algorithm": DIGEST_ALGORITHM,
        "chunk": chunk,
        "size": size,
        "chunk_count": len(normalized_chunks),
        "chunks": normalized_chunks,
        "object": object_digest,
    }


def verify_object(candidate_manifest: Mapping[str, Any], data: Any, *, limits: TransferLimits = DEFAULT_LIMITS) -> str:
    """Perform receiver-side end-to-end verification against a validated manifest."""
    normalized = validate_manifest(candidate_manifest, limits=limits)
    view = _require_bytes(data)
    if len(view) != normalized["size"]:
        raise DigestMismatch(
            "object size does not match manifest",
            expected=normalized["size"],
            actual=len(view),
        )
    recomputed = manifest(view, normalized["chunk"], limits=limits)
    if not hmac.compare_digest(recomputed["object"], normalized["object"]):
        raise DigestMismatch("object digest does not match manifest")
    # Compare the full list too.  This makes the integrity check explicit and
    # avoids relying only on a second-level digest comparison.
    if len(recomputed["chunks"]) != len(normalized["chunks"]) or any(
        not hmac.compare_digest(a, b) for a, b in zip(recomputed["chunks"], normalized["chunks"])
    ):
        raise DigestMismatch("one or more chunk digests do not match manifest")
    return normalized["object"]


@dataclass
class Receiver:
    """Bounded, resumable, in-memory receiver for one manifest.

    The manifest is validated and copied during initialization so an untrusted
    caller cannot mutate it after validation (a prior time-of-check/time-of-use
    weakness).  `accept` is thread-safe and duplicate delivery is idempotent.
    """

    m: Mapping[str, Any]
    limits: TransferLimits = DEFAULT_LIMITS
    received: dict[int, bytes] = field(default_factory=dict, init=False)
    failures: int = field(default=0, init=False)
    duplicate_chunks: int = field(default=0, init=False)
    bytes_received: int = field(default=0, init=False)
    _state: TransferState = field(default=TransferState.RECEIVING, init=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        self.m = validate_manifest(self.m, limits=self.limits)

    @property
    def state(self) -> TransferState:
        with self._lock:
            return self._state

    def accept(self, index: int, payload: Any) -> None:
        view = _require_bytes(payload, "payload")
        with self._lock:
            if self._state is TransferState.CLOSED:
                raise TransferClosed("receiver is closed")
            count = self.m["chunk_count"]
            if type(index) is not int or not 0 <= index < count:
                self.failures += 1
                raise DigestMismatch("chunk index is not in the manifest", index=index, chunk_count=count)

            expected_len = _expected_chunk_length(self.m["size"], self.m["chunk"], index, count)
            if len(view) != expected_len:
                self.failures += 1
                raise DigestMismatch(
                    "chunk length does not match manifest geometry",
                    index=index,
                    expected=expected_len,
                    actual=len(view),
                )
            actual_digest = hashlib.sha256(view).hexdigest()
            expected_digest = self.m["chunks"][index]
            if not hmac.compare_digest(actual_digest, expected_digest):
                self.failures += 1
                raise DigestMismatch("chunk does not verify", index=index)

            prior = self.received.get(index)
            if prior is not None:
                # The digest is already equal. Compare bytes to make the duplicate
                # semantics explicit even in the theoretical collision case.
                if not hmac.compare_digest(prior, view.tobytes()):
                    self.failures += 1
                    raise DigestMismatch("conflicting duplicate chunk", index=index)
                self.duplicate_chunks += 1
                return

            payload_bytes = view.tobytes()
            if self.bytes_received + len(payload_bytes) > self.limits.max_object_bytes:
                self.failures += 1
                raise DigestMismatch("receiver buffer limit exceeded", limit=self.limits.max_object_bytes)
            self.received[index] = payload_bytes
            self.bytes_received += len(payload_bytes)
            if len(self.received) == count:
                self._state = TransferState.COMPLETE

    def missing(self) -> list[int]:
        with self._lock:
            return [i for i in range(self.m["chunk_count"]) if i not in self.received]

    def last_contiguous_verified(self) -> int:
        """Return the highest contiguous verified index, or -1 if none."""
        with self._lock:
            index = -1
            while index + 1 in self.received:
                index += 1
            return index

    def resume_token(self) -> dict[str, Any]:
        with self._lock:
            return {
                "schema": RESUME_SCHEMA,
                "manifest_object": self.m["object"],
                "last_verified": self.last_contiguous_verified(),
                "verified": sorted(self.received),
            }

    def assemble(self) -> bytes:
        with self._lock:
            missing = [i for i in range(self.m["chunk_count"]) if i not in self.received]
            if missing:
                raise TransferIncomplete("object is incomplete", missing=missing, missing_count=len(missing))
            data = b"".join(self.received[i] for i in range(self.m["chunk_count"]))
            verify_object(self.m, data, limits=self.limits)
            self._state = TransferState.COMPLETE
            return data

    def close(self, *, clear: bool = False) -> None:
        with self._lock:
            self._state = TransferState.CLOSED
            if clear:
                self.received.clear()
                self.bytes_received = 0


class BoundedTransferPool:
    """Process-local admission control for concurrent bulk transfers."""

    def __init__(self, max_active: int = DEFAULT_LIMITS.max_concurrent_transfers) -> None:
        if type(max_active) is not int or max_active <= 0:
            raise ValueError("max_active must be a positive integer")
        self.max_active = max_active
        self._semaphore = threading.BoundedSemaphore(max_active)
        self._lock = threading.Lock()
        self._active = 0
        self._accepted = 0
        self._rejected = 0
        self._high_water = 0

    @contextmanager
    def slot(self, *, timeout: float | None = 0.0) -> Iterator[None]:
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative or None")
        acquired = self._semaphore.acquire(timeout=timeout) if timeout is not None else self._semaphore.acquire()
        if not acquired:
            with self._lock:
                self._rejected += 1
            raise AdmissionRejected("concurrent transfer limit reached", limit=self.max_active)
        with self._lock:
            self._active += 1
            self._accepted += 1
            self._high_water = max(self._high_water, self._active)
        try:
            yield
        finally:
            with self._lock:
                self._active -= 1
            self._semaphore.release()

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return {
                "transfers_active": self._active,
                "transfers_accepted": self._accepted,
                "transfers_rejected": self._rejected,
                "transfers_high_water": self._high_water,
                "transfers_limit": self.max_active,
            }
