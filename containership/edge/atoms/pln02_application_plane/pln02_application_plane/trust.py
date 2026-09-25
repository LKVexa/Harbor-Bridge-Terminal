"""MC-11 / MC-18 / MC-21 - Trust roots, key lifecycle, signing and verification.

A ``KeyRing`` holds trust roots by key id with a validity window, a purpose
(``catalogue``, ``artifact``, ``token``, ``audit``) and a revocation flag.
Two algorithms are supported:

* ``hmac-sha256`` - stdlib, symmetric; suitable for in-estate service tokens
  and audit chaining where the verifier is also trusted to sign.
* ``ed25519`` - asymmetric; used only when the optional ``cryptography``
  package is installed. Without it, ed25519 keys are refused (fail closed),
  never silently downgraded.

Key material is never logged, rendered in errors, or included in ``repr``.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import time
from typing import Any, Callable, Mapping

from .errors import PlaneError

try:  # optional asymmetric support
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    HAVE_ED25519 = True
except Exception:  # pragma: no cover - environment dependent
    HAVE_ED25519 = False

ALGORITHMS = ("hmac-sha256", "ed25519")
PURPOSES = ("catalogue", "artifact", "token", "audit", "config")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


@dataclass
class TrustKey:
    key_id: str
    algorithm: str
    purpose: str
    material: bytes = field(repr=False)  # hmac secret or ed25519 public/private raw bytes
    not_before: float = 0.0
    not_after: float = float("inf")
    revoked: bool = False
    can_sign: bool = True

    def __post_init__(self) -> None:
        if self.algorithm not in ALGORITHMS:
            raise PlaneError("unsupported key algorithm", code="CONFIG_INVALID", details={"field": "algorithm"})
        if self.purpose not in PURPOSES:
            raise PlaneError("unsupported key purpose", code="CONFIG_INVALID", details={"field": "purpose"})
        if self.algorithm == "hmac-sha256" and len(self.material) < 32:
            raise PlaneError("hmac key shorter than 256 bits", code="CONFIG_INVALID", details={"field": "material"})


class KeyRing:
    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._keys: dict[str, TrustKey] = {}
        self._clock = clock

    def add(self, key: TrustKey) -> None:
        if key.key_id in self._keys:
            raise PlaneError("duplicate key id", code="CONFIG_INVALID", details={"field": "key_id"})
        self._keys[key.key_id] = key

    def revoke(self, key_id: str) -> None:
        if key_id in self._keys:
            self._keys[key_id].revoked = True

    def rotate(self, old_id: str, new_key: TrustKey, *, overlap_seconds: float = 3600.0) -> None:
        """Add ``new_key`` and bound ``old_id`` to an overlap window for verification."""
        self.add(new_key)
        old = self._keys.get(old_id)
        if old is not None:
            old.not_after = min(old.not_after, self._clock() + overlap_seconds)
            old.can_sign = False

    def ids(self, purpose: str | None = None) -> list[str]:
        return sorted(k for k, v in self._keys.items() if purpose is None or v.purpose == purpose)

    def _usable(self, key_id: str, purpose: str) -> TrustKey:
        key = self._keys.get(key_id)
        now = self._clock()
        if key is None or key.revoked or key.purpose != purpose or not (key.not_before <= now < key.not_after):
            raise PlaneError("signature key not trusted", code="CATALOGUE_UNTRUSTED", details={"key_id": str(key_id)[:64]})
        if key.algorithm == "ed25519" and not HAVE_ED25519:
            raise PlaneError("ed25519 unavailable; refusing", code="CATALOGUE_UNTRUSTED", details={"key_id": key_id})
        return key

    def sign(self, key_id: str, purpose: str, payload: Any) -> str:
        key = self._usable(key_id, purpose)
        if not key.can_sign:
            raise PlaneError("key is verification-only", code="CATALOGUE_UNTRUSTED", details={"key_id": key_id})
        data = canonical(payload)
        if key.algorithm == "hmac-sha256":
            sig = hmac.new(key.material, data, hashlib.sha256).digest()
        else:
            sig = Ed25519PrivateKey.from_private_bytes(key.material).sign(data)
        return base64.b64encode(sig).decode()

    def verify(self, key_id: str, purpose: str, payload: Any, signature: str) -> bool:
        key = self._usable(key_id, purpose)
        try:
            sig = base64.b64decode(signature, validate=True)
        except Exception:
            raise PlaneError("malformed signature", code="CATALOGUE_UNTRUSTED", details={"key_id": key_id}) from None
        data = canonical(payload)
        if key.algorithm == "hmac-sha256":
            ok = hmac.compare_digest(hmac.new(key.material, data, hashlib.sha256).digest(), sig)
        else:
            try:
                priv_or_pub = key.material
                pub = (Ed25519PrivateKey.from_private_bytes(priv_or_pub).public_key() if key.can_sign
                       else Ed25519PublicKey.from_public_bytes(priv_or_pub))
                pub.verify(sig, data)
                ok = True
            except InvalidSignature:
                ok = False
        if not ok:
            raise PlaneError("signature verification failed", code="CATALOGUE_UNTRUSTED", details={"key_id": key_id})
        return True


# ---------------------------------------------------------------- MC-11 tokens
TOKEN_MAX_TTL = 900.0
CLOCK_SKEW = 30.0


def issue_token(ring: KeyRing, key_id: str, *, subject: str, tenant: str, audience: str,
                roles: list[str], ttl: float = 300.0, now: float | None = None) -> str:
    now = time.time() if now is None else now
    claims = {"sub": subject, "tenant": tenant, "aud": audience, "roles": sorted(roles),
              "iat": int(now), "exp": int(now + min(ttl, TOKEN_MAX_TTL)), "kid": key_id}
    sig = ring.sign(key_id, "token", claims)
    body = base64.urlsafe_b64encode(canonical(claims)).decode().rstrip("=")
    return f"{body}.{sig}"


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    roles: tuple[str, ...]


def authenticate(ring: KeyRing, token: object, *, audience: str, now: float | None = None) -> Principal:
    """Verify a bearer token; any failure is ``UNAUTHENTICATED`` with no detail leak."""
    def deny() -> PlaneError:
        return PlaneError("authentication failed", code="UNAUTHENTICATED")
    if not isinstance(token, str) or len(token) > 4096 or token.count(".") != 1:
        raise deny()
    body, sig = token.split(".")
    try:
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except Exception:
        raise deny() from None
    if not isinstance(claims, dict) or set(claims) != {"sub", "tenant", "aud", "roles", "iat", "exp", "kid"}:
        raise deny()
    try:
        ring.verify(claims["kid"], "token", claims, sig)
    except PlaneError:
        raise deny() from None
    now = time.time() if now is None else now
    if claims["aud"] != audience or not (claims["iat"] - CLOCK_SKEW <= now < claims["exp"] + CLOCK_SKEW):
        raise deny()
    if claims["exp"] - claims["iat"] > TOKEN_MAX_TTL:
        raise deny()
    return Principal(claims["sub"], claims["tenant"], tuple(claims["roles"]))


# --------------------------------------------------------- MC-21 artifacts
def verify_artifact(ring: KeyRing, attestation: Mapping[str, Any], *, approved: Mapping[str, set[str]],
                    revoked_digests: set[str] = frozenset()) -> dict:
    """Verify a signed provider/component artifact attestation.

    ``attestation`` = {"artifact": name, "version": v, "digest": sha256hex,
    "sbom_digest": sha256hex, "builder": str, "key_id": str, "signature": b64}.
    ``approved`` maps artifact name -> set of approved versions.
    """
    fields = {"artifact", "version", "digest", "sbom_digest", "builder", "key_id", "signature"}
    if not isinstance(attestation, Mapping) or set(attestation) != fields:
        raise PlaneError("malformed attestation", code="ARTIFACT_UNTRUSTED", details={"reason": "shape"})
    name = str(attestation["artifact"])
    body = {k: attestation[k] for k in fields - {"signature", "key_id"}}
    try:
        ring.verify(attestation["key_id"], "artifact", body, attestation["signature"])
    except PlaneError:
        raise PlaneError("artifact signature invalid", code="ARTIFACT_UNTRUSTED",
                         details={"artifact": name, "reason": "signature"}) from None
    for f in ("digest", "sbom_digest"):
        v = attestation[f]
        if not (isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)):
            raise PlaneError("bad digest", code="ARTIFACT_UNTRUSTED", details={"artifact": name, "reason": f})
    if attestation["digest"] in revoked_digests:
        raise PlaneError("artifact revoked", code="ARTIFACT_UNTRUSTED", details={"artifact": name, "reason": "revoked"})
    if attestation["version"] not in approved.get(name, set()):
        raise PlaneError("artifact version not approved", code="ARTIFACT_UNTRUSTED",
                         details={"artifact": name, "reason": "unapproved_version"})
    return dict(body)
