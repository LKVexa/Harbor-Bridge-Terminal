"""Generate the v4.3.0 interface JSON Schemas (2020-12) into schemas/.

Source of truth for wire contracts introduced in v4.3.0.  Run from anywhere:
    python gap14_data_gravity_manager/tools/gen_schemas.py
"""
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "schemas"
ID = {"type": "string", "minLength": 1, "maxLength": 128, "pattern": "^[A-Za-z0-9][A-Za-z0-9._:@/-]*$"}
NUM = {"type": "number", "minimum": 0}
TS = {"type": "number", "minimum": 0}
BOOL = {"type": "boolean"}
SIG = {"$ref": "PK_SIGNATURE-1.schema.json"}
DIR = {"enum": ["move-compute", "move-data", "move-data-partial", "replicate", "none"]}


def obj(required, optional=None, extra=False):
    props = dict(required)
    props.update(optional or {})
    return {"type": "object", "additionalProperties": extra, "required": list(required), "properties": props}


def signed(body_ref):
    return obj({"body": {"$ref": body_ref}, "sig": SIG})


S = {}
S["PK_SIGNATURE/1"] = obj({"alg": {"const": "HS256"}, "kid": ID, "iss": ID, "mac": {"type": "string", "pattern": "^[0-9a-f]{64}$"}})
S["PK_CAPABILITY_TOKEN/1"] = obj({"claims": obj({"schema": {"const": "PK_CAPABILITY_TOKEN/1"}, "sub": ID,
    "tenants": {"type": "array", "items": {"type": "string"}}, "scopes": {"type": "array", "items": {"enum": [
    "gravity:recommend", "gravity:handoff", "gravity:explain", "gravity:simulate", "gravity:admin"]}},
    "aud": {"const": "gap14.data-gravity"}, "iat": TS, "exp": TS, "jti": ID}), "sig": SIG})
SHARD = obj({"name": ID, "size_gb": NUM, "needed": BOOL}, {"converged": BOOL})
S["PK_GRAVITY_DECISION_REQUEST/1"] = obj(
    {"schema": {"const": "PK_GRAVITY_DECISION_REQUEST/1"}, "request_id": ID,
     "workload": obj({"tenant_id": ID, "workload_id": ID}, {"environment": {"enum": ["production", "staging", "development", "test"]}}),
     "dataset": obj({"name": ID, "tenant_id": ID, "site": ID, "size_gb": NUM, "classification": ID}),
     "compute_site": ID},
    {"requirements": obj({}, {"architecture": ID, "runtime": ID, "cpu": NUM, "gpu": NUM}),
     "profile": obj({}, {k: NUM for k in ["runs", "compute_warmup_cost", "cache_reuse_fraction", "read_gb_per_run",
        "write_gb_per_run", "iops_per_run", "compute_kwh_per_run", "compute_kw", "replica_months",
        "replica_sync_gb_per_run", "time_value_per_hour", "carbon_price_per_kg"]} | {"shards": {"type": "array", "maxItems": 10000, "items": SHARD}})})
OPTION = obj({"direction": DIR, "to": ID, "cost": NUM, "cost_breakdown": {"type": "object", "required": ["kind", "from", "to"]}})
ELIM = obj({"direction": DIR, "code": {"type": "string", "minLength": 1}, "reason": {"type": "string", "minLength": 1}})
S["PK_GRAVITY_DECISION/2"] = obj(
    {"schema": {"const": "PK_GRAVITY_DECISION/2"}, "executable": BOOL,
     "recommendation": obj({"direction": DIR, "to": ID, "cost": NUM, "cost_breakdown": {"type": "object", "required": ["kind", "from", "to"]},
                            "reason_code": {"type": "string"}, "options": {"type": "array", "items": OPTION},
                            "eliminated": {"type": "array", "items": {"type": "string"}},
                            "elimination_details": {"type": "array", "items": ELIM}}),
     "provenance": {"$ref": "PK_DECISION_PROVENANCE-1.schema.json"}, "sig": SIG},
    {"audit": obj({"seq": {"type": "integer", "minimum": 1}, "digest": {"type": "string"}})})
