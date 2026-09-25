"""G13-MC-001 cryptographic policy-bundle verification adapter.

Trust is *derived*, never asserted: the only object the activation path accepts
is a :class:`VerificationResult` in state ``VERIFIED`` minted inside this module
after the verifier has checked digest, algorithm allowlist, signer identity,
key lifecycle, purpose and issuer/environment binding over the exact immutable
payload bytes that are then parsed (no TOCTOU window).

The evaluator holds public keys only.  Private keys live in the signing
subsystem (GAP-07 / EXT-04); ``tools/sign_bundle.py`` is an offline helper for
fixtures and is never imported by the runtime.
"""
from __future__ import annotations

import base64
import binascii
import hmac
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Protocol

from .bundle import PolicyBundle, parse_bundle, strict_json_loads
from .canonical import sha256_hex
from .config import Limits
from .errors import BundleRejected, DependencyUnavailable, VerificationFailed

VERIFIER_VERSION = "g13-verifier/1.0.0"
ENVELOPE_SCHEMA = "PK_POLICY_SIGNED_BUNDLE/1"
SIGNING_PURPOSE = "policy-bundle-signing"
DOMAIN_TAG = b"PK_POLICY_BUNDLE/1\x00"
_MINT = object()


class VerificationState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    UNKNOWN_SIGNER = "UNKNOWN_SIGNER"
    UNSUPPORTED_ALGORITHM = "UNSUPPORTED_ALGORITHM"


# --------------------------------------------------------------------------- algorithms
def _ed25519_verify(public_key: bytes, signature: bytes, message: bytes) -> bool:
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
    except ImportError as exc:  # optional dependency
        raise DependencyUnavailable("ed25519 backend ('cryptography') not installed") from exc
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, message)
        return True
    except (InvalidSignature, ValueError):
        return False


#: Explicit allowlist.  Nothing in a bundle can add to it (no negotiation).
ALGORITHMS: dict[str, Callable[[bytes, bytes, bytes], bool]] = {"ed25519": _ed25519_verify}


def ed25519_available() -> bool:
    try:
        import cryptography.hazmat.primitives.asymmetric.ed25519  # noqa: F401
        return True
    except ImportError:
        return False


# --------------------------------------------------------------------------- trust store
@dataclass(frozen=True)
class TrustedKey:
    key_id: str
    algorithm: str
    public_key: bytes
    issuer: str
    environments: tuple[str, ...]
    not_before: int
    not_after: int
    purpose: str = SIGNING_PURPOSE
    revoked: bool = False
    compromised: bool = False


@dataclass(frozen=True)
class TrustStore:
    version: str
    keys: Mapping[str, TrustedKey]
    fetched_at: int = 0

    @classmethod
    def from_dict(cls, doc: Mapping[str, Any]) -> "TrustStore":
        if doc.get("schema") != "PK_POLICY_TRUST_STORE/1":
            raise BundleRejected("trust store schema must be PK_POLICY_TRUST_STORE/1")
        keys = {}
        for k in doc.get("keys", []):
            tk = TrustedKey(k["key_id"], k["algorithm"], base64.b64decode(k["public_key_b64"], validate=True),
                            k["issuer"], tuple(k["environments"]), int(k["not_before"]), int(k["not_after"]),
                            k.get("purpose", SIGNING_PURPOSE), bool(k.get("revoked", False)),
                            bool(k.get("compromised", False)))
            if tk.key_id in keys:
                raise BundleRejected(f"duplicate key_id in trust store: {tk.key_id}")
            keys[tk.key_id] = tk
        return cls(str(doc["version"]), keys, int(doc.get("fetched_at", 0)))


class TrustSource(Protocol):
    """GAP-07 adapter contract (``GAP07_TRUST_SOURCE/1``, docs/INTEGRATION_CONTRACTS.md)."""
    def trust_store(self) -> TrustStore: ...


@dataclass
class StaticTrustSource:
    store: TrustStore

    def trust_store(self) -> TrustStore:
        return self.store


# --------------------------------------------------------------------------- result
@dataclass(frozen=True)
class VerificationResult:
    state: VerificationState
    reason: str
    bundle: PolicyBundle | None
    payload: bytes | None
    digest: str | None
    key_id: str | None
    issuer: str | None
    trust_store_version: str | None
    verifier_version: str = VERIFIER_VERSION
    _mint: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.state is VerificationState.VERIFIED and self._mint is not _MINT:
            raise VerificationFailed("VERIFIED results can only be minted by BundleVerifier")

    @property
    def verified(self) -> bool:
        return self.state is VerificationState.VERIFIED and self._mint is _MINT

    def evidence(self) -> dict[str, Any]:
        return {"state": self.state.value, "reason": self.reason, "digest": self.digest, "key_id": self.key_id,
                "issuer": self.issuer, "trust_store_version": self.trust_store_version,
                "verifier_version": self.verifier_version,
                "bundle": self.bundle.identity() if self.bundle else None}


def is_trusted(result: Any) -> bool:
    return isinstance(result, VerificationResult) and result.verified


