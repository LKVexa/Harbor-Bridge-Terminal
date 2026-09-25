"""Pinned cryptographic profile (GAP04-C01-010, C01-019, C15).

Profile PK_CRYPTO/1:
  * Signatures: Ed25519 only (RFC 8032). No algorithm negotiation; the ``alg``
    field must equal ``"Ed25519"`` exactly. ``none``, RSA, ECDSA, HMAC and any
    other value are rejected (downgrade / substitution resistance).
  * At-rest encryption: AES-256-GCM with 96-bit random nonces, key id bound as
    associated data.
  * Integrity/MAC: HMAC-SHA-256 (audit chain), SHA-256 digests.

The only third-party dependency is ``cryptography`` (pinned in
``requirements.lock``). If it is not importable, every signed/encrypted path
fails closed with GAP04-E0208; the reference controller remains usable.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from .errors import Gap04Error

ALLOWED_SIG_ALGS = frozenset({"Ed25519"})
PROFILE = "PK_CRYPTO/1"

try:  # pragma: no cover - exercised by environment
    import cryptography
    from cryptography.exceptions import InvalidSignature, InvalidTag
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import serialization
    BACKEND_VERSION = cryptography.__version__
except Exception:  # pragma: no cover
    cryptography = None
    BACKEND_VERSION = None


def require_backend() -> None:
    if cryptography is None:
        raise Gap04Error("cryptography backend unavailable", code="GAP04-E0208")


def b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def b64d(s: str) -> bytes:
    if not isinstance(s, str) or not s or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in s):
        raise ValueError("invalid base64url")
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def generate_signing_key() -> tuple[bytes, str]:
    """Return (raw private seed, base64url public key). For issuers/tests only."""
    require_backend()
    sk = Ed25519PrivateKey.generate()
    raw = sk.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    pk = sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return raw, b64e(pk)


def sign(seed: bytes, message: bytes) -> str:
    require_backend()
    return b64e(Ed25519PrivateKey.from_private_bytes(seed).sign(message))


def verify(public_b64: str, message: bytes, signature_b64: str) -> bool:
    require_backend()
    try:
        pk = b64d(public_b64)
        sig = b64d(signature_b64)
    except Exception:
        return False
    if len(pk) != 32 or len(sig) != 64:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(pk).verify(sig, message)
        return True
    except (InvalidSignature, ValueError):
        return False


def fingerprint(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def hmac256(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def ct_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def aead_encrypt(key: bytes, plaintext: bytes, aad: bytes) -> bytes:
    require_backend()
    if len(key) != 32:
        raise ValueError("AES-256-GCM requires a 32-byte key")
    nonce = os.urandom(12)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def aead_decrypt(key: bytes, blob: bytes, aad: bytes) -> bytes:
    require_backend()
    try:
        return AESGCM(key).decrypt(blob[:12], blob[12:], aad)
    except (InvalidTag, ValueError):
        raise Gap04Error("decryption/authentication failed", code="GAP04-E0403") from None


def zeroize(buf: bytearray) -> None:
    """Best-effort zeroization of mutable key material (CPython cannot guarantee
    that immutable ``bytes`` copies are wiped; documented in THREAT_MODEL.md)."""
    for i in range(len(buf)):
        buf[i] = 0
