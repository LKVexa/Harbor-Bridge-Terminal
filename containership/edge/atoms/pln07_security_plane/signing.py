"""Reference signing / trust-root implementation for PLN-07 (MC-05).

Provides a key store with an explicit algorithm policy, key identifiers, key
lifecycle (active -> retiring -> revoked), rotation and a signature envelope
that binds ``alg``, ``kid`` and the canonical grant body.

Algorithms:
* ``Ed25519`` (asymmetric, preferred) - requires the ``cryptography`` package.
* ``HMAC-SHA256`` (symmetric, stdlib) - allowed only when the policy says so,
  e.g. single-host or test deployments.

Production deployments are expected to back ``KeyStore`` with an HSM/KMS via
``KeyBackend``; the in-memory backend here is the reference and test fixture.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from typing import Any

from .grants import Grant, SecurityPlaneError

try:  # optional asymmetric support
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    HAVE_ED25519 = True
except Exception:  # pragma: no cover - exercised when cryptography is absent
    HAVE_ED25519 = False

KEY_STATES = ("active", "retiring", "revoked")


class SigningError(SecurityPlaneError):
    code = "signing.error"


@dataclass(frozen=True)
class AlgorithmPolicy:
    allowed: frozenset[str] = frozenset({"Ed25519"})
    min_hmac_key_bytes: int = 32

    def check(self, alg: str) -> None:
        if alg not in self.allowed:
            raise SigningError(f"algorithm {alg!r} is not permitted by policy", details={"alg": alg})


@dataclass
class _Key:
    kid: str
    alg: str
    state: str
    secret: Any
    public: Any
    not_after: int | None


@dataclass
class KeyStore:
    """Trust root + signer.  ``trust_domain`` scopes every signature."""

    trust_domain: str
    policy: AlgorithmPolicy = field(default_factory=AlgorithmPolicy)
    _keys: dict[str, _Key] = field(default_factory=dict, init=False, repr=False)

    # -- lifecycle -----------------------------------------------------------
    def generate(self, alg: str = "Ed25519", *, not_after: int | None = None) -> str:
        self.policy.check(alg)
        if alg == "Ed25519":
            if not HAVE_ED25519:
                raise SigningError("Ed25519 requires the 'cryptography' package")
            sk = Ed25519PrivateKey.generate()
            pk = sk.public_key()
            from cryptography.hazmat.primitives import serialization

            raw = pk.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            kid = hashlib.sha256(raw).hexdigest()[:32]
            self._keys[kid] = _Key(kid, alg, "active", sk, pk, not_after)
        elif alg == "HMAC-SHA256":
            secret = secrets.token_bytes(max(32, self.policy.min_hmac_key_bytes))
            kid = hashlib.sha256(b"kid|" + secret).hexdigest()[:32]
            self._keys[kid] = _Key(kid, alg, "active", secret, None, not_after)
        else:
            raise SigningError(f"unknown algorithm {alg!r}")
        return kid

    def import_public(self, kid: str, raw_public: bytes) -> None:
        """Pin a verification-only Ed25519 key (trust-root distribution)."""
        self.policy.check("Ed25519")
        if not HAVE_ED25519:
            raise SigningError("Ed25519 requires the 'cryptography' package")
        self._keys[kid] = _Key(kid, "Ed25519", "active", None,
                               Ed25519PublicKey.from_public_bytes(raw_public), None)

    def rotate(self, old_kid: str, alg: str | None = None) -> str:
        old = self._require(old_kid)
        new = self.generate(alg or old.alg)
        old.state = "retiring"  # still verifies, no longer signs
        return new

    def revoke_key(self, kid: str) -> None:
        self._require(kid).state = "revoked"

    def active_kid(self) -> str:
        for key in self._keys.values():
            if key.state == "active" and key.secret is not None:
                return key.kid
        raise SigningError("no active signing key")

    def describe(self) -> list[dict]:
        return [
            {"kid": k.kid, "alg": k.alg, "state": k.state, "can_sign": k.secret is not None}
            for k in self._keys.values()
        ]

    def _require(self, kid: str) -> _Key:
        try:
            return self._keys[kid]
        except KeyError:
            raise SigningError("unknown key id", details={"kid": kid}) from None

    # -- sign / verify ------------------------------------------------------
    def _message(self, alg: str, kid: str, payload: bytes) -> bytes:
        header = f"PK_SIG/1|{self.trust_domain}|{alg}|{kid}|".encode()
        return header + payload

    def sign(self, payload: bytes, kid: str | None = None, *, now: int | None = None) -> dict:
        key = self._require(kid or self.active_kid())
        if key.state != "active" or key.secret is None:
            raise SigningError("key is not permitted to sign", details={"kid": key.kid, "state": key.state})
        if now is not None and key.not_after is not None and now > key.not_after:
            raise SigningError("signing key expired", details={"kid": key.kid})
        self.policy.check(key.alg)
        msg = self._message(key.alg, key.kid, payload)
        if key.alg == "Ed25519":
            raw = key.secret.sign(msg)
        else:
            raw = hmac.new(key.secret, msg, hashlib.sha256).digest()
        return {"type": "PK_SIG/1", "alg": key.alg, "kid": key.kid,
                "domain": self.trust_domain, "sig": base64.b64encode(raw).decode()}

    def verify(self, envelope: Any, payload: bytes) -> bool:
        if not isinstance(envelope, dict) or envelope.get("type") != "PK_SIG/1":
            return False
        if envelope.get("domain") != self.trust_domain:
            return False
        key = self._keys.get(envelope.get("kid", ""))
        if key is None or key.state == "revoked" or key.alg != envelope.get("alg"):
            return False
        try:
            self.policy.check(key.alg)
            raw = base64.b64decode(envelope.get("sig", ""), validate=True)
        except Exception:
            return False
        msg = self._message(key.alg, key.kid, payload)
        if key.alg == "Ed25519":
            try:
                key.public.verify(raw, msg)
                return True
            except InvalidSignature:
                return False
        expected = hmac.new(key.secret, msg, hashlib.sha256).digest()
        return hmac.compare_digest(expected, raw)

    # -- grant helpers --------------------------------------------------------
    def sign_grant(self, grant: Grant, *, now: int | None = None) -> Grant:
        return grant.signed(self.sign(grant.canonical_payload, now=now))

    def grant_verifier(self):
        """Adapter for ``Verifier(signature_verifier=...)``."""
        return lambda g: self.verify(g.signature, g.canonical_payload)
