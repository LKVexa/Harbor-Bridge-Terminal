"""Identity, capabilities, artifact trust, secrets and encryption for INV-63.

INV-63-C023 authentication  - :class:`TokenAuthority` (HMAC-SHA256 bearer
    tokens with issuer, audience, expiry, not-before, nonce replay protection).
INV-63-C024/C042 authorization / least privilege - :data:`ROLES` grants only
    the capabilities each actor needs; every call names its capability.
INV-63-C043 ambient authority - the service holds no filesystem/network handles
    except those injected (adapter, journal path); see docs/architecture.
INV-63-C044/C045 artifact trust - :class:`ArtifactVerifier` checks sha256 digest,
    Ed25519 signature by an allow-listed key id, approved version, provenance.
INV-63-C046 tenant isolation - :func:`namespace` and Authorizer tenant scoping.
INV-63-C047 encryption at rest - :class:`Sealer` (AES-256-GCM, key ids, rotation).
INV-63-C039 secrets - :func:`redact`, :func:`resolve_secret_ref`.
INV-63-C048 dependency outage - verifiers fail CLOSED when keys/crypto/time
    are unavailable.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import DeploymentError, ErrorCode

try:  # pinned in requirements.lock: cryptography==46.0.7
    from cryptography.exceptions import InvalidSignature, InvalidTag
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAVE_CRYPTO = True
except ModuleNotFoundError:  # pragma: no cover - fail closed below
    HAVE_CRYPTO = False

# ---------------------------------------------------------------- capabilities
CAPABILITIES = frozenset({
    "desired:write", "desired:read", "reconcile:run", "rollout:run", "rollback:run",
    "control:freeze", "control:quarantine", "explain:read", "config:activate", "audit:read",
})

ROLES: dict[str, frozenset[str]] = {
    # least privilege: each role is the minimum for its job (INV-63-C042)
    "tenant-deployer": frozenset({"desired:write", "desired:read", "reconcile:run", "rollout:run", "explain:read"}),
    "tenant-viewer": frozenset({"desired:read", "explain:read"}),
    "reconciler": frozenset({"reconcile:run", "desired:read"}),
    "sre-operator": frozenset({"control:freeze", "control:quarantine", "rollback:run", "explain:read", "desired:read"}),
    "config-admin": frozenset({"config:activate"}),
    "auditor": frozenset({"audit:read", "explain:read"}),
}

OP_CAPABILITY = {
    "set_desired": "desired:write", "reconcile": "reconcile:run", "rollout": "rollout:run",
    "rollback": "rollback:run", "freeze": "control:freeze", "unfreeze": "control:freeze",
    "quarantine": "control:quarantine", "release_quarantine": "control:quarantine",
    "explain": "explain:read",
}


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str            # "*" only for platform operators
    roles: frozenset[str]
    kind: str = "user"     # user | node | peer | controller

    @property
    def capabilities(self) -> frozenset[str]:
        caps: set[str] = set()
        for r in self.roles:
            caps |= ROLES.get(r, frozenset())
        return frozenset(caps)


class Authorizer:
    def check(self, p: Principal, capability: str, tenant: str) -> None:
        if capability not in CAPABILITIES:
            raise DeploymentError(ErrorCode.FORBIDDEN, f"unknown capability {capability!r}")
        if capability not in p.capabilities:
            raise DeploymentError(ErrorCode.FORBIDDEN, f"{p.subject} lacks {capability}",
                                  {"capability": capability})
        if p.tenant != "*" and p.tenant != tenant:
            raise DeploymentError(ErrorCode.TENANT_VIOLATION, f"{p.subject} is scoped to another tenant",
                                  {"requested_tenant": tenant})
        if p.tenant == "*" and capability in {"desired:write", "rollout:run"}:
            # platform actors cannot write tenant workloads (separation of duties)
            raise DeploymentError(ErrorCode.FORBIDDEN, "platform principals may not mutate tenant workloads")


TENANT_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")


def namespace(tenant: str, component: str) -> str:
    """Tenant-qualified component id; tenants can never collide (INV-63-C046)."""
    if not isinstance(tenant, str) or not TENANT_RE.fullmatch(tenant):
        raise DeploymentError(ErrorCode.TENANT_VIOLATION, "invalid tenant id")
    if not isinstance(component, str) or "/" in component or not component:
        raise DeploymentError(ErrorCode.INVALID_REQUEST, "component may not contain '/'")
    return f"{tenant}/{component}"


# ---------------------------------------------------------------- tokens
def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class TokenAuthority:
    """Issue/verify HMAC bearer tokens.  Keys are resolved via secret refs, never config literals."""

    def __init__(self, keys: dict[str, bytes], issuer: str = "inv63", audience: str = "inv63-api",
                 clock: Callable[[], float] = time.time, max_skew_s: float = 30.0, replay_window: int = 100_000):
        if not keys or any(len(k) < 32 for k in keys.values()):
            raise DeploymentError(ErrorCode.CONFIG_INVALID, "token keys must be >= 32 bytes")
        self.keys = dict(keys)
        self.active_kid = sorted(keys)[-1]
        self.issuer, self.audience, self.clock, self.max_skew_s = issuer, audience, clock, max_skew_s
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._replay_window = replay_window

    def issue(self, p: Principal, ttl_s: float = 300.0, nonce: str | None = None) -> str:
        now = self.clock()
        claims = {"iss": self.issuer, "aud": self.audience, "sub": p.subject, "ten": p.tenant,
                  "rol": sorted(p.roles), "knd": p.kind, "iat": now, "nbf": now, "exp": now + ttl_s,
                  "jti": nonce or _b64(os.urandom(12)), "kid": self.active_kid}
        body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
        sig = _b64(hmac.new(self.keys[self.active_kid], body.encode(), hashlib.sha256).digest())
        return f"{body}.{sig}"

    def verify(self, token: object) -> Principal:
        bad = DeploymentError(ErrorCode.UNAUTHENTICATED, "invalid token")
        if not isinstance(token, str) or token.count(".") != 1 or len(token) > 2048:
            raise bad
        body, sig = token.split(".")
        try:
            claims = json.loads(_unb64(body))
        except Exception:
            raise bad from None
        if not isinstance(claims, dict):
            raise bad
        key = self.keys.get(claims.get("kid"))
        if key is None:
            raise bad
        expect = _b64(hmac.new(key, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expect, sig):
            raise bad
        now = self.clock()
        if claims.get("iss") != self.issuer or claims.get("aud") != self.audience:
            raise bad
        if not (claims["nbf"] - self.max_skew_s <= now < claims["exp"] + self.max_skew_s):
            raise DeploymentError(ErrorCode.UNAUTHENTICATED, "token expired or not yet valid")
        jti = claims.get("jti")
        if jti in self._seen:
            raise DeploymentError(ErrorCode.REPLAY_DETECTED, "token nonce already used")
        self._seen[jti] = claims["exp"]
        while len(self._seen) > self._replay_window:
            self._seen.popitem(last=False)
        return Principal(claims["sub"], claims["ten"], frozenset(claims["rol"]), claims.get("knd", "user"))

    def rotate(self, kid: str, key: bytes) -> None:
        if len(key) < 32:
            raise DeploymentError(ErrorCode.CONFIG_INVALID, "key too short")
        self.keys[kid] = key
        self.active_kid = kid

    def retire(self, kid: str) -> None:
        if kid == self.active_kid:
            raise DeploymentError(ErrorCode.PRECONDITION_FAILED, "cannot retire the active key")
        self.keys.pop(kid, None)


# ---------------------------------------------------------------- artifacts
def sha256_ref(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _require_crypto() -> None:
    if not HAVE_CRYPTO:
        raise DeploymentError(ErrorCode.DEPENDENCY_UNAVAILABLE,
                              "cryptography==46.0.7 not installed; signature/encryption fail closed")


def signing_payload(component: str, version: str, digest: str, provenance: str = "") -> bytes:
    return json.dumps({"c": component, "v": version, "d": digest, "p": provenance},
                      sort_keys=True, separators=(",", ":")).encode()


@dataclass
class ArtifactVerifier:
    trusted_keys: dict[str, "Ed25519PublicKey"] = field(default_factory=dict)
    approved_versions: dict[str, set[str]] | None = None   # component -> versions; None = any
    revoked_digests: set[str] = field(default_factory=set)

    def verify(self, component: str, version: str, artifact: dict[str, Any] | None,
               blob: bytes | None = None) -> str:
        _require_crypto()
        if not artifact:
            raise DeploymentError(ErrorCode.ARTIFACT_UNTRUSTED, "unsigned artifact rejected")
        digest = artifact.get("digest", "")
        if blob is not None and sha256_ref(blob) != digest:
            raise DeploymentError(ErrorCode.ARTIFACT_UNTRUSTED, "artifact digest mismatch")
        if digest in self.revoked_digests:
            raise DeploymentError(ErrorCode.ARTIFACT_UNTRUSTED, "artifact digest revoked")
        key = self.trusted_keys.get(artifact.get("key_id", ""))
        if key is None:
            raise DeploymentError(ErrorCode.ARTIFACT_UNTRUSTED, "signing key not trusted")
        try:
            key.verify(bytes.fromhex(artifact.get("signature", "")),
                       signing_payload(component, version, digest, artifact.get("provenance", "")))
        except (InvalidSignature, ValueError):
            raise DeploymentError(ErrorCode.ARTIFACT_UNTRUSTED, "artifact signature invalid") from None
        if self.approved_versions is not None and version not in self.approved_versions.get(component, set()):
            raise DeploymentError(ErrorCode.ARTIFACT_UNTRUSTED, f"{component}@{version} is not an approved version")
        return digest


def sign_artifact(priv: "Ed25519PrivateKey", key_id: str, component: str, version: str, blob: bytes,
                  provenance: str = "") -> dict[str, str]:
    _require_crypto()
    d = sha256_ref(blob)
    return {"digest": d, "key_id": key_id, "provenance": provenance,
            "signature": priv.sign(signing_payload(component, version, d, provenance)).hex()}


# ---------------------------------------------------------------- secrets
SECRET_KEY_RE = re.compile(r"(pass(word)?|secret|token|api[_-]?key|private[_-]?key|credential|bearer)", re.I)
SECRET_VALUE_RES = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
]
REDACTED = "«redacted»"


def looks_secret(key: str, value: Any) -> bool:
    if isinstance(value, str):
        if any(r.search(value) for r in SECRET_VALUE_RES):
            return True
        if SECRET_KEY_RE.search(key or "") and not value.startswith(("env:", "file:")):
            return True
    return False


def redact(obj: Any, _key: str = "") -> Any:
    if isinstance(obj, dict):
        return {k: (REDACTED if SECRET_KEY_RE.search(str(k)) and not isinstance(v, (dict, list)) else redact(v, k))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v, _key) for v in obj]
    if isinstance(obj, str):
        out = obj
        for r in SECRET_VALUE_RES:
            out = r.sub(REDACTED, out)
        return out
    return obj


def resolve_secret_ref(ref: str, env: dict[str, str] | None = None) -> bytes:
    env = os.environ if env is None else env
    if not isinstance(ref, str):
        raise DeploymentError(ErrorCode.CONFIG_INVALID, "secret ref must be a string")
    if ref.startswith("env:"):
        val = env.get(ref[4:])
        if val is None:
            raise DeploymentError(ErrorCode.DEPENDENCY_UNAVAILABLE, f"secret {ref} unavailable")
        return val.encode()
    if ref.startswith("file:"):
        try:
            with open(ref[5:], "rb") as fh:
                return fh.read().strip()
        except OSError:
            raise DeploymentError(ErrorCode.DEPENDENCY_UNAVAILABLE, f"secret {ref} unavailable") from None
    raise DeploymentError(ErrorCode.CONFIG_INVALID, "unsupported secret ref scheme (env:, file:)")


# ---------------------------------------------------------------- encryption
class Sealer:
    """AES-256-GCM envelope with key ids and rotation (INV-63-C047)."""

    def __init__(self, keys: dict[str, bytes]):
        _require_crypto()
        if not keys or any(len(k) != 32 for k in keys.values()):
            raise DeploymentError(ErrorCode.CONFIG_INVALID, "data keys must be 32 bytes")
        self.keys = dict(keys)
        self.active = sorted(keys)[-1]

    def seal(self, plaintext: bytes, aad: bytes = b"inv63") -> str:
        nonce = os.urandom(12)
        ct = AESGCM(self.keys[self.active]).encrypt(nonce, plaintext, aad)
        return f"v1.{self.active}.{_b64(nonce)}.{_b64(ct)}"

    def open(self, token: str, aad: bytes = b"inv63") -> bytes:
        try:
            v, kid, n, c = token.split(".")
            if v != "v1":
                raise ValueError
            return AESGCM(self.keys[kid]).decrypt(_unb64(n), _unb64(c), aad)
        except (ValueError, KeyError, InvalidTag):
            raise DeploymentError(ErrorCode.STATE_CORRUPT, "sealed record failed authentication") from None

    def rotate(self, kid: str, key: bytes) -> None:
        if len(key) != 32:
            raise DeploymentError(ErrorCode.CONFIG_INVALID, "data key must be 32 bytes")
        self.keys[kid] = key
        self.active = kid

    def reseal(self, token: str, aad: bytes = b"inv63") -> str:
        return self.seal(self.open(token, aad), aad)
