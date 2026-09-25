"""Organisation/tenant RBAC hierarchy and capability model (MC-032, MC-013).

Scopes form a tree ``org:<o>`` ⊃ ``org:<o>/tenant:<t>`` ⊃ ``.../lattice:<l>``.
A binding grants (``allow``) or forbids (``deny``) a role's capabilities to a
subject (``user:``, ``group:``, ``service:``) on a scope and every descendant.

Decision rule (deterministic, see docs/CONSTRAINT_PRECEDENCE.md):
  1. expired bindings are ignored;
  2. any matching ``deny`` wins over every ``allow`` (explicit deny);
  3. otherwise allowed iff some ``allow`` binding's role holds the capability;
  4. default deny.
Production deploys additionally require the ``deploy.prod`` capability, which
only ``deployer`` bindings scoped to a prod lattice/tenant carry via the
``environment`` gate enforced in :mod:`service`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    "viewer": frozenset({"inventory.read", "decision.read"}),
    "auditor": frozenset({"audit.read", "audit.export", "inventory.read", "decision.read"}),
    "deployer": frozenset({"admit", "inventory.read", "decision.read"}),
    "approver": frozenset({"admit", "lifecycle.transition", "decision.read"}),
    "policy-admin": frozenset({"config.propose", "config.activate", "rbac.write", "decision.read"}),
    "org-admin": frozenset({"admit", "config.propose", "config.activate", "rbac.write", "freeze",
                            "lifecycle.transition", "audit.read", "audit.export", "inventory.read", "decision.read"}),
}


def scope_of(org: str, tenant: str | None = None, lattice: str | None = None) -> str:
    s = f"org:{org}"
    if tenant:
        s += f"/tenant:{tenant}"
        if lattice:
            s += f"/lattice:{lattice}"
    return s


def contains(parent: str, child: str) -> bool:
    return child == parent or child.startswith(parent + "/")


@dataclass(frozen=True)
class Binding:
    subject: str
    role: str
    scope: str
    effect: str = "allow"
    expires_at: int | None = None

    def __post_init__(self):
        if self.role not in ROLE_CAPABILITIES:
            raise ValueError(f"unknown role {self.role}")
        if self.effect not in ("allow", "deny"):
            raise ValueError("effect must be allow|deny")
        if not self.subject.startswith(("user:", "group:", "service:")):
            raise ValueError("subject must be user:/group:/service:")


@dataclass(frozen=True)
class AuthzResult:
    allowed: bool
    explicit_deny: bool
    matched: tuple[Binding, ...]


class RbacModel:
    def __init__(self, bindings: Iterable[Binding], groups: Mapping[str, Iterable[str]] | None = None):
        self.bindings = tuple(bindings)
        # configured group -> members (in addition to IdP groups claim)
        self.groups = {g: frozenset(m) for g, m in (groups or {}).items()}

    def subjects_for(self, subject: str, idp_groups: Iterable[str] = ()) -> frozenset[str]:
        subs = {subject}
        subs.update(f"group:{g}" for g in idp_groups)
        subs.update(f"group:{g}" for g, members in self.groups.items() if subject in members)
        return frozenset(subs)

    def check(self, subject: str, capability: str, scope: str, now: int, idp_groups: Iterable[str] = ()) -> AuthzResult:
        subs = self.subjects_for(subject, idp_groups)
        allow, deny = [], []
        for b in self.bindings:
            if b.subject not in subs or not contains(b.scope, scope):
                continue
            if b.expires_at is not None and now >= b.expires_at:
                continue
            if capability not in ROLE_CAPABILITIES[b.role]:
                continue
            (deny if b.effect == "deny" else allow).append(b)
        if deny:
            return AuthzResult(False, True, tuple(deny))
        return AuthzResult(bool(allow), False, tuple(allow))

    def to_list(self) -> list[dict]:
        return [dict(subject=b.subject, role=b.role, scope=b.scope, effect=b.effect,
                     **({"expires_at": b.expires_at} if b.expires_at is not None else {})) for b in self.bindings]


def effective_access(model: "RbacModel", subject: str, scope: str, now: int, idp_groups: Iterable[str] = ()) -> dict:
    """Access-review view: every capability on ``scope`` with the bindings that grant or deny it."""
    caps = sorted(set().union(*ROLE_CAPABILITIES.values()))
    out = {}
    for cap in caps:
        r = model.check(subject, cap, scope, now, idp_groups)
        out[cap] = {"allowed": r.allowed, "explicit_deny": r.explicit_deny,
                    "via": [dict(subject=b.subject, role=b.role, scope=b.scope, effect=b.effect) for b in r.matched]}
    return {"subject": subject, "scope": scope, "subjects_considered": sorted(model.subjects_for(subject, idp_groups)),
            "capabilities": out}
