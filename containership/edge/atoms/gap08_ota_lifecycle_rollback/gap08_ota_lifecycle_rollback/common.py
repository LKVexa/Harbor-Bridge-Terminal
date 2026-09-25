"""Shared primitives: canonical JSON, digests, HMAC signing, injectable clocks, IDs.

Only the Python standard library is used.  HMAC-SHA256 stands in for the
production signature scheme at trust boundaries; the ``Signer``/``Verifier``
protocol lets a deployment substitute asymmetric signatures (e.g. Ed25519 via
an HSM/KMS) without touching call sites.  Key material never leaves the
``KeyRing`` and is never serialised (see ``secrets_boundary``).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from typing import Any, Mapping, Protocol


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_of(value: Any) -> str:
    return sha256_hex(canonical_json(value))


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class Clock(Protocol):
    def now(self) -> float: ...        # wall-clock seconds (UTC epoch)
    def monotonic(self) -> float: ...  # for deadlines/leases


class SystemClock:
    def now(self) -> float:
        return time.time()

    def monotonic(self) -> float:
        return time.monotonic()


class FakeClock:
    """Deterministic clock for tests, soak and fault-injection harnesses."""

    def __init__(self, start: float = 1_790_000_000.0) -> None:
        self._t = start
        self._lock = threading.Lock()

    def now(self) -> float:
        with self._lock:
            return self._t

    def monotonic(self) -> float:
        return self.now()

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("clock cannot go backwards")
        with self._lock:
            self._t += seconds


class Signer(Protocol):
    key_id: str
    def sign(self, payload: bytes) -> str: ...


class KeyRing:
    """Holds verification keys by key id, supports rotation and revocation.

    Keys are held in memory only; ``__repr__`` and ``describe`` never reveal
    material.  ``sign``/``verify`` use HMAC-SHA256 with constant-time compare.
    """

    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}
        self._revoked: set[str] = set()
        self._lock = threading.Lock()

    def add(self, key_id: str, material: bytes | None = None) -> str:
        if not key_id:
            raise ValueError("key_id required")
        with self._lock:
            self._keys[key_id] = material if material is not None else os.urandom(32)
        return key_id

    def revoke(self, key_id: str) -> None:
        with self._lock:
            self._revoked.add(key_id)

    def is_active(self, key_id: str) -> bool:
        return key_id in self._keys and key_id not in self._revoked

    def sign(self, key_id: str, payload: bytes) -> str:
        with self._lock:
            if key_id in self._revoked or key_id not in self._keys:
                raise PermissionError(f"key {key_id} is not active")
            key = self._keys[key_id]
        return hmac.new(key, payload, hashlib.sha256).hexdigest()

    def verify(self, key_id: str, payload: bytes, signature: str) -> bool:
        with self._lock:
            key = self._keys.get(key_id)
            if key is None or key_id in self._revoked:
                return False
        if not isinstance(signature, str):
            return False
        expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def describe(self) -> dict[str, Any]:
        return {"keys": sorted(self._keys), "revoked": sorted(self._revoked)}

    def __repr__(self) -> str:  # never leak material
        return f"KeyRing(keys={len(self._keys)}, revoked={len(self._revoked)})"


def sign_envelope(keyring: KeyRing, key_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
    payload = canonical_json(dict(body))
    return {"body": dict(body), "key_id": key_id, "signature": keyring.sign(key_id, payload)}


def verify_envelope(keyring: KeyRing, envelope: Mapping[str, Any]) -> dict[str, Any] | None:
    if not isinstance(envelope, Mapping):
        return None
    body, key_id, sig = envelope.get("body"), envelope.get("key_id"), envelope.get("signature")
    if not isinstance(body, Mapping) or not isinstance(key_id, str):
        return None
    try:
        payload = canonical_json(dict(body))
    except (TypeError, ValueError):
        return None
    return dict(body) if keyring.verify(key_id, payload, sig) else None
