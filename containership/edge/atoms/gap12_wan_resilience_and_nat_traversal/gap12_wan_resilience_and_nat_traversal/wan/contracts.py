"""Externally consumed contracts named by ``contract.py`` (G12-H086):
PK_PATH_REQUEST/1, PK_PATH_STATE/1, PK_BACKOFF/1, PK_RELAY_ACCOUNTING/1.

Schemas are declared here as data (a strict JSON-Schema subset: type, enum,
required, properties, additionalProperties=false, minimum, maxLength) and
validated by ``validate`` — stdlib only.  ``PK_PATH_STATE/1`` describes the
document the v4.2.0 ``Path.state()`` already emits; the other three are
produced by the builders below.
"""
from __future__ import annotations

import math

NUM = ["number", "null"]
SCHEMAS = {
    "PK_PATH_REQUEST/1": {
        "type": "object", "additionalProperties": False,
        "required": ["schema", "peer", "strategies", "deadline_s"],
        "properties": {
            "schema": {"enum": ["PK_PATH_REQUEST/1"]},
            "peer": {"type": "string", "maxLength": 255},
            "strategies": {"type": "array", "items": {"enum": ["direct", "hole-punch", "relay"]}},
            "deadline_s": {"type": "number", "minimum": 0.1},
            "tenant": {"type": "string", "maxLength": 64},
            "trace": {"type": ["string", "null"], "maxLength": 55},
        },
    },
    "PK_PATH_STATE/1": {
        "type": "object", "additionalProperties": False,
        "required": ["schema", "peer", "strategy", "status", "healthy", "partitioned", "last_success", "failures",
                     "backoff", "retry_at", "retry_in", "relay_bytes", "last_error"],
        "properties": {
            "schema": {"enum": ["PK_PATH_STATE/1"]},
            "peer": {"type": "string", "maxLength": 255},
            "strategy": {"enum": ["direct", "hole-punch", "relay", None]},
            "status": {"enum": ["unknown", "healthy", "stale", "backing_off", "partitioned"]},
            "healthy": {"type": "boolean"}, "partitioned": {"type": "boolean"},
            "last_success": {"type": NUM}, "failures": {"type": "integer", "minimum": 0},
            "backoff": {"type": "integer", "minimum": 0}, "retry_at": {"type": NUM},
            "retry_in": {"type": "number", "minimum": 0}, "relay_bytes": {"type": "integer", "minimum": 0},
            "last_error": {"type": ["string", "null"], "maxLength": 64},
        },
    },
    "PK_BACKOFF/1": {
        "type": "object", "additionalProperties": False,
        "required": ["schema", "peer", "failures", "bound_s", "delay_s", "ceiling_s", "retry_at"],
        "properties": {
            "schema": {"enum": ["PK_BACKOFF/1"]}, "peer": {"type": "string", "maxLength": 255},
            "failures": {"type": "integer", "minimum": 0}, "bound_s": {"type": "integer", "minimum": 0},
            "delay_s": {"type": "number", "minimum": 0}, "ceiling_s": {"type": "integer", "minimum": 1},
            "retry_at": {"type": NUM},
        },
    },
    "PK_RELAY_ACCOUNTING/1": {
        "type": "object", "additionalProperties": False,
        "required": ["schema", "peer", "active", "relay_bytes"],
        "properties": {
            "schema": {"enum": ["PK_RELAY_ACCOUNTING/1"]}, "peer": {"type": "string", "maxLength": 255},
            "active": {"type": "boolean"}, "relay_bytes": {"type": "integer", "minimum": 0},
        },
    },
}

_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _type_ok(v, t) -> bool:
    if isinstance(t, list):
        return any(_type_ok(v, x) for x in t)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    return isinstance(v, _TYPES[t])


def validate(doc, schema: dict | str, path: str = "$") -> list[str]:
    if isinstance(schema, str):
        schema = SCHEMAS[schema]
    errs = []
    if "enum" in schema and doc not in schema["enum"]:
        return [f"{path}: {doc!r} not in enum"]
    if "type" in schema and not _type_ok(doc, schema["type"]):
        return [f"{path}: wrong type {type(doc).__name__}"]
    if isinstance(doc, (int, float)) and not isinstance(doc, bool) and "minimum" in schema and doc < schema["minimum"]:
        errs.append(f"{path}: below minimum")
    if isinstance(doc, str) and "maxLength" in schema and len(doc) > schema["maxLength"]:
        errs.append(f"{path}: too long")
    if isinstance(doc, dict):
        for r in schema.get("required", []):
            if r not in doc:
                errs.append(f"{path}.{r}: missing")
        props = schema.get("properties", {})
        for k, v in doc.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}.{k}: unexpected field")
    if isinstance(doc, list) and "items" in schema:
        for i, v in enumerate(doc):
            errs += validate(v, schema["items"], f"{path}[{i}]")
    return errs


def path_request(peer: str, *, strategies=("direct", "hole-punch", "relay"), deadline_s: float = 10.0,
                 tenant: str = "default", trace: str | None = None) -> dict:
    return {"schema": "PK_PATH_REQUEST/1", "peer": peer, "strategies": list(strategies), "deadline_s": deadline_s,
            "tenant": tenant, "trace": trace}


def backoff_doc(path, ceiling: int = 60) -> dict:
    return {"schema": "PK_BACKOFF/1", "peer": path.peer, "failures": path.failures, "bound_s": path.backoff(),
            "delay_s": path.retry_delay(), "ceiling_s": ceiling, "retry_at": path.retry_at}


def relay_accounting_doc(path) -> dict:
    return {"schema": "PK_RELAY_ACCOUNTING/1", "peer": path.peer, "active": path.strategy == "relay",
            "relay_bytes": path.relay_bytes}
