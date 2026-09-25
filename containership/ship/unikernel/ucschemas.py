"""JSON schemas for the ship's artifacts and a stdlib-only validator (the same
validator the DF containers ship, so gate G2's rule -- every artifact validates
against the schema shipped beside it -- holds for the ship too)."""

from __future__ import annotations

import re
from typing import Any, Dict, List

_TYPES = {"object": dict, "array": list, "string": str, "integer": int,
          "number": (int, float), "boolean": bool, "null": type(None)}


def validate(instance: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    errs: List[str] = []
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        ok = False
        for tt in types:
            if tt in ("integer", "number") and isinstance(instance, bool):
                continue
            if isinstance(instance, _TYPES[tt]):
                ok = True
                break
        if not ok:
            return [f"{path}: expected type {t}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in enum")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: {instance} < minimum {schema['minimum']}")
    if isinstance(instance, str) and "pattern" in schema and not re.search(schema["pattern"], instance):
        errs.append(f"{path}: {instance!r} does not match {schema['pattern']!r}")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in instance:
                errs.append(f"{path}: missing required property {req!r}")
        for k, v in instance.items():
            if k in props:
                errs.extend(validate(v, props[k], f"{path}.{k}"))
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: additional property {k!r} not allowed")
            elif isinstance(schema.get("additionalProperties"), dict):
                errs.extend(validate(v, schema["additionalProperties"], f"{path}.{k}"))
    if isinstance(instance, list):
        it = schema.get("items")
        if isinstance(it, dict):
            for i, v in enumerate(instance):
                errs.extend(validate(v, it, f"{path}[{i}]"))
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append(f"{path}: fewer than {schema['minItems']} items")
    return errs


NODE_ENUM = ["N_SMALL", "N_MEDIUM", "N_LARGE", "N_XLARGE"]
_HEX64 = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_FILE = {"type": "object", "required": ["path", "bytes", "sha256"],
         "properties": {"path": {"type": "string"}, "bytes": {"type": "integer", "minimum": 0}, "sha256": _HEX64}}

SCHEMAS: Dict[str, Dict[str, Any]] = {
    "UC_SHIP_MANIFEST": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_SHIP_MANIFEST.json",
        "title": "Unikernel Containership manifest", "type": "object",
        "required": ["schema", "uc_release", "package_name", "assembled_at_utc", "hull", "hold", "berths", "file_count", "total_bytes",
                     "files", "inventory_exclusions", "inventory_exclusion_reason", "physical_execution", "gates_measured_here"],
        "properties": {"schema": {"const": "UC/SHIP_MANIFEST/1"}, "files": {"type": "array", "items": _FILE, "minItems": 1},
                       "file_count": {"type": "integer", "minimum": 1},
                       "physical_execution": {"type": "object", "required": ["NETWORK", "BACKEND"]}},
    },
    "UC_SORT_LEDGER": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_SORT_LEDGER.json",
        "title": "sort ledger", "type": "object",
        "required": ["schema", "uc_release", "berth", "kind", "policy", "policy_sha256", "source", "scripts", "per_node", "records"],
        "properties": {"schema": {"const": "UC/SORT_LEDGER/1"}, "kind": {"enum": ["vm", "subsystem"]},
                       "records": {"type": "array", "minItems": 1, "items": {
                           "type": "object", "required": ["path", "node", "rule", "explanation", "kind", "bytes", "lines", "sha256",
                                                          "complexity_score", "complexity_band"],
                           "properties": {"node": {"enum": NODE_ENUM}, "rule": {"type": "string", "pattern": "^S[0-9]$"},
                                          "sha256": _HEX64, "complexity_band": {"enum": ["LOW", "MID", "HIGH", "VERY_HIGH"]}}}}},
    },
    "UC_BERTH": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_BERTH.json",
        "title": "berth record", "type": "object",
        "required": ["schema", "uc_release", "berth", "kind", "loaded_utc", "source", "scripts", "bytes", "per_node", "seals",
                     "reference_witnesses", "cargo_segments_of_84", "studio_face", "policy_sha256", "slots"],
        "properties": {"schema": {"const": "UC/BERTH/1"}, "kind": {"enum": ["vm", "subsystem"]},
                       "per_node": {"type": "object", "additionalProperties": {"type": "object", "required": ["count", "bytes", "tree_sha256"]}},
                       "seals": {"type": "object", "required": ["CARGO.pal", "BERTH.pal"]},
                       "reference_witnesses": {"type": "object", "required": ["CARGO.pal", "BERTH.pal"]}},
    },
    "UC_NODE_SLOT": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_NODE_SLOT.json",
        "title": "node slot", "type": "object",
        "required": ["schema", "uc_release", "berth", "slot", "node_id", "engine", "cargo", "holds_vm", "trust_domain", "qubits"],
        "properties": {"schema": {"const": "UC/NODE_SLOT/1"}, "node_id": {"enum": NODE_ENUM}, "holds_vm": {"const": False},
                       "trust_domain": {"const": "LOCAL_TRUSTED"}, "qubits": {"const": 0},
                       "engine": {"type": "object", "required": ["hold_container", "zip_sha256"]},
                       "cargo": {"type": "object", "required": ["count", "bytes", "tree_sha256"]}},
    },
    "UC_BILL_OF_LADING": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_BILL_OF_LADING.json",
        "title": "bill of lading", "type": "object",
        "required": ["schema", "uc_release", "berths", "berth_count", "totals", "engines", "rule"],
        "properties": {"schema": {"const": "UC/BILL_OF_LADING/1"}, "berths": {"type": "array", "items": {
            "type": "object", "required": ["berth", "kind", "scripts", "per_node", "seals", "reference_witnesses"]}}},
    },
    "UC_GATE_RESULTS": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_GATE_RESULTS.json",
        "title": "gate results", "type": "object",
        "required": ["schema", "uc_release", "subject", "executed_at_utc", "host", "gates", "totals", "verdict"],
        "properties": {"schema": {"const": "UC/GATE_RESULTS/1"},
                       "gates": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["id", "name", "status", "seconds", "detail"],
                                                                          "properties": {"status": {"enum": ["PASS", "FAIL", "SKIPPED"]}}}},
                       "verdict": {"enum": ["PASS", "FAIL"]}},
    },
    "UC_CAPABILITY_LEDGER": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_CAPABILITY_LEDGER.json",
        "title": "capability ledger", "type": "object",
        "required": ["schema", "uc_release", "subject", "rule", "items", "distribution", "integrity"],
        "properties": {"schema": {"const": "UC/CAPABILITY_LEDGER/1"},
                       "items": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["id", "title", "status", "statement", "evidence"],
                                                                          "properties": {"status": {"enum": ["BLOCKED", "SPECIFIED", "SCAFFOLDED", "IMPLEMENTED", "VERIFIED", "OPERATIONAL", "QUALIFIED", "BLOCKED_EXTERNAL_AUTHORITY", "BLOCKED_CAPABILITY_ABSENT", "SKIPPED", "NOT_CLAIMED"]}}}}},
    },
    "UC_SORT_POLICY": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_SORT_POLICY.json",
        "title": "sort policy", "type": "object", "required": ["schema", "version", "complexity", "rules", "first_match_wins", "nodes"],
        "properties": {"schema": {"const": "UC/SORT_POLICY/1"}, "rules": {"type": "array", "minItems": 10}},
    },
    "UC_HOLD_DIGEST": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_HOLD_DIGEST.json",
        "title": "hold digest", "type": "object", "required": ["schema", "uc_release", "df_release", "zips", "df_sha256sums_sha256"],
        "properties": {"schema": {"const": "UC/HOLD_DIGEST/1"}, "zips": {"type": "object", "additionalProperties": _HEX64}},
    },
    "UC_HULL_DIGEST": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_HULL_DIGEST.json",
        "title": "hull digest", "type": "object", "required": ["schema", "uc_release", "studio_version", "tree_sha256", "file_count", "files"],
        "properties": {"schema": {"const": "UC/HULL_DIGEST/1"}, "tree_sha256": _HEX64, "files": {"type": "array", "items": _FILE, "minItems": 1}},
    },
    "UC_FABRIC": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://uc.local/schema/UC_FABRIC.json",
        "title": "a container's own .tif fabric (sealed genesis record)", "type": "object",
        "required": ["schema", "uc_release", "berth", "container", "genesis", "state0", "declaration_words", "reference_witness", "live", "executes"],
        "properties": {"schema": {"const": "UC/FABRIC/1"}, "container": {"enum": ["DF_Small", "DF_Medium", "DF_Large", "DF_Xtra_Large", "DF_Fabric"]},
                       "genesis": {"type": "object", "required": ["file", "tick", "blob_sha256", "grid", "bytes", "reversible"],
                                   "properties": {"tick": {"const": 0}, "blob_sha256": _HEX64, "reversible": {"const": True}}},
                       "state0": {"type": "object", "required": ["tick", "acc", "ref", "rows", "index", "flags"]},
                       "declaration_words": {"type": "integer", "minimum": 1, "maximum": 116}},
    },
}