# --------------------------------------------------------------------------- verifier
class BundleVerifier:
    def __init__(self, trust: TrustSource, *, environment: str, limits: Limits = Limits(),
                 allowed_algorithms: tuple[str, ...] = ("ed25519",),
                 max_trust_store_age: int | None = 86400) -> None:
        unknown = set(allowed_algorithms) - set(ALGORITHMS)
        if unknown:
            raise ValueError(f"algorithms not implemented: {sorted(unknown)}")
        self.trust = trust
        self.environment = environment
        self.limits = limits
        self.allowed = tuple(allowed_algorithms)
        self.max_trust_store_age = max_trust_store_age

    def _fail(self, state: VerificationState, reason: str, **kw: Any) -> VerificationResult:
        return VerificationResult(state, reason, None, None, kw.get("digest"), kw.get("key_id"),
                                  kw.get("issuer"), kw.get("tsv"))

    def verify(self, envelope: bytes, *, now: int) -> VerificationResult:
        S = VerificationState
        try:
            env = strict_json_loads(envelope, max_bytes=self.limits.max_bundle_bytes * 2, max_depth=4)
        except BundleRejected as exc:
            return self._fail(S.REJECTED, f"envelope: {exc}")
        if not isinstance(env, dict) or env.get("schema") != ENVELOPE_SCHEMA:
            return self._fail(S.REJECTED, "envelope schema must be " + ENVELOPE_SCHEMA)
        if set(env) != {"schema", "payload_b64", "digest", "signature"}:
            return self._fail(S.REJECTED, "envelope has missing/unknown fields")
        sig = env["signature"]
        if not isinstance(sig, dict) or set(sig) != {"alg", "key_id", "value_b64"}:
            return self._fail(S.REJECTED, "signature block malformed")
        try:
            payload = base64.b64decode(env["payload_b64"], validate=True)
            sig_bytes = base64.b64decode(sig["value_b64"], validate=True)
        except (binascii.Error, TypeError, ValueError):
            return self._fail(S.REJECTED, "base64 decoding failed")
        payload = bytes(payload)                       # immutable copy -> verified == parsed
        actual = "sha256:" + sha256_hex(payload)
        if not isinstance(env["digest"], str) or not hmac.compare_digest(env["digest"], actual):
            return self._fail(S.REJECTED, "digest mismatch", digest=actual)
        alg, key_id = sig["alg"], sig["key_id"]
        if alg not in self.allowed:
            return self._fail(S.UNSUPPORTED_ALGORITHM, f"algorithm {str(alg)[:32]!r} not in allowlist",
                              digest=actual)
        try:
            store = self.trust.trust_store()
        except Exception as exc:  # dependency outage -> fail closed
            raise DependencyUnavailable(f"trust source unavailable: {type(exc).__name__}") from exc
        if self.max_trust_store_age is not None and store.fetched_at and now - store.fetched_at > self.max_trust_store_age:
            return self._fail(S.REJECTED, "trust store is stale", digest=actual, tsv=store.version)
        key = store.keys.get(key_id) if isinstance(key_id, str) else None
        if key is None:
            return self._fail(S.UNKNOWN_SIGNER, "signer key not in trust store", digest=actual, tsv=store.version)
        kw = dict(digest=actual, key_id=key.key_id, issuer=key.issuer, tsv=store.version)
        if key.algorithm != alg:
            return self._fail(S.UNSUPPORTED_ALGORITHM, "algorithm does not match key's registered algorithm", **kw)
        if key.revoked or key.compromised:
            return self._fail(S.REVOKED, "signer key revoked/compromised", **kw)
        if not key.not_before <= now <= key.not_after:
            return self._fail(S.EXPIRED, "signer key outside validity window", **kw)
        if key.purpose != SIGNING_PURPOSE:
            return self._fail(S.REJECTED, "key not approved for policy-bundle signing", **kw)
        if self.environment not in key.environments:
            return self._fail(S.REJECTED, "key not trusted for this environment", **kw)
        if not ALGORITHMS[alg](key.public_key, sig_bytes, DOMAIN_TAG + payload):
            return self._fail(S.REJECTED, "signature invalid", **kw)
        try:
            bundle = parse_bundle(payload, self.limits)
        except BundleRejected as exc:
            return self._fail(S.REJECTED, f"payload: [{exc.code}] {exc}", **kw)
        if bundle.issuer != key.issuer:
            return self._fail(S.REJECTED, "bundle issuer does not match signer's issuer", **kw)
        if bundle.environment != self.environment:
            return self._fail(S.REJECTED, "bundle environment does not match verifier environment", **kw)
        if bundle.issued_at > now + 300:
            return self._fail(S.REJECTED, "bundle issued_at is in the future", **kw)
        if bundle.expires_at is not None and now >= bundle.expires_at:
            return self._fail(S.EXPIRED, "bundle past expires_at", **kw)
        return VerificationResult(S.VERIFIED, "ok", bundle, payload, actual, key.key_id, key.issuer,
                                  store.version, _mint=_MINT)
