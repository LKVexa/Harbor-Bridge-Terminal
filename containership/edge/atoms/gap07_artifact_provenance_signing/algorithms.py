"""Approved signature-algorithm registry and algorithm-agility policy (v6).

The verifier never infers an algorithm from key shape or signature length: the
envelope names ``alg`` explicitly, the registry validates it, the pinned public
key must be of the exact matching type/size, and the per-key/per-policy
``allowed`` set must contain it.  All primitives come from ``cryptography``
(OpenSSL/BoringSSL-backed, constant-time where applicable); GAP-07 implements
no curve or RSA arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa

from .errors import fail

PROFILE_PRODUCTION = "production"
PROFILE_REFERENCE = "reference"

MAX_SIGNATURE_BYTES = 1024  # RSA-4096 = 512 bytes; generous but bounded
MAX_PUBLIC_KEY_BYTES = 4096


@dataclass(frozen=True)
class Algorithm:
    alg_id: str
    family: str
    strength: int  # comparable security level in bits
    fips: bool
    production: bool
    deprecated_after: int | None  # unix seconds; None = not scheduled
    forbidden: bool = False
    deterministic: bool = False
    sig_len: tuple[int, int] = (0, MAX_SIGNATURE_BYTES)


REGISTRY: dict[str, Algorithm] = {
    "ed25519": Algorithm("ed25519", "eddsa", 128, True, True, None, deterministic=True, sig_len=(64, 64)),
    "ecdsa-p256-sha256": Algorithm("ecdsa-p256-sha256", "ecdsa", 128, True, True, None, sig_len=(8, 72)),
    "ecdsa-p384-sha384": Algorithm("ecdsa-p384-sha384", "ecdsa", 192, True, True, None, sig_len=(8, 104)),
    "rsa-pss-sha256-3072": Algorithm("rsa-pss-sha256-3072", "rsa-pss", 128, True, True, None, sig_len=(384, 384)),
    "rsa-pss-sha384-4096": Algorithm("rsa-pss-sha384-4096", "rsa-pss", 152, True, True, None, sig_len=(512, 512)),
    # historical / reference only - never production-admissible
    "rsa-pss-sha256-2048": Algorithm("rsa-pss-sha256-2048", "rsa-pss", 112, True, False, 1_893_456_000, sig_len=(256, 256)),
    "HMAC-SHA256-REF-v2": Algorithm("HMAC-SHA256-REF-v2", "hmac-reference", 128, False, False, None, deterministic=True, sig_len=(32, 32)),
    "rsa-pkcs1v15-sha1": Algorithm("rsa-pkcs1v15-sha1", "rsa", 0, False, False, 0, forbidden=True),
}


def get(alg_id: Any, *, profile: str = PROFILE_PRODUCTION, now: int | None = None) -> Algorithm:
    if not isinstance(alg_id, str) or alg_id not in REGISTRY:
        raise fail("ALG_UNSUPPORTED", "unknown signature algorithm", alg=str(alg_id)[:64])
    alg = REGISTRY[alg_id]
    if alg.forbidden:
        raise fail("ALG_UNSUPPORTED", "algorithm is forbidden", alg=alg_id)
    if profile == PROFILE_PRODUCTION and not alg.production:
        raise fail("ALG_REFERENCE_ONLY", "algorithm is not admissible under the production profile", alg=alg_id)
    if now is not None and alg.deprecated_after is not None and now >= alg.deprecated_after:
        raise fail("ALG_DEPRECATED", "algorithm is past its deprecation date", alg=alg_id, deprecated_after=alg.deprecated_after)
    return alg


def check_not_downgrade(alg_id: str, allowed: frozenset[str] | set[str], min_strength: int = 128) -> None:
    alg = REGISTRY.get(alg_id)
    if alg is None:
        raise fail("ALG_UNSUPPORTED", "unknown signature algorithm", alg=alg_id)
    if alg_id not in allowed:
        raise fail("ALG_DOWNGRADE", "algorithm not permitted for this key/identity/policy", alg=alg_id, allowed=sorted(allowed))
    if alg.strength < min_strength:
        raise fail("ALG_DOWNGRADE", "algorithm below minimum strength", alg=alg_id, strength=alg.strength, min_strength=min_strength)


# ---------------------------------------------------------------- public keys

def load_public_key(alg_id: str, spki_der: bytes):
    """Load an SPKI public key and enforce it is exactly the type ``alg_id`` needs."""
    if not isinstance(spki_der, (bytes, bytearray)) or not 0 < len(spki_der) <= MAX_PUBLIC_KEY_BYTES:
        raise fail("ENVELOPE_MALFORMED", "public key missing or too large")
    try:
        key = serialization.load_der_public_key(bytes(spki_der))
    except (ValueError, TypeError) as exc:
        raise fail("ENVELOPE_MALFORMED", "public key is not valid DER SPKI") from exc
    _assert_key_matches(alg_id, key)
    return key


def _assert_key_matches(alg_id: str, key: Any) -> None:
    ok = False
    if alg_id == "ed25519":
        ok = isinstance(key, ed25519.Ed25519PublicKey)
    elif alg_id == "ecdsa-p256-sha256":
        ok = isinstance(key, ec.EllipticCurvePublicKey) and isinstance(key.curve, ec.SECP256R1)
    elif alg_id == "ecdsa-p384-sha384":
        ok = isinstance(key, ec.EllipticCurvePublicKey) and isinstance(key.curve, ec.SECP384R1)
    elif alg_id.startswith("rsa-pss-"):
        bits = int(alg_id.rsplit("-", 1)[1])
        ok = isinstance(key, rsa.RSAPublicKey) and key.key_size == bits and key.public_numbers().e == 65537
    if not ok:
        raise fail("KEY_POLICY_VIOLATION", "public key type/size does not match declared algorithm", alg=alg_id)


def spki(public_key: Any) -> bytes:
    return public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)


def _hash_for(alg_id: str):
    return hashes.SHA384() if "sha384" in alg_id else hashes.SHA256()


def verify_raw(alg_id: str, spki_der: bytes, signature: bytes, message: bytes, *, profile: str = PROFILE_PRODUCTION, now: int | None = None) -> None:
    """Verify ``signature`` over ``message`` or raise SIGNATURE_INVALID."""
    alg = get(alg_id, profile=profile, now=now)
    lo, hi = alg.sig_len
    if not isinstance(signature, (bytes, bytearray)) or not lo <= len(signature) <= min(hi, MAX_SIGNATURE_BYTES):
        raise fail("SIGNATURE_INVALID", "signature length outside algorithm bounds", alg=alg_id)
    if alg.family == "hmac-reference":
        raise fail("ALG_REFERENCE_ONLY", "HMAC reference signatures are verified only by the isolated v2 reference verifier")
    key = load_public_key(alg_id, spki_der)
    try:
        if alg.family == "eddsa":
            key.verify(bytes(signature), message)
        elif alg.family == "ecdsa":
            key.verify(bytes(signature), message, ec.ECDSA(_hash_for(alg_id)))
        elif alg.family == "rsa-pss":
            h = _hash_for(alg_id)
            key.verify(bytes(signature), message, padding.PSS(mgf=padding.MGF1(h), salt_length=h.digest_size), h)
        else:  # pragma: no cover - registry guarantees coverage
            raise fail("ALG_UNSUPPORTED", "no verifier for algorithm family", alg=alg_id)
    except InvalidSignature as exc:
        raise fail("SIGNATURE_INVALID", "signature does not verify", alg=alg_id) from exc


def software_signer(alg_id: str, private_key: Any) -> Callable[[bytes], bytes]:
    """Return a sign(message) closure for a *software* private key (dev/test/KMS fakes)."""
    get(alg_id, profile=PROFILE_REFERENCE)
    _assert_key_matches(alg_id, private_key.public_key())
    fam = REGISTRY[alg_id].family

    def _sign(message: bytes) -> bytes:
        if fam == "eddsa":
            return private_key.sign(message)
        if fam == "ecdsa":
            return private_key.sign(message, ec.ECDSA(_hash_for(alg_id)))
        h = _hash_for(alg_id)
        return private_key.sign(message, padding.PSS(mgf=padding.MGF1(h), salt_length=h.digest_size), h)

    return _sign


def generate_private_key(alg_id: str):
    """Test/dev helper - production keys are generated inside the KMS/HSM."""
    if alg_id == "ed25519":
        return ed25519.Ed25519PrivateKey.generate()
    if alg_id == "ecdsa-p256-sha256":
        return ec.generate_private_key(ec.SECP256R1())
    if alg_id == "ecdsa-p384-sha384":
        return ec.generate_private_key(ec.SECP384R1())
    if alg_id.startswith("rsa-pss-"):
        return rsa.generate_private_key(public_exponent=65537, key_size=int(alg_id.rsplit("-", 1)[1]))
    raise fail("ALG_UNSUPPORTED", "cannot generate key for algorithm", alg=alg_id)


def registry_document() -> dict[str, Any]:
    """Machine-readable algorithm-agility policy (exported in COMPATIBILITY.json)."""
    return {
        "schema": "PK_ALGORITHM_REGISTRY/1",
        "algorithms": {
            a.alg_id: {
                "family": a.family, "strength_bits": a.strength, "fips_approved": a.fips,
                "production": a.production, "deprecated_after": a.deprecated_after,
                "forbidden": a.forbidden, "deterministic": a.deterministic,
            }
            for a in REGISTRY.values()
        },
    }
