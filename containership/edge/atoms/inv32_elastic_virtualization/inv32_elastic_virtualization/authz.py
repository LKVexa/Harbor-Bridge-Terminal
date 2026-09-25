"""Authentication, authorization and capability enforcement (WS 4).

* Principals carry a stable ID ``<kind>:<issuer>/<subject>`` independent of display names.
* Credentials are compact HMAC-SHA256 signed tokens (``inv32tok.<b64 claims>.<b64 mac>``) with
  audience, issuer, not-before, expiry, scope and a unique ``jti``.  In production the keyring
  is fed from the key service by secret reference (config.SecretRef); keys rotate by ``kid``.
  Service-to-service transport authentication (mTLS) is a deployment concern -- see
  THREAT_MODEL.md T-S1 -- and is BLOCKED on the platform PKI decision (ADR-0004).
* Policy is deny-by-default; every decision returns a decision ID and the policy version,
  both of which the controller writes into the audit event.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable
from uuid import uuid4

from . import errors as E

ACTIONS = frozenset({
    "guest.read", "memory.adjust", "vcpu.adjust", "adjustment.revert", "audit.read", "audit.export",
    "host.read", "quarantine.set", "config.activate", "emergency.disable", "secret.read", "explain.read",
})
# Actions that need an elevated (non-tenant) principal or break-glass.
ELEVATED_ACTIONS = frozenset({"adjustment.revert", "quarantine.set", "config.activate", "emergency.disable",
                              "audit.export", "secret.read"})
PRINCIPAL_KINDS = frozenset({"node", "controller", "operator", "service", "tenant", "workload", "provider",
                             "build", "automation"})
_PRINCIPAL_RE = re.compile(r"^(?P<kind>[a-z]+):(?P<issuer>[a-z0-9.-]{1,64})/(?P<sub>[A-Za-z0-9._:-]{1,128})$")
MAX_CLOCK_SKEW_S = 30
MAX_TOKEN_TTL_S = 3600
BREAK_GLASS_MAX_TTL_S = 900
TOKEN_PREFIX = "inv32tok"


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@dataclass(frozen=True)
class Principal:
    id: str
    kind: str
    tenant: str | None = None  # tenant scope; None == not tenant-scoped
    hosts: frozenset[str] = frozenset({"*"})
    actions: frozenset[str] = frozenset()
    break_glass: bool = False
    break_glass_reason: str | None = None
    token_id: str | None = None

    def __post_init__(self) -> None:
        m = _PRINCIPAL_RE.match(self.id)
        if not m or m.group("kind") != self.kind or self.kind not in PRINCIPAL_KINDS:
            raise E.AuthenticationFailed("malformed principal identifier")
        unknown = set(self.actions) - ACTIONS
        if unknown:
            raise E.AuthenticationFailed("credential names unknown actions")


class Keyring:
    """kid -> key.  Rotation: add new kid, issue with it, retire old after max TTL."""

    def __init__(self, keys: dict[str, bytes], active_kid: str) -> None:
        if active_kid not in keys or any(len(k) < 32 for k in keys.values()):
            raise ValueError("keyring requires an active kid and >=256-bit keys")
        self._keys = dict(keys)
        self.active_kid = active_kid

    def get(self, kid: str) -> bytes | None:
        return self._keys.get(kid)

    def rotate(self, kid: str, key: bytes) -> None:
        if len(key) < 32:
            raise ValueError("key too short")
        self._keys[kid] = key
        self.active_kid = kid

    def retire(self, kid: str) -> None:
        if kid == self.active_kid:
            raise ValueError("cannot retire the active key")
        self._keys.pop(kid, None)


class Authenticator:
    def __init__(self, keyring: Keyring, *, issuer: str, audience: str, clock=time.time) -> None:
        self.keyring = keyring
        self.issuer = issuer
        self.audience = audience
        self._clock = clock
        self._revoked_jti: dict[str, float] = {}
        self._revoked_sub_before: dict[str, float] = {}  # emergency invalidation per principal
        self._lock = threading.Lock()

    # -- issuance (used by tests/bootstrap; production issuance is the identity service)
    def issue(self, principal_id: str, kind: str, *, tenant: str | None = None, hosts: Iterable[str] = ("*",),
              actions: Iterable[str] = (), ttl: int = 300, audience: str | None = None,
              break_glass_reason: str | None = None, now: float | None = None) -> str:
        now = self._clock() if now is None else now
        if break_glass_reason is not None:
            if not break_glass_reason.strip() or ttl > BREAK_GLASS_MAX_TTL_S:
                raise E.AuthorizationDenied("break-glass requires a reason and ttl <= 900s")
        if ttl > MAX_TOKEN_TTL_S:
            raise ValueError("ttl exceeds maximum credential lifetime")
        claims = {"iss": self.issuer, "aud": audience or self.audience, "sub": principal_id, "knd": kind,
                  "ten": tenant, "hst": sorted(hosts), "act": sorted(actions), "iat": int(now),
                  "nbf": int(now), "exp": int(now + ttl), "jti": uuid4().hex, "kid": self.keyring.active_kid}
        if break_glass_reason is not None:
            claims["bg"] = break_glass_reason
        body = _b64e(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
        key = self.keyring.get(self.keyring.active_kid)
        assert key is not None
        mac = hmac.new(key, body.encode(), hashlib.sha256).digest()
        return f"{TOKEN_PREFIX}.{body}.{_b64e(mac)}"

    def revoke(self, jti: str, *, until: float | None = None) -> None:
        with self._lock:
            self._revoked_jti[jti] = until or self._clock() + MAX_TOKEN_TTL_S + MAX_CLOCK_SKEW_S

    def revoke_principal(self, principal_id: str) -> None:
        with self._lock:
            self._revoked_sub_before[principal_id] = self._clock()

    def authenticate(self, token: Any) -> Principal:
        if not isinstance(token, str) or len(token) > 4096:
            raise E.AuthenticationFailed("missing or oversized credential")
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
            raise E.AuthenticationFailed("malformed credential")
        try:
            claims = json.loads(_b64d(parts[1]))
            mac = _b64d(parts[2])
        except Exception:
            raise E.AuthenticationFailed("malformed credential") from None
        if not isinstance(claims, dict):
            raise E.AuthenticationFailed("malformed credential")
        key = self.keyring.get(str(claims.get("kid")))
        if key is None or not hmac.compare_digest(mac, hmac.new(key, parts[1].encode(), hashlib.sha256).digest()):
            raise E.AuthenticationFailed("credential signature invalid")
        now = self._clock()
        if claims.get("iss") != self.issuer or claims.get("aud") != self.audience:
            raise E.AuthenticationFailed("credential audience/issuer mismatch")
        try:
            nbf, exp, iat = int(claims["nbf"]), int(claims["exp"]), int(claims["iat"])
        except (KeyError, TypeError, ValueError):
            raise E.AuthenticationFailed("malformed credential") from None
        if now + MAX_CLOCK_SKEW_S < nbf:
            raise E.AuthenticationFailed("credential not yet valid")
        if now - MAX_CLOCK_SKEW_S >= exp:
            raise E.AuthenticationFailed("credential expired")
        with self._lock:
            if claims.get("jti") in self._revoked_jti:
                raise E.AuthenticationFailed("credential revoked")
            cutoff = self._revoked_sub_before.get(str(claims.get("sub")))
            if cutoff is not None and iat <= cutoff:
                raise E.AuthenticationFailed("credential revoked")
        try:
            return Principal(
                id=str(claims["sub"]), kind=str(claims["knd"]), tenant=claims.get("ten"),
                hosts=frozenset(claims.get("hst") or ()), actions=frozenset(claims.get("act") or ()),
                break_glass="bg" in claims, break_glass_reason=claims.get("bg"), token_id=claims.get("jti"),
            )
        except TypeError:
            raise E.AuthenticationFailed("malformed credential") from None


@dataclass(frozen=True)
class Decision:
    allowed: bool
    decision_id: str
    policy_version: str
    principal: str
    action: str
    resource: dict[str, Any]
    reason: str

    def audit_fields(self) -> dict[str, Any]:
        return {"authz_decision_id": self.decision_id, "authz_policy_version": self.policy_version,
                "principal": self.principal, "action": self.action, "authz_result": "allow" if self.allowed else "deny",
                "break_glass": self.reason == "break_glass"}


@dataclass
class Policy:
    """Deny-by-default capability policy.

    A request is allowed only when (1) the credential grants the action, (2) the host is in scope,
    (3) a tenant-scoped principal only names its own tenant's guest, (4) elevated actions come from a
    non-tenant principal kind listed in ``elevated_kinds`` or from break-glass.
    """

    version: str = "policy-1"
    elevated_kinds: frozenset[str] = frozenset({"operator", "controller", "automation"})
    tenant_kinds: frozenset[str] = frozenset({"tenant", "workload"})
    available: bool = True  # decisions are never cached: revocation takes effect on the next request

    def decide(self, p: Principal, action: str, *, host: str, tenant: str | None) -> Decision:
        if not self.available:
            raise E.PolicyUnavailable("policy service unavailable; failing closed")
        did = uuid4().hex
        resource = {"host": host, "tenant": tenant}

        def deny(reason: str) -> Decision:
            return Decision(False, did, self.version, p.id, action, resource, reason)

        if action not in ACTIONS:
            return deny("unknown_action")
        if action not in p.actions:
            return deny("action_not_granted")
        if "*" not in p.hosts and host not in p.hosts:
            return deny("host_out_of_scope")
        if p.kind in self.tenant_kinds:
            if p.tenant is None or tenant is None or p.tenant != tenant:
                return deny("tenant_out_of_scope")
        if action in ELEVATED_ACTIONS:
            if p.break_glass:
                return Decision(True, did, self.version, p.id, action, resource, "break_glass")
            if p.kind not in self.elevated_kinds:
                return deny("elevation_required")
        return Decision(True, did, self.version, p.id, action, resource, "granted")


def authorize(policy: Policy, principal: Principal, action: str, *, host: str, tenant: str | None) -> Decision:
    d = policy.decide(principal, action, host=host, tenant=tenant)
    if not d.allowed:
        # Same message for "no such guest" and "not yours": no cross-tenant existence leak.
        raise E.AuthorizationDenied("not authorized", decision_id=d.decision_id, reason=d.reason)
    return d
