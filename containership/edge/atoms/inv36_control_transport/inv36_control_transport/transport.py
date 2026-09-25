"""Cryptographic control-frame transport for INV-36.

PK_CTRL_FRAME/2 deliberately uses a standard misuse-resistant AEAD instead of
home-grown encryption.  The transport is independent of ``pk_core`` so its
security-critical behavior can be tested even when the wider estate tooling is
not installed.

Session establishment is intentionally out of scope here: callers must provide
an authenticated shared secret and a fresh, jointly-known ``session_id``.  The
session ID is public context, not a secret.  Reusing it with the same shared
secret is forbidden by the contract even though AES-GCM-SIV is designed to be
more tolerant of nonce misuse than ordinary GCM.
"""
from __future__ import annotations

import hashlib
import secrets
import struct
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCMSIV
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .errors import ErrorCode, Inv36Error

MAGIC = b"PKCT"
FRAME_VERSION = 2
ALGORITHM_AES_256_GCM_SIV = 1
_HEADER = struct.Struct(">4sBBQ")
HEADER_SIZE = _HEADER.size
TAG_SIZE = 16
MAX_FRAME = 64 * 1024
MAX_WIRE_FRAME = HEADER_SIZE + MAX_FRAME + TAG_SIZE
MAX_SEQUENCE = (1 << 64) - 1
MIN_SHARED_SECRET = 16
MIN_SESSION_ID = 16
MAX_SESSION_ID = 64
DEFAULT_RELAY_HISTORY = 256
MAX_RELAY_HISTORY = 4096

# Cross-check hand-written constants against the IDL-generated module (MC-06.012).
from . import _wire  # noqa: E402

if (
    MAGIC != _wire.FRAME_MAGIC
    or FRAME_VERSION != _wire.FRAME_VERSION
    or ALGORITHM_AES_256_GCM_SIV != _wire.FRAME_ALGORITHMS["AES_256_GCM_SIV"]
    or MAX_FRAME != _wire.FRAME_MAX_PLAINTEXT
    or TAG_SIZE != _wire.FRAME_TAG_SIZE
    or MAX_WIRE_FRAME != _wire.STREAM_MAX_RECORD
):  # pragma: no cover - only reachable if the IDL and code diverge
    raise ImportError("PK_CTRL_FRAME/2 constants diverge from schema/pk_ctrl.idl.json")


class TransportError(Inv36Error, ValueError):
    """Base class for transport-level refusals (stable code in ``.code``)."""


class AuthFailure(TransportError):
    """Raised when a frame's AEAD tag does not verify."""

    code = ErrorCode.AUTH_FAILURE


class Replay(TransportError):
    """Raised when an authenticated frame has already been accepted."""

    code = ErrorCode.REPLAY


class OutOfOrder(TransportError):
    """Raised when an authenticated frame skips the next expected sequence."""

    code = ErrorCode.OUT_OF_ORDER


class FrameTooLarge(TransportError):
    """Raised when plaintext or wire-frame size exceeds the configured bound."""

    code = ErrorCode.FRAME_TOO_LARGE


class FrameFormatError(TransportError):
    """Raised for malformed, unsupported, or truncated wire frames."""

    code = ErrorCode.FRAME_FORMAT


class SequenceExhausted(TransportError):
    """Raised before the 64-bit sequence space would wrap and reuse a nonce."""

    code = ErrorCode.SEQUENCE_EXHAUSTED


class SessionClosed(TransportError):
    """Raised when a closed session is used."""

    code = ErrorCode.SESSION_CLOSED


@dataclass(frozen=True)
class _DirectionMaterial:
    key: bytes = field(repr=False)
    nonce_prefix: bytes = field(repr=False)
    aad_prefix: bytes = field(repr=False)


def _bytes(value: bytes | bytearray | memoryview, *, name: str) -> bytes:
    if not isinstance(value, (bytes, bytearray, memoryview)):
        raise TypeError(f"{name} must be bytes-like")
    return bytes(value)


