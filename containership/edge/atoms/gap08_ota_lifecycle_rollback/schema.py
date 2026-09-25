"""Typed external API schemas (component 20): loader and stdlib validator.

Implements the JSON-Schema subset used by ``schemas/*.schema.json``: type,
const, enum, required, properties, additionalProperties (bool or schema),
items, minItems, minLength, minimum, pattern and local ``$ref``.  Production
deployments may validate with a full JSON-Schema implementation; the schema
files are standard draft 2020-12.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .errors import ValidationFailed

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


@lru_cache(maxsize=None)
def load(name: str) -> dict[str, Any]:
    fn = name if name.endswith(".json") else name.replace("/", "_") + ".schema.json"
    return json.loads((SCHEMA_DIR / fn).read_text())


def _type_ok(value: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[t])


def errors(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    if "$ref" in schema:
        return errors(value, load(schema["$ref"]), path)
    out: list[str] = []
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_type_ok(value, x) for x in ts):
            return [f"{path}: expected {t}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        out.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            out.append(f"{path}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and "minimum" in schema \
            and value < schema["minimum"]:
        out.append(f"{path}: below minimum {schema['minimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            out.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, v in enumerate(value):
                out.extend(errors(v, schema["items"], f"{path}[{i}]"))
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                out.append(f"{path}: missing required {k}")
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties", True)
        for k, v in value.items():
            if k in props:
                out.extend(errors(v, props[k], f"{path}.{k}"))
            elif addl is False:
                out.append(f"{path}: unexpected property {k}")
            elif isinstance(addl, dict):
                out.extend(errors(v, addl, f"{path}.{k}"))
    return out


def validate(value: Any, schema_id: str) -> None:
    errs = errors(value, load(schema_id))
    if errs:
        raise ValidationFailed(f"{schema_id} validation failed: {errs[:5]}", errors=errs)
