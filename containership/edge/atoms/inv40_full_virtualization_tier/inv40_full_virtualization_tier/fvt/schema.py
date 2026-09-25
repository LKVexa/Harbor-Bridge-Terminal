"""Versioned typed schemas and a bounded stdlib validator (INV-40-C022, C028, C085).

Supports the JSON-Schema subset the tier's contracts use: type, required,
properties, additionalProperties(false), enum, const, minimum, maximum,
minLength, maxLength, pattern, items, maxItems, uniqueItems.  Depth and size
are bounded so hostile documents cannot exhaust the validator.
"""
from __future__ import annotations

import json
import pathlib
import re

SCHEMA_DIR = pathlib.Path(__file__).resolve().parents[1] / "schemas"
MAX_DEPTH = 16
MAX_DOC_BYTES = 64 * 1024

_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


class SchemaError(ValueError):
    def __init__(self, path: str, msg: str):
        super().__init__(f"{path or '$'}: {msg}")
        self.path, self.msg = path, msg


def load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def _is_type(v, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def validate(doc, schema: dict, path: str = "", depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise SchemaError(path, "nesting too deep")
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_is_type(doc, x) for x in ts):
            raise SchemaError(path, f"expected {t}, got {type(doc).__name__}")
    if "const" in schema and doc != schema["const"]:
        raise SchemaError(path, f"must equal {schema['const']!r}")
    if "enum" in schema and doc not in schema["enum"]:
        raise SchemaError(path, f"not in enum {schema['enum']}")
    if isinstance(doc, (int, float)) and not isinstance(doc, bool):
        if "minimum" in schema and doc < schema["minimum"]:
            raise SchemaError(path, f"< minimum {schema['minimum']}")
        if "maximum" in schema and doc > schema["maximum"]:
            raise SchemaError(path, f"> maximum {schema['maximum']}")
    if isinstance(doc, str):
        if len(doc) < schema.get("minLength", 0):
            raise SchemaError(path, "too short")
        if "maxLength" in schema and len(doc) > schema["maxLength"]:
            raise SchemaError(path, "too long")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], doc):
            raise SchemaError(path, "pattern mismatch")
    if isinstance(doc, list):
        if "maxItems" in schema and len(doc) > schema["maxItems"]:
            raise SchemaError(path, "too many items")
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in doc}) != len(doc):
            raise SchemaError(path, "items not unique")
        if "items" in schema:
            for i, x in enumerate(doc):
                validate(x, schema["items"], f"{path}[{i}]", depth + 1)
    if isinstance(doc, dict):
        for k in schema.get("required", []):
            if k not in doc:
                raise SchemaError(path, f"missing required '{k}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = set(doc) - set(props)
            if extra:
                raise SchemaError(path, f"unexpected properties {sorted(extra)}")
        for k, v in doc.items():
            if k in props:
                validate(v, props[k], f"{path}.{k}", depth + 1)


def parse_and_validate(raw: bytes | str, name: str) -> dict:
    """Parse untrusted JSON with a size bound, then validate against a named schema."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if len(raw) > MAX_DOC_BYTES:
        raise SchemaError("", f"document exceeds {MAX_DOC_BYTES} bytes")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise SchemaError("", f"not valid JSON: {type(exc).__name__}") from None
    validate(doc, load(name))
    return doc
