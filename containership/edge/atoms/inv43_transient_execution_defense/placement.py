"""Checklist 15: SCH-01 scheduler/placement adapter with refusal propagation.

INV-43 does not place workloads (a non-goal).  SCH-01 hands this adapter a
candidate workload and the candidate nodes with their current residents; the
adapter returns which nodes are *eligible* and, for every excluded node, the
exact ``PK_ERROR/1`` refusal(s) and decision ids so SCH-01 can surface them
to the requester and operators.  A node is eligible only if the candidate may
co-reside with every resident of a different tenant.  Any error inside the
evaluation of a node excludes that node (fail closed); the adapter never
returns a node it could not evaluate.
"""
from __future__ import annotations

from .registry import PostureRegistry

ADAPTER_SCHEMA = "INV43_SCH01_FILTER/1"
MAX_CANDIDATES = 5000
MAX_RESIDENTS_PER_NODE = 512


def filter_nodes(registry: PostureRegistry, principal: str, workload: dict,
                 candidates: dict[str, list[dict]], *, tier: str, traceparent: str | None = None) -> dict:
    if not isinstance(candidates, dict) or len(candidates) > MAX_CANDIDATES:
        return {"schema": ADAPTER_SCHEMA, "eligible": [], "refused": {},
                "error": {"schema": "PK_ERROR/1", "code": "bad_request",
                          "message": "candidates must be a mapping of at most %d nodes" % MAX_CANDIDATES,
                          "details": {}}}
    eligible, refused = [], {}
    for node in sorted(candidates):
        residents = candidates[node]
        if not isinstance(residents, list) or len(residents) > MAX_RESIDENTS_PER_NODE:
            refused[node] = [{"schema": "PK_ERROR/1", "code": "bad_request",
                              "message": "residents must be a bounded list", "details": {}}]
            continue
        errs = []
        # evaluate against the empty node too, so posture/quarantine/freeze apply even to a first tenant
        peers = residents or [workload]
        for r in peers:
            out = registry.decide(principal, node, workload, r, tier=tier, traceparent=traceparent)
            if not out.get("permitted"):
                errs.append(out)
        if errs:
            refused[node] = errs
        else:
            eligible.append(node)
    return {"schema": ADAPTER_SCHEMA, "eligible": eligible, "refused": refused}
