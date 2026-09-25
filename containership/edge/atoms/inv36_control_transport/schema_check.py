"""Dependency-free validator for the JSON-Schema subset used by INV-36 schemas.

Supported keywords: type, required, properties, additionalProperties (bool),
enum, const, items, minimum, maximum, minLength, maxLength, pattern,
minItems, maxItems.  Unknown keywords are rejected at load time so a schema
cannot silently rely on unsupported validation.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schema"
_KNOWN = {"$schema", "$id", "title", "description", "type", "required", "properties", "additionalProperties",
          "enum", "const", "items", "minimum", "maximum", "minLength", "maxLength", "pattern", "minItems",
          "maxItems"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


class SchemaViolation(ValueError):
    pass


def _check_keywords(s: Any, path: str = "#") -> None:
    if not isinstance(s, dict):
        return
    bad = set(s) - _KNOWN
    if bad:
        raise SchemaViolation(f"{path}: unsupported schema keywords {sorted(bad)}")
    for k, v in s.get("properties", {}).items():
        _check_keywords(v, f"{path}/properties/{k}")
    if isinstance(s.get("items"), dict):
        _check_keywords(s["items"], f"{path}/items")


def load(name: str) -> dict:
    s = json.loads((SCHEMA_DIR / name).read_text())
    _check_keywords(s)
    return s


def _type_ok(v: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def validate(doc: Any, schema: dict, path: str = "$") -> None:
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(doc, x) for x in types):
            raise SchemaViolation(f"{path}: expected {t}")
    if "const" in schema and doc != schema["const"]:
        raise SchemaViolation(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and doc not in schema["enum"]:
        raise SchemaViolation(f"{path}: {doc!r} not in enum")
    if isinstance(doc, (int, float)) and not isinstance(doc, bool):
        if "minimum" in schema and doc < schema["minimum"]:
            raise SchemaViolation(f"{path}: below minimum")
        if "maximum" in schema and doc > schema["maximum"]:
            raise SchemaViolation(f"{path}: above maximum")
    if isinstance(doc, str):
        if len(doc) < schema.get("minLength", 0) or len(doc) > schema.get("maxLength", 1 << 30):
            raise SchemaViolation(f"{path}: string length out of range")
        if "pattern" in schema and not re.search(schema["pattern"], doc):
            raise SchemaViolation(f"{path}: pattern mismatch")
    if isinstance(doc, list):
        if len(doc) < schema.get("minItems", 0) or len(doc) > schema.get("maxItems", 1 << 30):
            raise SchemaViolation(f"{path}: item count out of range")
        if isinstance(schema.get("items"), dict):
            for i, item in enumerate(doc):
                validate(item, schema["items"], f"{path}[{i}]")
    if isinstance(doc, dict):
        for r in schema.get("required", []):
            if r not in doc:
                raise SchemaViolation(f"{path}: missing required {r!r}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = set(doc) - set(props)
            if extra:
                raise SchemaViolation(f"{path}: unexpected properties {sorted(extra)}")
        for k, sub in props.items():
            if k in doc:
                validate(doc[k], sub, f"{path}.{k}")
