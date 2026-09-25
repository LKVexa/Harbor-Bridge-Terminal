"""Minimal, dependency-free JSON Schema (2020-12 subset) validator (MC-012/013/014/022).

Supports: type, const, enum, required, properties, additionalProperties,
items, minItems, maxItems, minLength, maxLength, pattern, minimum, maximum,
and ``$ref`` to any bundled schema ``$id``.  The test-suite cross-checks this
validator against the reference ``jsonschema`` package when it is installed.
"""
from __future__ import annotations

import json
import pathlib
import re
from functools import lru_cache
from typing import Any

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


@lru_cache(maxsize=None)
def registry() -> dict[str, dict]:
    out = {}
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        doc = json.loads(path.read_text("utf-8"))
        out[doc["$id"]] = doc
    return out


def schema_by_id(schema_id: str) -> dict:
    return registry()[schema_id]


def _type_ok(value: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[t]) and not (t != "boolean" and isinstance(value, bool) and _TYPES[t] is not bool)


def validate(value: Any, schema: dict | str, path: str = "$", limit: int = 50) -> list[str]:
    """Return a list of human-readable violations (empty means valid)."""
    if isinstance(schema, str):
        schema = schema_by_id(schema)
    errors: list[str] = []
    _walk(value, schema, path, errors, limit)
    return errors


def _walk(v: Any, s: dict, p: str, errs: list[str], limit: int) -> None:
    if len(errs) >= limit:
        return
    if "$ref" in s:
        _walk(v, schema_by_id(s["$ref"]), p, errs, limit)
        return
    if "const" in s and v != s["const"]:
        errs.append(f"{p}: must equal {s['const']!r}")
        return
    if "enum" in s and v not in s["enum"]:
        errs.append(f"{p}: must be one of {s['enum']}")
        return
    if "type" in s:
        types = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_type_ok(v, t) for t in types):
            errs.append(f"{p}: expected type {s['type']}")
            return
    if isinstance(v, str):
        if "minLength" in s and len(v) < s["minLength"]:
            errs.append(f"{p}: shorter than {s['minLength']}")
        if "maxLength" in s and len(v) > s["maxLength"]:
            errs.append(f"{p}: longer than {s['maxLength']}")
        if "pattern" in s and re.search(s["pattern"], v) is None:
            errs.append(f"{p}: does not match pattern")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]:
            errs.append(f"{p}: below minimum {s['minimum']}")
        if "maximum" in s and v > s["maximum"]:
            errs.append(f"{p}: above maximum {s['maximum']}")
    if isinstance(v, list):
        if "minItems" in s and len(v) < s["minItems"]:
            errs.append(f"{p}: fewer than {s['minItems']} items")
        if "maxItems" in s and len(v) > s["maxItems"]:
            errs.append(f"{p}: more than {s['maxItems']} items")
            return
        if "items" in s:
            for i, item in enumerate(v):
                _walk(item, s["items"], f"{p}[{i}]", errs, limit)
    if isinstance(v, dict):
        for key in s.get("required", []):
            if key not in v:
                errs.append(f"{p}: missing required property {key!r}")
        props = s.get("properties", {})
        extra = s.get("additionalProperties", True)
        for key, item in v.items():
            if key in props:
                _walk(item, props[key], f"{p}.{key}", errs, limit)
            elif extra is False:
                errs.append(f"{p}: unexpected property {key!r}")
            elif isinstance(extra, dict):
                _walk(item, extra, f"{p}.{key}", errs, limit)
