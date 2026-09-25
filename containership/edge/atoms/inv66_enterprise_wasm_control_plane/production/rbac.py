"""Organisation/tenant/lattice RBAC with capabilities, groups, service principals and deny (MC-032, MC-013).

Scopes are paths ``org``, ``org/tenant`` or ``org/tenant/lattice``.  A binding at a
scope applies to that scope and everything beneath it.  Evaluation is
deterministic: **any matching deny wins over any allow** (C042 least privilege,
C046 explicit deny), then an allow grants, otherwise the default is deny.

Delegated administration: a principal holding ``rbac.admin`` at scope S may create
or remove bindings only at S or beneath it, and only for roles whose capability
set is a subset of the capabilities that principal itself holds at S (no
privilege escalation by delegation).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .errors import EcpError
from .identity import Principal

CAPABILITIES = frozenset({"admit", "admit.dry_run", "rbac.admin", "policy.admin", "config.activate", "config.approve",
                          "audit.read", "audit.export", "quarantine", "inventory.read", "explain.read"})

BUILTIN_ROLES: dict[str, frozenset[str]] = {
    "viewer": frozenset({"inventory.read", "explain.read", "admit.dry_run"}),
    "deployer": frozenset({"admit", "admit.dry_run", "inventory.read", "explain.read"}),
    "auditor": frozenset({"audit.read", "audit.export", "inventory.read", "explain.read"}),
    "tenant-admin": frozenset({"rbac.admin", "admit", "admit.dry_run", "inventory.read", "explain.read", "audit.read"}),
    "security-admin": frozenset({"policy.admin", "config.approve", "quarantine", "audit.read", "audit.export", "explain.read", "inventory.read"}),
    "org-admin": frozenset(CAPABILITIES),
}


def scope_path(org: str, tenant: str | None = None, lattice: str | None = None) -> tuple[str, ...]:
    return tuple(x for x in (org, tenant, lattice) if x)


def parse_scope(s: str) -> tuple[str, ...]:
    parts = tuple(s.split("/"))
    if not 1 <= len(parts) <= 3 or any(not p for p in parts):
        raise EcpError("ECP_SCHEMA_INVALID", "scope must be org[/tenant[/lattice]]", field="scope")
    return parts


def _covers(binding_scope: tuple[str, ...], target: tuple[str, ...]) -> bool:
    return target[: len(binding_scope)] == binding_scope


@dataclass(frozen=True)
class Binding:
    role: str
    scope: tuple[str, ...]
    effect: str = "allow"
    subject: str | None = None
    group: str | None = None

    @classmethod
    def from_doc(cls, d: dict[str, Any]) -> "Binding":
        if bool(d.get("subject")) == bool(d.get("group")):
            raise EcpError("ECP_CONFIG_INVALID", "binding needs exactly one of subject/group", field="binding")
        return cls(role=d["role"], scope=parse_scope(d["scope"]), effect=d.get("effect", "allow"),
                   subject=d.get("subject"), group=d.get("group"))

    def to_doc(self) -> dict[str, Any]:
        d = {"role": self.role, "scope": "/".join(self.scope), "effect": self.effect}
        if self.subject:
            d["subject"] = self.subject
        if self.group:
            d["group"] = self.group
        return d

    def matches(self, p: Principal) -> bool:
        return (self.subject is not None and self.subject == p.subject) or \
               (self.group is not None and self.group in p.groups)


class Rbac:
    def __init__(self, roles: dict[str, Iterable[str]], bindings: Iterable[Binding]):
        merged = {k: frozenset(v) for k, v in BUILTIN_ROLES.items()}
        for name, caps in roles.items():
            caps = frozenset(caps)
            if not caps <= CAPABILITIES:
                raise EcpError("ECP_CONFIG_INVALID", "role has unknown capability", field="roles", rule=name)
            merged[name] = caps
        self.roles = merged
        self.bindings = tuple(bindings)
        for b in self.bindings:
            if b.role not in self.roles:
                raise EcpError("ECP_CONFIG_INVALID", "binding references unknown role", field="bindings", rule=b.role)
            if b.effect not in ("allow", "deny"):
                raise EcpError("ECP_CONFIG_INVALID", "binding effect must be allow|deny", field="bindings")

    def capabilities(self, p: Principal, target: tuple[str, ...]) -> frozenset[str]:
        allow: set[str] = set()
        deny: set[str] = set()
        for b in self.bindings:
            if b.matches(p) and _covers(b.scope, target):
                (deny if b.effect == "deny" else allow).update(self.roles[b.role])
        return frozenset(allow - deny)

    def explain(self, p: Principal, capability: str, target: tuple[str, ...]) -> dict[str, Any]:
        matched = [b.to_doc() for b in self.bindings
                   if b.matches(p) and _covers(b.scope, target) and capability in self.roles[b.role]]
        allowed = capability in self.capabilities(p, target)
        return {"capability": capability, "scope": "/".join(target), "allowed": allowed, "matched_bindings": matched,
                "rule": "deny-overrides; default-deny"}

    def check(self, p: Principal, capability: str, target: tuple[str, ...]) -> None:
        if p.org != target[0]:
            raise EcpError("ECP_FORBIDDEN", "principal belongs to another organisation", capability=capability,
                           scope="/".join(target))
        if p.kind == "workload" and p.tenant and len(target) > 1 and target[1] != p.tenant:
            raise EcpError("ECP_FORBIDDEN", "workload identity is confined to its own tenant", capability=capability,
                           scope="/".join(target))
        if capability not in self.capabilities(p, target):
            raise EcpError("ECP_FORBIDDEN", f"{p.subject} lacks {capability} on {'/'.join(target)}",
                           capability=capability, scope="/".join(target))

    def admin_authority(self, admin: Principal, scope: tuple[str, ...]) -> tuple[str, ...]:
        """The broadest scope (closest to the org root) at which ``admin`` holds rbac.admin over ``scope``."""
        best = None
        for b in self.bindings:
            if b.matches(admin) and b.effect == "allow" and "rbac.admin" in self.roles[b.role] and _covers(b.scope, scope):
                if best is None or len(b.scope) < len(best):
                    best = b.scope
        if best is None:
            raise EcpError("ECP_FORBIDDEN", "no rbac.admin authority", capability="rbac.admin", scope="/".join(scope))
        return best

    def check_delegation(self, admin: Principal, binding: Binding) -> None:
        self.check(admin, "rbac.admin", binding.scope)
        held = self.capabilities(admin, binding.scope)
        if binding.effect == "allow" and not self.roles[binding.role] <= held:
            raise EcpError("ECP_FORBIDDEN", "cannot delegate capabilities you do not hold",
                           capability="rbac.admin", scope="/".join(binding.scope), rule=binding.role)