S["PK_DECISION_PROVENANCE/1"] = obj(
    {"decision_id": {"type": "string", "pattern": "^dec-[0-9a-f]{32}$"}, "issued_at": TS,
     "mode": {"enum": ["production", "staging", "development", "test"]},
     "engine": obj({"package": {"type": "string"}, "version": {"type": "string"}, "model_revision": {"type": "string"}}),
     "identity": obj({"tenant_id": ID, "workload_id": ID, "environment": {"type": "string"}}),
     "actor": obj({"subject": ID, "token_id": ID}), "request": {"type": "object"},
     "inputs": obj({"topology": {"type": "object"}, "placement": {"type": "object"}, "convergence": {"type": "object"},
                    "policy": {"type": "object"}, "config": obj({"revision": {"type": "integer"}, "digest": {"type": "string"}, "mode": {"type": "string"}}),
                    "request": {"type": "object"}, "identity": {"type": "object"}}),
     "input_digest": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}, "obligations": {"type": "object", "additionalProperties": True},
     "quality": obj({"status": {"enum": ["fresh", "degraded"]}, "stale_sources": {"type": "array", "items": {"type": "string"}}}),
     "trace": obj({"trace_id": {"type": "string", "pattern": "^[0-9a-f]{32}$"}, "span_id": {"type": "string", "pattern": "^[0-9a-f]{16}$"}}),
     "schema_versions": {"type": "object"}})
S["PK_POLICY_REQUEST/1"] = obj({"schema": {"const": "PK_POLICY_REQUEST/1"}, "tenant_id": ID, "workload_id": ID, "dataset": ID,
    "classification": ID, "source_site": ID, "destination_site": ID, "operation": {"enum": ["hold", "process"]},
    "jurisdiction_tags": {"type": "array", "items": ID}, "evaluated_at": TS})
S["PK_POLICY_VERDICT/1"] = obj({"schema": {"const": "PK_POLICY_VERDICT/1"}, "decision_id": ID,
    "request_hash": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}, "allow": BOOL, "policy_version": {"type": "integer", "minimum": 0},
    "rule_ids": {"type": "array", "items": ID}, "obligations": {"type": "object", "additionalProperties": True}, "issued_at": TS,
    "ttl_s": {"type": "number", "minimum": 0, "maximum": 86400}})
S["PK_TOPOLOGY_SNAPSHOT/1"] = obj({"schema": {"const": "PK_TOPOLOGY_SNAPSHOT/1"}, "snapshot_id": ID, "version": {"type": "integer", "minimum": 0},
    "issued_at": TS, "routes": {"type": "array", "maxItems": 10000, "items": obj(
        {"from": ID, "to": ID, "available": BOOL, "locality_multiplier": {"type": "number", "exclusiveMinimum": 0}, "egress_per_gb": NUM},
        {"bandwidth_gbps": {"type": "number", "exclusiveMinimum": 0}, "congestion": {"type": "number", "minimum": 0, "maximum": 0.99}})}})
S["PK_CONVERGENCE_PROOF/1"] = obj({"schema": {"const": "PK_CONVERGENCE_PROOF/1"}, "tenant_id": ID, "dataset": ID,
    "dataset_version": {"type": "integer", "minimum": 0}, "converged": BOOL, "open_conflicts": {"type": "integer", "minimum": 0},
    "watermark": ID, "issued_at": TS})
SITE = obj({"available": BOOL, "architectures": {"type": "array", "items": ID}, "runtimes": {"type": "array", "items": ID},
            "free_cpu": NUM, "free_gpu": NUM, "quota_remaining_gb": NUM, "storage_free_gb": NUM})