def _identity(value: str, *, name: str) -> bytes:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    encoded = value.encode("utf-8")
    if not encoded:
        raise ValueError(f"{name} must not be empty")
    if len(encoded) > 0xFFFF:
        raise ValueError(f"{name} is too long")
    return len(encoded).to_bytes(2, "big") + encoded


def _direction_context(session_id: bytes, source: str, destination: str) -> bytes:
    return (
        b"PK_CTRL_DIRECTION/2\x00"
        + len(session_id).to_bytes(2, "big")
        + session_id
        + _identity(source, name="source")
        + _identity(destination, name="destination")
    )


def _derive_direction(shared: bytes, session_id: bytes, source: str, destination: str) -> _DirectionMaterial:
    context = _direction_context(session_id, source, destination)
    salt = hashlib.sha256(b"PK_CTRL_SESSION/2\x00" + session_id).digest()
    material = HKDF(
        algorithm=hashes.SHA256(),
        length=36,
        salt=salt,
        info=context,
    ).derive(shared)
    return _DirectionMaterial(
        key=material[:32],
        nonce_prefix=material[32:],
        aad_prefix=b"PK_CTRL_FRAME/2\x00" + context,
    )


def new_session_id() -> bytes:
    """Return a fresh public session identifier suitable for PK_CTRL_SESSION/2."""
    return secrets.token_bytes(MIN_SESSION_ID)


