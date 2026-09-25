"""GAP11-P0-12 versioned wire schemas (+ stdlib validator and limits).

Schemas are JSON-Schema-shaped dicts (draft 2020-12 subset) and are also written to
``gap11_control/schemas/*.schema.json`` by ``tools/build_artifacts.py``.
Compatibility policy (see docs/COMPATIBILITY.md): within a major version only
additive OPTIONAL fields; readers ignore unknown fields only where
``additionalProperties`` is true (responses), requests are closed (false) so a
misspelt field is an error instead of silently ignored; enum growth is a minor
bump that old readers must map to ``UNKNOWN``; removal/rename is a new major.
"""
from __future__ import annotations

import json
from typing import Any

from .common import REASON_CODES, ControlError

MAX_MESSAGE_BYTES = 64 * 1024
MAX_DEPTH = 8
MAX_STRING = 256
MAX_ITEMS = 256

_id = {"type": "string", "minLength": 1, "maxLength": 128, "pattern": r"^[A-Za-z0-9._:\-]+$"}
_rid = {"type": "string", "minLength": 8, "maxLength": 128, "pattern": r"^[A-Za-z0-9._:\-]+$"}
_trace = {"type": "string", "pattern": r"^00-[0-9a-f]{32}-[0-9a-f]{16}-0[01]$"}

SCHEMAS: dict[str, dict[str, Any]] = {
    "PK_ACCELERATOR_ALLOCATION_REQUEST/1": {
        "type": "object", "additionalProperties": False,
        "required": ["schema", "request_id", "tenant", "workload"],
        "properties": {
            "schema": {"const": "PK_ACCELERATOR_ALLOCATION_REQUEST/1"}, "request_id": _rid,
            "tenant": _id, "workload": _id, "memory_gb": {"type": "integer", "minimum": 0, "maximum": 4096},
            "kind": {"enum": ["gpu", "npu", "fpga", "generic"]}, "generation": _id,
            "features": {"type": "array", "items": _id, "maxItems": 64, "uniqueItems": True},
            "partition": _id, "priority": {"enum": ["low", "normal", "high"]},
            "deadline_ms": {"type": "integer", "minimum": 1, "maximum": 600000}, "traceparent": _trace,
        },
    },
    "PK_ACCELERATOR_ALLOCATION/1": {
        "type": "object", "additionalProperties": True,
        "required": ["schema", "lease_id", "device", "tenant", "workload", "partition", "fencing_token"],
        "properties": {"schema": {"const": "PK_ACCELERATOR_ALLOCATION/1"}, "lease_id": {"type": "string", "pattern": r"^[0-9a-f]{32}$"},
                       "device": _id, "tenant": _id, "workload": _id, "partition": {"type": ["string", "null"]},
                       "fencing_token": {"type": "integer", "minimum": 1}, "ttl_seconds": {"type": "number"}},
    },
    "PK_ACCELERATOR_RELEASE_REQUEST/1": {
        "type": "object", "additionalProperties": False, "required": ["schema", "request_id", "lease_id"],
        "properties": {"schema": {"const": "PK_ACCELERATOR_RELEASE_REQUEST/1"}, "request_id": _rid,
                       "lease_id": {"type": "string", "pattern": r"^[0-9a-f]{32}$"}, "traceparent": _trace},
    },
    "PK_ACCELERATOR_RELEASE/1": {
        "type": "object", "additionalProperties": True, "required": ["schema", "lease_id", "device", "released"],
        "properties": {"schema": {"const": "PK_ACCELERATOR_RELEASE/1"}, "lease_id": {"type": "string"},
                       "device": _id, "released": {"type": "boolean"}},
    },
    "PK_SCRUB_REQUEST/1": {
        "type": "object", "additionalProperties": False, "required": ["schema", "request_id", "device"],
        "properties": {"schema": {"const": "PK_SCRUB_REQUEST/1"}, "request_id": _rid, "device": _id, "traceparent": _trace},
    },
    "PK_SCRUB/1": {
        "type": "object", "additionalProperties": True, "required": ["schema", "device", "completed", "quarantined"],
        "properties": {"schema": {"const": "PK_SCRUB/1"}, "device": _id, "completed": {"type": "boolean"}, "quarantined": {"type": "boolean"}},
    },
    "PK_ACCELERATOR_INVENTORY/1": {
        "type": "object", "additionalProperties": True, "required": ["schema", "devices"],
        "properties": {"schema": {"const": "PK_ACCELERATOR_INVENTORY/1"},
                       "devices": {"type": "array", "maxItems": 4096, "items": {"type": "object", "required": ["device", "kind", "memory_gb"],
                                   "properties": {"device": _id, "kind": {"type": "string"}, "memory_gb": {"type": "integer", "minimum": 1}}}}},
    },
    "PK_ERROR/1": {
        "type": "object", "additionalProperties": False, "required": ["schema", "code", "message"],
        "properties": {"schema": {"const": "PK_ERROR/1"}, "code": {"enum": sorted(REASON_CODES)},
                       "message": {"type": "string", "maxLength": 512}, "request_id": {"type": "string"},
                       "retryable": {"type": "boolean"}, "details": {"type": "object"}},
    },
}

