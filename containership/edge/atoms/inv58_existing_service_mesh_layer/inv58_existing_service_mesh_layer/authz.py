"""Boundary authentication and deny-by-default capability authorization.

Covers MC-005 (INV-58-C023/C024), MC-011 least privilege (C042), MC-012 actor
authentication (C044) and the tenant-scope part of MC-013 (C046).

* Every public operation is listed in :data:`BOUNDARY_MATRIX` with its required
  capability, permitted actor types, accepted authentication mechanisms and
  whether it is tenant scoped.  Operations absent from the matrix are denied.
* Principals are produced only by :class:`Authenticator` — from a strict SPIFFE
  SAN presented by the mesh (workloads, controllers, nodes) or from a signed,
  short-lived, audience-bound, single-use operator/CI token.
* Authorization is capability based.  Roles are just named capability sets
  from a versioned policy; wildcard capabilities do not exist, and the
  ``break_glass`` capability is only honoured while explicitly armed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable, Mapping

from .mesh_logic import Unmappable, map_identity

ACTOR_TYPES = ("workload", "controller", "node", "operator", "ci", "auditor")
AUTH_MECHANISMS = ("mtls_spiffe", "signed_token")

CAPABILITIES = frozenset({
    "status.read", "reconcile.evaluate", "route.read", "route.migrate",
    "identity.map", "bypass.report", "bypass.read", "config.validate",
    "config.activate", "config.rollback", "audit.read", "audit.export",
    "control.freeze", "control.quarantine", "control.break_glass", "state.restore",
    "artifact.verify",
})

# operation -> (capability, allowed actor types, mechanisms, tenant_scoped)
BOUNDARY_MATRIX: dict[str, tuple[str, frozenset, frozenset, bool]] = {
    "status":        ("status.read", frozenset({"operator", "controller", "node", "auditor", "ci"}), frozenset(AUTH_MECHANISMS), False),
    "reconcile":     ("reconcile.evaluate", frozenset({"controller", "operator", "ci"}), frozenset(AUTH_MECHANISMS), True),
    "route.read":    ("route.read", frozenset({"controller", "operator", "auditor"}), frozenset(AUTH_MECHANISMS), True),
    "route.migrate": ("route.migrate", frozenset({"controller", "operator"}), frozenset(AUTH_MECHANISMS), True),
    "identity":      ("identity.map", frozenset({"node", "controller"}), frozenset({"mtls_spiffe"}), True),
    "bypass":        ("bypass.report", frozenset({"node", "controller"}), frozenset({"mtls_spiffe"}), True),
    "bypass.read":   ("bypass.read", frozenset({"operator", "auditor", "controller"}), frozenset(AUTH_MECHANISMS), True),
    "config.validate": ("config.validate", frozenset({"operator", "ci"}), frozenset({"signed_token"}), False),
    "config.activate": ("config.activate", frozenset({"operator", "ci"}), frozenset({"signed_token"}), False),
    "config.rollback": ("config.rollback", frozenset({"operator"}), frozenset({"signed_token"}), False),
    "audit.read":    ("audit.read", frozenset({"auditor", "operator"}), frozenset({"signed_token"}), False),
    "audit.export":  ("audit.export", frozenset({"auditor"}), frozenset({"signed_token"}), False),
    "control.freeze": ("control.freeze", frozenset({"operator"}), frozenset({"signed_token"}), False),
    "control.quarantine": ("control.quarantine", frozenset({"operator"}), frozenset({"signed_token"}), True),
    "control.break_glass": ("control.break_glass", frozenset({"operator"}), frozenset({"signed_token"}), False),
    "state.restore": ("state.restore", frozenset({"operator"}), frozenset({"signed_token"}), False),
    "artifact.verify": ("artifact.verify", frozenset({"ci", "operator", "controller"}), frozenset(AUTH_MECHANISMS), False),
}

# Stable decision codes (audit + metrics safe).
ALLOW = "ALLOW"
DENY_CODES = (
    "DENY_UNAUTHENTICATED", "DENY_EXPIRED", "DENY_NOT_YET_VALID", "DENY_REPLAY", "DENY_BAD_SIGNATURE",
    "DENY_AUDIENCE", "DENY_AMBIGUOUS_IDENTITY", "DENY_UNKNOWN_OPERATION", "DENY_ACTOR_TYPE",
    "DENY_MECHANISM", "DENY_UNKNOWN_ROLE", "DENY_NO_CAPABILITY", "DENY_TENANT_SCOPE",
    "DENY_STALE_POLICY", "DENY_TRUST_UNAVAILABLE", "DENY_BREAK_GLASS_NOT_ARMED",
)

DEFAULT_MAX_TOKEN_TTL = 900
DEFAULT_CLOCK_SKEW = 30
DEFAULT_REPLAY_CACHE = 65_536


@dataclass(frozen=True)
class Principal:
    subject: str
    actor_type: str
    tenant: str | None          # None = platform-scope actor (never implies all tenants)
    roles: frozenset
    mechanism: str
    tenants: frozenset = frozenset()  # explicit extra tenant grants for platform actors

    def may_access_tenant(self, tenant: str | None) -> bool:
        if tenant is None:
            return True
        return tenant == self.tenant or tenant in self.tenants


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str
    operation: str
    capability: str | None
    policy_version: str

    def __bool__(self) -> bool:
        return self.allowed


@dataclass
class CapabilityPolicy:
    """Versioned role→capability policy.  Immutable once constructed."""

    version: str
    roles: Mapping[str, frozenset]
    issued_at: float
    max_age_s: float = 86_400.0

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("policy version required")
        frozen = {}
        for role, caps in dict(self.roles).items():
            caps = frozenset(caps)
            unknown = caps - CAPABILITIES
            if unknown:
                raise ValueError(f"role {role!r} grants unknown capabilities {sorted(unknown)}")
            if any("*" in c for c in caps):
                raise ValueError("wildcard capabilities are not permitted")
            frozen[role] = caps
        self.roles = frozen

    def is_stale(self, now: float) -> bool:
        return now - self.issued_at > self.max_age_s


DEFAULT_ROLES = {
    "mesh-node": {"identity.map", "bypass.report"},
    "mesh-controller": {"status.read", "reconcile.evaluate", "route.read", "route.migrate", "bypass.read", "artifact.verify"},
    "mesh-observer": {"status.read", "route.read", "bypass.read"},
    "config-publisher": {"config.validate", "config.activate", "artifact.verify"},
    "mesh-operator": {"status.read", "route.read", "bypass.read", "config.validate", "config.rollback",
                      "control.freeze", "control.quarantine", "state.restore"},
    "security-auditor": {"status.read", "audit.read", "audit.export", "bypass.read", "route.read"},
    "break-glass": {"control.break_glass"},
}


class Authenticator:
    """Turns presented credentials into Principals, failing closed."""

    def __init__(self, *, trust_domain: str, token_key: Callable[[], bytes], audience: str = "inv58",
                 spiffe_bindings: Mapping[str, tuple] | None = None,
                 clock: Callable[[], float] = time.time, max_token_ttl: int = DEFAULT_MAX_TOKEN_TTL,
                 clock_skew: int = DEFAULT_CLOCK_SKEW, replay_cache_size: int = DEFAULT_REPLAY_CACHE):
        self.trust_domain = trust_domain
        self._token_key = token_key
        self.audience = audience
        # runtime identity -> (actor_type, roles)
        self._bindings = {k: (v[0], frozenset(v[1]), frozenset(v[2]) if len(v) > 2 else frozenset())
                          for k, v in (spiffe_bindings or {}).items()}
        self.clock = clock
        self.max_token_ttl = max_token_ttl
        self.clock_skew = clock_skew
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._max_seen = replay_cache_size
        self._lock = RLock()

    # -- mesh-presented workload / node / controller identity -------------
    def from_spiffe(self, san: str) -> Principal | str:
        try:
            runtime = map_identity(san, self.trust_domain)
        except Unmappable:
            return "DENY_AMBIGUOUS_IDENTITY"
        binding = self._bindings.get(runtime)
        segs = runtime[len("runtime:"):].split("/")
        tenant = segs[1] if len(segs) >= 2 and segs[0] == "ns" else None
        if binding is None:
            # Unbound workloads are authenticated but hold no roles.
            return Principal(runtime, "workload", tenant, frozenset(), "mtls_spiffe")
        actor_type, roles, tenants = binding
        return Principal(runtime, actor_type, tenant, roles, "mtls_spiffe", tenants)

    # -- signed operator / CI / auditor token -----------------------------
    @staticmethod
    def mint(key: bytes, claims: dict) -> str:
        """Test/ops helper: produce ``b64(claims).b64(hmac)``."""
        body = base64.urlsafe_b64encode(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()).rstrip(b"=")
        sig = base64.urlsafe_b64encode(hmac.new(key, body, hashlib.sha256).digest()).rstrip(b"=")
        return (body + b"." + sig).decode()

    def from_token(self, token: str) -> Principal | str:
        if not isinstance(token, str) or len(token) > 4096 or token.count(".") != 1:
            return "DENY_UNAUTHENTICATED"
        try:
            key = self._token_key()
        except Exception:
            return "DENY_TRUST_UNAVAILABLE"
        body, sig = token.encode().split(b".")
        expect = base64.urlsafe_b64encode(hmac.new(key, body, hashlib.sha256).digest()).rstrip(b"=")
        if not hmac.compare_digest(sig, expect):
            return "DENY_BAD_SIGNATURE"
        try:
            claims = json.loads(base64.urlsafe_b64decode(body + b"=" * (-len(body) % 4)))
            sub, typ, aud = claims["sub"], claims["typ"], claims["aud"]
            iat, exp, nonce = int(claims["iat"]), int(claims["exp"]), str(claims["nonce"])
            roles = frozenset(claims.get("roles", ()))
            tenant = claims.get("tenant")
            tenants = frozenset(claims.get("tenants", ()))
        except Exception:
            return "DENY_UNAUTHENTICATED"
        if typ not in ACTOR_TYPES or typ in ("workload", "node") or not isinstance(sub, str) or not sub:
            return "DENY_UNAUTHENTICATED"
        if aud != self.audience:
            return "DENY_AUDIENCE"
        now = self.clock()
        if exp - iat > self.max_token_ttl or exp <= iat:
            return "DENY_UNAUTHENTICATED"
        if iat - self.clock_skew > now:
            return "DENY_NOT_YET_VALID"
        if now >= exp + self.clock_skew:
            return "DENY_EXPIRED"
        with self._lock:
            # evict expired nonces, then bound
            while self._seen and next(iter(self._seen.values())) < now - self.clock_skew:
                self._seen.popitem(last=False)
            if nonce in self._seen:
                return "DENY_REPLAY"
            if len(self._seen) >= self._max_seen:
                return "DENY_TRUST_UNAVAILABLE"  # replay protection saturated: fail closed
            self._seen[nonce] = exp
        return Principal(sub, typ, tenant, roles, "signed_token", tenants)


class Authorizer:
    def __init__(self, policy: CapabilityPolicy, clock: Callable[[], float] = time.time):
        self._policy = policy
        self.clock = clock
        self._break_glass_until = 0.0
        self._lock = RLock()

    @property
    def policy(self) -> CapabilityPolicy:
        return self._policy

    def replace_policy(self, policy: CapabilityPolicy) -> None:
        with self._lock:
            self._policy = policy

    def arm_break_glass(self, seconds: float) -> None:
        if not 0 < seconds <= 3600:
            raise ValueError("break-glass window must be within (0, 3600] seconds")
        with self._lock:
            self._break_glass_until = self.clock() + seconds

    def disarm_break_glass(self) -> None:
        with self._lock:
            self._break_glass_until = 0.0

    def authorize(self, principal: Principal | str | None, operation: str, tenant: str | None = None) -> Decision:
        with self._lock:
            policy = self._policy
            bg_until = self._break_glass_until
        pv = policy.version

        def deny(code, cap=None):
            return Decision(False, code, operation, cap, pv)

        spec = BOUNDARY_MATRIX.get(operation)
        if spec is None:
            return deny("DENY_UNKNOWN_OPERATION")
        cap, actor_types, mechanisms, scoped = spec
        if isinstance(principal, str):
            return deny(principal if principal in DENY_CODES else "DENY_UNAUTHENTICATED", cap)
        if not isinstance(principal, Principal):
            return deny("DENY_UNAUTHENTICATED", cap)
        now = self.clock()
        if policy.is_stale(now):
            return deny("DENY_STALE_POLICY", cap)
        if principal.mechanism not in mechanisms:
            return deny("DENY_MECHANISM", cap)
        if principal.actor_type not in actor_types:
            return deny("DENY_ACTOR_TYPE", cap)
        granted: set = set()
        for role in principal.roles:
            if role not in policy.roles:
                return deny("DENY_UNKNOWN_ROLE", cap)
            granted |= policy.roles[role]
        if cap not in granted:
            return deny("DENY_NO_CAPABILITY", cap)
        if cap == "control.break_glass" and now >= bg_until:
            return deny("DENY_BREAK_GLASS_NOT_ARMED", cap)
        if scoped:
            if tenant is None or not principal.may_access_tenant(tenant):
                return deny("DENY_TENANT_SCOPE", cap)
        return Decision(True, ALLOW, operation, cap, pv)


def privilege_inventory() -> list[dict]:
    """Machine-readable least-privilege inventory (C042)."""
    rows = []
    for role, caps in sorted(DEFAULT_ROLES.items()):
        ops = sorted(op for op, spec in BOUNDARY_MATRIX.items() if spec[0] in caps)
        rows.append({"role": role, "capabilities": sorted(caps), "operations": ops})
    return rows
