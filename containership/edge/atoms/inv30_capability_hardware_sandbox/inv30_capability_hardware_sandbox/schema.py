# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Minimal, dependency-free JSON Schema (2020-12 subset) validator for INV-30's own schemas (GAP-015).

Supported keywords: type, const, enum, required, properties, additionalProperties,
items, uniqueItems, maxItems, minimum, maximum, pattern, maxLength. Unknown keywords
in *our* schemas raise at load time so the validator can never silently ignore a
constraint. Booleans are never accepted as integers.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .errors import SchemaInvalid

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
_KNOWN = {"$schema", "$id", "title", "description", "type", "const", "enum", "required", "properties",
          "additionalProperties", "items", "uniqueItems", "maxItems", "minimum", "maximum", "pattern", "maxLength"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool}


def _audit(node, path="$"):
    if isinstance(node, dict):
        unknown = set(node) - _KNOWN
        if unknown and path.split(".")[-1] != "properties":
            raise ValueError(f"unsupported schema keyword(s) {sorted(unknown)} at {path}")
        for k, v in node.items():
            if k == "properties":
                for pk, pv in v.items():
                    _audit(pv, f"{path}.properties.{pk}")
            elif isinstance(v, dict):
                _audit(v, f"{path}.{k}")


@lru_cache(maxsize=None)
def load(name: str) -> dict:
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    _audit(schema)
    return schema


def _is_type(value, t):
    if t == "integer":
        return type(value) is int
    if t == "number":
        return type(value) in (int, float)
    if t == "null":
        return value is None
    return isinstance(value, _TYPES[t]) and not (t != "boolean" and isinstance(value, bool))


def errors(schema: dict, value, path: str = "$") -> list[str]:
    out: list[str] = []
    if "const" in schema and not (value == schema["const"] and type(value) is type(schema["const"])):
        out.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: not one of {schema['enum']}")
    t = schema.get("type")
    if t and not _is_type(value, t):
        return out + [f"{path}: expected {t}"]
    if isinstance(value, dict):
        for r in schema.get("required", []):
            if r not in value:
                out.append(f"{path}: missing {r}")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                out += errors(props[k], v, f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                out.append(f"{path}: unexpected property {k!r}")
    if isinstance(value, list):
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            out.append(f"{path}: too many items")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            out.append(f"{path}: items not unique")
        if "items" in schema:
            for i, v in enumerate(value):
                out += errors(schema["items"], v, f"{path}[{i}]")
    if type(value) in (int, float) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            out.append(f"{path}: above maximum {schema['maximum']}")
    if isinstance(value, str):
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{path}: does not match {schema['pattern']}")
    return out


def validate(name: str, value) -> None:
    errs = errors(load(name), value)
    if errs:
        raise SchemaInvalid("; ".join(errs[:5]))


def all_schemas() -> list[str]:
    return sorted(p.name.replace(".schema.json", "") for p in SCHEMA_DIR.glob("*.schema.json"))
