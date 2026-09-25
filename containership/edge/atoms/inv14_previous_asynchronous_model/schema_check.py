"""Minimal stdlib JSON-Schema (draft 2020-12 subset) validator for INV-14 contracts.

Supported keywords: type, const, enum, pattern, required, properties,
additionalProperties (bool), items, minItems, maxItems, minimum, maximum,
maxLength, minLength, $ref (local "#/$defs/..").  Unknown keywords in a schema are
an error (fail closed) so a schema cannot silently rely on unsupported checks.
"""
from __future__ import annotations

import json
import pathlib
import re

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
_KNOWN = {"$schema", "$id", "title", "description", "type", "const", "enum", "pattern", "required",
          "properties", "additionalProperties", "items", "minItems", "maxItems", "minimum", "maximum",
          "maxLength", "minLength", "$ref", "$defs", "x-version"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _type_ok(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def validate(instance, schema: dict, root: dict | None = None, path: str = "$") -> list:
    root = root or schema
    errs = []
    unknown = set(schema) - _KNOWN
    if unknown:
        return [f"{path}: schema uses unsupported keywords {sorted(unknown)}"]
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            return [f"{path}: unsupported $ref {ref}"]
        return validate(instance, root["$defs"][ref.split("/")[-1]], root, path)
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_type_ok(instance, x) for x in ts):
            return [f"{path}: expected {t}"]
    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: not in enum")
    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append(f"{path}: pattern mismatch")
        if len(instance) > schema.get("maxLength", 1 << 30) or len(instance) < schema.get("minLength", 0):
            errs.append(f"{path}: length out of range")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(instance, dict):
        for k in schema.get("required", []):
            if k not in instance:
                errs.append(f"{path}: missing {k}")
        props = schema.get("properties", {})
        for k, v in instance.items():
            if k in props:
                errs += validate(v, props[k], root, f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected property {k}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0) or len(instance) > schema.get("maxItems", 1 << 30):
            errs.append(f"{path}: item count out of range")
        if "items" in schema:
            for i, v in enumerate(instance):
                errs += validate(v, schema["items"], root, f"{path}[{i}]")
    return errs


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


def check(instance, name: str) -> list:
    return validate(instance, load_schema(name))