@dataclass
class Session:
    """One authenticated, ordered, bidirectional control session.

    ``shared`` must come from an authenticated session-establishment mechanism;
    this class does not perform peer attestation or key exchange.  ``session_id``
    must be fresh for every establishment using the same shared secret.
    """

    local: str
    peer: str
    shared: bytes = field(repr=False)
    session_id: bytes
    send_seq: int = field(default=0, init=False)
    recv_seq: int = field(default=0, init=False)
    frames_sealed: int = field(default=0, init=False)
    frames_opened: int = field(default=0, init=False)
    auth_failures: int = field(default=0, init=False)
    replays: int = field(default=0, init=False)
    out_of_order: int = field(default=0, init=False)
    malformed_frames: int = field(default=0, init=False)
    closed: bool = field(default=False, init=False)
    _send_material: _DirectionMaterial = field(init=False, repr=False)
    _recv_material: _DirectionMaterial = field(init=False, repr=False)
    _send_aead: AESGCMSIV | None = field(init=False, repr=False)
    _recv_aead: AESGCMSIV | None = field(init=False, repr=False)
    _send_lock: threading.Lock = field(init=False, repr=False)
    _recv_lock: threading.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        shared = _bytes(self.shared, name="shared")
        session_id = _bytes(self.session_id, name="session_id")
        if len(shared) < MIN_SHARED_SECRET:
            raise ValueError(f"shared must contain at least {MIN_SHARED_SECRET} bytes")
        if not MIN_SESSION_ID <= len(session_id) <= MAX_SESSION_ID:
            raise ValueError(f"session_id must be {MIN_SESSION_ID}..{MAX_SESSION_ID} bytes")
        if self.local == self.peer:
            raise ValueError("local and peer identities must differ")
        # Validate identities before deriving any key material.
        _identity(self.local, name="local")
        _identity(self.peer, name="peer")

        self.session_id = session_id
        self._send_material = _derive_direction(shared, session_id, self.local, self.peer)
        self._recv_material = _derive_direction(shared, session_id, self.peer, self.local)
        self._send_aead = AESGCMSIV(self._send_material.key)
        self._recv_aead = AESGCMSIV(self._recv_material.key)
        self._send_lock = threading.Lock()
        self._recv_lock = threading.Lock()

        # Avoid retaining the caller's long-lived/establishment secret in this object.
        # Derived AEAD keys still exist until close()/object destruction; Python cannot
        # guarantee physical zeroization of immutable bytes.
        self.shared = b""

    def _ensure_open(self) -> None:
        if self.closed or self._send_aead is None or self._recv_aead is None:
            raise SessionClosed("session is closed")

    @staticmethod
    def _nonce(material: _DirectionMaterial, seq: int) -> bytes:
        return material.nonce_prefix + seq.to_bytes(8, "big")

    def seal(self, plaintext: bytes | bytearray | memoryview) -> bytes:
        data = _bytes(plaintext, name="plaintext")
        if len(data) > MAX_FRAME:
            raise FrameTooLarge(f"{len(data)} bytes > {MAX_FRAME}")
        with self._send_lock:
            self._ensure_open()
            if self.send_seq >= MAX_SEQUENCE:
                raise SequenceExhausted("send sequence exhausted; establish a new session")
            seq = self.send_seq + 1
            header = _HEADER.pack(MAGIC, FRAME_VERSION, ALGORITHM_AES_256_GCM_SIV, seq)
            aead = self._send_aead
            if aead is None:
                raise SessionClosed("session is closed")
            body = aead.encrypt(
                self._nonce(self._send_material, seq),
                data,
                self._send_material.aad_prefix + header,
            )
            self.send_seq = seq
            self.frames_sealed += 1
            return header + body

    def open(self, frame: bytes | bytearray | memoryview) -> bytes:
        wire = _bytes(frame, name="frame")
        if len(wire) > MAX_WIRE_FRAME:
            raise FrameTooLarge(f"wire frame {len(wire)} bytes > {MAX_WIRE_FRAME}")

        with self._recv_lock:
            self._ensure_open()
            if len(wire) < HEADER_SIZE + TAG_SIZE:
                self.malformed_frames += 1
                raise FrameFormatError("frame shorter than header plus AEAD tag")

            magic, version, algorithm, seq = _HEADER.unpack_from(wire)
            if magic != MAGIC:
                self.malformed_frames += 1
                raise FrameFormatError("invalid frame magic")
            if version != FRAME_VERSION:
                self.malformed_frames += 1
                raise FrameFormatError(f"unsupported frame version {version}")
            if algorithm != ALGORITHM_AES_256_GCM_SIV:
                self.malformed_frames += 1
                raise FrameFormatError(f"unsupported algorithm {algorithm}")
            if seq == 0:
                self.malformed_frames += 1
                raise FrameFormatError("sequence zero is reserved")

            header = wire[:HEADER_SIZE]
            ciphertext = wire[HEADER_SIZE:]
            try:
                aead = self._recv_aead
                if aead is None:
                    raise SessionClosed("session is closed")
                plaintext = aead.decrypt(
                    self._nonce(self._recv_material, seq),
                    ciphertext,
                    self._recv_material.aad_prefix + header,
                )
            except InvalidTag as exc:
                self.auth_failures += 1
                raise AuthFailure("frame authentication failed") from exc

            expected = self.recv_seq + 1
            if seq <= self.recv_seq:
                self.replays += 1
                raise Replay(f"sequence {seq} has already been accepted")
            if seq != expected:
                self.out_of_order += 1
                raise OutOfOrder(f"sequence {seq} received; expected {expected}")

            self.recv_seq = seq
            self.frames_opened += 1
            return plaintext

    def close(self) -> None:
        """Drop references to derived key material and reject future operations."""
        # Keep lock ordering stable to avoid deadlock if close races with traffic.
        with self._send_lock:
            with self._recv_lock:
                self.closed = True
                self._send_aead = None
                self._recv_aead = None
                self._send_material = _DirectionMaterial(b"", b"", b"")
                self._recv_material = _DirectionMaterial(b"", b"", b"")

    def __enter__(self) -> "Session":
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


@dataclass
class Relay:
    """Opaque forwarder with bounded diagnostic history and no cryptographic key."""

    max_history: int = DEFAULT_RELAY_HISTORY
    seen: Deque[bytes] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.max_history, int):
            raise TypeError("max_history must be int")
        if not 0 <= self.max_history <= MAX_RELAY_HISTORY:
            raise ValueError(f"max_history must be 0..{MAX_RELAY_HISTORY}")
        self.seen = deque(maxlen=self.max_history)

    def forward(self, frame: bytes | bytearray | memoryview) -> bytes:
        wire = _bytes(frame, name="frame")
        if len(wire) > MAX_WIRE_FRAME:
            raise FrameTooLarge(f"wire frame {len(wire)} bytes > {MAX_WIRE_FRAME}")
        if self.max_history:
            self.seen.append(wire)
        return wire
