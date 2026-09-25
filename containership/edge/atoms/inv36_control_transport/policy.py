"""Authorization / tenant policy layer (MC-07).

A single mandatory decision point (:meth:`Authorizer.decide`) sits between an
authenticated, decrypted, decoded :class:`~.messages.ControlMessage` and any
application handler.  Identity comes only from the handshake credential - the
tenant inside the message must be bound to it (MC-07.009) - and the decision is
default-deny with explicit-deny precedence (MC-07.005).

Policy documents are versioned, expire, cannot be rolled back to an older
version without a recovery authorization (MC-07.006/.019), and a stale/absent
policy fails closed for every operation (MC-07.007).
"""
from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .errors import ErrorCode, Inv36Error
from .messages import MESSAGE_TYPES, TYPE_NAMES

# Every operation the transport exposes, its resource, scope and side effect (MC-07.001/.025).
OPERATIONS: dict[str, dict[str, str]] = {
    "PLACEMENT": {"capability": "ctrl.placement.write", "resource": "workload", "side_effect": "schedules workload"},
    "LEASE_GRANT": {"capability": "ctrl.lease.grant", "resource": "lease", "side_effect": "grants lease"},
    "LEASE_RENEW": {"capability": "ctrl.lease.renew", "resource": "lease", "side_effect": "extends lease"},
    "LEASE_REVOKE": {"capability": "ctrl.lease.revoke", "resource": "lease", "side_effect": "revokes lease"},
    "HEARTBEAT": {"capability": "ctrl.heartbeat", "resource": "session", "side_effect": "none (liveness)"},
    "DRAIN": {"capability": "ctrl.drain", "resource": "node", "side_effect": "drains node workloads"},
    "STATUS_QUERY": {"capability": "ctrl.status.read", "resource": "status", "side_effect": "none (read)"},
    "ERROR_REPORT": {"capability": "ctrl.error.report", "resource": "session", "side_effect": "none (report)"},
}
if set(OPERATIONS) != set(MESSAGE_TYPES):  # pragma: no cover - registry/policy drift guard
    raise ImportError("every registered message type needs an authorization mapping")

PRINCIPAL_ROLES = ("host_agent", "guest_agent", "node", "service", "operator", "relay")
BREAK_GLASS = "ctrl.break_glass"
WILDCARD = "*"


class AuthzError(Inv36Error, PermissionError):
    code = ErrorCode.AUTHZ_DENIED


