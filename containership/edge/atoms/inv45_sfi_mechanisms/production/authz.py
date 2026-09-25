"""Boundary authentication and capability authorization (C023, C024, C042).

* Every privileged call presents a bearer **identity token** minted by the
  configured identity provider (HMAC-SHA256 over canonical claims, key held by
  reference).  Tokens carry subject, principal kind (``human`` | ``service``),
  tenant, capabilities, expiry and a nonce.  No token => ``SFI_UNAUTHENTICATED``.
* Authorization is **deny-by-default** and purely capability-based: there is no
  role or name check anywhere.  A grant may be scoped to a tenant and/or an exact
  artifact digest; the check binds operation + tenant + digest.
* One-time **load authorizations** are consumed through a replay cache, so a
  captured authorization cannot be replayed (``SFI_REPLAY_DETECTED``).
* High-impact actions (global disable, key revocation) require **dual
  authorization** by two distinct human principals.
"""
from __future__ import annotations

import hmac
import secrets as _secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .errors import SfiError
from .sfi import canonical_json
from .trust import SecretRef

CAPABILITIES = frozenset({
    "sfi.submit",          # submit an artifact for rewrite/verification
    "sfi.verify",          # run the verifier / obtain a proof
    "sfi.load",            # trusted load of a sealed artifact
    "sfi.execute",         # invoke an export of a loaded instance
    "sfi.policy.write",    # change profile/config generations
    "sfi.quarantine",      # quarantine/freeze/disable/release
    "sfi.audit.read",      # read audit and explain views
    "sfi.keys.admin",      # rotate/revoke sealing keys and trust roots
    "sfi.release.certify", # sign release acceptance evidence
})
KINDS = frozenset({"human", "service"})
TOKEN_SCHEMA = "PK_SFI_IDENTITY/1"


@dataclass(frozen=True)
class Grant:
    capability: str
    tenant: Optional[str] = None       # None = any tenant (operator scope)
    artifact_sha256: Optional[str] = None

    def __post_init__(self) -> None:
        if self.capability not in CAPABILITIES:
            raise SfiError("SFI_CONFIG_INVALID", "unknown capability", capability=self.capability)


@dataclass(frozen=True)
class Principal:
    subject: str
    kind: str
    tenant: Optional[str]
    grants: tuple[Grant, ...]
    token_id: str


@dataclass
class IdentityProvider:
    secret: SecretRef
    issuer: str = "inv45-idp"
    clock: Callable[[], float] = time.time
    max_ttl: float = 3600.0

    def mint(self, subject: str, kind: str, tenant: Optional[str], grants: list[Grant],
             ttl: float = 600.0) -> str:
        if kind not in KINDS:
            raise SfiError("SFI_CONFIG_INVALID", "unknown principal kind", field="kind")
        if not 0 < ttl <= self.max_ttl:
            raise SfiError("SFI_CONFIG_INVALID", "token ttl out of bounds", field="ttl")
        claims = {"schema": TOKEN_SCHEMA, "iss": self.issuer, "sub": subject, "kind": kind, "tenant": tenant,
                  "grants": [[g.capability, g.tenant, g.artifact_sha256] for g in grants],
                  "exp": self.clock() + ttl, "jti": _secrets.token_hex(12)}
        body = canonical_json(claims)
        mac = hmac.new(self.secret.resolve(), body, "sha256").hexdigest()
        return body.hex() + "." + mac

    def authenticate(self, token: Any) -> Principal:
        if not isinstance(token, str) or token.count(".") != 1 or len(token) > 16384:
            raise SfiError("SFI_UNAUTHENTICATED", "missing or malformed identity token")
        body_hex, mac = token.split(".")
        try:
            body = bytes.fromhex(body_hex)
        except ValueError:
            raise SfiError("SFI_UNAUTHENTICATED", "malformed identity token") from None
        expect = hmac.new(self.secret.resolve(), body, "sha256").hexdigest()
        if not hmac.compare_digest(expect, mac):
            raise SfiError("SFI_UNAUTHENTICATED", "identity token signature invalid")
        import json
        claims = json.loads(body)
        if claims.get("schema") != TOKEN_SCHEMA or claims.get("iss") != self.issuer:
            raise SfiError("SFI_UNAUTHENTICATED", "identity token issuer/schema not accepted")
        if self.clock() > claims["exp"]:
            raise SfiError("SFI_UNAUTHENTICATED", "identity token expired")
        grants = tuple(Grant(c, t, d) for c, t, d in claims["grants"])
        return Principal(claims["sub"], claims["kind"], claims["tenant"], grants, claims["jti"])


class Authorizer:
    """Deny-by-default capability evaluation with audit hook."""

    def __init__(self, audit: Optional[Callable[[dict[str, Any]], None]] = None):
        self._audit = audit

    def check(self, principal: Optional[Principal], capability: str, *, tenant: Optional[str] = None,
              artifact_sha256: Optional[str] = None) -> None:
        allowed = False
        if principal is not None and capability in CAPABILITIES:
            # a tenant-bound principal can never act for another tenant (confused deputy)
            if principal.tenant is None or tenant is None or principal.tenant == tenant:
                for g in principal.grants:
                    if (g.capability == capability
                            and (g.tenant is None or g.tenant == tenant)
                            and (g.artifact_sha256 is None or g.artifact_sha256 == artifact_sha256)):
                        allowed = True
                        break
        if self._audit:
            self._audit({"event": "authz.decision", "capability": capability, "tenant": tenant,
                         "artifact_sha256": artifact_sha256, "allowed": allowed,
                         "subject": principal.subject if principal else None})
        if principal is None:
            raise SfiError("SFI_UNAUTHENTICATED", "no authenticated principal", capability=capability)
        if not allowed:
            raise SfiError("SFI_UNAUTHORIZED", "capability not granted for this context",
                           capability=capability, tenant=tenant)

    def check_dual(self, a: Principal, b: Principal, capability: str) -> None:
        self.check(a, capability)
        self.check(b, capability)
        if a.subject == b.subject or a.kind != "human" or b.kind != "human":
            raise SfiError("SFI_DUAL_AUTH_REQUIRED", "two distinct human principals are required",
                           capability=capability)


class ReplayCache:
    """Bounded one-time-use nonce set (thread-safe).

    Entries are kept until their own expiry, so a nonce can never be forgotten
    while the thing it protects is still valid.  When the cache is full of
    unexpired entries it fails closed with ``SFI_OVERLOADED`` rather than evicting.
    """

    def __init__(self, capacity: int = 100_000, clock: Callable[[], float] = time.time):
        self._seen: dict[str, float] = {}
        self._cap = capacity
        self._clock = clock
        self._lock = threading.Lock()

    def consume(self, nonce: str, expires_at: float) -> None:
        with self._lock:
            now = self._clock()
            if nonce in self._seen:
                raise SfiError("SFI_REPLAY_DETECTED", "nonce already used")
            if len(self._seen) >= self._cap:
                for k in [k for k, exp in self._seen.items() if exp < now]:
                    del self._seen[k]
                if len(self._seen) >= self._cap:
                    raise SfiError("SFI_OVERLOADED", "replay cache full of unexpired nonces",
                                   limit=self._cap)
            self._seen[nonce] = expires_at

    def __len__(self) -> int:
        return len(self._seen)
