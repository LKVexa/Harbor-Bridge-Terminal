"""Minimal, dependency-free JSON Schema (2020-12 subset) validator.

Supports exactly the keywords the INV-35 schemas use: type, const, enum,
required, properties, additionalProperties, items, minimum, maximum, minItems,
maxItems, minLength, pattern, oneOf, $ref (local ``#/$defs/...``).  Unknown
keywords raise so a schema cannot silently rely on unsupported validation.
"""
from __future__ import annotations

import re
from typing import Any

SUPPORTED = {"$schema", "$id", "$defs", "$ref", "title", "description", "default", "type", "const", "enum",
             "required", "properties", "additionalProperties", "items", "minimum", "maximum", "minItems",
             "maxItems", "minLength", "pattern", "oneOf"}
_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class SchemaError(ValueError):
    pass


def validate(instance: Any, schema: dict[str, Any], *, root: dict[str, Any] | None = None, path: str = "$") -> None:
    root = root or schema
    unknown = set(schema) - SUPPORTED
    if unknown:
        raise SchemaError(f"schema at {path} uses unsupported keywords {sorted(unknown)}")
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise SchemaError(f"only local $defs refs supported: {ref}")
        return validate(instance, root["$defs"][ref.split("/")[-1]], root=root, path=path)
    if "oneOf" in schema:
        hits = 0
        for sub in schema["oneOf"]:
            try:
                validate(instance, sub, root=root, path=path)
                hits += 1
            except SchemaError:
                pass
        if hits != 1:
            raise SchemaError(f"{path}: matched {hits} of oneOf")
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](instance) for x in types):
            raise SchemaError(f"{path}: expected {t}, got {type(instance).__name__}")
    if "const" in schema and instance != schema["const"]:
        raise SchemaError(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaError(f"{path}: {instance!r} not in enum")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaError(f"{path}: {instance} < {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaError(f"{path}: {instance} > {schema['maximum']}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise SchemaError(f"{path}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            raise SchemaError(f"{path}: {instance!r} !~ {schema['pattern']}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                raise SchemaError(f"{path}: missing required {key!r}")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                validate(value, props[key], root=root, path=f"{path}.{key}")
            elif extra is False:
                raise SchemaError(f"{path}: unexpected property {key!r}")
            elif isinstance(extra, dict):
                validate(value, extra, root=root, path=f"{path}.{key}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise SchemaError(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SchemaError(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for i, value in enumerate(instance):
                validate(value, schema["items"], root=root, path=f"{path}[{i}]")
