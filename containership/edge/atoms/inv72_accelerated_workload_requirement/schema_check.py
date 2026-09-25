"""Versioned machine-readable schemas and a strict stdlib validator (C022, C027, C029, C082).

The JSON Schema documents under ``schemas/`` are the published contract.  ``validate`` implements the
subset of JSON Schema those documents use (type, required, properties, additionalProperties=false,
enum, const, minimum/maximum, minLength/maxLength, pattern, items, minItems/maxItems, uniqueItems) so the
contract can be enforced with no third-party dependency.  Unknown keywords in a schema are an error, so
a schema edit cannot silently weaken validation.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
SUPPORTED_KEYWORDS = {"$schema", "$id", "title", "description", "type", "required", "properties",
                      "additionalProperties", "enum", "const", "minimum", "maximum", "exclusiveMinimum",
                      "minLength", "maxLength", "pattern", "items", "minItems", "maxItems", "uniqueItems",
                      "x-version", "x-compat"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


class SchemaError(ValueError):
    pass


def load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def _is_type(value: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    return isinstance(value, _TYPES[t])


def validate(value: Any, schema: dict, path: str = "$") -> list[str]:
    errs: list[str] = []
    unknown = set(schema) - SUPPORTED_KEYWORDS
    if unknown:
        raise SchemaError(f"unsupported schema keywords at {path}: {sorted(unknown)}")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, t) for t in types):
            return [f"{path}: expected {'/'.join(types)}"]
    if "const" in schema and value != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: not in {schema['enum']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: below minimum {schema['minimum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errs.append(f"{path}: not above {schema['exclusiveMinimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: above maximum {schema['maximum']}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errs.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            errs.append(f"{path}: items not unique")
        if "items" in schema:
            for i, v in enumerate(value):
                errs += validate(v, schema["items"], f"{path}[{i}]")
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errs.append(f"{path}: missing {k!r}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in value:
                if k not in props:
                    errs.append(f"{path}: unexpected property {k!r}")
        for k, sub in props.items():
            if k in value:
                errs += validate(value[k], sub, f"{path}.{k}")
    return errs


def check(value: Any, name: str) -> list[str]:
    return validate(value, load(name))


ALL = ("PK_ACCEL_REQ-1", "PK_ACCEL_INVENTORY-1", "PK_ACCEL_MATCH-1", "PK_ACCEL_ERROR-1",
       "PK_ACCEL_CONFIG-1", "PK_ACCEL_AUDIT_EVENT-1", "PK_ACCEL_STATUS-1")
