"""Minimal, strict JSON-Schema subset validator (stdlib only) for INV-44.

Supports: type, enum, const, required, properties, additionalProperties
(bool), items, minItems, maxItems, uniqueItems, minimum, maximum, minLength,
maxLength, pattern, $ref to "#/$defs/...". Any other keyword in a schema is an
error, so a schema can never silently rely on an unenforced keyword.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
_KNOWN = {"$schema", "$id", "$defs", "$ref", "title", "description", "type", "enum", "const",
          "required", "properties", "additionalProperties", "items", "minItems", "maxItems",
          "uniqueItems", "minimum", "maximum", "minLength", "maxLength", "pattern", "x-version"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def validate(instance: object, schema: dict, *, root: dict | None = None, path: str = "$") -> list[str]:
    root = schema if root is None else root
    errs: list[str] = []
    unknown = set(schema) - _KNOWN
    if unknown:
        return [f"{path}: schema uses unsupported keywords {sorted(unknown)}"]
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            return [f"{path}: unsupported $ref {ref}"]
        return validate(instance, root["$defs"][ref[8:]], root=root, path=path)
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        ok = False
        for ty in types:
            if ty == "integer":
                ok |= isinstance(instance, int) and not isinstance(instance, bool)
            elif ty == "number":
                ok |= isinstance(instance, (int, float)) and not isinstance(instance, bool)
            else:
                ok |= isinstance(instance, _TYPES[ty])
        if not ok:
            return [f"{path}: expected {t}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errs.append(f"{path}: shorter than minLength")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errs.append(f"{path}: longer than maxLength")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], instance):
            errs.append(f"{path}: does not match pattern")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: above maximum {schema['maximum']}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errs.append(f"{path}: fewer than minItems")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errs.append(f"{path}: more than maxItems")
        if schema.get("uniqueItems") and len({json.dumps(i, sort_keys=True) for i in instance}) != len(instance):
            errs.append(f"{path}: items not unique")
        if "items" in schema:
            for i, item in enumerate(instance):
                errs += validate(item, schema["items"], root=root, path=f"{path}[{i}]")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errs.append(f"{path}: missing required {key!r}")
        props = schema.get("properties", {})
        for key, val in instance.items():
            if key in props:
                errs += validate(val, props[key], root=root, path=f"{path}.{key}")
            elif schema.get("additionalProperties", True) is False:
                errs.append(f"{path}: unexpected property {key!r}")
    return errs