class Effect(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str
    tenant: str

    @classmethod
    def from_credential(cls, cred) -> "Principal":
        return cls(cred.subject, cred.role, cred.tenant)


@dataclass(frozen=True)
class Rule:
    effect: Effect
    roles: frozenset[str]
    capabilities: frozenset[str]
    tenants: frozenset[str] = frozenset({"$self"})  # "$self" = the principal's own tenant
    subjects: frozenset[str] = frozenset()
    approved_by: str = ""   # required for wildcard / admin capabilities (MC-07.026)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Rule":
        allowed_keys = {"effect", "roles", "capabilities", "tenants", "subjects", "approved_by"}
        if set(d) - allowed_keys:
            raise AuthzError("unknown policy rule field", code=ErrorCode.CONFIG_INVALID)
        rule = cls(Effect(d["effect"]), frozenset(d["roles"]), frozenset(d["capabilities"]),
                   frozenset(d.get("tenants", ["$self"])), frozenset(d.get("subjects", [])),
                   str(d.get("approved_by", "")))
        known_caps = {o["capability"] for o in OPERATIONS.values()} | {BREAK_GLASS, WILDCARD}
        if not rule.roles <= set(PRINCIPAL_ROLES) or not rule.capabilities <= known_caps:
            raise AuthzError("rule names unknown role or capability", code=ErrorCode.CONFIG_INVALID)
        broad = WILDCARD in rule.capabilities or BREAK_GLASS in rule.capabilities or WILDCARD in rule.tenants
        if broad and rule.effect is Effect.ALLOW and not rule.approved_by:
            raise AuthzError("wildcard/admin allow requires security-owner approval", code=ErrorCode.CONFIG_INVALID)
        return rule


@dataclass(frozen=True)
class PolicyDocument:
    version: int
    issued_at: float
    expires_at: float
    rules: tuple[Rule, ...]

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "PolicyDocument":
        if set(d) - {"version", "issued_at", "expires_at", "rules"}:
            raise AuthzError("unknown policy field", code=ErrorCode.CONFIG_INVALID)
        v = int(d["version"])
        if v < 1 or float(d["expires_at"]) <= float(d["issued_at"]):
            raise AuthzError("invalid policy version or validity", code=ErrorCode.CONFIG_INVALID)
        return cls(v, float(d["issued_at"]), float(d["expires_at"]), tuple(Rule.from_dict(r) for r in d["rules"]))


@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str
    policy_version: int
    capability: str
    operation: str

    def to_dict(self) -> dict:
        return {"allow": self.allow, "reason": self.reason, "policy_version": self.policy_version,
                "capability": self.capability, "operation": self.operation}


class TokenBucket:
    def __init__(self, rate_per_s: float, burst: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.rate, self.burst, self.clock = rate_per_s, burst, clock
        self.tokens = float(burst)
        self.t = clock()

    def take(self) -> bool:
        now = self.clock()
        self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate)
        self.t = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class PolicyStore:
    """Holds the active policy; enforces monotonic versions and expiry."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self.clock = clock
        self._doc: PolicyDocument | None = None
        self._lock = threading.Lock()
        self.highest_version = 0
        self.listeners: list[Callable[[str, dict], None]] = []

    def _emit(self, ev: str, **data) -> None:
        for fn in list(self.listeners):
            fn(ev, data)

    def load(self, doc: PolicyDocument | Mapping[str, Any], *, recovery_authorization: str | None = None) -> None:
        d = doc if isinstance(doc, PolicyDocument) else PolicyDocument.from_dict(doc)
        with self._lock:
            if d.version <= self.highest_version and not recovery_authorization:
                self._emit("policy.rollback_denied", version=d.version, highest=self.highest_version)
                raise AuthzError("policy version rollback refused", code=ErrorCode.AUTHZ_POLICY_ROLLBACK)
            self._doc = d
            self.highest_version = max(self.highest_version, d.version)
        self._emit("policy.activate", version=d.version, recovery=bool(recovery_authorization))

    def current(self) -> PolicyDocument:
        with self._lock:
            d = self._doc
        if d is None:
            raise AuthzError("no policy loaded", code=ErrorCode.AUTHZ_POLICY_UNAVAILABLE)
        if self.clock() >= d.expires_at:
            raise AuthzError("policy expired", code=ErrorCode.AUTHZ_POLICY_UNAVAILABLE,
                             detail={"policy_version": d.version})
        return d


class Authorizer:
    """The single mandatory authorization decision point (MC-07.008)."""

    def __init__(self, store: PolicyStore, *, deny_rate_per_s: float = 5.0, deny_burst: int = 20,
                 audit: Callable[[str, dict], None] | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.store = store
        self.audit = audit
        self.clock = clock
        self.deny_rate, self.deny_burst = deny_rate_per_s, deny_burst
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        self.revoked_subjects: set[str] = set()

    def _record(self, principal: Principal, decision: Decision, tenant: str) -> None:
        if self.audit:
            self.audit("authz.decision", {"subject": principal.subject, "role": principal.role,
                                          "principal_tenant": principal.tenant, "target_tenant": tenant,
                                          **decision.to_dict()})

    def _rate_limited(self, subject: str) -> bool:
        with self._lock:
            b = self._buckets.get(subject)
            if b is None:
                if len(self._buckets) > 10000:
                    self._buckets.clear()  # bounded; resets limiter rather than growing
                b = self._buckets[subject] = TokenBucket(self.deny_rate, self.deny_burst, self.clock)
            return not b.take()

    def decide(self, principal: Principal, msg_type: int, target_tenant: str) -> Decision:
        op = TYPE_NAMES.get(msg_type)
        if op is None:
            d = Decision(False, "unknown_operation", 0, "", str(msg_type))
            self._record(principal, d, target_tenant)
            return d
        cap = OPERATIONS[op]["capability"]
        try:
            doc = self.store.current()
        except AuthzError:
            d = Decision(False, "policy_unavailable", 0, cap, op)
            self._record(principal, d, target_tenant)
            return d
        if principal.subject in self.revoked_subjects:
            d = Decision(False, "subject_revoked", doc.version, cap, op)
            self._record(principal, d, target_tenant)
            return d
        if principal.role not in PRINCIPAL_ROLES or principal.role == "relay":
            d = Decision(False, "role_not_permitted", doc.version, cap, op)
            self._record(principal, d, target_tenant)
            return d

        def matches(rule: Rule) -> bool:
            if principal.role not in rule.roles:
                return False
            if rule.subjects and principal.subject not in rule.subjects:
                return False
            if not (cap in rule.capabilities or WILDCARD in rule.capabilities):
                return False
            tenants = {principal.tenant if t == "$self" else t for t in rule.tenants}
            return target_tenant in tenants or WILDCARD in tenants

        matched = [r for r in doc.rules if matches(r)]
        if any(r.effect is Effect.DENY for r in matched):
            d = Decision(False, "explicit_deny", doc.version, cap, op)
        elif any(r.effect is Effect.ALLOW for r in matched):
            reason = "allow_cross_tenant" if target_tenant != principal.tenant else "allow"
            d = Decision(True, reason, doc.version, cap, op)
        elif target_tenant != principal.tenant:
            d = Decision(False, "cross_tenant_default_deny", doc.version, cap, op)
        else:
            d = Decision(False, "default_deny", doc.version, cap, op)
        self._record(principal, d, target_tenant)
        return d

    def enforce(self, principal: Principal, msg_type: int, target_tenant: str) -> Decision:
        d = self.decide(principal, msg_type, target_tenant)
        if d.allow:
            return d
        limited = self._rate_limited(principal.subject)
        code = ErrorCode.AUTHZ_CROSS_TENANT if d.reason == "cross_tenant_default_deny" else ErrorCode.AUTHZ_DENIED
        if d.reason == "policy_unavailable":
            code = ErrorCode.AUTHZ_POLICY_UNAVAILABLE
        if limited:
            code = ErrorCode.AUTHZ_RATE_LIMITED
        raise AuthzError(f"operation {d.operation} denied: {d.reason}", code=code,
                         detail={"reason": d.reason, "policy_version": d.policy_version})

    def break_glass(self, principal: Principal) -> Decision:
        """Admin bypass exists only as an explicit, audited capability (MC-07.012)."""
        doc = self.store.current()
        ok = any(r.effect is Effect.ALLOW and BREAK_GLASS in r.capabilities and principal.role in r.roles
                 and (not r.subjects or principal.subject in r.subjects) for r in doc.rules)
        ok = ok and not any(r.effect is Effect.DENY and BREAK_GLASS in r.capabilities and principal.role in r.roles
                            for r in doc.rules)
        d = Decision(ok, "break_glass" if ok else "break_glass_denied", doc.version, BREAK_GLASS, "BREAK_GLASS")
        self._record(principal, d, principal.tenant)
        return d


def default_policy(now: float, ttl_s: float = 86400.0, version: int = 1) -> dict:
    """Least-privilege baseline: agents act only inside their own tenant."""
    caps = lambda *ops: [OPERATIONS[o]["capability"] for o in ops]  # noqa: E731
    return {
        "version": version, "issued_at": now, "expires_at": now + ttl_s,
        "rules": [
            {"effect": "allow", "roles": ["host_agent", "node"],
             "capabilities": caps("PLACEMENT", "LEASE_GRANT", "LEASE_RENEW", "LEASE_REVOKE", "DRAIN",
                                  "STATUS_QUERY", "HEARTBEAT")},
            {"effect": "allow", "roles": ["guest_agent"],
             "capabilities": caps("LEASE_RENEW", "HEARTBEAT", "STATUS_QUERY", "ERROR_REPORT")},
            {"effect": "allow", "roles": ["service"], "capabilities": caps("STATUS_QUERY", "HEARTBEAT")},
            {"effect": "deny", "roles": ["guest_agent"], "capabilities": caps("DRAIN", "PLACEMENT", "LEASE_GRANT")},
        ],
    }
