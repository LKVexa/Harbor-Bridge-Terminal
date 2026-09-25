"""Encryption at rest with key rotation for INV-27 state exports (MC-046; C047).

Scope: journal/audit/decision exports written by this component.  INV-27 has no network listener of
its own, so *in-transit* protection belongs to the host API layer (recorded as a boundary in
ops/BOUNDARIES.md, not claimed here).

Format ``PKUK-SEALED/1``: ``b"PKUK1" | key_version(u32) | nonce(12) | AES-256-GCM(ciphertext+tag)``
with the key version and a caller context string as associated data.  ``KeyRing`` holds versioned
32-byte keys resolved from the secret store; ``rotate`` adds a new active version; old versions stay
decrypt-only until ``retire``; ``rewrap`` re-encrypts under the active key.

AES-GCM requires the optional ``cryptography`` package.  Without it ``seal`` raises
``UK_DEPENDENCY_UNAVAILABLE`` - the component never silently writes plaintext.
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass, field

from .errors import UkError

MAGIC = b"PKUK1"


def _aead():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise UkError("UK_DEPENDENCY_UNAVAILABLE", "cryptography (AES-GCM) not installed; refusing plaintext") from None
    return AESGCM


@dataclass
class KeyRing:
    keys: dict = field(default_factory=dict)       # version -> 32-byte key
    active: int = 0
    retired: set = field(default_factory=set)

    def rotate(self, key: bytes) -> int:
        if not isinstance(key, bytes) or len(key) != 32:
            raise UkError("UK_CONFIG_INVALID", "keys must be 32 bytes")
        v = max(self.keys, default=0) + 1
        self.keys[v] = key
        self.active = v
        return v

    def retire(self, version: int) -> None:
        if version == self.active:
            raise UkError("UK_CONFIG_INVALID", "cannot retire the active key")
        self.retired.add(version)


def seal(ring: KeyRing, plaintext: bytes, context: str) -> bytes:
    if ring.active not in ring.keys:
        raise UkError("UK_CONFIG_INVALID", "no active key")
    nonce = os.urandom(12)
    aad = struct.pack(">I", ring.active) + context.encode()
    ct = _aead()(ring.keys[ring.active]).encrypt(nonce, plaintext, aad)
    return MAGIC + struct.pack(">I", ring.active) + nonce + ct


def open_sealed(ring: KeyRing, blob: bytes, context: str) -> bytes:
    if len(blob) < 5 + 4 + 12 + 16 or blob[:5] != MAGIC:
        raise UkError("UK_STATE_CORRUPT", "not a PKUK-SEALED/1 blob")
    (ver,) = struct.unpack(">I", blob[5:9])
    if ver not in ring.keys or ver in ring.retired:
        raise UkError("UK_STATE_CORRUPT", f"key version {ver} unavailable or retired")
    try:
        return _aead()(ring.keys[ver]).decrypt(blob[9:21], blob[21:], blob[5:9] + context.encode())
    except UkError:
        raise
    except Exception:
        raise UkError("UK_STATE_CORRUPT", "authentication failed (tampered, wrong key or wrong context)") from None


def rewrap(ring: KeyRing, blob: bytes, context: str) -> bytes:
    return seal(ring, open_sealed(ring, blob, context), context)
