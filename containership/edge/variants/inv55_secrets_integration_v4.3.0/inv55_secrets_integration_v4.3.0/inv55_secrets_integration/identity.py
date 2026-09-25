"""Boundary authentication and authorization (checklist #18, #19, #39, #40, #43).

* ``Principal`` is the only identity type the service accepts; there is no ambient
  authority (no global "current user", no environment-variable fallback).
* ``HmacJwtAuthenticator`` validates compact HS256 workload tokens (issuer, audience,
  expiry, not-before, tenant claim).  Deployments using SPIFFE/mTLS or OIDC plug in
  their own ``Authenticator`` producing the same ``Principal``.
* ``PolicyEngine`` is deny-by-default and returns a ``Decision`` with a reason code
  and policy digest so every decision is explainable (checklist #76, #77).
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import fnmatch
import hashlib
import hmac
import json
import re
import threading
from typing import Callable, Iterable, Protocol

from .errors import ErrorCode, error


@dataclass(frozen=True)
class Principal:
    subject: str          # workload/application id
    tenant: str
    roles: frozenset[str] = frozenset()
    authn_method: str = "unknown"


class Authenticator(Protocol):
    def authenticate(self, credential: str) -> Principal: ...


# Tenants form the first provider-path segment, so they may not contain '/' or be '.'/'..'.
_TENANT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_SUBJECT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _b64d(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@dataclass
class HmacJwtAuthenticator:
    key: bytes
    issuer: str
    audience: str
    clock: Callable[[], float]
    leeway_s: float = 30.0
    max_token_bytes: int = 8192

    def issue(self, sub: str, tenant: str, roles: Iterable[str] = (), ttl_s: float = 300) -> str:
        """Test/bootstrap helper; production tokens come from the identity issuer."""
        now = self.clock()
        header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        body = _b64e(json.dumps({"iss": self.issuer, "aud": self.audience, "sub": sub, "tenant": tenant,
                                 "roles": sorted(roles), "iat": now, "nbf": now, "exp": now + ttl_s}).encode())
        sig = _b64e(hmac.new(self.key, f"{header}.{body}".encode(), hashlib.sha256).digest())
        return f"{header}.{body}.{sig}"

    def authenticate(self, credential: str) -> Principal:
        if not isinstance(credential, str) or len(credential) > self.max_token_bytes or credential.count(".") != 2:
            raise error(ErrorCode.UNAUTHENTICATED)
        header_b64, body_b64, sig_b64 = credential.split(".")
        try:
            header = json.loads(_b64d(header_b64))
            claims = json.loads(_b64d(body_b64))
            sig = _b64d(sig_b64)
        except (ValueError, TypeError):
            raise error(ErrorCode.UNAUTHENTICATED) from None
        if not isinstance(header, dict) or not isinstance(claims, dict) or header.get("alg") != "HS256":
            raise error(ErrorCode.UNAUTHENTICATED)  # rejects alg=none, algorithm confusion, non-object JSON
        expected = hmac.new(self.key, f"{header_b64}.{body_b64}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, sig):
            raise error(ErrorCode.UNAUTHENTICATED)
        now = self.clock()
        try:
            roles = claims.get("roles") or []
            ok = (claims["iss"] == self.issuer and claims["aud"] == self.audience
                  and float(claims["nbf"]) - self.leeway_s <= now < float(claims["exp"]) + self.leeway_s
                  and isinstance(claims["sub"], str) and _SUBJECT.fullmatch(claims["sub"]) is not None
                  and isinstance(claims["tenant"], str) and _TENANT.fullmatch(claims["tenant"]) is not None
                  and isinstance(roles, list) and len(roles) <= 16 and all(isinstance(r, str) for r in roles))
        except (KeyError, TypeError, ValueError):
            ok = False
        if not ok:
            raise error(ErrorCode.UNAUTHENTICATED)
        return Principal(claims["sub"], claims["tenant"], frozenset(roles), "jwt-hs256")


# ---------------------------------------------------------------------- authorization
@dataclass(frozen=True)
class Rule:
    tenant: str
    subject: str            # glob, e.g. "orders" or "orders-*"
    secret: str             # glob over secret names within the tenant
    actions: frozenset[str]  # resolve | use | rotate | scope | retire | revoke


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    policy_digest: str
    rule_index: int | None = None


ROLE_ACTIONS = {
    # least-privilege role catalogue (docs/security/identity-roles.md)
    "consumer": frozenset({"resolve", "use"}),
    "rotator": frozenset({"rotate"}),
    "secret-admin": frozenset({"scope", "retire", "revoke"}),
    "operator": frozenset({"freeze", "status"}),
}


@dataclass
class PolicyEngine:
    rules: list[Rule] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _digest: str | None = field(default=None, repr=False)
    _by_tenant: dict = field(default_factory=dict, repr=False)

    def _compute(self) -> None:
        canon = json.dumps([[r.tenant, r.subject, r.secret, sorted(r.actions)] for r in self.rules],
                           sort_keys=True).encode()
        self._digest = "sha256:" + hashlib.sha256(canon).hexdigest()
        idx: dict = {}
        for i, r in enumerate(self.rules):
            idx.setdefault(r.tenant, []).append((i, r))
        self._by_tenant = idx

    def digest(self) -> str:
        with self._lock:
            if self._digest is None:
                self._compute()
            return self._digest

    def replace(self, rules: Iterable[Rule]) -> str:
        """Atomic policy swap; digest and tenant index are recomputed once per change."""
        with self._lock:
            self.rules = list(rules)
            self._compute()
            return self._digest

    def decide(self, p: Principal, action: str, secret: str) -> Decision:
        with self._lock:
            if self._digest is None:
                self._compute()
            digest, rules = self._digest, self._by_tenant.get(p.tenant, ())
        role_ok = any(action in ROLE_ACTIONS.get(r, ()) for r in p.roles)
        if not role_ok:
            return Decision(False, "role_lacks_action", digest)
        for i, r in rules:
            if (action in r.actions
                    and fnmatch.fnmatchcase(p.subject, r.subject)
                    and fnmatch.fnmatchcase(secret, r.secret)):
                return Decision(True, "rule_match", digest, i)
        return Decision(False, "no_matching_rule", digest)