ARTIFACT_SCHEMA_MAP = {
    "MANIFEST.json": "UC_SHIP_MANIFEST",
    "registry/BILL_OF_LADING.json": "UC_BILL_OF_LADING",
    "conformance/UC_GATE_RESULTS.json": "UC_GATE_RESULTS",
    "reports/UC_CAPABILITY_LEDGER.json": "UC_CAPABILITY_LEDGER",
    "reports/SORT_POLICY.json": "UC_SORT_POLICY",
    "hold/HOLD_DIGEST.json": "UC_HOLD_DIGEST",
    "hull/HULL_DIGEST.json": "UC_HULL_DIGEST",
}
BERTH_SCHEMA_MAP = {
    "BERTH.json": "UC_BERTH",
    "SORT_LEDGER.json": "UC_SORT_LEDGER",
    "DF_Small/SLOT.json": "UC_NODE_SLOT",
    "DF_Medium/SLOT.json": "UC_NODE_SLOT",
    "DF_Large/SLOT.json": "UC_NODE_SLOT",
    "DF_Xtra_Large/SLOT.json": "UC_NODE_SLOT",
    "DF_Small/fabric/FABRIC.json": "UC_FABRIC",
    "DF_Medium/fabric/FABRIC.json": "UC_FABRIC",
    "DF_Large/fabric/FABRIC.json": "UC_FABRIC",
    "DF_Xtra_Large/fabric/FABRIC.json": "UC_FABRIC",
    "DF_Fabric/fabric/FABRIC.json": "UC_FABRIC",
}
#: FABRIC.json is present only when the berth was loaded with the .tif fabric available (Pillow); B1 treats a
#: missing FABRIC.json as a violation only when BERTH.json says the fabric was available at load time
OPTIONAL_WHEN_FABRIC_UNAVAILABLE = tuple(k for k in BERTH_SCHEMA_MAP if k.endswith("fabric/FABRIC.json"))
