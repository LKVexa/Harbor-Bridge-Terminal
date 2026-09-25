"""Generate schemas/*.json deterministically (MC-17).  Run: python3 -B tools/gen_schemas.py [--check]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
from sch01_workload_classification_and_runtime_placem import errors as E  # noqa: E402

S = "https://json-schema.org/draft/2020-12/schema"
TIERS = ["process", "wasm", "unikernel", "microvm", "vm"]
TRUST = ["trusted", "first-party", "third-party", "untrusted", "hostile"]
st = {"type": "string", "minLength": 1}; it = {"type": "integer", "minimum": 0}
strs = {"type": "array", "items": st}; nst = {"type": ["string", "null"]}


def obj(props, req=None):
    return {"type": "object", "required": sorted(req if req is not None else props), "properties": props,
            "additionalProperties": False}


def doc(sid, body):
    return {"$schema": S, "$id": f"urn:pk:sch01:{sid}", "title": sid, **body}


def build():
    klass = obj({"schema": {"const": "PK_WORKLOAD_CLASS/1"}, "workload": st, "trust_class": {"enum": TRUST},
                 "required_tier": {"enum": TIERS}, "latency_class": {"enum": ["interactive", "batch"]}, "hardware": strs})
    decision = obj({"strategy": st, "score": {"type": "array"}})
    p1 = {"schema": {"const": "PK_PLACEMENT/1"}, "workload": st, "tenant": st, "node": st, "site": st,
          "tier": {"enum": TIERS}, "trust_class": {"enum": TRUST}, "lease_issued_at": it, "lease_expires": it,
          "candidates_total": it, "candidates_considered": it, "decision": decision}
    p2 = dict(p1, schema={"const": "PK_PLACEMENT/2"}, zone=st, runtime=st, latency_class={"enum": ["interactive", "batch"]},
              lease_id={"type": "string", "pattern": "^[0-9a-f]{24}$"}, devices=strs, jurisdiction=st,
              result_class={"enum": ["SUCCESS", "DEGRADED_SUCCESS"]}, degraded=strs, explain={"type": "object"})
    node = obj({"schema": {"const": "PK_NODE_REPORT/1"}, "name": st, "site": st, "tiers": {"type": "array", "items": {"enum": TIERS}},
                "capabilities": strs, "free_slots": it, "reported_at": it, "thermally_excluded": {"type": "boolean"},
                "occupants": {"type": "object"}}, req=["schema", "name", "site", "tiers"])
    codes = sorted(E.CATALOG)
    e1 = obj({"schema": {"const": "PK_SCHEDULER_ERROR/1"}, "code": st, "message": {"type": "string"}, "details": {"type": "object"}})
    e2 = obj({"schema": {"const": "PK_SCHEDULER_ERROR/2"}, "code": {"enum": codes}, "message": {"type": "string"},
              "retryable": {"type": "boolean"}, "category": {"enum": ["caller", "policy", "capacity", "security", "availability", "internal"]},
              "action": st, "details": {"type": "object"}, "retry_after_ms": it},
             req=["schema", "code", "message", "retryable", "category", "action", "details"])
    req = obj({"schema": {"const": "PK_PLACEMENT_REQUEST/1"}, "workload": obj({"name": st, "tenant": st, "provenance": st,
               "latency_sensitive": {"type": "boolean"}, "needs": strs, "site_affinity": nst}, req=["name", "tenant", "provenance"]),
               "environment": st, "accelerators": {"type": "object"}, "residency": strs, "dataset": nst,
               "anti_affinity_zone": nst, "preferred_zone": nst, "origin_site": nst, "runtime": nst,
               "slots": {"type": "integer", "minimum": 1}, "idempotency_key": st, "deadline": it},
              req=["schema", "workload", "idempotency_key", "deadline"])
    health = obj({"schema": {"const": "PK_SCHEDULER_HEALTH/1"}, "state": st, "live": {"type": "boolean"},
                  "ready": {"type": "boolean"}, "version": st, "decision_code_sha256": st, "config_rev": it,
                  "config_digest": st, "dependencies": {"type": "object"}, "capabilities": strs, "inflight": it,
                  "nodes": it, "active_leases": it})
    return {"PK_WORKLOAD_CLASS.v1": doc("PK_WORKLOAD_CLASS/1", klass), "PK_PLACEMENT.v1": doc("PK_PLACEMENT/1", obj(p1)),
            "PK_PLACEMENT.v2": doc("PK_PLACEMENT/2", obj(p2)), "PK_NODE_REPORT.v1": doc("PK_NODE_REPORT/1", node),
            "PK_SCHEDULER_ERROR.v1": doc("PK_SCHEDULER_ERROR/1", e1), "PK_SCHEDULER_ERROR.v2": doc("PK_SCHEDULER_ERROR/2", e2),
            "PK_PLACEMENT_REQUEST.v1": doc("PK_PLACEMENT_REQUEST/1", req), "PK_SCHEDULER_HEALTH.v1": doc("PK_SCHEDULER_HEALTH/1", health)}


def main(check: bool) -> int:
    d = PKG / "schemas"; d.mkdir(exist_ok=True); drift = []
    for name, body in build().items():
        text = json.dumps(body, indent=2, sort_keys=True) + "\n"; p = d / f"{name}.json"
        if check:
            if not p.exists() or p.read_text() != text: drift.append(name)
        else:
            p.write_text(text)
    if drift: print("SCHEMA DRIFT:", drift); return 1
    print("schemas", "in sync" if check else "written", len(build())); return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
