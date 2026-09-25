"""G13-MC-009 secure administrative authorization boundary.

Authentication: compact HMAC-SHA256 tokens (``PK_POLICY_TOKEN/1``) issued by the
identity subsystem (EXT-03).  Validation covers signature, issuer, audience,
expiry/not-before, nonce replay and revocation.  Authorization: one capability
per privileged operation, scoped by environment/site/tenant, deny by default.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from .errors import DependencyUnavailable, Unauthenticated, Unauthorized


class Capability(str, Enum):
    EVALUATE = "policy.evaluate"
    EXPLAIN = "policy.explain"
    EXPLAIN_DETAILED = "policy.explain.detailed"
    STATUS = "policy.status"
    BUNDLE_STAGE = "policy.bundle.stage"
    BUNDLE_ACTIVATE = "policy.bundle.activate"
    BUNDLE_ROLLBACK = "policy.bundle.rollback"
    CONTROL_FREEZE = "policy.control.freeze"
    CONTROL_DENY_ONLY = "policy.control.deny_only"
    CONTROL_DISABLE = "policy.control.disable"
    CONTROL_QUARANTINE = "policy.control.quarantine"
    CONTROL_CLEAR = "policy.control.clear"
    CONFIG_CHANGE = "policy.config.change"
    EVIDENCE_EXPORT = "policy.evidence.export"
    AUDIT_READ = "policy.audit.read"
    TRUST_ADMIN = "policy.trust.admin"


C = Capability
ROLES: dict[str, frozenset[Capability]] = {
    "service": frozenset({C.EVALUATE, C.EXPLAIN, C.STATUS}),
    "viewer": frozenset({C.STATUS, C.EXPLAIN}),
    "operator": frozenset({C.STATUS, C.EXPLAIN, C.EXPLAIN_DETAILED, C.CONTROL_FREEZE, C.CONTROL_DENY_ONLY,
                           C.EVIDENCE_EXPORT, C.AUDIT_READ}),
    "policy_admin": frozenset({C.STATUS, C.BUNDLE_STAGE, C.BUNDLE_ACTIVATE, C.BUNDLE_ROLLBACK, C.CONFIG_CHANGE}),
    "security": frozenset({C.STATUS, C.CONTROL_QUARANTINE, C.CONTROL_DISABLE, C.CONTROL_CLEAR,
                           C.CONTROL_FREEZE, C.CONTROL_DENY_ONLY, C.AUDIT_READ, C.EXPLAIN_DETAILED}),
    "trust_admin": frozenset({C.STATUS, C.TRUST_ADMIN}),
}
#: service identities may never hold these, whatever the token says
HUMAN_ONLY = frozenset(set(Capability) - ROLES["service"])
#: step-up (fresh auth <= 300 s and ``mfa``) required
HIGH_IMPACT = frozenset({C.BUNDLE_ACTIVATE, C.BUNDLE_ROLLBACK, C.CONTROL_DISABLE, C.CONTROL_CLEAR,
                         C.TRUST_ADMIN, C.CONFIG_CHANGE})


@dataclass(frozen=True)
class Principal:
    subject: str
    kind: str                       # "human" | "service" | "breakglass"
    roles: frozenset[str]
    environments: frozenset[str]
    sites: frozenset[str] = frozenset({"*"})
    tenants: frozenset[str] = frozenset({"*"})
    auth_time: int = 0
    mfa: bool = False
    token_id: str = ""

    @property
    def capabilities(self) -> frozenset[Capability]:
        caps: set[Capability] = set()
        for r in self.roles:
            caps |= ROLES.get(r, frozenset())
        if self.kind == "service":
            caps -= HUMAN_ONLY
        return frozenset(caps)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue_token(key: bytes, claims: Mapping[str, Any]) -> str:
    """Test/IdP helper.  Runtime only *verifies* tokens."""
    body = _b64(json.dumps(dict(claims), sort_keys=True, separators=(",", ":")).encode())
    mac = _b64(hmac.new(key, b"PK_POLICY_TOKEN/1." + body.encode(), hashlib.sha256).digest())
    return f"{body}.{mac}"


class TokenAuthenticator:
    def __init__(self, keys: Mapping[str, bytes], *, issuer: str, audience: str, clock=time.time,
                 max_lifetime: int = 3600) -> None:
        self.keys = dict(keys)
        self.issuer = issuer
        self.audience = audience
        self.clock = clock
        self.max_lifetime = max_lifetime
        self.revoked: set[str] = set()
        self._nonces: dict[str, int] = {}
        self._lock = threading.Lock()
        self.available = True

    def authenticate(self, token: str) -> Principal:
        if not self.available:
            raise DependencyUnavailable("identity dependency unavailable; denying")
        if not isinstance(token, str) or token.count(".") != 1 or len(token) > 8192:
            raise Unauthenticated("malformed token")
        body, mac = token.split(".")
        try:
            claims = json.loads(_unb64(body))
            got = _unb64(mac)
        except Exception as exc:
            raise Unauthenticated("malformed token") from exc
        kid = claims.get("kid") if isinstance(claims, dict) else None
        key = self.keys.get(kid) if isinstance(kid, str) else None
        if key is None:
            raise Unauthenticated("unknown token key")
        want = hmac.new(key, b"PK_POLICY_TOKEN/1." + body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(want, got):
            raise Unauthenticated("bad token signature")
        now = int(self.clock())
        if claims.get("iss") != self.issuer:
            raise Unauthenticated("wrong issuer")
        if claims.get("aud") != self.audience:
            raise Unauthenticated("wrong audience")
        exp, nbf, iat = claims.get("exp"), claims.get("nbf", 0), claims.get("iat", 0)
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in (exp, nbf, iat)):
            raise Unauthenticated("bad time claims")
        if now >= exp or now < nbf or exp - iat > self.max_lifetime:
            raise Unauthenticated("token expired/not yet valid/over-long")
        jti = claims.get("jti")
        if not isinstance(jti, str) or not jti:
            raise Unauthenticated("missing jti")
        if jti in self.revoked:
            raise Unauthenticated("token revoked")
        with self._lock:
            for n, e in list(self._nonces.items()):
                if e <= now:
                    del self._nonces[n]
            if jti in self._nonces:
                raise Unauthenticated("token replay")
            self._nonces[jti] = exp
        kind = claims.get("kind", "human")
        if kind not in ("human", "service", "breakglass"):
            raise Unauthenticated("bad principal kind")
        return Principal(str(claims.get("sub", "")), kind, frozenset(claims.get("roles", [])),
                         frozenset(claims.get("env", [])), frozenset(claims.get("sites", ["*"])),
                         frozenset(claims.get("tenants", ["*"])), int(claims.get("auth_time", iat)),
                         bool(claims.get("mfa", False)), jti)


class RateLimiter:
    def __init__(self, rate_per_minute: int = 30, clock=time.time) -> None:
        self.rate = rate_per_minute
        self.clock = clock
        self._b: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        with self._lock:
            now = self.clock()
            tokens, last = self._b.get(key, (float(self.rate), now))
            tokens = min(self.rate, tokens + (now - last) * self.rate / 60.0)
            if tokens < 1:
                self._b[key] = (tokens, now)
                return False
            self._b[key] = (tokens - 1, now)
            return True


@dataclass
class Authorizer:
    environment: str
    site: str = "default"
    clock: Any = time.time
    limiter: RateLimiter = field(default_factory=RateLimiter)
    denials: int = 0

    def require(self, principal: Principal | None, cap: Capability, *, tenant: str | None = None) -> None:
        if principal is None:
            self.denials += 1
            raise Unauthorized(f"{cap.value}: no principal")
        if cap not in principal.capabilities:
            self.denials += 1
            raise Unauthorized(f"{cap.value}: capability not granted", details={"subject": principal.subject})
        if self.environment not in principal.environments:
            self.denials += 1
            raise Unauthorized(f"{cap.value}: environment out of scope")
        if "*" not in principal.sites and self.site not in principal.sites:
            self.denials += 1
            raise Unauthorized(f"{cap.value}: site out of scope")
        if tenant is not None and "*" not in principal.tenants and tenant not in principal.tenants:
            self.denials += 1
            raise Unauthorized(f"{cap.value}: tenant out of scope")
        if cap in HIGH_IMPACT and principal.kind != "breakglass":
            if not principal.mfa or self.clock() - principal.auth_time > 300:
                self.denials += 1
                raise Unauthorized(f"{cap.value}: step-up authentication required")
        if cap not in ROLES["service"] and not self.limiter.allow(principal.subject):
            self.denials += 1
            raise Unauthorized(f"{cap.value}: privileged rate limit exceeded")
