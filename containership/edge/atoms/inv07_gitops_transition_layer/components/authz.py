"""Authentication and authorization boundary (component 10).

Authentication
  ``TokenAuthority`` issues/verifies compact Ed25519-signed bearer tokens
  (``PKT1.<b64 claims>.<b64 sig>``) with ``sub``, ``tenant``, ``roles``,
  ``aud``, ``iat``/``exp`` and ``jti``.  Verification refuses unknown key ids,
  wrong audience, expired/not-yet-valid tokens, revoked ``jti`` and a lifetime
  over ``max_ttl`` (short-lived credentials).  A production IdP/OIDC issuer
  is an adapter slot: its JWKS would be loaded as the same key set.

Authorization (RBAC + ABAC + capability)
  roles map to capabilities (``ROLES``); every decision additionally checks the
  subject's tenant equals the resource tenant (ABAC) and privileged
  capabilities (``freeze.override``, ``trust.rotate``, ``rollback.exception``)
  require a *second, distinct* approver token (two-person rule).  Every
  decision -- allow or deny -- is returned as a record and written to the
  audit ledger when one is attached.
"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass

from . import ed25519
from .errors import Unauthenticated, Unauthorized

ROLES = {
    "viewer": {"status.read", "explain.read", "metrics.read"},
    "operator": {"status.read", "explain.read", "metrics.read", "sync.trigger", "freeze.set", "freeze.release"},
    "admin": {"status.read", "explain.read", "metrics.read", "sync.trigger", "freeze.set", "freeze.release",
              "config.reload", "backup.run", "restore.run", "freeze.override", "trust.rotate",
              "rollback.exception"},
    "controller": {"sync.run", "status.read", "metrics.read"},
}
PRIVILEGED = {"freeze.override", "trust.rotate", "rollback.exception", "restore.run"}


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@dataclass(frozen=True)
class Principal:
    sub: str
    tenant: str
    roles: tuple[str, ...]
    jti: str

    def capabilities(self) -> set[str]:
        caps: set[str] = set()
        for r in self.roles:
            caps |= ROLES.get(r, set())
        return caps


class TokenAuthority:
    def __init__(self, keys: dict[str, bytes], *, audience: str, max_ttl: int = 3600,
                 clock=time.time) -> None:
        self.keys, self.aud, self.max_ttl, self.clock = dict(keys), audience, max_ttl, clock
        self.revoked: set[str] = set()

    @staticmethod
    def issue(secret: bytes, kid: str, claims: dict) -> str:
        body = _b64(json.dumps({**claims, "kid": kid}, sort_keys=True, separators=(",", ":")).encode())
        sig = ed25519.sign(secret, ("PKT1." + body).encode())
        return f"PKT1.{body}.{_b64(sig)}"

    def verify(self, token: str | None) -> Principal:
        if not token or not isinstance(token, str) or len(token) > 4096:
            raise Unauthenticated("missing or oversized credential")
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != "PKT1":
            raise Unauthenticated("malformed credential")
        try:
            claims = json.loads(_unb64(parts[1]))
            sig = _unb64(parts[2])
        except (ValueError, TypeError):
            raise Unauthenticated("malformed credential") from None
        pub = self.keys.get(claims.get("kid", ""))
        if pub is None or not ed25519.verify(pub, ("PKT1." + parts[1]).encode(), sig):
            raise Unauthenticated("credential signature invalid")
        now = self.clock()
        if claims.get("aud") != self.aud:
            raise Unauthenticated("credential audience mismatch")
        iat, exp = claims.get("iat", 0), claims.get("exp", 0)
        if not (iat - 60 <= now < exp):
            raise Unauthenticated("credential expired or not yet valid")
        if exp - iat > self.max_ttl:
            raise Unauthenticated("credential lifetime exceeds max_ttl")
        if claims.get("jti") in self.revoked:
            raise Unauthenticated("credential revoked")
        roles = tuple(r for r in claims.get("roles", []) if r in ROLES)
        if not claims.get("sub") or not claims.get("tenant"):
            raise Unauthenticated("credential missing subject/tenant")
        return Principal(claims["sub"], claims["tenant"], roles, str(claims.get("jti", "")))


class Authorizer:
    def __init__(self, *, tenant: str, audit=None) -> None:
        self.tenant, self.audit = tenant, audit

    def decide(self, p: Principal, capability: str, *, tenant: str | None = None,
               approver: Principal | None = None) -> dict:
        tenant = tenant or self.tenant
        rec = {"sub": p.sub, "capability": capability, "tenant": tenant, "decision": "deny", "reason": ""}
        if p.tenant != tenant:
            rec["reason"] = "tenant scope mismatch"
        elif capability not in p.capabilities():
            rec["reason"] = "capability not granted by role"
        elif capability in PRIVILEGED and (approver is None or approver.sub == p.sub
                                           or capability not in approver.capabilities()
                                           or approver.tenant != tenant):
            rec["reason"] = "privileged capability requires a distinct authorised approver"
        else:
            rec["decision"], rec["reason"] = "allow", "granted"
            if approver:
                rec["approver"] = approver.sub
        if self.audit:
            self.audit.append("authz.decision", rec, actor=p.sub)
        return rec

    def require(self, p: Principal, capability: str, **kw) -> dict:
        rec = self.decide(p, capability, **kw)
        if rec["decision"] != "allow":
            raise Unauthorized(rec["reason"], capability=capability)
        return rec
