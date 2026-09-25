"""Component 30 support - a small, dependency-free JSON Schema (2020-12 subset)
validator sufficient for the bundled GAP-10 schemas: type, const, enum,
required, properties, additionalProperties, minimum/maximum,
exclusiveMinimum/exclusiveMaximum, minLength/maxLength, items, minItems,
maxItems, pattern. Unsupported keywords raise so a schema can never be
silently under-validated."""
from __future__ import annotations

import json
import math
import pathlib
import re

SUPPORTED = {"$schema", "$id", "title", "description", "type", "const", "enum", "required", "properties",
             "additionalProperties", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
             "minLength", "maxLength", "items", "minItems", "maxItems", "pattern", "default", "$comment"}

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v),
}


def validate(instance, schema, path="$") -> list[str]:
    errs: list[str] = []
    unknown = set(schema) - SUPPORTED
    if unknown:
        raise ValueError(f"unsupported schema keywords at {path}: {sorted(unknown)}")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPES[t](instance) for t in types):
            return [f"{path}: expected {types}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: not in enum")
    num = _TYPES["number"](instance)
    if num:
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: > maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errs.append(f"{path}: <= exclusiveMinimum {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errs.append(f"{path}: >= exclusiveMaximum {schema['exclusiveMaximum']}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append(f"{path}: does not match pattern")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errs.append(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for i, item in enumerate(instance):
                errs.extend(validate(item, schema["items"], f"{path}[{i}]"))
    if isinstance(instance, dict):
        for r in schema.get("required", []):
            if r not in instance:
                errs.append(f"{path}: missing required {r!r}")
        props = schema.get("properties", {})
        for k, v in instance.items():
            if k in props:
                errs.extend(validate(v, props[k], f"{path}.{k}"))
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected property {k!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                errs.extend(validate(v, schema["additionalProperties"], f"{path}.{k}"))
    return errs


def load_schemas(schema_dir: pathlib.Path) -> dict[str, dict]:
    out = {}
    for p in sorted(schema_dir.glob("*.schema.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        out[s["title"]] = s
    return out
