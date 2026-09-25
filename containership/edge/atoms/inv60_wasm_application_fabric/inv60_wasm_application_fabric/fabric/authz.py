"""M18 - default-deny authorization and capability grants.

Decision tuple: (principal, action, resource, tenant, context, policy_version).
Rules are explicit allows; everything else is denied. Link grants are capability
records bound to principal, tenant, interface, allowed operations and expiry,
independent of mere link existence. Every decision is recorded with the rule id.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from .errors import FabricError

ACTIONS = ("membership.join", "membership.remove", "artifact.push", "component.start",
           "component.stop", "link.grant", "link.revoke", "component.call", "diagnostics.read",
           "config.activate", "config.rollback", "control.quarantine", "control.freeze",
           "release.certify")
POLICY_VERSION = "inv60-policy/1.0.0"
MAX_STALE_CACHE_S = 0.0  # revocation is effective immediately in-process


@dataclass(frozen=True)
class Rule:
    id: str
    kinds: tuple[str, ...]
    actions: tuple[str, ...]
    same_tenant: bool = True


DEFAULT_RULES = (
    Rule("R-HOST-JOIN", ("host",), ("membership.join",), same_tenant=False),
    Rule("R-OPS-MEMBERSHIP", ("operator", "automation"), ("membership.join", "membership.remove"), same_tenant=False),
    Rule("R-DEPLOY", ("automation", "operator"), ("artifact.push", "component.start", "component.stop",
                                                 "link.grant", "link.revoke"), same_tenant=True),
    Rule("R-INVOKE", ("workload",), ("component.call",), same_tenant=True),
    Rule("R-DIAG", ("operator",), ("diagnostics.read",), same_tenant=True),
    Rule("R-CONFIG", ("automation",), ("config.activate", "config.rollback"), same_tenant=False),
    Rule("R-CONTROL", ("operator",), ("control.quarantine", "control.freeze"), same_tenant=False),
)


@dataclass
class Decision:
    allowed: bool
    principal: str
    action: str
    resource: str
    tenant: str
    rule: str
    reason: str
    policy_version: str = POLICY_VERSION
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    at: float = field(default_factory=time.time)

    def record(self) -> dict:
        return dict(self.__dict__)


@dataclass
class Grant:
    id: str
    component: str
    link: str
    tenant: str
    grantee: str               # principal allowed to exercise it (component's workload id)
    interface: str
    operations: frozenset
    expires_at: float
    revoked: bool = False


class Authorizer:
    def __init__(self, rules=DEFAULT_RULES, *, clock=time.time) -> None:
        self.rules = tuple(rules)
        self.clock = clock
        self.decisions: list[Decision] = []
        self.grants: dict[tuple[str, str], Grant] = {}
        self.break_glass: dict[str, float] = {}  # principal -> expiry
        self.policy_available = True

    def decide(self, principal, action: str, resource: str, tenant: str) -> Decision:
        if not self.policy_available:
            d = Decision(False, principal.id, action, resource, tenant, "-", "policy engine unavailable (fail closed)")
        elif action not in ACTIONS:
            d = Decision(False, principal.id, action, resource, tenant, "-", "unknown action")
        else:
            d = Decision(False, principal.id, action, resource, tenant, "DEFAULT-DENY", "no rule allows")
            for r in self.rules:
                if principal.kind in r.kinds and action in r.actions:
                    if r.same_tenant and principal.tenant != tenant:
                        d = Decision(False, principal.id, action, resource, tenant, r.id, "cross-tenant")
                        break
                    d = Decision(True, principal.id, action, resource, tenant, r.id, "allowed")
                    break
            if not d.allowed and self.break_glass.get(principal.id, 0) > self.clock() and principal.kind == "operator":
                d = Decision(True, principal.id, action, resource, tenant, "BREAK-GLASS", "time-bounded break-glass")
        self.decisions.append(d)
        return d

    def require(self, principal, action, resource, tenant) -> Decision:
        d = self.decide(principal, action, resource, tenant)
        if not d.allowed:
            code = "UNAVAILABLE" if "unavailable" in d.reason else "PERMISSION_DENIED"
            raise FabricError(code, f"{action} on {resource}: {d.reason}",
                              detail={"rule": d.rule, "decision": d.correlation_id})
        return d

    def enable_break_glass(self, principal, duration_s: float, *, second_factor: bool) -> None:
        if principal.kind != "operator" or not second_factor:
            raise FabricError("PERMISSION_DENIED", "break-glass requires an operator and a second factor")
        self.break_glass[principal.id] = self.clock() + min(duration_s, 3600.0)

    # -- capability grants ------------------------------------------
    def grant(self, component: str, link: str, tenant: str, grantee: str, interface: str,
              operations, ttl_s: float) -> Grant:
        g = Grant("grant-" + uuid.uuid4().hex[:12], component, link, tenant, grantee, interface,
                  frozenset(operations), self.clock() + ttl_s)
        self.grants[(component, link)] = g
        return g

    def revoke(self, component: str, link: str) -> None:
        g = self.grants.get((component, link))
        if g:
            g.revoked = True

    def check_capability(self, caller, component: str, link: str, operation: str, tenant: str) -> Grant:
        g = self.grants.get((component, link))
        if g is None or g.revoked:
            raise FabricError("NOT_LINKED", f"{component} has no active grant for {link!r}")
        if g.expires_at <= self.clock():
            raise FabricError("NOT_LINKED", "grant expired")
        if caller.id != g.grantee:
            raise FabricError("PERMISSION_DENIED", "caller is not the grantee (confused deputy)")
        if caller.tenant != g.tenant or tenant != g.tenant:
            raise FabricError("PERMISSION_DENIED", "cross-tenant capability use")
        if operation not in g.operations:
            raise FabricError("PERMISSION_DENIED", f"operation {operation!r} not in grant")
        return g
