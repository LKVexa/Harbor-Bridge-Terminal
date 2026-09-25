"""Checklist 12: least-privilege capability model (deny by default).

Capabilities are the only unit of authority.  Roles are named bundles of
capabilities; a principal holds roles, optionally scoped to a set of nodes.
There is no wildcard capability and no implicit admin: a principal that is
not registered, or lacks the exact capability for the exact node, is refused
with ``authz_denied``.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from .defense import MitigationMissing, _require_identifier

CAP_POSTURE_WRITE = "posture.write"        # collectors only: submit attested read-back
CAP_POSTURE_READ = "posture.read"          # query PK_MITIGATIONS
CAP_COTENANCY_DECIDE = "cotenancy.decide"  # scheduler asks for PK_COTENANCY
CAP_EXPLAIN = "decision.explain"
CAP_CONTROL = "control.emergency"          # quarantine / freeze / kill switch
CAP_CONFIG_ACTIVATE = "config.activate"
CAP_AUDIT_READ = "audit.read"

ALL_CAPS = frozenset({CAP_POSTURE_WRITE, CAP_POSTURE_READ, CAP_COTENANCY_DECIDE, CAP_EXPLAIN,
                      CAP_CONTROL, CAP_CONFIG_ACTIVATE, CAP_AUDIT_READ})

ROLES: dict[str, frozenset[str]] = {
    "collector": frozenset({CAP_POSTURE_WRITE}),
    "scheduler": frozenset({CAP_COTENANCY_DECIDE, CAP_POSTURE_READ}),
    "observer": frozenset({CAP_POSTURE_READ, CAP_EXPLAIN}),
    "operator": frozenset({CAP_POSTURE_READ, CAP_EXPLAIN, CAP_CONTROL}),
    "policy-admin": frozenset({CAP_CONFIG_ACTIVATE}),
    "auditor": frozenset({CAP_AUDIT_READ, CAP_EXPLAIN}),
}


class AuthzDenied(MitigationMissing):
    def __init__(self, principal: str, capability: str, node: str | None):
        super().__init__(f"{principal!r} lacks {capability!r}" + (f" on {node!r}" if node else ""),
                         code="authz_denied",
                         details={"principal": principal, "capability": capability, "node": node})


@dataclass
class Principal:
    name: str
    roles: frozenset[str]
    node_scope: frozenset[str] | None = None  # None = all nodes (never for collectors)

    def caps(self) -> frozenset[str]:
        out: set[str] = set()
        for r in self.roles:
            out |= ROLES[r]
        return frozenset(out)


class Authorizer:
    def __init__(self) -> None:
        self._p: dict[str, Principal] = {}
        self._lock = threading.Lock()

    def grant(self, name: str, roles: set[str] | frozenset[str], node_scope=None) -> Principal:
        name = _require_identifier(name, "principal")
        unknown = set(roles) - set(ROLES)
        if unknown:
            raise ValueError(f"unknown roles {sorted(unknown)}")
        if "collector" in roles and node_scope is None:
            raise ValueError("collector principals must be scoped to explicit nodes")
        if "collector" in roles and len(roles) > 1:
            raise ValueError("collector identities may not hold other roles (separation of duty)")
        p = Principal(name, frozenset(roles), None if node_scope is None else frozenset(node_scope))
        with self._lock:
            self._p[name] = p
        return p

    def revoke(self, name: str) -> None:
        with self._lock:
            self._p.pop(name, None)

    def check(self, principal: str | None, capability: str, node: str | None = None) -> None:
        if capability not in ALL_CAPS:
            raise AuthzDenied(str(principal), capability, node)
        with self._lock:
            p = self._p.get(principal) if isinstance(principal, str) else None
        if p is None or capability not in p.caps():
            raise AuthzDenied(str(principal), capability, node)
        if p.node_scope is not None and (node is None or node not in p.node_scope):
            raise AuthzDenied(p.name, capability, node)