RETRYABLE = {"OVERLOADED", "DEADLINE_EXCEEDED", "STORE_UNAVAILABLE", "DEPENDENCY_UNAVAILABLE", "NOT_LEADER", "STALE_REVISION"}
HTTP_STATUS = {"SCHEMA_INVALID": 400, "MESSAGE_TOO_LARGE": 413, "UNAUTHENTICATED": 401, "REPLAY_DETECTED": 401,
               "POLICY_DENIED": 403, "LEASE_NOT_FOUND": 404, "IDEMPOTENCY_CONFLICT": 409, "STALE_REVISION": 409,
               "STALE_FENCE": 409, "ILLEGAL_TRANSITION": 409, "CAPACITY_EXHAUSTED": 409, "QUOTA_EXCEEDED": 429,
               "OVERLOADED": 503, "DEADLINE_EXCEEDED": 504, "NOT_LEADER": 503, "MAINTENANCE_MODE": 503,
               "DEPENDENCY_UNAVAILABLE": 503, "STORE_UNAVAILABLE": 503}


def _type_ok(v: Any, t: Any) -> bool:
    types = t if isinstance(t, list) else [t]
    m = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
    for ty in types:
        if ty == "integer" and isinstance(v, int) and not isinstance(v, bool):
            return True
        if ty == "number" and isinstance(v, (int, float)) and not isinstance(v, bool):
            return True
        if ty in m and isinstance(v, m[ty]):
            return True
    return False


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    import re
    errs: list[str] = []
    if "const" in schema and instance != schema["const"]:
        return [f"{path}: expected const {schema['const']!r}"]
    if "enum" in schema and instance not in schema["enum"]:
        return [f"{path}: not in enum"]
    if "type" in schema and not _type_ok(instance, schema["type"]):
        return [f"{path}: wrong type"]
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0) or len(instance) > schema.get("maxLength", MAX_STRING * 4):
            errs.append(f"{path}: length out of range")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], instance):
            errs.append(f"{path}: pattern mismatch")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(instance, list):
        if len(instance) > schema.get("maxItems", MAX_ITEMS):
            errs.append(f"{path}: too many items")
        if schema.get("uniqueItems") and len({json.dumps(i, sort_keys=True) for i in instance}) != len(instance):
            errs.append(f"{path}: duplicate items")
        for i, item in enumerate(instance):
            if "items" in schema:
                errs += validate(item, schema["items"], f"{path}[{i}]")
    if isinstance(instance, dict):
        for r in schema.get("required", []):
            if r not in instance:
                errs.append(f"{path}.{r}: required")
        props = schema.get("properties", {})
        for k, v in instance.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties", True) is False:
                errs.append(f"{path}.{k}: unknown field")
    return errs


def _depth(v: Any, d: int = 0) -> int:
    if d > MAX_DEPTH:
        return d
    if isinstance(v, dict):
        return max([_depth(x, d + 1) for x in v.values()] or [d + 1])
    if isinstance(v, list):
        return max([_depth(x, d + 1) for x in v] or [d + 1])
    return d


def decode(raw: bytes, schema_name: str) -> dict[str, Any]:
    """Size limit -> strict UTF-8 JSON -> depth limit -> schema. Every failure is typed."""
    if not isinstance(raw, (bytes, bytearray)):
        raise ControlError("SCHEMA_INVALID", "body must be bytes")
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ControlError("MESSAGE_TOO_LARGE", size=len(raw), limit=MAX_MESSAGE_BYTES)

    def no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate key")
        return dict(pairs)

    try:
        obj = json.loads(bytes(raw).decode("utf-8"), object_pairs_hook=no_dupes,
                         parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ControlError("SCHEMA_INVALID", "body is not strict UTF-8 JSON") from exc
    if _depth(obj) > MAX_DEPTH:
        raise ControlError("MESSAGE_TOO_LARGE", "nesting too deep")
    if schema_name not in SCHEMAS:
        raise ControlError("SCHEMA_INVALID", f"unknown schema {schema_name}")
    errs = validate(obj, SCHEMAS[schema_name])
    if errs:
        raise ControlError("SCHEMA_INVALID", "; ".join(errs[:5]), errors=len(errs))
    return obj


def error_envelope(exc: ControlError, request_id: str | None = None) -> dict[str, Any]:
    safe_details = {k: v for k, v in exc.details.items() if isinstance(v, (str, int, bool, type(None))) and k not in ("tenant", "previous_tenant")}
    env = {"schema": "PK_ERROR/1", "code": exc.code, "message": str(exc)[:512], "retryable": exc.code in RETRYABLE,
           "details": safe_details}
    if request_id:
        env["request_id"] = request_id
    return env
