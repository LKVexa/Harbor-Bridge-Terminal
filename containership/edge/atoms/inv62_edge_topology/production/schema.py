"""Minimal, dependency-free JSON-Schema (2020-12 subset) validator.

Supported keywords: type, properties, required, additionalProperties (bool or
schema), enum, const, minimum, maximum, exclusiveMinimum, minLength,
maxLength, pattern, items, minItems, maxItems, uniqueItems, $ref (local
``#/$defs/...``), oneOf, anyOf.  Unknown keywords are *rejected at schema load*
so a schema can never silently weaken because the validator ignores a rule.
"""
from __future__ import annotations

import math
import re
from typing import Any

_KNOWN = {
    "$schema", "$id", "$defs", "$ref", "title", "description", "type", "properties",
    "required", "additionalProperties", "enum", "const", "minimum", "maximum",
    "exclusiveMinimum", "minLength", "maxLength", "pattern", "items", "minItems",
    "maxItems", "uniqueItems", "oneOf", "anyOf", "default", "examples",
}


class SchemaViolation(ValueError):
    def __init__(self, path: str, message: str):
        path = "$" + path if not path.startswith("$") else path
        super().__init__(f"{path}: {message}")
        self.path = path
        self.reason = message


def check_schema(schema: Any, where: str = "#") -> None:
    """Reject schemas using keywords this validator does not implement."""
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise ValueError(f"{where}: schema must be an object")
    unknown = set(schema) - _KNOWN
    if unknown:
        raise ValueError(f"{where}: unsupported schema keywords {sorted(unknown)}")
    for key in ("properties", "$defs"):
        for name, sub in schema.get(key, {}).items():
            check_schema(sub, f"{where}/{key}/{name}")
    for key in ("items", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            check_schema(schema[key], f"{where}/{key}")
    for key in ("oneOf", "anyOf"):
        for i, sub in enumerate(schema.get(key, [])):
            check_schema(sub, f"{where}/{key}/{i}")


def _type_ok(value: Any, t: str) -> bool:
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "null":
        return value is None
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    raise ValueError(f"unknown type {t}")


class Validator:
    def __init__(self, schema: dict[str, Any]):
        check_schema(schema)
        self.root = schema
        self._patterns: dict[str, re.Pattern[str]] = {}

    def _resolve(self, ref: str) -> Any:
        if not ref.startswith("#/"):
            raise ValueError(f"only local refs supported: {ref}")
        node: Any = self.root
        for part in ref[2:].split("/"):
            node = node[part]
        return node

    def validate(self, value: Any, schema: Any = None, path: str = "") -> None:
        schema = self.root if schema is None else schema
        if schema is True:
            return
        if schema is False:
            raise SchemaViolation(path, "no value is allowed here")
        if "$ref" in schema:
            self.validate(value, self._resolve(schema["$ref"]), path)
        t = schema.get("type")
        if t is not None:
            types = t if isinstance(t, list) else [t]
            if not any(_type_ok(value, x) for x in types):
                raise SchemaViolation(path, f"expected {t}, got {type(value).__name__}")
        if "const" in schema and value != schema["const"]:
            raise SchemaViolation(path, f"must equal {schema['const']!r}")
        if "enum" in schema and value not in schema["enum"]:
            raise SchemaViolation(path, f"must be one of {schema['enum']!r}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                raise SchemaViolation(path, f"must be >= {schema['minimum']}")
            if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
                raise SchemaViolation(path, f"must be > {schema['exclusiveMinimum']}")
            if "maximum" in schema and value > schema["maximum"]:
                raise SchemaViolation(path, f"must be <= {schema['maximum']}")
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                raise SchemaViolation(path, f"shorter than {schema['minLength']}")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                raise SchemaViolation(path, f"longer than {schema['maxLength']}")
            if "pattern" in schema:
                pat = self._patterns.get(schema["pattern"])
                if pat is None:
                    pat = self._patterns[schema["pattern"]] = re.compile(schema["pattern"])
                if not pat.fullmatch(value):
                    raise SchemaViolation(path, "does not match required pattern")
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                raise SchemaViolation(path, f"fewer than {schema['minItems']} items")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                raise SchemaViolation(path, f"more than {schema['maxItems']} items")
            if schema.get("uniqueItems"):
                seen = [repr(v) for v in value]
                if len(set(seen)) != len(seen):
                    raise SchemaViolation(path, "items are not unique")
            if "items" in schema:
                for i, item in enumerate(value):
                    self.validate(item, schema["items"], f"{path}[{i}]")
        if isinstance(value, dict):
            for req in schema.get("required", []):
                if req not in value:
                    raise SchemaViolation(path, f"missing required property {req!r}")
            props = schema.get("properties", {})
            extra = schema.get("additionalProperties", True)
            for key, item in value.items():
                if key in props:
                    self.validate(item, props[key], f"{path}.{key}")
                elif extra is False:
                    raise SchemaViolation(path, f"unexpected property {key!r}")
                elif isinstance(extra, dict):
                    self.validate(item, extra, f"{path}.{key}")
        if "oneOf" in schema:
            hits = 0
            for sub in schema["oneOf"]:
                try:
                    self.validate(value, sub, path)
                    hits += 1
                except SchemaViolation:
                    pass
            if hits != 1:
                raise SchemaViolation(path, f"must match exactly one alternative (matched {hits})")
        if "anyOf" in schema:
            for sub in schema["anyOf"]:
                try:
                    self.validate(value, sub, path)
                    break
                except SchemaViolation:
                    continue
            else:
                raise SchemaViolation(path, "matches no alternative")
