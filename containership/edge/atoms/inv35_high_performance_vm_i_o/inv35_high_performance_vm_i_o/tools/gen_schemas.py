"""Generate schemas/ from the code that owns each interface (single source of truth).

``python tools/gen_schemas.py``          rewrite schemas/
``python tools/gen_schemas.py --check``  exit 1 if committed schemas drifted (CI gate)
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
pkg = importlib.import_module(PKG.name)
errors = importlib.import_module(PKG.name + ".runtime.errors")
config = importlib.import_module(PKG.name + ".runtime.config")
lifecycle = importlib.import_module(PKG.name + ".runtime.lifecycle")

S = "https://json-schema.org/draft/2020-12/schema"
HEX32 = "^[0-9a-f]{32}$"
CODES = sorted(errors.REGISTRY)


def schemas() -> dict[str, dict]:
    idx = {"type": "integer", "minimum": 0}
    out = {
        "submit/descriptor_chain.request.schema.json": {
            "$schema": S, "$id": "PK_VIRTQUEUE_SUBMIT/1#request",
            "description": "Wire form of a guest-posted chain as the VMM hands it to the datapath. Values are untrusted.",
            "type": "object", "additionalProperties": False, "required": ["queue", "tenant", "head", "descriptors"],
            "properties": {
                "queue": {"type": "string", "minLength": 1}, "tenant": {"type": "string", "minLength": 1},
                "head": idx, "idempotency_key": {"type": "string", "minLength": 1},
                "traceparent": {"type": "string"},
                "descriptors": {"type": "array", "minItems": 1, "maxItems": pkg.QUEUE_DEPTH, "items": {
                    "type": "object", "additionalProperties": False, "required": ["index", "address", "length"],
                    "properties": {"index": idx, "address": idx, "length": idx,
                                   "next_index": {"type": ["integer", "null"], "minimum": 0}}}},
            }},
        "submit/submit.result.schema.json": {
            "$schema": S, "$id": "PK_VIRTQUEUE_SUBMIT/1#result", "type": "object", "additionalProperties": False,
            "required": ["schema", "queue", "descriptors", "descriptor_count", "bytes", "validated", "code", "trace_id",
                         "idempotency_key"],
            "properties": {
                "schema": {"const": "PK_VIRTQUEUE_SUBMIT/1"}, "queue": {"type": "string"},
                "descriptors": {"type": "array", "minItems": 1, "maxItems": pkg.MAX_CHAIN, "items": idx},
                "descriptor_count": {"type": "integer", "minimum": 1, "maximum": pkg.MAX_CHAIN},
                "bytes": idx, "validated": {"const": True}, "code": {"enum": ["INV35-E000", "INV35-E001"]},
                "trace_id": {"type": "string", "pattern": HEX32},
                "idempotency_key": {"type": ["string", "null"]}, "replayed": {"const": True}}},
        "complete/complete.result.schema.json": {
            "$schema": S, "$id": "PK_VIRTQUEUE_COMPLETE/1#result", "type": "object", "additionalProperties": False,
            "required": ["schema", "queue", "notified", "pending", "in_flight_descriptors", "descriptors_released", "trace_id"],
            "properties": {
                "schema": {"const": "PK_VIRTQUEUE_COMPLETE/1"}, "queue": {"type": "string"},
                "notified": {"type": "boolean"}, "pending": idx,
                "in_flight_descriptors": {"type": "integer", "minimum": 0, "maximum": pkg.QUEUE_DEPTH},
                "descriptors_released": {"type": "integer", "minimum": 1, "maximum": pkg.MAX_CHAIN},
                "trace_id": {"type": "string", "pattern": HEX32}}},
        "errors/error.schema.json": {
            "$schema": S, "$id": "INV35_ERROR/1", "type": "object", "additionalProperties": False,
            "required": ["schema", "code", "outcome", "security_relevant", "summary", "detail"],
            "properties": {"schema": {"const": "INV35_ERROR/1"}, "code": {"enum": CODES},
                           "outcome": {"enum": [o.value for o in errors.Outcome]},
                           "security_relevant": {"type": "boolean"}, "summary": {"type": "string"},
                           "detail": {"type": "string"}}},
        "errors/error_codes.json": errors.registry_document(),
        "config/config.schema.json": config.json_schema(),
        "status/status.schema.json": {
            "$schema": S, "$id": "INV35_STATUS/1", "type": "object", "additionalProperties": False,
            "required": ["schema", "version", "live", "ready", "config", "interfaces", "dependencies", "capabilities",
                         "saturation", "queues", "stalls"],
            "properties": {
                "schema": {"const": "INV35_STATUS/1"}, "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                "live": {"type": "boolean"}, "ready": {"type": "boolean"},
                "config": {"type": "object", "required": ["digest", "generation"], "additionalProperties": False,
                           "properties": {"digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                                          "generation": {"type": "integer", "minimum": 1}}},
                "interfaces": {"type": "object"}, "dependencies": {"type": "object"},
                "capabilities": {"type": "array", "items": {"type": "string"}},
                "saturation": {"type": "number", "minimum": 0, "maximum": 1},
                "queues": {"type": "object", "additionalProperties": {
                    "type": "object", "additionalProperties": False,
                    "required": ["tenant", "state", "mode", "in_flight_descriptors", "pending", "depth_limit"],
                    "properties": {"tenant": {"type": "string"}, "state": {"enum": [s.value for s in lifecycle.State]},
                                   "mode": {"enum": [m.value for m in lifecycle.DegradedMode]},
                                   "in_flight_descriptors": idx, "pending": idx,
                                   "depth_limit": {"type": "integer", "minimum": 1}}}},
                "stalls": {"type": "array"}}},
        "status/lifecycle.json": lifecycle.state_machine_document(),
        "status/decision.schema.json": {
            "$schema": S, "$id": "INV35_DECISION/1", "type": "object", "additionalProperties": False,
            "required": ["schema", "action", "outcome", "code", "rule", "inputs", "trace_id", "ts"],
            "properties": {"schema": {"const": "INV35_DECISION/1"}, "action": {"type": "string"},
                           "outcome": {"type": "string"}, "code": {"enum": CODES}, "rule": {"type": "string"},
                           "inputs": {"type": "object"}, "trace_id": {"type": ["string", "null"]},
                           "ts": {"type": "number"}}},
        "evidence/gate_results.schema.json": {
            "$schema": S, "$id": "INV35_GATE_RESULTS/1", "type": "object", "additionalProperties": False,
            "required": ["schema", "version", "verdict", "tree_digest", "environment", "gates", "blockers", "seal"],
            "properties": {"schema": {"const": "INV35_GATE_RESULTS/1"}, "version": {"type": "string"},
                           "verdict": {"enum": ["PASS", "PARTIAL", "FAIL"]},
                           "tree_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                           "environment": {"type": "object"}, "gates": {"type": "object"},
                           "blockers": {"type": "array"}, "seal": {"type": "object"},
                           "generated_at": {"type": "string"}}},
    }
    return out


def main() -> int:
    check = "--check" in sys.argv
    drift = []
    for rel, doc in schemas().items():
        path = PKG / "schemas" / rel
        text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                drift.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    if drift:
        print("SCHEMA_DRIFT " + " ".join(drift))
        return 1
    print("SCHEMAS=OK" if check else "SCHEMAS=WRITTEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
