"""Minimal JSON Schema 2020-12 subset validator (stdlib) for contract tests.

Supports: $ref (sibling file), type, const, enum, required, properties,
additionalProperties (bool|schema), items, minItems, maxItems, minLength,
maxLength, pattern, minimum, maximum, exclusiveMinimum, oneOf.  Anything else
in a schema raises, so an unsupported keyword can never be silently ignored.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
_KNOWN = {"$schema", "$id", "title", "description", "$ref", "type", "const", "enum", "required", "properties",
          "additionalProperties", "items", "minItems", "maxItems", "minLength", "maxLength", "pattern", "minimum",
          "maximum", "exclusiveMinimum", "oneOf"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


class SchemaError(ValueError):
    pass


@lru_cache(maxsize=None)
def load(name: str) -> dict[str, Any]:
    fname = name if name.endswith(".json") else name.replace("/", "-") + ".schema.json"
    return json.loads((SCHEMA_DIR / fname).read_text(encoding="utf-8"))


def _type_ok(v: Any, t: str) -> bool:
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "integer":
        return (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, float) and v.is_integer())
    return isinstance(v, _TYPES[t])


def validate(value: Any, schema: dict[str, Any] | str, path: str = "$") -> None:
    if isinstance(schema, str):
        schema = load(schema)
    unknown = set(schema) - _KNOWN
    if unknown:
        raise SchemaError(f"unsupported keywords {unknown} at {path}")
    if "$ref" in schema:
        validate(value, load(schema["$ref"]), path)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, t) for t in types):
            raise SchemaError(f"{path}: expected {types}, got {type(value).__name__}")
    if "const" in schema and value != schema["const"]:
        raise SchemaError(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaError(f"{path}: {value!r} not in enum")
    if isinstance(value, dict):
        for r in schema.get("required", []):
            if r not in value:
                raise SchemaError(f"{path}: missing {r}")
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties", True)
        for k, v in value.items():
            if k in props:
                validate(v, props[k], f"{path}.{k}")
            elif addl is False:
                raise SchemaError(f"{path}: unexpected property {k}")
            elif isinstance(addl, dict):
                validate(v, addl, f"{path}.{k}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", 10**12):
            raise SchemaError(f"{path}: array length out of bounds")
        if "items" in schema:
            for i, v in enumerate(value):
                validate(v, schema["items"], f"{path}[{i}]")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 10**12):
            raise SchemaError(f"{path}: string length out of bounds")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise SchemaError(f"{path}: pattern mismatch")
    if _type_ok(value, "number"):
        if "minimum" in schema and value < schema["minimum"]:
            raise SchemaError(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise SchemaError(f"{path}: above maximum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            raise SchemaError(f"{path}: not above exclusiveMinimum")
    if "oneOf" in schema:
        ok = 0
        for sub in schema["oneOf"]:
            try:
                validate(value, sub, path)
                ok += 1
            except SchemaError:
                pass
        if ok != 1:
            raise SchemaError(f"{path}: matched {ok} oneOf branches")
