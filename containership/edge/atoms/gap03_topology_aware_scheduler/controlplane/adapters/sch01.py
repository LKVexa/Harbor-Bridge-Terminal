"""MC-008 - SCH-01 (workload classification & placement) integration.

Responsibility split: GAP-03 scores and reserves; SCH-01 owns the final
placement decision and lifecycle.  SCH-01 may choose ANY node from
``ranked`` but may not choose a node GAP-03 marked infeasible unless the
request carries an explicit, audited ``override_policy``.

``SCH01Harness`` is a schema-faithful conformance fake (deterministic
latency/error injection) - NOT the real SCH-01 (its real-implementation CI
contract test is a blocked item).
"""
from __future__ import annotations

from .. import canonical
from ..errors import SchedulerError

PROTOCOL = "SCH01-PLACE"
SUPPORTED = ("1.0", "1.1")
LIFECYCLE = ("accepted", "placed", "refused", "absent")
SCH_ERRORS = {  # SCH-01 native -> GAP03-ERR/1, plus compensation rule
    "E_NO_NODE": ("NO_FEASIBLE_CANDIDATE", "release"),
    "E_POLICY": ("PERMISSION_DENIED", "release"),
    "E_BUSY": ("OVERLOADED", "retain_until_retry_or_expiry"),
    "E_TIMEOUT": ("DEADLINE_EXCEEDED", "query_status_before_release"),
    "E_STALE": ("STALE_STATE", "release"),
    "E_FENCED": ("FENCED", "none_superseded_leader"),
    "E_VERSION": ("UNSUPPORTED_VERSION", "release"),
}


def negotiate(peer_versions: list[str]) -> str:
    common = sorted(set(SUPPORTED) & set(peer_versions))
    if not common:
        raise SchedulerError("UNSUPPORTED_VERSION", "no common SCH-01 protocol version")
    return common[-1]


def to_request(*, txn: str, version: str, scoring_result, tenant: str, slots: int, fence: int, trace: str = "",
               infeasible: dict | None = None) -> dict:
    """Lossless mapping of GAP-03 records into the SCH-01 request."""
    f = scoring_result.fairness
    return {"protocol": PROTOCOL, "version": version, "txn": txn, "idempotency_key": txn, "fence": fence,
            "traceparent": trace, "tenant": tenant, "slots": slots,
            "topology_generation": scoring_result.topology_generation,
            "ranked": [{"node": c.node, "rank_score": c.rank_score, "locality_cost": c.locality_cost,
                        "spread_penalty": c.spread_penalty, "failure_domain": c.failure_domain} for c in scoring_result.candidates],
            "infeasible": dict(sorted((infeasible or {}).items())),
            "fairness": {"allowed": f.allowed, "reason": f.reason, "state_token": f.state_token,
                         "reserved_slots": f.reserved_slots, "held_slots": f.held_slots,
                         "surplus_available": f.surplus_available}}


def map_error(native: str) -> SchedulerError:
    code, comp = SCH_ERRORS.get(native, ("INTERNAL", "query_status_before_release"))
    return SchedulerError(code, f"sch01:{native}", detail={"compensation": comp})


def check_selection(request: dict, chosen: str, override_policy: str | None = None) -> None:
    if chosen in request["infeasible"] and not override_policy:
        raise SchedulerError("PERMISSION_DENIED", "SCH-01 selected a node GAP-03 marked infeasible without override policy")
    if chosen not in {r["node"] for r in request["ranked"]} and chosen not in request["infeasible"]:
        raise SchedulerError("INVALID_ARGUMENT", "SCH-01 selected a node outside the candidate set")


class SCH01Harness:
    """Conformance fake: idempotent by txn, fenced, bounded queue, injectable faults."""

    def __init__(self, *, versions=SUPPORTED, max_queue: int = 64, faults=None):
        self.versions, self.max_queue = versions, max_queue
        self.faults = list(faults or [])  # sequence of native error names / "lost_response" / None
        self.placements: dict[str, dict] = {}
        self.max_fence = 0
        self.calls = 0

    def place(self, req: dict) -> dict:
        self.calls += 1
        if req.get("version", "1.1") not in self.versions:
            raise map_error("E_VERSION")
        if req["fence"] < self.max_fence:
            raise map_error("E_FENCED")
        self.max_fence = req["fence"]
        if req["txn"] in self.placements:
            return dict(self.placements[req["txn"]])
        fault = self.faults.pop(0) if self.faults else None
        if fault == "E_BUSY" or len(self.placements) >= self.max_queue:
            raise map_error("E_BUSY")
        if fault in SCH_ERRORS:
            raise map_error(fault)
        rec = {"status": "placed", "txn": req["txn"], "node": req["node"], "operation_id": "sch01-" + canonical.digest(req["txn"])[:16]}
        self.placements[req["txn"]] = rec
        if fault == "lost_response":
            raise map_error("E_TIMEOUT")
        return dict(rec)

    def status(self, txn: str) -> dict:
        return dict(self.placements.get(txn, {"status": "absent", "txn": txn}))

    def release(self, txn: str) -> dict:
        rec = self.placements.pop(txn, None)
        return {"status": "released" if rec else "absent", "txn": txn}
