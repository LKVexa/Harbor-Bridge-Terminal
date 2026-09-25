"""Minimal, bounded JSON-Schema (draft 2020-12 subset) validator.

Supported keywords: type, const, enum, required, properties,
additionalProperties (bool), items, minItems, maxItems, uniqueItems,
minimum, maximum, minLength, maxLength, pattern, $ref (local #/$defs only).
Unsupported keywords in a schema are rejected at load time so a schema can
never silently weaken validation.
"""
from __future__ import annotations

import json
import pathlib
import re
from functools import lru_cache

from ..errors import Inv24Error

HERE = pathlib.Path(__file__).resolve().parent
SCHEMA_FILES = {
    "PK_MICROVM/1": "PK_MICROVM_V1.json",
    "PK_MICROVM_BOOT/1": "PK_MICROVM_BOOT_V1.json",
    "PK_MICROVM_LIFECYCLE/1": "PK_MICROVM_LIFECYCLE_V1.json",
    "PK_MICROVM_STATUS/1": "PK_MICROVM_STATUS_V1.json",
    "PK_MICROVM_ERROR/1": "PK_MICROVM_ERROR_V1.json",
    "PK_MICROVM_DEVICE/1": "PK_MICROVM_DEVICE_V1.json",
    "PK_MICROVM_SNAPSHOT/1": "PK_MICROVM_SNAPSHOT_V1.json",
    "PK_MICROVM_ADMISSION/1": "PK_MICROVM_ADMISSION_V1.json",
    "PK_MICROVM_CONFIG/1": "PK_MICROVM_CONFIG_V1.json",
    "PK_MICROVM_EVIDENCE/1": "PK_MICROVM_EVIDENCE_V1.json",
}
_KNOWN = {"$schema", "$id", "$defs", "$ref", "title", "description", "type", "const", "enum",
          "required", "properties", "additionalProperties", "items", "minItems", "maxItems",
          "uniqueItems", "minimum", "maximum", "minLength", "maxLength", "pattern"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
MAX_DEPTH = 32


def _check_keywords(schema: object, path: str = "#") -> None:
    if isinstance(schema, dict):
        unknown = set(schema) - _KNOWN
        if unknown:
            raise Inv24Error("SCHEMA_VIOLATION", f"unsupported schema keywords at {path}: {sorted(unknown)}")
        for key in ("properties", "$defs"):
            for name, sub in schema.get(key, {}).items():
                _check_keywords(sub, f"{path}/{key}/{name}")
        if "items" in schema:
            _check_keywords(schema["items"], f"{path}/items")


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict:
    if name not in SCHEMA_FILES:
        raise Inv24Error("SCHEMA_VIOLATION", f"unknown schema {name!r}")
    schema = json.loads((HERE / SCHEMA_FILES[name]).read_text(encoding="utf-8"))
    _check_keywords(schema)
    return schema


def _is_type(value: object, typ: str) -> bool:
    if typ == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if typ == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[typ])


def _validate(value, schema, root, path, depth, errors):
    if depth > MAX_DEPTH:
        errors.append(f"{path}: nesting too deep")
        return
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            errors.append(f"{path}: non-local $ref {ref}")
            return
        schema = root["$defs"][ref.split("/")[-1]]
    typ = schema.get("type")
    if typ is not None:
        types = typ if isinstance(typ, list) else [typ]
        if not any(_is_type(value, t) for t in types):
            errors.append(f"{path}: expected {typ}")
            return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: not in enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: too short")
        if len(value) > schema.get("maxLength", 1 << 20):
            errors.append(f"{path}: too long")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errors.append(f"{path}: pattern mismatch")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", 4096):
            errors.append(f"{path}: item count out of range")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            errors.append(f"{path}: items not unique")
        if "items" in schema:
            for i, item in enumerate(value[:4096]):
                _validate(item, schema["items"], root, f"{path}/{i}", depth + 1, errors)
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing {req}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties", True) is False:
            extra = set(value) - set(props)
            if extra:
                errors.append(f"{path}: unexpected {sorted(extra)}")
        for key, sub in props.items():
            if key in value:
                _validate(value[key], sub, root, f"{path}/{key}", depth + 1, errors)


def validate(payload: object, name: str | None = None) -> None:
    """Raise ``Inv24Error(SCHEMA_VIOLATION)`` unless payload satisfies its schema."""
    if name is None:
        name = payload.get("schema") if isinstance(payload, dict) else None
    schema = load_schema(str(name))
    errors: list[str] = []
    _validate(payload, schema, schema, "#", 0, errors)
    if errors:
        raise Inv24Error("SCHEMA_VIOLATION", f"{name}: " + "; ".join(errors[:10]))
