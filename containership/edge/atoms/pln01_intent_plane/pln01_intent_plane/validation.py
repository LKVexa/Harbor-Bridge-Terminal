"""Dependency-free validator for the bundled JSON Schema artifacts (MC-009).

Implements the subset of JSON Schema 2020-12 used by ``schemas/*.schema.json``:
type, const, enum, required, properties, additionalProperties (bool/schema),
items, minItems/maxItems, minLength/maxLength, pattern, minimum/maximum,
exclusiveMinimum, maxProperties, and local ``$ref`` into ``$defs``.  Unknown
keywords raise at load time so a schema can never silently weaken.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
from functools import lru_cache
from typing import Any

from .errors import UnsupportedSchemaError
from .graph import ValidationError

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
SCHEMA_FILES = {
    "PK_DECLARATION/1": "pk_declaration_1.schema.json",
    "PK_ACTUAL_STATE/1": "pk_actual_state_1.schema.json",
    "PK_RECONCILIATION_PLAN/1": "pk_reconciliation_plan_1.schema.json",
    "PK_INTENT_GRAPH/1": "pk_intent_graph_1.schema.json",
    "PK_ERROR/1": "pk_error_1.schema.json",
    "PLN01_CONFIG/1": "pln01_config_1.schema.json",
}
_KNOWN = {"$schema", "$id", "title", "description", "$defs", "$ref", "type", "const", "enum", "required",
          "properties", "additionalProperties", "items", "minItems", "maxItems", "minLength", "maxLength",
          "pattern", "minimum", "maximum", "exclusiveMinimum", "maxProperties"}
_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v),
}


def _audit_keywords(node: Any) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("properties", "$defs"):
                for sub in value.values():
                    _audit_keywords(sub)
            elif key in ("items", "additionalProperties") and isinstance(value, dict):
                _audit_keywords(value)
            elif key not in _KNOWN:
                raise UnsupportedSchemaError(f"unsupported schema keyword {key!r}")


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    if name not in SCHEMA_FILES:
        raise UnsupportedSchemaError(f"unknown schema {name!r}")
    schema = json.loads((SCHEMA_DIR / SCHEMA_FILES[name]).read_text(encoding="utf-8"))
    _audit_keywords(schema)
    return schema


def _resolve(ref: str, root: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/$defs/"):
        raise UnsupportedSchemaError(f"only local $defs refs are supported: {ref}")
    return root["$defs"][ref[len("#/$defs/"):]]


def _errors(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str, out: list[str]) -> None:
    if "$ref" in schema:
        _errors(value, _resolve(schema["$ref"], root), root, path, out)
        return
    t = schema.get("type")
    if t is not None and not _TYPES[t](value):
        out.append(f"{path or '$'}: expected {t}")
        return
    if "const" in schema and value != schema["const"]:
        out.append(f"{path or '$'}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path or '$'}: not one of {schema['enum']}")
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                out.append(f"{path or '$'}: missing required {req!r}")
        if "maxProperties" in schema and len(value) > schema["maxProperties"]:
            out.append(f"{path or '$'}: too many properties")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for k, v in value.items():
            if not isinstance(k, str):
                out.append(f"{path or '$'}: non-string key")
                continue
            if k in props:
                _errors(v, props[k], root, f"{path}.{k}", out)
            elif extra is False:
                out.append(f"{path or '$'}: unexpected property {k!r}")
            elif isinstance(extra, dict):
                _errors(v, extra, root, f"{path}.{k}", out)
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            out.append(f"{path or '$'}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            out.append(f"{path or '$'}: more than {schema['maxItems']} items")
        if isinstance(schema.get("items"), dict):
            for i, item in enumerate(value):
                _errors(item, schema["items"], root, f"{path}[{i}]", out)
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            out.append(f"{path or '$'}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append(f"{path or '$'}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{path or '$'}: does not match pattern")
    if _TYPES["number"](value):
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{path or '$'}: below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            out.append(f"{path or '$'}: above maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            out.append(f"{path or '$'}: must exceed {schema['exclusiveMinimum']}")


def errors(document: Any, schema_name: str) -> list[str]:
    schema = load_schema(schema_name)
    out: list[str] = []
    _errors(document, schema, schema, "", out)
    return out


def validate(document: Any, schema_name: str) -> Any:
    problems = errors(document, schema_name)
    if problems:
        raise ValidationError(f"{schema_name} validation failed: " + "; ".join(problems[:20]))
    return document
