"""MC-08 result/failure/lifecycle model and MC-09 version/compatibility policy."""
from __future__ import annotations

from .errors import SchedulerError

# Placement lease lifecycle.
LEASE_STATES = ("REQUESTED", "RESERVED", "ADMITTED", "RUNNING", "RELEASED", "EXPIRED", "REVOKED", "REFUSED")
TERMINAL = frozenset({"RELEASED", "EXPIRED", "REVOKED", "REFUSED"})
TRANSITIONS: dict[str, frozenset[str]] = {
    "REQUESTED": frozenset({"RESERVED", "REFUSED"}),
    "RESERVED": frozenset({"ADMITTED", "EXPIRED", "REVOKED", "RELEASED"}),
    "ADMITTED": frozenset({"RUNNING", "REVOKED", "RELEASED"}),
    "RUNNING": frozenset({"RELEASED", "REVOKED"}),
}

# Result classes (a decision's outcome, distinct from the lease state).
RESULT_CLASSES = {
    "SUCCESS": "placed on a node satisfying every hard constraint",
    "DEGRADED_SUCCESS": "placed, but a soft preference (latency/topology) was not met; reasons listed",
    "RETRYABLE_FAILURE": "refused for a transient reason (capacity, overload, dependency); retry is safe",
    "TERMINAL_FAILURE": "refused for a reason retry cannot fix (policy, auth, invalid input)",
}

# Scheduler service lifecycle.
SERVICE_STATES = ("STARTING", "RECOVERING", "READY", "DEGRADED", "FROZEN", "DISABLED", "FENCED", "STOPPED")
SERVICE_TRANSITIONS: dict[str, frozenset[str]] = {
    "STARTING": frozenset({"RECOVERING", "STOPPED"}),
    "RECOVERING": frozenset({"READY", "STOPPED", "FENCED"}),
    "READY": frozenset({"DEGRADED", "FROZEN", "DISABLED", "FENCED", "STOPPED"}),
    "DEGRADED": frozenset({"READY", "FROZEN", "DISABLED", "FENCED", "STOPPED"}),
    "FROZEN": frozenset({"READY", "DISABLED", "STOPPED", "FENCED"}),
    "DISABLED": frozenset({"READY", "STOPPED"}),
    "FENCED": frozenset({"RECOVERING", "STOPPED"}),
}


def check(table: dict[str, frozenset[str]], src: str, dst: str) -> None:
    if dst not in table.get(src, frozenset()):
        raise SchedulerError("ILLEGAL_TRANSITION", f"{src} -> {dst} is not permitted",
                             details={"from": src, "to": dst})


def result_class(code: str | None) -> str:
    from .errors import CATALOG
    if code is None:
        return "SUCCESS"
    return "RETRYABLE_FAILURE" if CATALOG[code].retryable else "TERMINAL_FAILURE"


# ---------------------------------------------------------------- MC-09
SUPPORTED_SCHEMAS = {
    "PK_WORKLOAD_CLASS": {1: "supported"},
    "PK_PLACEMENT": {1: "deprecated", 2: "supported"},
    "PK_NODE_REPORT": {1: "supported"},
    "PK_SCHEDULER_ERROR": {1: "deprecated", 2: "supported"},
    "PK_PLACEMENT_REQUEST": {1: "supported"},
}
DEPRECATION_WINDOW_MINOR_RELEASES = 2


def negotiate(schema_id: str) -> str:
    """Accept `NAME/N`; refuse unknown or removed versions with UNSUPPORTED_VERSION."""
    try:
        name, ver = schema_id.split("/"); v = int(ver)
    except Exception:
        raise SchedulerError("UNSUPPORTED_VERSION", f"malformed schema id {schema_id!r}") from None
    status = SUPPORTED_SCHEMAS.get(name, {}).get(v)
    if status is None:
        raise SchedulerError("UNSUPPORTED_VERSION", f"{schema_id} is not supported",
                             details={"supported": {k: sorted(x) for k, x in SUPPORTED_SCHEMAS.items()}})
    return status


def downgrade_placement_v2_to_v1(p2: dict) -> dict:
    """Migration contract: a v2 placement is a strict superset of v1."""
    keys = ("workload", "tenant", "node", "site", "tier", "trust_class", "lease_issued_at", "lease_expires",
            "candidates_total", "candidates_considered", "decision")
    out = {k: p2[k] for k in keys}
    out["decision"] = {"strategy": p2["decision"]["strategy"], "score": p2["decision"]["score"]}
    out["schema"] = "PK_PLACEMENT/1"
    return out
