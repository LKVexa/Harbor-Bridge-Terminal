"""M35 - Runtime validation and canonical serialisation against the shipped schemas.

A deliberately small, fail-closed JSON Schema (draft 2020-12) validator that
implements exactly the keywords the PLN-04 schemas use.  An unsupported
keyword in a shipped schema is an error at load time, so a schema can never
silently stop being enforced.  Input is bounded in bytes and nesting depth
before parsing.
"""
from __future__ import annotations

import json
import pathlib
import re
from functools import lru_cache
from typing import Any

from .errors import PlaneError

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
MAX_DOCUMENT_BYTES = 64 * 1024
MAX_DEPTH = 16

SUPPORTED_KEYWORDS = frozenset({
    "$schema", "$id", "title", "description", "type", "const", "enum", "required",
    "properties", "additionalProperties", "propertyNames", "minLength", "maxLength",
    "minimum", "maximum", "pattern", "items", "uniqueItems", "allOf", "if", "then",
    "maxItems", "minItems",
})

SCHEMA_FILES = {
    "PK_ADMISSION/1": "PK_ADMISSION_1.schema.json",
    "PK_TIER_CATALOGUE/1": "PK_TIER_CATALOGUE_1.schema.json",
    "PK_TIER_LIFECYCLE/1": "PK_TIER_LIFECYCLE_1.schema.json",
    "PK_PROVIDER_REQUEST/1": "PK_PROVIDER_REQUEST_1.schema.json",
    "PK_PLANE_CONFIG/1": "PK_PLANE_CONFIG_1.schema.json",
}

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _check_keywords(schema: Any, where: str = "#") -> None:
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise ValueError(f"schema at {where} must be an object or boolean")
    unknown = set(schema) - SUPPORTED_KEYWORDS
    if unknown:
        raise ValueError(f"unsupported schema keyword(s) at {where}: {sorted(unknown)}")
    for key in ("properties",):
        for name, sub in schema.get(key, {}).items():
            _check_keywords(sub, f"{where}/{key}/{name}")
    for key in ("additionalProperties", "propertyNames", "items", "if", "then"):
        if key in schema:
            _check_keywords(schema[key], f"{where}/{key}")
    for i, sub in enumerate(schema.get("allOf", [])):
        _check_keywords(sub, f"{where}/allOf/{i}")


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict:
    if name not in SCHEMA_FILES:
        raise PlaneError("PLN04-VAL-003", details={"field": "schema", "reason": f"unknown schema {name!r}"})
    schema = json.loads((SCHEMA_DIR / SCHEMA_FILES[name]).read_text(encoding="utf-8"))
    _check_keywords(schema)
    return schema


def _is_type(value: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[expected])


def _errors(value: Any, schema: Any, path: str, depth: int) -> list[str]:
    if depth > MAX_DEPTH:
        return [f"{path}: nesting exceeds {MAX_DEPTH}"]
    if schema is True:
        return []
    if schema is False:
        return [f"{path}: not permitted"]
    out: list[str] = []
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, t) for t in types):
            return [f"{path}: expected {schema['type']}"]
    if "const" in schema and (value != schema["const"] or type(value) is not type(schema["const"])):
        out.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and not any(value == e and type(value) is type(e) for e in schema["enum"]):
        out.append(f"{path}: not in enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            out.append(f"{path}: shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append(f"{path}: longer than maxLength")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{path}: does not match pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            out.append(f"{path}: above maximum")
    if isinstance(value, list):
        if "items" in schema:
            for i, item in enumerate(value):
                out.extend(_errors(item, schema["items"], f"{path}/{i}", depth + 1))
        if schema.get("uniqueItems"):
            seen = [json.dumps(v, sort_keys=True) for v in value]
            if len(seen) != len(set(seen)):
                out.append(f"{path}: items not unique")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            out.append(f"{path}: too many items")
        if len(value) < schema.get("minItems", 0):
            out.append(f"{path}: too few items")
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                out.append(f"{path}: missing required {req!r}")
        props = schema.get("properties", {})
        for key, sub in value.items():
            if not isinstance(key, str):
                out.append(f"{path}: non-string key")
                continue
            if "propertyNames" in schema:
                out.extend(_errors(key, schema["propertyNames"], f"{path}/<key {key!r}>", depth + 1))
            if key in props:
                out.extend(_errors(sub, props[key], f"{path}/{key}", depth + 1))
            elif "additionalProperties" in schema:
                out.extend(_errors(sub, schema["additionalProperties"], f"{path}/{key}", depth + 1))
    for sub in schema.get("allOf", []):
        out.extend(_errors(value, sub, path, depth + 1))
    if "if" in schema and not _errors(value, schema["if"], path, depth + 1) and "then" in schema:
        out.extend(_errors(value, schema["then"], path, depth + 1))
    return out


def validate(document: Any, schema_name: str) -> None:
    """Raise :class:`PlaneError` (PLN04-VAL-001) listing every violation."""
    problems = _errors(document, load_schema(schema_name), "#", 0)
    if problems:
        raise PlaneError("PLN04-VAL-001", details={"field": problems[0], "reason": f"{len(problems)} violation(s)"})


def _depth(value: Any, depth: int = 0) -> int:
    if depth > MAX_DEPTH:
        return depth
    if isinstance(value, dict):
        return max([_depth(v, depth + 1) for v in value.values()] or [depth + 1])
    if isinstance(value, list):
        return max([_depth(v, depth + 1) for v in value] or [depth + 1])
    return depth


def parse(raw: bytes | str, schema_name: str) -> dict:
    """Bounded parse + validate.  Rejects oversize, deep, duplicate-key or non-JSON input."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise PlaneError("PLN04-VAL-002", details={"limit": MAX_DOCUMENT_BYTES})
    # cheap pre-scan so a hostile deeply nested document cannot recurse the parser
    depth = running = 0
    in_str = esc = False
    for byte in raw:
        ch = chr(byte)
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "[{":
            running += 1
            depth = max(depth, running)
            if depth > MAX_DEPTH:
                raise PlaneError("PLN04-VAL-002", details={"limit": MAX_DEPTH, "field": "depth"})
        elif ch in "]}":
            running -= 1

    def _no_dupes(pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate key")
        return dict(pairs)

    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupes,
                         parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except (ValueError, UnicodeDecodeError) as exc:
        raise PlaneError("PLN04-VAL-001", details={"reason": "malformed JSON"}, cause=exc) from None
    if not isinstance(doc, dict):
        raise PlaneError("PLN04-VAL-001", details={"reason": "document must be an object"})
    validate(doc, schema_name)
    return doc


def dumps(document: dict, schema_name: str) -> str:
    """Validate then canonically serialise (sorted keys, no whitespace, ASCII)."""
    validate(document, schema_name)
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
