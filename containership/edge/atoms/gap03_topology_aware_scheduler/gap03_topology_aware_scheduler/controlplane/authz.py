"""MC-002 - RBAC/ABAC for topology (and shared privileged) operations.

Least privilege: no role grants anything implicitly.  Re-parenting and bulk
import are high-blast-radius and require ``min_approvers`` distinct verified
approvers other than the requester (two-person rule).
"""
from __future__ import annotations

from .errors import SchedulerError

ROLE_PERMISSIONS = {
    "topology-editor": {"topology.create", "topology.relabel"},
    "topology-admin": {"topology.create", "topology.relabel", "topology.reparent", "topology.quarantine",
                       "topology.delete", "topology.bulk_import"},
    "break-glass": {"topology.override", "control.hard_stop", "degraded.override"},
    "entitlement-admin": {"entitlement.write"},
    "scheduler-service": {"placement.commit", "explain.read", "topology.read"},
    "operator": {"control.write", "explain.read", "health.deep", "config.write"},
    "auditor": {"audit.read", "audit.export", "explain.read"},
    "release-manager": {"release.promote", "waiver.approve"},
}
OP_PERMISSION = {"create": "topology.create", "relabel": "topology.relabel", "reparent": "topology.reparent",
                 "set_lifecycle": "topology.quarantine", "delete": "topology.delete"}
HIGH_BLAST = {"topology.reparent", "topology.bulk_import", "topology.override", "control.hard_stop"}
BULK_THRESHOLD = 50


def permissions(roles) -> set[str]:
    out: set[str] = set()
    for r in roles:
        out |= ROLE_PERMISSIONS.get(r, set())
    return out


def required_permissions(mutations: list[dict]) -> set[str]:
    perms = {OP_PERMISSION.get(m.get("op"), "topology.override") for m in mutations}
    if len(mutations) > BULK_THRESHOLD:
        perms.add("topology.bulk_import")
    return perms


def authorize(roles, needed: set[str], *, requester: str, approvers: list[dict], min_approvers: int = 1) -> dict:
    have = permissions(roles)
    missing = sorted(needed - have)
    if missing:
        raise SchedulerError("PERMISSION_DENIED", f"missing permission(s): {missing}")
    high = sorted(needed & HIGH_BLAST)
    if high:
        distinct = {a["sub"] for a in approvers if a["sub"] != requester and needed & HIGH_BLAST <= permissions(a.get("roles", []))}
        if len(distinct) < min_approvers:
            raise SchedulerError("PERMISSION_DENIED", f"two-person approval required for {high}")
    return {"granted": sorted(needed), "high_blast": high, "approvers": sorted({a["sub"] for a in approvers})}
