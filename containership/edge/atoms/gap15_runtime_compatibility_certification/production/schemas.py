"""Schema definitions, validators and compatibility diffing (component 09).

The schemas below are the single source of truth: ``publish()`` writes them as
JSON Schema (draft 2020-12 subset) files under ``schemas/`` and ``validate()``
interprets exactly that subset, so the published artifact and the runtime
validator cannot drift (MC-09-06). Unknown fields are rejected on every
security-sensitive object (``additionalProperties: false``, MC-09-04).
Semantic cross-field invariants that JSON Schema cannot express live in
``semantic_checks`` (MC-09-03). ``diff()`` classifies a schema change as
compatible or breaking for the release gate (MC-09-10).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

SCHEMA_SET_VERSION = "1.0.0"
ID = r"^[A-Za-z0-9][A-Za-z0-9._:@/+-]{0,255}$"
DIGEST = r"^sha256:[0-9a-f]{64}$"
PART = r"^[a-z0-9-]{1,63}/[a-z0-9-]{1,63}/[a-z0-9-]{1,63}$"
INT = {"type": "integer", "minimum": 0, "maximum": 2**62}

VERDICT_ENUM = ["certified", "incompatible", "untested", "expired", "end-of-life", "revoked", "quarantined", "retest-required"]

SCHEMAS: dict = {
    "GAP15_EVIDENCE/1": {
        "$id": "urn:gap15:schema:evidence:1", "type": "object", "additionalProperties": False,
        "required": ["schema", "producer", "producer_event_id", "partition", "artifact", "runtime", "attestation",
                     "result", "observed_at", "test_suite", "signature", "provenance"],
        "properties": {
            "schema": {"const": "GAP15_EVIDENCE/1"},
            "producer": {"type": "string", "pattern": ID},
            "producer_event_id": {"type": "string", "pattern": ID},
            "partition": {"type": "string", "pattern": PART},
            "artifact": {"type": "object", "additionalProperties": False, "required": ["digest", "media_type"],
                         "properties": {"digest": {"type": "string", "pattern": DIGEST},
                                        "media_type": {"type": "string", "maxLength": 128}}},
            "runtime": {"type": "string", "pattern": r"^[a-z0-9-]{1,32}@[0-9A-Za-z.+-]{1,64}$"},
            "attestation": {"type": "object", "additionalProperties": False, "required": ["quote", "signature", "nonce"],
                            "properties": {"quote": {"type": "object"}, "signature": {"type": "object"},
                                           "nonce": {"type": "string", "pattern": r"^[0-9a-f]{32,64}$"}}},
            "provenance": {"type": "object", "additionalProperties": False, "required": ["statement", "signature"],
                           "properties": {"statement": {"type": "object"}, "signature": {"type": "object"},
                                          "sbom": {"type": "object"}}},
            "result": {"enum": ["compatible", "incompatible"]},
            "failure_class": {"enum": ["deterministic", "security-policy", "performance", "transient", "flaky", "harness-defect"]},
            "features": {"type": "array", "maxItems": 256, "items": {"type": "object", "additionalProperties": False,
                         "required": ["feature", "result"], "properties": {
                             "feature": {"type": "string", "pattern": r"^[a-z0-9:/._-]{1,128}$"},
                             "result": {"enum": ["passed", "failed"]}}}},
            "observed_at": INT,
            "time_confidence": {"enum": ["high", "medium", "low"]},
            "test_suite": {"type": "object", "additionalProperties": False, "required": ["id", "version", "harness_digest"],
                           "properties": {"id": {"type": "string", "pattern": ID}, "version": {"type": "string", "pattern": ID},
                                          "harness_digest": {"type": "string", "pattern": DIGEST}}},
            "supersedes": {"type": "string", "pattern": ID},
            "signature": {"type": "object", "additionalProperties": False,
                          "required": ["algorithm", "key_id", "signed_at", "payload_digest", "value"],
                          "properties": {"algorithm": {"type": "string", "maxLength": 32}, "key_id": {"type": "string", "pattern": ID},
                                         "signed_at": INT, "payload_digest": {"type": "string", "pattern": DIGEST},
                                         "value": {"type": "string", "maxLength": 128}}},
        },
    },
    "PK_CERTIFICATION/1": {
        "$id": "urn:gap15:schema:certification:1", "type": "object", "additionalProperties": True,
        "required": ["schema", "verdict", "reason_code", "reason", "deployable", "key", "matrix_revision",
                     "ledger_seq", "policy_revision", "evaluated_at"],
        "properties": {
            "schema": {"const": "PK_CERTIFICATION/1"}, "verdict": {"enum": VERDICT_ENUM},
            "reason_code": {"type": "string", "pattern": r"^R_[A-Z_]{2,40}$"}, "reason": {"type": "string", "maxLength": 1024},
            "deployable": {"type": "boolean"}, "matrix_revision": INT, "ledger_seq": INT, "evaluated_at": INT,
            "policy_revision": {"type": "string", "maxLength": 128},
            "key": {"type": "object", "additionalProperties": False, "required": ["partition", "artifact_digest", "runtime", "profile_id"],
                    "properties": {"partition": {"type": "string", "pattern": PART}, "artifact_digest": {"type": "string", "pattern": DIGEST},
                                   "runtime": {"type": "string", "maxLength": 100}, "profile_id": {"type": "string", "maxLength": 100}}},
            "tested_at": INT, "expires_at": INT, "age": {"type": "integer"},
        },
    },
    "PK_COMPATIBILITY_MATRIX/1": {
        "$id": "urn:gap15:schema:matrix:1", "type": "object", "additionalProperties": False,
        "required": ["schema", "partition", "revision", "results"],
        "properties": {"schema": {"const": "PK_COMPATIBILITY_MATRIX/1"}, "partition": {"type": "string", "pattern": PART},
                       "revision": INT, "results": {"type": "array", "maxItems": 1000000, "items": {
                           "type": "object", "additionalProperties": False,
                           "required": ["artifact_digest", "runtime", "profile_id", "compatible", "tested_at", "evidence_id"],
                           "properties": {"artifact_digest": {"type": "string", "pattern": DIGEST}, "runtime": {"type": "string"},
                                          "profile_id": {"type": "string"}, "compatible": {"type": "boolean"},
                                          "tested_at": INT, "evidence_id": {"type": "string", "pattern": ID}}}}},
    },
    "PK_RUNTIME_LIFECYCLE/1": {
        "$id": "urn:gap15:schema:lifecycle:1", "type": "object", "additionalProperties": False,
        "required": ["schema", "partition", "revision", "runtimes"],
        "properties": {"schema": {"const": "PK_RUNTIME_LIFECYCLE/1"}, "partition": {"type": "string"}, "revision": INT,
                       "runtimes": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                    "required": ["runtime", "state", "effective_at"],
                                    "properties": {"runtime": {"type": "string"},
                                                   "state": {"enum": ["active", "deprecated", "blocked-for-new", "end-of-life", "revoked", "reactivated-by-waiver"]},
                                                   "effective_at": INT, "replacement": {"type": ["string", "null"]},
                                                   "reason": {"type": "string"}, "waiver_id": {"type": ["string", "null"]}}}}},
    },
}


class SchemaError(ValueError):
    def __init__(self, code: str, path: str, detail: str) -> None:
        super().__init__(f"{code} at {path}: {detail}")
        self.code, self.path, self.detail = code, path, detail


_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is_type(v: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def _validate(v: Any, s: dict, path: str) -> None:
    if "const" in s and v != s["const"]:
        raise SchemaError("E_SCHEMA_CONST", path, f"expected {s['const']!r}")
    if "enum" in s and v not in s["enum"]:
        raise SchemaError("E_SCHEMA_ENUM", path, "value not in enumeration")
    if "type" in s:
        types = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_is_type(v, t) for t in types):
            raise SchemaError("E_SCHEMA_TYPE", path, f"expected {types}")
    if isinstance(v, str):
        if len(v) > s.get("maxLength", 8192):
            raise SchemaError("E_SCHEMA_LENGTH", path, "string too long")
        if "pattern" in s and not re.fullmatch(s["pattern"].strip("^$"), v):
            raise SchemaError("E_SCHEMA_PATTERN", path, "does not match identifier grammar")
    if isinstance(v, int) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]:
            raise SchemaError("E_SCHEMA_RANGE", path, "below minimum")
        if "maximum" in s and v > s["maximum"]:
            raise SchemaError("E_SCHEMA_RANGE", path, "above maximum")
    if isinstance(v, dict):
        for r in s.get("required", []):
            if r not in v:
                raise SchemaError("E_SCHEMA_REQUIRED", f"{path}.{r}", "missing required field")
        props = s.get("properties", {})
        if s.get("additionalProperties") is False:
            extra = sorted(set(v) - set(props))
            if extra:
                raise SchemaError("E_SCHEMA_UNKNOWN_FIELD", f"{path}.{extra[0]}", "unknown field")
        for k, sub in props.items():
            if k in v:
                if v[k] is None and "null" not in (sub.get("type") if isinstance(sub.get("type"), list) else [sub.get("type")]):
                    raise SchemaError("E_SCHEMA_NULL", f"{path}.{k}", "null is not absent")
                _validate(v[k], sub, f"{path}.{k}")
    if isinstance(v, list):
        if len(v) > s.get("maxItems", 4096):
            raise SchemaError("E_SCHEMA_SIZE", path, "too many items")
        for i, item in enumerate(v):
            if "items" in s:
                _validate(item, s["items"], f"{path}[{i}]")


def semantic_checks(schema_id: str, v: dict) -> None:
    if schema_id == "GAP15_EVIDENCE/1":
        if v["result"] == "incompatible" and "failure_class" not in v:
            raise SchemaError("E_SCHEMA_SEMANTIC", "$.failure_class", "incompatible evidence must classify the failure")
        if v["result"] == "compatible" and "failure_class" in v:
            raise SchemaError("E_SCHEMA_SEMANTIC", "$.failure_class", "compatible evidence carries no failure class")
        if v["signature"]["signed_at"] < v["observed_at"]:
            raise SchemaError("E_SCHEMA_SEMANTIC", "$.signature.signed_at", "signed before the test was observed")
    if schema_id == "PK_CERTIFICATION/1":
        if v["deployable"] and v["verdict"] != "certified":
            raise SchemaError("E_SCHEMA_SEMANTIC", "$.deployable", "only a certified verdict may be deployable")
        if v["verdict"] == "certified" and not {"tested_at", "expires_at"} <= set(v):
            raise SchemaError("E_SCHEMA_SEMANTIC", "$", "certified verdict must carry tested_at and expires_at")


def validate(schema_id: str, value: Any) -> None:
    if schema_id not in SCHEMAS:
        raise SchemaError("E_SCHEMA_UNSUPPORTED", "$", f"unsupported schema {schema_id!r}")
    _validate(value, SCHEMAS[schema_id], "$")
    semantic_checks(schema_id, value)


def publish(directory: str) -> list:
    os.makedirs(directory, exist_ok=True)
    out = []
    for sid, schema in sorted(SCHEMAS.items()):
        doc = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": sid,
               "x-gap15-schema-set": SCHEMA_SET_VERSION, **schema}
        name = sid.replace("/", "_v") + ".schema.json"
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
        out.append(path)
    return out


def diff(old: dict, new: dict, path: str = "$") -> list:
    """Return breaking changes between two schema dicts (empty list => compatible)."""
    breaks = []
    if old.get("type") != new.get("type"):
        breaks.append(f"{path}: type {old.get('type')} -> {new.get('type')}")
    if "enum" in old and "enum" in new and set(old["enum"]) - set(new["enum"]):
        breaks.append(f"{path}: enum narrowed (removed {sorted(set(old['enum']) - set(new['enum']))})")
    new_req = set(new.get("required", [])) - set(old.get("required", []))
    if new_req:
        breaks.append(f"{path}: new required fields {sorted(new_req)}")
    for k, sub in old.get("properties", {}).items():
        if k not in new.get("properties", {}):
            breaks.append(f"{path}.{k}: property removed")
        else:
            breaks.extend(diff(sub, new["properties"][k], f"{path}.{k}"))
    if old.get("additionalProperties") is not False and new.get("additionalProperties") is False:
        breaks.append(f"{path}: now rejects unknown fields")
    if old.get("maxLength", 8192) > new.get("maxLength", 8192):
        breaks.append(f"{path}: maxLength reduced")
    return breaks
