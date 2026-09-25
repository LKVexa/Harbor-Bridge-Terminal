"""Evidence signing, trust store and signer authorization (component 03).

* Domain separation: every signature covers
  ``GAP15-SIG/1|<message-type>|<environment>|<protocol-version>|`` + canonical
  payload, so a signature cannot be replayed across message types,
  environments or protocol versions (MC-03-01).
* Algorithm policy: only ``ed25519`` is approved; unknown/deprecated names are
  rejected before any cryptography runs (MC-03-02, algorithm substitution).
* Trust store: versioned, each key has an overlapping validity window,
  a compromise flag and an authorisation scope (MC-03-05, MC-03-06).
* Keys: private keys are only reachable through ``KeyProvider``. The bundled
  ``DevelopmentKeyProvider`` refuses to operate when ``production=True``;
  a real HSM/KMS/TPM provider is an external dependency (MC-03-07 BLOCKED).
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Optional

from . import ed25519
from .canonical import canonical_bytes, digest

SIGNATURE_PROTOCOL = "GAP15-SIG/1"
APPROVED_ALGORITHMS = {"ed25519"}
DEPRECATED_ALGORITHMS = {"hmac-sha256", "rsa-pkcs1-sha1", "ecdsa-sha1"}


class SignatureError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64d(text: str) -> bytes:
    if not isinstance(text, str) or len(text) > 256:
        raise SignatureError("E_SIG_MALFORMED", "encoded value must be a short string")
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (ValueError, TypeError) as exc:
        raise SignatureError("E_SIG_MALFORMED", "invalid base64url") from exc


def signing_input(message_type: str, environment: str, payload: object, protocol_version: str = "1") -> bytes:
    for name, value in (("message_type", message_type), ("environment", environment), ("protocol_version", protocol_version)):
        if not isinstance(value, str) or not value or "|" in value:
            raise SignatureError("E_SIG_DOMAIN", f"invalid {name}")
    prefix = f"{SIGNATURE_PROTOCOL}|{message_type}|{environment}|{protocol_version}|".encode()
    return prefix + canonical_bytes(payload)


@dataclass(frozen=True)
class TrustedKey:
    key_id: str
    signer: str
    public_key: bytes
    algorithm: str = "ed25519"
    not_before: int = 0
    not_after: int = 2**62
    #: scopes like ``evidence:submit:prod`` or ``evidence:submit:*``
    scopes: frozenset = field(default_factory=frozenset)
    compromised_at: Optional[int] = None


class TrustStore:
    """Versioned set of trusted verification keys."""

    def __init__(self) -> None:
        self._keys: dict[str, TrustedKey] = {}
        self.revision = 0

    def add(self, key: TrustedKey) -> None:
        if key.algorithm not in APPROVED_ALGORITHMS:
            raise SignatureError("E_SIG_ALG_UNAPPROVED", key.algorithm)
        if key.key_id in self._keys:
            raise SignatureError("E_SIG_KEY_EXISTS", "key ids are never reused")
        if len(key.public_key) != 32:
            raise SignatureError("E_SIG_KEY_MALFORMED", "ed25519 public keys are 32 bytes")
        self._keys[key.key_id] = key
        self.revision += 1

    def mark_compromised(self, key_id: str, at: int) -> None:
        key = self._keys[key_id]
        self._keys[key_id] = TrustedKey(**{**key.__dict__, "compromised_at": at})
        self.revision += 1

    def get(self, key_id: str) -> Optional[TrustedKey]:
        return self._keys.get(key_id)

    def keys(self) -> list[TrustedKey]:
        return [self._keys[k] for k in sorted(self._keys)]

    def export_bundle(self) -> dict:
        """Offline verification bundle (MC-03-08): trust roots + revision + canonicalization version."""
        return {
            "schema": "GAP15_TRUST_BUNDLE/1",
            "canonicalization": "GAP15-CANON-JSON/1",
            "signature_protocol": SIGNATURE_PROTOCOL,
            "trust_store_revision": self.revision,
            "keys": [
                {
                    "key_id": k.key_id,
                    "signer": k.signer,
                    "algorithm": k.algorithm,
                    "public_key": b64e(k.public_key),
                    "not_before": k.not_before,
                    "not_after": k.not_after,
                    "scopes": sorted(k.scopes),
                    "compromised_at": k.compromised_at,
                }
                for k in self.keys()
            ],
        }

    @classmethod
    def from_bundle(cls, bundle: dict) -> "TrustStore":
        if bundle.get("schema") != "GAP15_TRUST_BUNDLE/1":
            raise SignatureError("E_SIG_BUNDLE", "unknown trust bundle schema")
        store = cls()
        for k in bundle["keys"]:
            store.add(TrustedKey(k["key_id"], k["signer"], b64d(k["public_key"]), k["algorithm"],
                                 k["not_before"], k["not_after"], frozenset(k["scopes"]), k["compromised_at"]))
        store.revision = bundle["trust_store_revision"]
        return store


class KeyProvider:
    """Boundary for private key operations. Implementations: HSM/KMS/TPM."""

    production_grade = False

    def sign(self, key_id: str, data: bytes) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError

    def public_key(self, key_id: str) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError


class DevelopmentKeyProvider(KeyProvider):
    """In-memory keys for tests and local fixtures only; refuses production mode."""

    def __init__(self, *, production: bool = False) -> None:
        if production:
            raise SignatureError(
                "E_KEY_PROVIDER_NOT_PRODUCTION",
                "development key provider cannot be used in production; configure an HSM/KMS provider",
            )
        self._secrets: dict[str, bytes] = {}

    def generate(self, key_id: str, seed: Optional[bytes] = None) -> bytes:
        secret = seed if seed is not None else os.urandom(32)
        self._secrets[key_id] = secret
        return ed25519.public_key(secret)

    def public_key(self, key_id: str) -> bytes:
        return ed25519.public_key(self._secrets[key_id])

    def sign(self, key_id: str, data: bytes) -> bytes:
        return ed25519.sign(self._secrets[key_id], data)

    def __repr__(self) -> str:  # never render secrets
        return f"DevelopmentKeyProvider(keys={sorted(self._secrets)})"


def sign_payload(provider: KeyProvider, key_id: str, *, message_type: str, environment: str,
                 payload: object, signed_at: int) -> dict:
    data = signing_input(message_type, environment, payload)
    return {
        "algorithm": "ed25519",
        "key_id": key_id,
        "signed_at": signed_at,
        "payload_digest": digest(payload),
        "value": b64e(provider.sign(key_id, data)),
    }


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    code: str
    signer: Optional[str]
    key_id: Optional[str]
    trust_store_revision: int

    def as_dict(self) -> dict:
        return dict(ok=self.ok, code=self.code, signer=self.signer, key_id=self.key_id,
                    trust_store_revision=self.trust_store_revision)


def verify_payload(store: TrustStore, signature: object, *, message_type: str, environment: str,
                   payload: object, required_scope: Optional[str] = None,
                   evaluated_at: Optional[int] = None) -> VerificationResult:
    """Verify before persistence; every failure returns a stable reason code (MC-03-04)."""
    rev = store.revision

    def fail(code: str, key: Optional[TrustedKey] = None, key_id: Optional[str] = None) -> VerificationResult:
        return VerificationResult(False, code, key.signer if key else None, key_id, rev)

    if not isinstance(signature, dict):
        return fail("E_SIG_MISSING")
    alg = signature.get("algorithm")
    key_id = signature.get("key_id")
    if alg in DEPRECATED_ALGORITHMS:
        return fail("E_SIG_ALG_DEPRECATED", key_id=key_id if isinstance(key_id, str) else None)
    if alg not in APPROVED_ALGORITHMS:
        return fail("E_SIG_ALG_UNAPPROVED")
    if not isinstance(key_id, str):
        return fail("E_SIG_MALFORMED")
    key = store.get(key_id)
    if key is None:
        return fail("E_SIG_UNKNOWN_KEY", key_id=key_id)
    if key.algorithm != alg:
        return fail("E_SIG_ALG_KEY_MISMATCH", key, key_id)
    signed_at = signature.get("signed_at")
    if isinstance(signed_at, bool) or not isinstance(signed_at, int):
        return fail("E_SIG_MALFORMED", key, key_id)
    if not key.not_before <= signed_at <= key.not_after:
        return fail("E_SIG_KEY_EXPIRED", key, key_id)
    if key.compromised_at is not None:
        # A compromised key's signing time is itself attacker-controlled, so no
        # new submission under it is accepted. Evidence it signed earlier stays
        # in the ledger and is enumerated for re-evaluation (revocation module).
        return fail("E_SIG_KEY_REVOKED", key, key_id)
    if evaluated_at is not None and signed_at > evaluated_at:
        return fail("E_SIG_FUTURE_SIGNED", key, key_id)
    try:
        payload_digest = digest(payload)
    except ValueError:
        return fail("E_SIG_PAYLOAD_NONCANONICAL", key, key_id)
    if signature.get("payload_digest") != payload_digest:
        return fail("E_SIG_DIGEST_MISMATCH", key, key_id)
    try:
        raw = b64d(signature.get("value", ""))
    except SignatureError:
        return fail("E_SIG_MALFORMED", key, key_id)
    if len(raw) != 64:
        return fail("E_SIG_MALFORMED", key, key_id)
    try:
        data = signing_input(message_type, environment, payload)
    except (SignatureError, ValueError):
        return fail("E_SIG_DOMAIN", key, key_id)
    if not ed25519.verify(key.public_key, data, raw):
        return fail("E_SIG_INVALID", key, key_id)
    if required_scope is not None and not scope_allows(key.scopes, required_scope):
        return fail("E_SIG_SIGNER_UNAUTHORIZED", key, key_id)
    return VerificationResult(True, "OK", key.signer, key_id, rev)


def scope_allows(granted: frozenset, required: str) -> bool:
    """``a:b:c`` matches exactly, or a granted ``a:b:*`` suffix wildcard (single level only)."""
    for scope in granted:
        if scope == required:
            return True
        if scope.endswith(":*") and required.startswith(scope[:-1]) and ":" not in required[len(scope) - 1:]:
            return True
    return False
