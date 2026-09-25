"""Component 45 - quarantine / freeze / emergency kill switch with authz,
break-glass and a hash-chained audit trail (production/audit.py).

Contract ``PK_DYN_CONTROLS/1``:
* Actions: quarantine, unquarantine, freeze, thaw, kill, unkill.  Each requires
  the actor's role to grant the action (``POLICY``) or an unexpired
  break-glass grant.  Denials are audited too.
* quarantine(node): controller never deletes/creates/reuses the node; it is
  drained.  freeze(scope): no scaling decisions (Pool.tick not called) for the
  scope ("site:<name>" or "global").  kill: no provider mutations at all.
* Safe thaw: unquarantine requires a passing health check callback; thaw
  requires a passing preflight callback; unkill requires a second, distinct
  approver holding the ``unkill`` right (two-person rule).
* Break-glass: any actor may open a time-bounded grant with a reason; it is
  audited at severity critical and expires on the injected clock.
Role -> person assignment is an organisational input: UNASSIGNED here.
"""
from __future__ import annotations

from typing import Callable

from .audit import AuditLog
from .core import Inv08Error, Outcome

POLICY = {
    "viewer": set(),
    "operator": {"quarantine", "freeze"},
    "sre_lead": {"quarantine", "unquarantine", "freeze", "thaw", "kill", "unkill"},
}
BREAK_GLASS_MAX_TTL = 3600.0


class Controls:
    def __init__(self, audit: AuditLog, roles: dict[str, str], *, clock: Callable[[], float]) -> None:
        unknown = {r for r in roles.values() if r not in POLICY}
        if unknown:
            raise ValueError(f"unknown roles {unknown}")
        self.audit, self.roles, self.clock = audit, dict(roles), clock
        self.quarantined: dict[str, str] = {}
        self.frozen: dict[str, str] = {}
        self.killed: str | None = None
        self._break_glass: dict[str, float] = {}

    # ------------------------------------------------------------ authz
    def _authorize(self, actor: str, action: str, resource: str) -> str:
        now = self.clock()
        role = self.roles.get(actor, "viewer")
        if action in POLICY[role]:
            return "role"
        if self._break_glass.get(actor, -1) > now:
            return "break_glass"
        self.audit.append(actor, action, resource, "DENIED", {"role": role}, ts=now)
        raise Inv08Error("INV08.AUTHZ.DENIED", f"{actor} may not {action}",
                         outcome=Outcome.OPERATOR_REQUIRED, severity="warning",
                         remediation="request the role or use break-glass with a reason",
                         details={"actor": actor, "action": action})

    def _ok(self, actor: str, action: str, resource: str, via: str, **details) -> None:
        self.audit.append(actor, action, resource, "SUCCESS", dict(details, via=via), ts=self.clock())

    def break_glass(self, actor: str, reason: str, ttl: float) -> float:
        if not reason or not reason.strip():
            raise ValueError("break-glass requires a reason")
        if not 0 < ttl <= BREAK_GLASS_MAX_TTL:
            raise ValueError(f"ttl must be in (0, {BREAK_GLASS_MAX_TTL}]")
        until = self.clock() + ttl
        self._break_glass[actor] = until
        self.audit.append(actor, "break_glass", "controls", "SUCCESS",
                          {"reason": reason, "until": until, "severity": "critical"}, ts=self.clock())
        return until

    # ------------------------------------------------------------ actions
    def quarantine(self, actor: str, node_id: str, reason: str) -> None:
        via = self._authorize(actor, "quarantine", node_id)
        self.quarantined[node_id] = reason
        self._ok(actor, "quarantine", node_id, via, reason=reason)

    def unquarantine(self, actor: str, node_id: str, health_check: Callable[[str], bool]) -> None:
        via = self._authorize(actor, "unquarantine", node_id)
        if node_id not in self.quarantined:
            raise KeyError(node_id)
        if not health_check(node_id):
            self.audit.append(actor, "unquarantine", node_id, "REFUSED", {"why": "health check failed"},
                              ts=self.clock())
            raise Inv08Error("INV08.CONTROLS.UNSAFE_THAW", f"{node_id} failed health check",
                             outcome=Outcome.OPERATOR_REQUIRED, details={"node_id": node_id})
        del self.quarantined[node_id]
        self._ok(actor, "unquarantine", node_id, via)

    def freeze(self, actor: str, scope: str, reason: str) -> None:
        if scope != "global" and not scope.startswith("site:"):
            raise ValueError("scope must be 'global' or 'site:<name>'")
        via = self._authorize(actor, "freeze", scope)
        self.frozen[scope] = reason
        self._ok(actor, "freeze", scope, via, reason=reason)

    def thaw(self, actor: str, scope: str, preflight: Callable[[], bool]) -> None:
        via = self._authorize(actor, "thaw", scope)
        if scope not in self.frozen:
            raise KeyError(scope)
        if not preflight():
            self.audit.append(actor, "thaw", scope, "REFUSED", {"why": "preflight failed"}, ts=self.clock())
            raise Inv08Error("INV08.CONTROLS.UNSAFE_THAW", f"thaw of {scope} refused by preflight",
                             outcome=Outcome.OPERATOR_REQUIRED, details={"scope": scope})
        del self.frozen[scope]
        self._ok(actor, "thaw", scope, via)

    def kill(self, actor: str, reason: str) -> None:
        via = self._authorize(actor, "kill", "global")
        self.killed = reason
        self._ok(actor, "kill", "global", via, reason=reason)

    def unkill(self, actor: str, approver: str) -> None:
        via = self._authorize(actor, "unkill", "global")
        if approver == actor:
            raise Inv08Error("INV08.AUTHZ.TWO_PERSON", "unkill needs a distinct approver",
                             outcome=Outcome.OPERATOR_REQUIRED)
        self._authorize(approver, "unkill", "global")
        self.killed = None
        self._ok(actor, "unkill", "global", via, approver=approver)

    # ------------------------------------------------------------ queries
    def is_frozen(self, site: str) -> bool:
        return "global" in self.frozen or f"site:{site}" in self.frozen

    def is_killed(self) -> bool:
        return self.killed is not None
