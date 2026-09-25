"""GAP02-MC-19 — Report authorization policy (deny by default).

Actions: read.scheduling_facts, read.detailed_inventory, probe.deep,
probe.force, control.quarantine, control.freeze. Roles map to actions;
principals map to roles. Unknown principal/action → deny.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .errors import Code, Gap02Error

ACTIONS = frozenset({"read.scheduling_facts", "read.detailed_inventory", "probe.deep",
                     "probe.force", "control.quarantine", "control.freeze"})
DEFAULT_ROLES = {
    "scheduler": {"read.scheduling_facts"},
    "operator": {"read.scheduling_facts", "read.detailed_inventory", "probe.force"},
    "security-admin": {"read.detailed_inventory", "probe.deep", "control.quarantine", "control.freeze"},
    "supervisor": {"read.scheduling_facts", "probe.force"},
}


@dataclass
class AuthzPolicy:
    bindings: Mapping[str, set[str]] = field(default_factory=dict)   # principal -> roles
    roles: Mapping[str, set[str]] = field(default_factory=lambda: {k: set(v) for k, v in DEFAULT_ROLES.items()})

    def __post_init__(self) -> None:
        for r, acts in self.roles.items():
            if not set(acts) <= ACTIONS:
                raise Gap02Error(Code.CONFIG_INVALID, f"role {r} has unknown actions")

    def allowed(self, principal: str, action: str) -> bool:
        if action not in ACTIONS:
            return False
        return any(action in self.roles.get(r, ()) for r in self.bindings.get(principal, ()))

    def require(self, principal: str, action: str) -> None:
        if not self.allowed(principal, action):
            raise Gap02Error(Code.POLICY_DENIED, f"{principal!r} may not {action}")
