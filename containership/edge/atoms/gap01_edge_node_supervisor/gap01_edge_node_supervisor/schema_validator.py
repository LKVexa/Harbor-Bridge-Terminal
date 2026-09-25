"""Versioned public schemas (6, 64) and a dependency-free validator for the
JSON-Schema subset they use (type, const, enum, required, properties,
additionalProperties, pattern, maxLength, minimum, maximum, items, maxItems,
maxProperties).  Compatibility rule: within a major version (``/1``) fields
may only be added as optional; removing/renaming a field or narrowing an enum
requires ``/2``.  ``x-extensions`` is the forward-compatible extension slot.
"""
from __future__ import annotations

import json
import pathlib
import re
from functools import cache
from typing import Any

DIR = pathlib.Path(__file__).resolve().parent / "schemas"
NAMES = {
    "request": "pk_node_lifecycle_1.request",
    "status": "pk_node_lifecycle_1.status",
    "drain": "pk_drain_1",
    "health": "pk_node_health_1",
    "error": "gap01_error_1",
}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


@cache
def load(name: str) -> dict:
    return json.loads((DIR / f"{NAMES[name]}.schema.json").read_text())


def _is_type(v: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def check(schema: dict, v: Any, path: str = "$") -> list[str]:
    out: list[str] = []
    if "const" in schema and v != schema["const"]:
        return [f"{path}: expected {schema['const']!r}"]
    if "enum" in schema and v not in schema["enum"]:
        return [f"{path}: not in enum"]
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_is_type(v, x) for x in ts):
            return [f"{path}: expected {t}"]
    if isinstance(v, str):
        if "maxLength" in schema and len(v) > schema["maxLength"]:
            out.append(f"{path}: too long")
        if "pattern" in schema and not re.search(schema["pattern"], v):
            out.append(f"{path}: pattern mismatch")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in schema and v < schema["minimum"]:
            out.append(f"{path}: below minimum")
        if "maximum" in schema and v > schema["maximum"]:
            out.append(f"{path}: above maximum")
    if isinstance(v, list):
        if "maxItems" in schema and len(v) > schema["maxItems"]:
            out.append(f"{path}: too many items")
        if "items" in schema:
            for i, x in enumerate(v):
                out += check(schema["items"], x, f"{path}[{i}]")
    if isinstance(v, dict):
        if "maxProperties" in schema and len(v) > schema["maxProperties"]:
            out.append(f"{path}: too many properties")
        for r in schema.get("required", []):
            if r not in v:
                out.append(f"{path}.{r}: required")
        props = schema.get("properties", {})
        for k, x in v.items():
            if k in props:
                out += check(props[k], x, f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                out.append(f"{path}.{k}: unexpected property")
    return out


def validate(name: str, doc: Any) -> list[str]:
    schema = load(name)
    problems = check(schema, doc)
    if name == "request" and not problems:
        arg_schema = schema["x-op-args"][doc["op"]]
        problems = check(arg_schema, doc["args"], "$.args")
    return problems
