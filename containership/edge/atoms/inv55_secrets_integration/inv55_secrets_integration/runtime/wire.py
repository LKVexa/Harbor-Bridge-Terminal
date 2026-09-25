"""Minimal JSON-Schema subset validator + wire schemas (checklist #17, #23).

Supports: type, enum, const, required, properties, additionalProperties(false),
pattern, minLength, maxLength, minimum, maximum, items, minItems, maxItems.
The same schemas are shipped as files under ``schemas/`` (draft 2020-12
compatible) so non-Python clients can validate against them.
"""
from __future__ import annotations

import json
import pathlib
import re

_T = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
SCHEMA_DIR = pathlib.Path(__file__).resolve().parents[1] / "schemas"


def _type_ok(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _T[t])


def validate(v, s, path="$") -> list[str]:
    e = []
    if "type" in s:
        ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_type_ok(v, t) for t in ts):
            return [f"{path}: expected {s['type']}"]
    if "enum" in s and v not in s["enum"]:
        e.append(f"{path}: not in enum")
    if "const" in s and v != s["const"]:
        e.append(f"{path}: const mismatch")
    if isinstance(v, str):
        if len(v) < s.get("minLength", 0):
            e.append(f"{path}: too short")
        if "maxLength" in s and len(v) > s["maxLength"]:
            e.append(f"{path}: too long")
        if "pattern" in s and not re.search(s["pattern"], v):
            e.append(f"{path}: pattern mismatch")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]:
            e.append(f"{path}: below minimum")
        if "maximum" in s and v > s["maximum"]:
            e.append(f"{path}: above maximum")
    if isinstance(v, dict):
        for r in s.get("required", []):
            if r not in v:
                e.append(f"{path}.{r}: required")
        props = s.get("properties", {})
        for k, sub in v.items():
            if k in props:
                e += validate(sub, props[k], f"{path}.{k}")
            elif s.get("additionalProperties") is False:
                e.append(f"{path}.{k}: additional property")
    if isinstance(v, list):
        if len(v) < s.get("minItems", 0):
            e.append(f"{path}: too few items")
        if "maxItems" in s and len(v) > s["maxItems"]:
            e.append(f"{path}: too many items")
        if "items" in s:
            for i, it in enumerate(v):
                e += validate(it, s["items"], f"{path}[{i}]")
    return e


_ID = "^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$"
_NAME = "^[a-z0-9-]{1,63}/[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$"   # <tenant>/<path>
_VERS = {"type": "array", "minItems": 1, "maxItems": 8, "items": {"type": "string", "maxLength": 32}}
_EXT = {"type": "object"}  # tolerant-reader extension bag

SCHEMAS = {
    "PK_SECRET_RESOLVE/1.request": {
        "$id": "PK_SECRET_RESOLVE/1.request", "type": "object", "additionalProperties": False,
        "required": ["versions", "request_id", "name"],
        "properties": {"versions": _VERS, "request_id": {"type": "string", "pattern": "^[A-Za-z0-9-]{8,64}$"},
                       "name": {"type": "string", "pattern": _NAME},
                       "version": {"type": "integer", "minimum": 1, "maximum": 1000000},
                       "ttl_s": {"type": "number", "minimum": 1, "maximum": 86400}, "ext": _EXT}},
    "PK_SECRET_RESOLVE/1.response": {
        "$id": "PK_SECRET_RESOLVE/1.response", "type": "object", "additionalProperties": False,
        "required": ["protocol", "request_id", "outcome", "lease"],
        "properties": {"protocol": {"const": "PK_SECRET_RESOLVE/1"}, "request_id": {"type": "string"},
                       "outcome": {"enum": ["SUCCESS", "DEGRADED"]},
                       "lease": {"type": "object", "additionalProperties": False,
                                 "required": ["lease_id", "name", "version", "expires_in_s"],
                                 "properties": {"lease_id": {"type": "string"}, "name": {"type": "string"},
                                                "version": {"type": "integer"}, "expires_in_s": {"type": "number"}}}}},
    "PK_SECRET_ROTATE/1.request": {
        "$id": "PK_SECRET_ROTATE/1.request", "type": "object", "additionalProperties": False,
        "required": ["versions", "request_id", "name", "idempotency_key"],
        "properties": {"versions": _VERS, "request_id": {"type": "string", "pattern": "^[A-Za-z0-9-]{8,64}$"},
                       "name": {"type": "string", "pattern": _NAME},
                       "idempotency_key": {"type": "string", "pattern": "^[A-Za-z0-9-]{8,64}$"},
                       "expected_version": {"type": "integer", "minimum": 0}, "ext": _EXT}},
    "PK_SECRET_SCOPE/1.request": {
        "$id": "PK_SECRET_SCOPE/1.request", "type": "object", "additionalProperties": False,
        "required": ["versions", "request_id", "name", "members"],
        "properties": {"versions": _VERS, "request_id": {"type": "string", "pattern": "^[A-Za-z0-9-]{8,64}$"},
                       "name": {"type": "string", "pattern": _NAME},
                       "members": {"type": "array", "minItems": 1, "maxItems": 1024,
                                   "items": {"type": "string", "pattern": "^[a-z0-9-]{1,63}/[A-Za-z0-9._-]{1,128}$"}},
                       "ext": _EXT}},
    "error": {
        "$id": "PK_SECRET/error", "type": "object", "additionalProperties": False, "required": ["error"],
        "properties": {"error": {"type": "object", "additionalProperties": False,
                                 "required": ["code", "outcome", "message", "reason"],
                                 "properties": {"code": {"type": "string", "pattern": "^INV55-E-[A-Z-]+$"},
                                                "outcome": {"enum": ["DEGRADED", "RETRYABLE", "TERMINAL", "DENIED"]},
                                                "message": {"type": "string"}, "reason": {"type": "string"},
                                                "retry_after_ms": {"type": "integer"}, "request_id": {"type": "string"}}}}},
}


def write_schema_files(out=SCHEMA_DIR):
    out.mkdir(parents=True, exist_ok=True)
    for k, s in SCHEMAS.items():
        (out / f"{k.replace('/', '_')}.schema.json").write_text(
            json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", **s}, indent=2, sort_keys=True) + "\n")
