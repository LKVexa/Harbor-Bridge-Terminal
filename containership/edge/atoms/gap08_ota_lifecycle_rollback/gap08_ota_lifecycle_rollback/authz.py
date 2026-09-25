"""Authorization policy layer (component 11) with two-person approval.

Capabilities are explicit; nothing is implied by role name.  Operators are
never tenant principals (OTA is estate infrastructure).  Safety-relevant
overrides and emergency-freeze *lifting* require an approval by a second,
distinct principal holding ``approve`` — the requester can never approve
their own request (separation of duties).  Approvals are time-boxed.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .common import Clock, SystemClock, new_id
from .errors import Unauthorized, ValidationFailed


class Cap(str, Enum):
    START = "rollout.start"
    STEP = "rollout.step"
    GATE = "rollout.gate"
    APPROVE = "rollout.approve"
    PAUSE = "rollout.pause"
    RESUME = "rollout.resume"
    CANCEL = "rollout.cancel"
    RETRY_DEFERRED = "rollout.retry_deferred"
    ROLLBACK = "rollout.rollback"
    OVERRIDE = "rollout.override"
    FREEZE = "emergency.freeze"
    UNFREEZE = "emergency.unfreeze"
    QUARANTINE_RELEASE = "quarantine.release"
    RECONCILE = "fleet.reconcile"
    CONFIG = "config.propose"
    READ = "rollout.read"


DEFAULT_ROLES: dict[str, frozenset[Cap]] = {
    "viewer": frozenset({Cap.READ}),
    "release-operator": frozenset({Cap.READ, Cap.START, Cap.STEP, Cap.GATE, Cap.PAUSE, Cap.RESUME, Cap.CANCEL,
                                   Cap.RETRY_DEFERRED, Cap.ROLLBACK, Cap.RECONCILE, Cap.FREEZE}),
    "release-approver": frozenset({Cap.READ, Cap.APPROVE, Cap.FREEZE}),
    "sre-oncall": frozenset({Cap.READ, Cap.PAUSE, Cap.CANCEL, Cap.ROLLBACK, Cap.FREEZE, Cap.RECONCILE,
                             Cap.QUARANTINE_RELEASE, Cap.OVERRIDE}),
    "security-officer": frozenset({Cap.READ, Cap.FREEZE, Cap.UNFREEZE, Cap.APPROVE}),
    "controller": frozenset({Cap.READ, Cap.STEP, Cap.GATE, Cap.RECONCILE}),  # workload identity
}
TWO_PERSON = frozenset({Cap.OVERRIDE, Cap.UNFREEZE, Cap.QUARANTINE_RELEASE})


@dataclass(frozen=True)
class Principal:
    id: str
    roles: frozenset[str]
    tenant: str | None = None
    environments: frozenset[str] | None = None   # None = every environment; otherwise scoped


@dataclass
class Policy:
    roles: dict[str, frozenset[Cap]] = field(default_factory=lambda: dict(DEFAULT_ROLES))

    def caps(self, p: Principal) -> frozenset[Cap]:
        out: set[Cap] = set()
        for r in p.roles:
            out |= self.roles.get(r, frozenset())
        return frozenset(out)

    def check(self, p: Principal, cap: Cap, resource: str = "*", *, environment: str | None = None) -> None:
        if not isinstance(p, Principal) or not p.id:
            raise Unauthorized("unauthenticated caller", resource=resource)
        if p.tenant is not None:
            raise Unauthorized("OTA is estate infrastructure; tenant principals are never authorized",
                               resource=resource)
        if cap not in self.caps(p):
            raise Unauthorized(f"{p.id} lacks {cap.value}", resource=resource, capability=cap.value)
        if environment is not None and p.environments is not None and environment not in p.environments:
            raise Unauthorized(f"{p.id} is not scoped to environment {environment}", resource=resource)


@dataclass
class ApprovalLedger:
    policy: Policy
    clock: Clock = field(default_factory=SystemClock)
    max_ttl_s: float = 3600.0
    _req: dict[str, dict[str, Any]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def request(self, requester: Principal, cap: Cap, resource: str, justification: str,
                ttl_s: float = 900.0) -> str:
        self.policy.check(requester, cap, resource)
        if not justification.strip():
            raise ValidationFailed("justification required")
        rid = new_id("appr")
        with self._lock:
            self._req[rid] = {"approval_id": rid, "cap": cap.value, "resource": resource, "requester": requester.id,
                              "justification": justification, "approver": None,
                              "expires_at": self.clock.now() + min(ttl_s, self.max_ttl_s), "used": False}
        return rid

    def approve(self, approver: Principal, approval_id: str) -> dict[str, Any]:
        self.policy.check(approver, Cap.APPROVE, approval_id)
        with self._lock:
            r = self._req.get(approval_id)
            if r is None:
                raise ValidationFailed("unknown approval")
            if r["requester"] == approver.id:
                raise Unauthorized("separation of duties: requester cannot approve", resource=approval_id)
            r["approver"] = approver.id
            return dict(r)

    def consume(self, approval_id: str, cap: Cap, resource: str) -> dict[str, Any]:
        with self._lock:
            r = self._req.get(approval_id)
            if r is None or r["approver"] is None:
                raise Unauthorized("approval missing or not yet approved", resource=resource)
            if r["used"] or r["cap"] != cap.value or r["resource"] != resource:
                raise Unauthorized("approval already used or bound to another action", resource=resource)
            if self.clock.now() > r["expires_at"]:
                raise Unauthorized("approval expired", resource=resource)
            r["used"] = True
            return dict(r)
