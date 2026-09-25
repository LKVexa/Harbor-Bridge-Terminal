"""Minimal, stdlib-only JSON Schema checker for the subset the INV-28 schemas use (MC-004, MC-005, MC-040).

Supported keywords: type, const, enum, pattern, minLength, maxLength, minimum, maximum, required,
properties, additionalProperties (bool or schema), minProperties, items, minItems, maxItems,
uniqueItems, oneOf, $ref (to a sibling file id, e.g. ``"PK_TOOLCHAIN-2"``).  An *unknown* keyword
is an error, so a schema can never silently rely on a keyword this checker ignores.
"""
from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
KNOWN = {"$schema", "$id", "title", "description", "type", "const", "enum", "pattern", "minLength", "maxLength",
         "minimum", "maximum", "required", "properties", "additionalProperties", "minProperties", "items",
         "minItems", "maxItems", "uniqueItems", "oneOf", "$ref"}
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


@cache
def load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def _type_ok(t, v):
    if t == "integer":
        return type(v) is int
    if t == "number":
        return type(v) in (int, float)
    return isinstance(v, TYPES[t]) and not (t != "boolean" and type(v) is bool)


def validate(schema: dict, value, path: str = "$") -> list[str]:
    errs: list[str] = []
    unknown = set(schema) - KNOWN
    if unknown:
        return [f"{path}: schema uses unsupported keywords {sorted(unknown)}"]
    if "$ref" in schema:
        return validate(load(schema["$ref"]), value, path)
    if "oneOf" in schema:
        ok = [s for s in schema["oneOf"] if not validate(s, value, path)]
        if len(ok) != 1:
            errs.append(f"{path}: matches {len(ok)} of oneOf branches (need exactly 1)")
        return errs
    if "type" in schema and not _type_ok(schema["type"], value):
        return [f"{path}: expected {schema['type']}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in enum")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append(f"{path}: {value[:40]!r} does not match {schema['pattern']}")
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 10 ** 9):
            errs.append(f"{path}: length out of bounds")
    if type(value) in (int, float) and type(value) is not bool:
        if value < schema.get("minimum", float("-inf")) or value > schema.get("maximum", float("inf")):
            errs.append(f"{path}: {value} out of range")
    if isinstance(value, dict):
        for r in schema.get("required", []):
            if r not in value:
                errs.append(f"{path}: missing required {r!r}")
        if len(value) < schema.get("minProperties", 0):
            errs.append(f"{path}: too few properties")
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties", True)
        for k, v in value.items():
            if k in props:
                errs += validate(props[k], v, f"{path}.{k}")
            elif addl is False:
                errs.append(f"{path}: unexpected property {k!r}")
            elif isinstance(addl, dict):
                errs += validate(addl, v, f"{path}.{k}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", 10 ** 9):
            errs.append(f"{path}: item count out of bounds")
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            errs.append(f"{path}: items not unique")
        if "items" in schema:
            for i, v in enumerate(value):
                errs += validate(schema["items"], v, f"{path}[{i}]")
    return errs


def validate_file(name: str, value) -> list[str]:
    return validate(load(name), value)