S["PK_PLACEMENT_SNAPSHOT/1"] = obj({"schema": {"const": "PK_PLACEMENT_SNAPSHOT/1"}, "snapshot_id": ID, "version": {"type": "integer", "minimum": 0},
    "tenant_id": ID, "issued_at": TS, "sites": {"type": "object", "additionalProperties": SITE}})
S["PK_DATA_MOVE_HANDOFF/1"] = obj({"schema": {"const": "PK_DATA_MOVE_HANDOFF/1"}, "handoff_id": {"type": "string", "pattern": "^ho-[0-9a-f]{32}$"},
    "decision_id": {"type": "string"}, "tenant_id": ID, "dataset": ID, "kind": {"enum": ["move-data", "move-data-partial", "replicate"]},
    "shards": {"type": ["array", "null"], "items": ID}, "from": ID, "to": ID, "size_gb": NUM,
    "obligations": {"type": "object", "additionalProperties": True}, "provenance_digest": {"type": "string"}, "not_after": TS})
S["PK_DATA_MOVE_ACK/1"] = obj({"schema": {"const": "PK_DATA_MOVE_ACK/1"}, "handoff_id": {"type": "string"}, "accepted": BOOL,
    "status": {"type": "string", "maxLength": 64}})
S["PK_AUDIT_RECORD/1"] = obj({"schema": {"const": "PK_AUDIT_RECORD/1"}, "seq": {"type": "integer", "minimum": 1},
    "prev": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}, "event": {"type": "string"}, "at": TS,
    "payload": {"type": "object", "additionalProperties": True}, "mac": SIG})
S["PK_GAP14_CONFIG/1"] = obj({"schema": {"const": "PK_GAP14_CONFIG/1"}, "revision": {"type": "integer", "minimum": 1},
    "mode": {"enum": ["production", "staging", "development", "test"]}},
    {"knobs": {"type": "object"}, "ttls": {"type": "object"}, "site_jurisdictions": {"type": "object"},
     "dev_flags": {"type": "object"}, "site_economics": {"type": "object"},
     "shadow_model": obj({"revision": ID, "compute_relocation_cost": NUM}), "canary_percent": {"type": "number", "minimum": 0, "maximum": 100}})
S["PK_HEALTH/1"] = obj({"schema": {"const": "PK_HEALTH/1"}, "live": BOOL, "ready": BOOL, "checks": {"type": "object"},
    "dependencies": {"type": "object"}, "config": {"type": ["object", "null"]}, "version": {"type": "string"},
    "audit_head": {"type": "object"}, "inflight": {"type": "integer"}, "reason_code": {"type": ["string", "null"]}})
S["PK_GRAVITY_EXPLAIN/1"] = obj({"schema": {"const": "PK_GRAVITY_EXPLAIN/1"}, "decision_id": {"type": "string"}, "summary": {"type": "string"},
    "chosen": {"type": "object"}, "alternatives": {"type": "array"}, "eliminated": {"type": "array"}, "inputs": {"type": "object"},
    "input_digest": {"type": "string"}, "obligations": {"type": "object", "additionalProperties": True}, "model_revision": {"type": "string"},
    "shadow": {"type": ["object", "null"], "additionalProperties": True}, "audit": {"type": "object"}})
S["PK_GRAVITY_SIMULATION/1"] = obj({"schema": {"const": "PK_GRAVITY_SIMULATION/1"}, "executable": {"const": False},
    "simulation_id": {"type": "string", "pattern": "^sim-[0-9a-f]{32}$"}, "notice": {"type": "string"}, "result": {"type": "object"},
    "scenario_digest": {"type": "string"}, "actor": ID})

if __name__ == "__main__":
    for name, sch in S.items():
        fname = name.replace("/", "-") + ".schema.json"
        doc = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"urn:pk:schema:{name.replace('/', ':')}",
               "title": name, **sch}
        (OUT / fname).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print("wrote", fname)
