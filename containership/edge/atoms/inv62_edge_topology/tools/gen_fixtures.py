"""Generate the reference conformance corpus under fixtures/ (MC-019).

Each fixture: {"id","description","role","node"?,"raw"?,"request"?,"expect":{"outcome","code"?,"result_keys"?}}.
Credentials are the placeholder "@CREDENTIAL" and are minted by the harness.
Run:  python inv62_edge_topology/tools/gen_fixtures.py
"""
from __future__ import annotations

import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "fixtures"
T = "tenant-a"


def req(protocol, op, body, **kw):
    e = {"protocol": protocol, "op": op, "tenant": T, "request_id": "req-fixture01", "credential": "@CREDENTIAL", "body": body}
    e.update(kw)
    return e


FIX = [
    ("graph-get", "Read the tenant graph", "topology-feed", req("PK_TOPO_GRAPH/1", "get", {}), {"outcome": "success", "result_keys": ["links", "nodes", "quarantined"]}),
    ("graph-apply-add", "Atomic add of a device and link", "topology-feed",
     req("PK_TOPO_GRAPH/1", "apply", {"mutations": [{"kind": "add_node", "node": "s1-d9", "tier": "device", "site": "s1", "parent": "s1-gw", "residency": "eu"},
                                                    {"kind": "connect", "a": "s1-gw", "b": "s1-d9", "latency_ms": 1.5}]},
         idempotency_key="idem-fixture01"), {"outcome": "success", "result_keys": ["applied", "links", "nodes"]}),
    ("graph-apply-probe", "Probe result with hysteresis", "topology-feed",
     req("PK_TOPO_GRAPH/1", "apply", {"mutations": [{"kind": "probe", "a": "r1", "b": "s1-gw", "ok": False, "at": 1800000001}]}),
     {"outcome": "success"}),
    ("graph-apply-cas-conflict", "Stale expected_revision", "topology-feed",
     req("PK_TOPO_GRAPH/1", "apply", {"expected_revision": 1, "mutations": [{"kind": "remove_node", "node": "s1-d2"}]}),
     {"outcome": "terminal_failure", "code": "TOPO.CONFLICT"}),
    ("graph-apply-invalid-hierarchy", "Device under cloud", "topology-feed",
     req("PK_TOPO_GRAPH/1", "apply", {"mutations": [{"kind": "add_node", "node": "bad", "tier": "device", "site": "s1", "parent": "cloud"}]}),
     {"outcome": "terminal_failure", "code": "TOPO.INVALID_TOPOLOGY"}),
    ("nearest-resolve", "Nearest GPU from a device", "scheduler",
     req("PK_TOPO_NEAREST/1", "resolve", {"origin": "s1-d1", "capability": "gpu", "explain": True}),
     {"outcome": "success", "result_keys": ["considered", "latency_ms", "node"]}),
    ("nearest-residency", "Residency constraint", "scheduler",
     req("PK_TOPO_NEAREST/1", "resolve", {"origin": "s1-d1", "capability": "gpu", "constraints": {"residency": ["us"]}}),
     {"outcome": "terminal_failure", "code": "TOPO.NO_CAPABLE_NODE"}),
    ("nearest-unknown-origin", "Unknown origin", "scheduler",
     req("PK_TOPO_NEAREST/1", "resolve", {"origin": "nope", "capability": "gpu"}),
     {"outcome": "terminal_failure", "code": "TOPO.UNKNOWN_NODE"}),
    ("partition-status", "Connected site status", "scheduler",
     req("PK_TOPO_PARTITION/1", "status", {"site": "s1"}),
     {"outcome": "success", "result_keys": ["coordinator", "mode", "partitioned", "preferred_candidate", "site", "state", "term"]}),
    ("partition-acquire", "Preferred candidate acquires", "node-agent:s1-gw",
     req("PK_TOPO_PARTITION/1", "acquire", {"site": "s1", "candidate": "s1-gw"}),
     {"outcome": "success", "result_keys": ["expires_at", "fencing_token", "holder", "site", "term"]}),
    ("partition-acquire-foreign", "Node agent campaigning for another node", "node-agent:s1-gw2",
     req("PK_TOPO_PARTITION/1", "acquire", {"site": "s1", "candidate": "s1-gw"}),
     {"outcome": "terminal_failure", "code": "TOPO.FORBIDDEN"}),
    ("partition-validate-none", "Token with no lease", "scheduler",
     req("PK_TOPO_PARTITION/1", "validate_token", {"site": "s1", "fencing_token": 1}),
     {"outcome": "terminal_failure", "code": "TOPO.STALE_LEADER"}),
    ("authz-scheduler-write", "Scheduler cannot mutate", "scheduler",
     req("PK_TOPO_GRAPH/1", "apply", {"mutations": [{"kind": "remove_node", "node": "s1-d2"}]}),
     {"outcome": "terminal_failure", "code": "TOPO.FORBIDDEN"}),
    ("version-unsupported", "Unsupported major", "scheduler",
     req("PK_TOPO_NEAREST/9", "resolve", {"origin": "s1-d1", "capability": "gpu"}),
     {"outcome": "terminal_failure", "code": "TOPO.UNSUPPORTED_VERSION"}),
    ("version-negotiated", "Downgrade via accept_versions", "scheduler",
     req("PK_TOPO_NEAREST/2", "resolve", {"origin": "s1-d1", "capability": "gpu"}, accept_versions=[2, 1]),
     {"outcome": "success"}),
    ("schema-extra-field", "Unknown body field", "scheduler",
     req("PK_TOPO_NEAREST/1", "resolve", {"origin": "s1-d1", "capability": "gpu", "hint": "x"}),
     {"outcome": "terminal_failure", "code": "TOPO.INVALID_REQUEST"}),
    ("schema-bad-identifier", "Identifier with space", "scheduler",
     req("PK_TOPO_NEAREST/1", "resolve", {"origin": "s1 d1", "capability": "gpu"}),
     {"outcome": "terminal_failure", "code": "TOPO.INVALID_REQUEST"}),
    ("unauthenticated", "Garbage credential", None,
     req("PK_TOPO_NEAREST/1", "resolve", {"origin": "s1-d1", "capability": "gpu"}, credential="PKT1.k1.AAAAAAAA.BBBBBBBB"),
     {"outcome": "terminal_failure", "code": "TOPO.UNAUTHENTICATED"}),
]
RAW = [
    ("raw-not-json", "Binary garbage", "ÿþ", {"code": "TOPO.INVALID_REQUEST"}),
    ("raw-nan", "NaN literal", '{"a": NaN}', {"code": "TOPO.INVALID_REQUEST"}),
    ("raw-duplicate-key", "Duplicate keys", '{"protocol":"PK_TOPO_GRAPH/1","protocol":"PK_TOPO_NEAREST/1"}', {"code": "TOPO.INVALID_REQUEST"}),
    ("raw-array", "Top-level array", "[]", {"code": "TOPO.INVALID_REQUEST"}),
]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for p in OUT.glob("*.json"):
        p.unlink()
    for fid, desc, role, request, expect in FIX:
        (OUT / f"{fid}.json").write_text(json.dumps({"id": fid, "description": desc, "role": role, "request": request,
                                                     "expect": expect}, indent=2, sort_keys=True) + "\n")
    for fid, desc, raw, expect in RAW:
        (OUT / f"{fid}.json").write_text(json.dumps({"id": fid, "description": desc, "raw": raw,
                                                     "expect": {"outcome": "terminal_failure", **expect}}, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(FIX) + len(RAW)} fixtures to {OUT}")


if __name__ == "__main__":
    main()
