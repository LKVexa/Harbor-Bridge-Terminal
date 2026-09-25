"""Stdlib validator for the JSON-Schema (draft 2020-12 subset) files in ``schemas/``.

Supported keywords: type, const, enum, required, properties,
additionalProperties (bool), items, minItems, maxItems, minLength,
maxLength, pattern, minimum, maximum, $ref (local "#/$defs/..."), anyOf.
Unsupported keywords in a schema are a hard error (never silently ignored).
Compatibility rule (docs/COMPATIBILITY.md): unknown fields are rejected at the
public boundary (``additionalProperties: false``); a new optional field needs a
minor schema bump, a new required field / removed field / narrowed type needs
a new major identifier (``/2``).
"""
from __future__ import annotations

import json
import pathlib
import re
from functools import lru_cache

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
_KNOWN = {"$schema", "$id", "$defs", "title", "description", "type", "const", "enum", "required",
          "properties", "additionalProperties", "items", "minItems", "maxItems", "minLength",
          "maxLength", "pattern", "minimum", "maximum", "$ref", "anyOf", "x-version", "default"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def check_keywords(schema, path: str = "$") -> None:
    """Reject unsupported keywords anywhere in a schema (not only on visited branches)."""
    if not isinstance(schema, dict):
        raise ValueError(f"schema at {path} must be an object")
    unknown = set(schema) - _KNOWN
    if unknown:
        raise ValueError(f"unsupported schema keywords at {path}: {sorted(unknown)}")
    for k in ("properties", "$defs"):
        for n, sub in schema.get(k, {}).items():
            check_keywords(sub, f"{path}.{k}.{n}")
    for k in ("items",):
        if k in schema:
            check_keywords(schema[k], f"{path}.{k}")
    if isinstance(schema.get("additionalProperties"), dict):
        check_keywords(schema["additionalProperties"], f"{path}.additionalProperties")
    for i, sub in enumerate(schema.get("anyOf", [])):
        check_keywords(sub, f"{path}.anyOf[{i}]")


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict:
    s = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    check_keywords(s)
    return s


def _same(a, b) -> bool:
    """JSON equality: booleans never equal numbers (True != 1)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    return type(a) in (int, float) and type(b) in (int, float) and a == b or \
        (type(a) is type(b) and a == b)


def schema_names() -> list:
    return sorted(p.name[: -len(".schema.json")] for p in SCHEMA_DIR.glob("*.schema.json"))


def _is_type(v, t) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def validate(inst, schema: dict, root: dict | None = None, path: str = "$") -> list:
    if root is None:  # top-level call: reject unsupported keywords anywhere in the schema up front
        check_keywords(schema)
    root = root or schema
    unknown = set(schema) - _KNOWN
    if unknown:
        raise ValueError(f"unsupported schema keywords at {path}: {sorted(unknown)}")
    errs: list = []
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise ValueError("only local $defs refs supported")
        return validate(inst, root["$defs"][ref[8:]], root, path)
    if "anyOf" in schema:  # evaluated, then sibling keywords are applied too
        if all(validate(inst, s, root, path) for s in schema["anyOf"]):
            errs.append(f"{path}: matches no anyOf branch")
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_is_type(inst, x) for x in ts):
            return [f"{path}: expected {t}"]
    if "const" in schema and not _same(inst, schema["const"]):
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and not any(_same(inst, e) for e in schema["enum"]):
        errs.append(f"{path}: not in enum")
    if isinstance(inst, str):
        if len(inst) < schema.get("minLength", 0):
            errs.append(f"{path}: too short")
        if "maxLength" in schema and len(inst) > schema["maxLength"]:
            errs.append(f"{path}: too long")
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errs.append(f"{path}: pattern mismatch")
    if _is_type(inst, "number"):
        if "minimum" in schema and inst < schema["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in schema and inst > schema["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(inst, list):
        if len(inst) < schema.get("minItems", 0):
            errs.append(f"{path}: too few items")
        if "maxItems" in schema and len(inst) > schema["maxItems"]:
            errs.append(f"{path}: too many items")
        if "items" in schema:
            for i, v in enumerate(inst):
                errs += validate(v, schema["items"], root, f"{path}[{i}]")
    if isinstance(inst, dict):
        for r in schema.get("required", []):
            if r not in inst:
                errs.append(f"{path}: missing {r}")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for k, v in inst.items():
            if k in props:
                errs += validate(v, props[k], root, f"{path}.{k}")
            elif extra is False:
                errs.append(f"{path}: unknown field {k}")
            elif isinstance(extra, dict):
                errs += validate(v, extra, root, f"{path}.{k}")
    return errs
