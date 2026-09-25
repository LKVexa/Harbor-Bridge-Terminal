"""At-rest encryption with managed key rotation (M19).

AES-256-GCM envelope (``cryptography`` package, optional extra ``[crypto]``).
Records carry the key id; a ``KeyRing`` holds one active key plus retired
decrypt-only keys, so rotation re-encrypts lazily.  Missing key or missing
library fails closed with PK_PROVIDER_KEY_UNAVAILABLE -- never a plaintext
fallback.  AAD binds ciphertext to its record key so blobs cannot be swapped.
"""
from __future__ import annotations

import base64
import os
import threading

from ..errors.mapping import ProviderFault

try:  # optional dependency
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:  # pragma: no cover - exercised when the extra is absent
    AESGCM = None


class KeyRing:
    def __init__(self):
        self._keys: dict[str, bytes] = {}
        self._active: str | None = None
        self._lock = threading.Lock()

    def add(self, kid: str, key: bytes, *, activate: bool = True) -> None:
        if len(key) != 32:
            raise ValueError("AES-256 key must be 32 bytes")
        with self._lock:
            self._keys[kid] = bytes(key)
            if activate:
                self._active = kid

    def retire(self, kid: str) -> None:
        with self._lock:
            self._keys.pop(kid, None)
            if self._active == kid:
                self._active = None

    def active(self) -> tuple[str, bytes]:
        with self._lock:
            if self._active is None:
                raise ProviderFault("PK_PROVIDER_KEY_UNAVAILABLE", "no active state key")
            return self._active, self._keys[self._active]

    def get(self, kid: str) -> bytes:
        with self._lock:
            if kid not in self._keys:
                raise ProviderFault("PK_PROVIDER_KEY_UNAVAILABLE", f"state key {kid!r} unavailable")
            return self._keys[kid]


def available() -> bool:
    return AESGCM is not None


def seal(ring: KeyRing, plaintext: bytes, aad: bytes) -> str:
    if AESGCM is None:
        raise ProviderFault("PK_PROVIDER_KEY_UNAVAILABLE", "AES-GCM library not installed")
    kid, key = ring.active()
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, aad)
    return f"v1.{kid}.{base64.b64encode(nonce + ct).decode()}"


def open_(ring: KeyRing, blob: str, aad: bytes) -> tuple[bytes, str]:
    if AESGCM is None:
        raise ProviderFault("PK_PROVIDER_KEY_UNAVAILABLE", "AES-GCM library not installed")
    try:
        ver, kid, b64 = blob.split(".", 2)
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        raise ProviderFault("PK_PROVIDER_STATE_CORRUPT", "malformed sealed blob") from None
    if ver != "v1" or len(raw) < 28:
        raise ProviderFault("PK_PROVIDER_STATE_CORRUPT", "malformed sealed blob")
    key = ring.get(kid)
    try:
        return AESGCM(key).decrypt(raw[:12], raw[12:], aad), kid
    except Exception:
        raise ProviderFault("PK_PROVIDER_STATE_CORRUPT", "sealed blob failed authentication") from None
