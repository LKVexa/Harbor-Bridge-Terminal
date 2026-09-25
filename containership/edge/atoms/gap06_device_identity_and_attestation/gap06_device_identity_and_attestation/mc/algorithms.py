"""MC-31: algorithm agility.  Named digest/signature profiles, deprecation, policy hooks.

Signature verification is delegated to the ``cryptography`` package (OpenSSL);
no signature primitive is implemented here (checklist 01.12).  When that package
is missing, every verification fails closed with E_UNSUPPORTED_ALG.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .errors import fail

TPM_ALG = {0x0004: "sha1", 0x000B: "sha256", 0x000C: "sha384", 0x000D: "sha512"}
TPM_ALG_ID = {v: k for k, v in TPM_ALG.items()}
DIGEST_SIZE = {"sha1": 20, "sha256": 32, "sha384": 48, "sha512": 64}


@dataclass(frozen=True)
class AlgorithmPolicy:
    """Which digests/signature profiles are allowed.  SHA-1 is denied unless an
    explicit, expiring migration exception is supplied."""
    digests: frozenset = frozenset({"sha256", "sha384", "sha512"})
    signatures: frozenset = frozenset({"ecdsa-p256-sha256", "ecdsa-p384-sha384", "rsassa-pss-sha256",
                                       "rsassa-pkcs1v15-sha256", "ed25519"})
    min_rsa_bits: int = 2048
    sha1_migration_expires_at: float | None = None  # epoch seconds; None = SHA-1 forbidden
    fips_mode: bool = False

    def check_digest(self, name: str, now: float = 0.0) -> str:
        if name == "sha1":
            if self.sha1_migration_expires_at is not None and now < self.sha1_migration_expires_at:
                return name
            raise fail("E_UNSUPPORTED_ALG", "sha1 is deprecated and no migration exception is active")
        if name not in self.digests or name not in DIGEST_SIZE:
            raise fail("E_UNSUPPORTED_ALG", f"digest {name} not allowed")
        return name

    def check_signature(self, profile: str) -> str:
        if profile not in self.signatures:
            raise fail("E_UNSUPPORTED_ALG", f"signature profile {profile} not allowed")
        if self.fips_mode and profile == "ed25519":
            raise fail("E_UNSUPPORTED_ALG", "ed25519 disabled by FIPS policy hook")
        return profile


DEFAULT_POLICY = AlgorithmPolicy()


def digest(name: str, data: bytes) -> bytes:
    return hashlib.new(name, data).digest()


def _crypto():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
        from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    except ImportError as exc:  # fail closed
        raise fail("E_UNSUPPORTED_ALG", "cryptography package unavailable; cannot verify") from exc
    return InvalidSignature, hashes, serialization, ec, ed25519, padding, rsa, encode_dss_signature


def load_public_key(spki: bytes):
    _, _, serialization, *_ = _crypto()
    try:
        if spki.lstrip().startswith(b"-----BEGIN"):
            return serialization.load_pem_public_key(spki)
        return serialization.load_der_public_key(spki)
    except Exception as exc:
        raise fail("E_UNKNOWN_KEY", "public key could not be parsed") from exc


def profile_of(key) -> str:
    InvalidSignature, hashes, serialization, ec, ed25519, padding, rsa, _ = _crypto()
    if isinstance(key, ec.EllipticCurvePublicKey):
        return {"secp256r1": "ecdsa-p256-sha256", "secp384r1": "ecdsa-p384-sha384"}.get(key.curve.name, "ecdsa-unsupported")
    if isinstance(key, ed25519.Ed25519PublicKey):
        return "ed25519"
    if isinstance(key, rsa.RSAPublicKey):
        return "rsa"
    return "unknown"


def verify(key, profile: str, signature: bytes, message: bytes, policy: AlgorithmPolicy = DEFAULT_POLICY) -> None:
    """Verify or raise E_SIGNATURE / E_UNSUPPORTED_ALG.  Never returns False."""
    InvalidSignature, hashes, serialization, ec, ed25519, padding, rsa, encode_dss = _crypto()
    policy.check_signature(profile)
    try:
        if profile.startswith("ecdsa"):
            want = {"ecdsa-p256-sha256": ("secp256r1", hashes.SHA256()), "ecdsa-p384-sha384": ("secp384r1", hashes.SHA384())}[profile]
            if not isinstance(key, ec.EllipticCurvePublicKey) or key.curve.name != want[0]:
                raise fail("E_UNSUPPORTED_ALG", "key/curve does not match profile")
            key.verify(signature, message, ec.ECDSA(want[1]))
        elif profile == "ed25519":
            if not isinstance(key, ed25519.Ed25519PublicKey):
                raise fail("E_UNSUPPORTED_ALG", "key does not match profile")
            if len(signature) != 64:
                raise fail("E_SIGNATURE", "ed25519 signature must be 64 bytes")
            key.verify(signature, message)
        elif profile.startswith("rsassa"):
            if not isinstance(key, rsa.RSAPublicKey) or key.key_size < policy.min_rsa_bits:
                raise fail("E_UNSUPPORTED_ALG", "RSA key too small or wrong type")
            if len(signature) != key.key_size // 8:
                raise fail("E_SIGNATURE", "RSA signature length mismatch")
            pad = (padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.AUTO)
                   if profile == "rsassa-pss-sha256" else padding.PKCS1v15())
            key.verify(signature, message, pad, hashes.SHA256())
        else:
            raise fail("E_UNSUPPORTED_ALG", profile)
    except InvalidSignature as exc:
        raise fail("E_SIGNATURE", "signature verification failed") from exc


def ecdsa_raw_to_der(r: bytes, s: bytes) -> bytes:
    *_, encode_dss = _crypto()
    return encode_dss(int.from_bytes(r, "big"), int.from_bytes(s, "big"))
