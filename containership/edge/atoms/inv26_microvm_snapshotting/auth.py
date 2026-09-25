"""Authentication, capability authorization and anti-replay restore grants
(C023, C024, C042, C044, X008).

Credentials
-----------
A credential is a compact signed token ``b64url(header).b64url(claims).b64url(sig)``.
Algorithms: ``EdDSA`` (Ed25519, publicly verifiable, **required in the
production profile**) and ``HS256`` (shared-secret; accepted only when the
active profile is ``reference``). ``none`` and every other value are refused.

Verification binds the token to audience (``aud`` = this service instance),
environment and site, checks ``nbf``/``exp`` with a bounded clock skew, the
issuer's key id against a :class:`TrustStore` (keys have states:
active/verify_only/revoked; revocation is immediate), and caps the lifetime
(``exp - iat``) so long-lived credentials are refused.

Authorization
-------------
Deny-by-default capabilities: ``snapshot.capture``, ``snapshot.restore``,
``snapshot.delete``, ``snapshot.inspect``, ``snapshot.quarantine``,
``snapshot.admin``. Each grant in ``claims["caps"]`` is scoped to
tenant/workload/environment (``*`` allowed only for ``admin`` scopes). The
request's tenant/workload/environment must fall inside the caller's scope —
the service never trusts request fields alone (confused-deputy defence).
Break-glass tokens (``bg: true``) need ``bg_reason``, a lifetime of at most
15 minutes, and are always audited with severity ``critical``.

Restore grants (X008)
---------------------
A restore needs a one-shot grant issued by the control plane over
``{op, snapshot_id, manifest_sha256, tenant, workload, environment, node,
target_vm_id, action: "restore", generation, iat, exp, nonce, aud}``.
:func:`consume_grant` records the nonce in the durable metastore with a
compare-and-swap, so the same grant commits at most one restore, across
restarts and processes. A retry carrying the **same idempotency key** gets the
recorded result back instead of a second restore.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import SnapshotServiceError

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    HAVE_ED25519 = True
except ImportError:  # pragma: no cover
    HAVE_ED25519 = False

CAPABILITIES = frozenset({"snapshot.capture", "snapshot.restore", "snapshot.delete", "snapshot.inspect",
                          "snapshot.quarantine", "snapshot.admin"})
MAX_SKEW_S = 30
MAX_LIFETIME_S = 3600
MAX_BREAKGLASS_S = 900
MAX_TOKEN_BYTES = 4096


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    if not isinstance(s, str) or len(s) > MAX_TOKEN_BYTES:
        raise ValueError("bad segment")
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _canon(o: Any) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


# ------------------------------------------------------------------ keys
@dataclass
class TrustedKey:
    kid: str
    alg: str
    public: bytes  # Ed25519 raw public key, or HMAC secret for HS256
    role: str      # "caller" | "grant-issuer"
    trust_domain: str  # e.g. "prod/site-a"
    state: str = "active"  # active | verify_only | revoked


@dataclass
class TrustStore:
    keys: dict[str, TrustedKey] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, key: TrustedKey) -> None:
        if key.alg not in ("EdDSA", "HS256"):
            raise ValueError("unsupported algorithm")
        with self._lock:
            if key.kid in self.keys and self.keys[key.kid].state == "revoked":
                raise ValueError("a revoked kid cannot be re-added")
            self.keys[key.kid] = key

    def revoke(self, kid: str) -> None:
        with self._lock:
            if kid in self.keys:
                self.keys[kid].state = "revoked"

    def get(self, kid: str) -> TrustedKey | None:
        with self._lock:
            return self.keys.get(kid)


@dataclass
class Signer:
    kid: str
    alg: str
    secret: bytes  # Ed25519 raw private key or HMAC secret

    @classmethod
    def ed25519(cls, kid: str) -> tuple["Signer", bytes]:
        if not HAVE_ED25519:
            raise SnapshotServiceError("SNAP_DEPENDENCY_UNAVAILABLE", "cryptography not installed")
        k = Ed25519PrivateKey.generate()
        priv = k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                               serialization.NoEncryption())
        pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return cls(kid, "EdDSA", priv), pub

    def sign(self, claims: dict) -> str:
        header = {"alg": self.alg, "kid": self.kid, "typ": "PK_SNAPSHOT_TOKEN/1"}
        signing_input = f"{_b64e(_canon(header))}.{_b64e(_canon(claims))}".encode()
        if self.alg == "EdDSA":
            sig = Ed25519PrivateKey.from_private_bytes(self.secret).sign(signing_input)
        elif self.alg == "HS256":
            sig = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        else:
            raise ValueError("unsupported algorithm")
        return f"{signing_input.decode()}.{_b64e(sig)}"


def _verify_sig(key: TrustedKey, signing_input: bytes, sig: bytes) -> bool:
    if key.alg == "EdDSA":
        if not HAVE_ED25519:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(key.public).verify(sig, signing_input)
            return True
        except (InvalidSignature, ValueError):
            return False
    if key.alg == "HS256":
        return hmac.compare_digest(hmac.new(key.public, signing_input, hashlib.sha256).digest(), sig)
    return False


@dataclass(frozen=True)
class Principal:
    subject: str
    caps: tuple[dict, ...]
    breakglass: bool
    breakglass_reason: str | None
    kid: str
    token_id: str


class Authenticator:
    def __init__(self, trust: TrustStore, *, audience: str, environment: str, site: str,
                 profile: str = "production", clock: Callable[[], float] = time.time):
        self.trust, self.audience, self.environment, self.site = trust, audience, environment, site
        self.profile, self.clock = profile, clock

    def _decode(self, token: str, role: str) -> tuple[dict, TrustedKey]:
        if not isinstance(token, str) or len(token) > MAX_TOKEN_BYTES or token.count(".") != 2:
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "malformed credential")
        h, c, s = token.split(".")
        try:
            header, claims, sig = json.loads(_b64d(h)), json.loads(_b64d(c)), _b64d(s)
        except (ValueError, UnicodeDecodeError):
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "undecodable credential") from None
        if not isinstance(header, dict) or not isinstance(claims, dict):
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "malformed credential")
        alg = header.get("alg")
        if alg not in ("EdDSA", "HS256"):
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", f"algorithm {str(alg)[:16]!r} refused")
        if alg == "HS256" and self.profile != "reference":
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "HS256 not permitted in this profile")
        key = self.trust.get(str(header.get("kid")))
        if key is None or key.state == "revoked" or key.alg != alg or key.role != role:
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "unknown, revoked or mismatched key")
        if key.trust_domain != f"{self.environment}/{self.site}":
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "key from another trust domain")
        if not _verify_sig(key, f"{h}.{c}".encode(), sig):
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "signature invalid")
        now = self.clock()
        try:
            iat, nbf, exp = float(claims["iat"]), float(claims.get("nbf", claims["iat"])), float(claims["exp"])
        except (KeyError, TypeError, ValueError):
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "missing time claims") from None
        if now + MAX_SKEW_S < nbf:
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "credential not yet valid")
        if now - MAX_SKEW_S >= exp:
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "credential expired")
        if exp - iat > MAX_LIFETIME_S or exp < iat:
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "credential lifetime too long")
        if claims.get("aud") != self.audience:
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "wrong audience")
        if claims.get("env") != self.environment or claims.get("site") != self.site:
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "wrong environment/site")
        return claims, key

    def authenticate(self, token: str) -> Principal:
        claims, key = self._decode(token, "caller")
        caps = claims.get("caps")
        if not isinstance(caps, list) or len(caps) > 64:
            raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "bad capability claim")
        bg = claims.get("bg") is True
        if bg:
            if not isinstance(claims.get("bg_reason"), str) or len(claims["bg_reason"].strip()) < 10:
                raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "break-glass requires a reason")
            if float(claims["exp"]) - float(claims["iat"]) > MAX_BREAKGLASS_S:
                raise SnapshotServiceError("SNAP_UNAUTHENTICATED", "break-glass lifetime too long")
        return Principal(str(claims.get("sub"))[:128], tuple(c for c in caps if isinstance(c, dict)), bg,
                         claims.get("bg_reason") if bg else None, key.kid, str(claims.get("jti", ""))[:64])

    def verify_grant(self, token: str) -> dict:
        claims, _key = self._decode(token, "grant-issuer")
        need = ("op", "snapshot_id", "manifest_sha256", "tenant", "workload", "environment", "node",
                "target_vm_id", "action", "generation", "nonce")
        if any(k not in claims for k in need) or claims["action"] != "restore":
            raise SnapshotServiceError("SNAP_GRANT_INVALID", "grant missing fields or wrong action")
        return claims


def _scope_ok(cap: dict, tenant: str | None, workload: str | None, environment: str | None) -> bool:
    for k, v in (("tenant", tenant), ("workload", workload), ("environment", environment)):
        allowed = cap.get(k)
        if allowed == "*":
            if cap.get("cap") != "snapshot.admin":
                return False  # wildcards are admin-only
            continue
        if v is not None and allowed != v:
            return False
    return True


def authorize(p: Principal, capability: str, *, tenant: str | None, workload: str | None = None,
              environment: str | None = None) -> dict:
    """Deny-by-default check; returns the matching capability grant."""
    if capability not in CAPABILITIES:
        raise SnapshotServiceError("SNAP_FORBIDDEN", "unknown capability")
    for cap in p.caps:
        if cap.get("cap") == capability and _scope_ok(cap, tenant, workload, environment):
            return cap
    if p.breakglass and capability != "snapshot.admin":
        for cap in p.caps:
            if cap.get("cap") == "snapshot.admin" and _scope_ok(cap, tenant, workload, environment):
                return cap
    raise SnapshotServiceError("SNAP_FORBIDDEN", f"{p.subject} lacks {capability} for requested scope")


def new_nonce() -> str:
    return secrets.token_hex(16)
