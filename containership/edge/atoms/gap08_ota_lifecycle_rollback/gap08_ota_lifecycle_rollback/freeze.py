"""Emergency freeze/disable control (component 10).

Independent of ordinary gating: an authorized operator can freeze *all*
forward progress, one rollout, or one artifact digest (disable).  Freezing
needs one ``emergency.freeze`` holder; lifting needs ``emergency.unfreeze``
plus a second-person approval.  Freezes never block rollback, quarantine or
reconciliation.  Every change is returned as an audit event for the caller to
seal.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from .authz import ApprovalLedger, Cap, Principal
from .common import Clock, SystemClock
from .errors import Frozen, ValidationFailed


@dataclass
class FreezeControl:
    approvals: ApprovalLedger
    clock: Clock = field(default_factory=SystemClock)
    _freezes: dict[str, dict[str, Any]] = field(default_factory=dict)  # key -> record
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @staticmethod
    def key(scope: str, target: str = "*") -> str:
        if scope not in ("global", "rollout", "artifact"):
            raise ValidationFailed(f"unknown freeze scope {scope}")
        return f"{scope}:{target}"

    def freeze(self, who: Principal, scope: str, target: str = "*", reason: str = "") -> dict[str, Any]:
        self.approvals.policy.check(who, Cap.FREEZE, target)
        if not reason.strip():
            raise ValidationFailed("freeze reason required")
        k = self.key(scope, target)
        rec = {"event": "freeze", "key": k, "by": who.id, "reason": reason, "at": self.clock.now()}
        with self._lock:
            self._freezes[k] = rec
        return rec

    def unfreeze(self, who: Principal, scope: str, target: str, approval_id: str) -> dict[str, Any]:
        k = self.key(scope, target)
        self.approvals.policy.check(who, Cap.UNFREEZE, k)
        appr = self.approvals.consume(approval_id, Cap.UNFREEZE, k)
        with self._lock:
            if k not in self._freezes:
                raise ValidationFailed(f"{k} is not frozen")
            del self._freezes[k]
        return {"event": "unfreeze", "key": k, "by": who.id, "approval": appr["approval_id"],
                "approver": appr["approver"], "at": self.clock.now()}

    def check(self, *, rollout_id: str, artifact_digest: str | None) -> None:
        with self._lock:
            for k in ("global:*", f"rollout:{rollout_id}", f"artifact:{artifact_digest}"):
                if k in self._freezes:
                    raise Frozen(f"{k} frozen: {self._freezes[k]['reason']}", resource=k)

    def active(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self._freezes.items()}
