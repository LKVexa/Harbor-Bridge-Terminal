"""Minimal, dependency-free JSON Schema (2020-12 subset) validator used by tests and the gate.

Supports: type (incl. unions), const, enum, required, properties, additionalProperties(bool),
items, minItems, uniqueItems, minLength, maxLength, pattern, minimum.  Anything outside the
subset raises, so a schema cannot silently go unchecked.
"""
from __future__ import annotations

import re
from typing import Any

_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
_KNOWN = {"$schema", "$id", "title", "description", "type", "const", "enum", "required", "properties",
          "additionalProperties", "items", "minItems", "uniqueItems", "minLength", "maxLength", "pattern",
          "minimum", "maxItems"}


def _is(t: str, v: Any) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def validate(inst: Any, schema: dict, path: str = "$") -> list[str]:
    unknown = set(schema) - _KNOWN
    if unknown:
        raise ValueError(f"unsupported schema keywords at {path}: {sorted(unknown)}")
    errs: list[str] = []
    if "type" in schema:
        ts = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is(t, inst) for t in ts):
            return [f"{path}: expected {ts}"]
    if "const" in schema and inst != schema["const"]:
        errs.append(f"{path}: const mismatch")
    if "enum" in schema and inst not in schema["enum"]:
        errs.append(f"{path}: not in enum")
    if isinstance(inst, dict):
        for r in schema.get("required", []):
            if r not in inst:
                errs.append(f"{path}: missing {r}")
        props = schema.get("properties", {})
        for k, v in inst.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected {k}")
    if isinstance(inst, list):
        if len(inst) < schema.get("minItems", 0):
            errs.append(f"{path}: too few items")
        if len(inst) > schema.get("maxItems", 1 << 62):
            errs.append(f"{path}: too many items")
        if schema.get("uniqueItems") and len({repr(x) for x in inst}) != len(inst):
            errs.append(f"{path}: items not unique")
        if "items" in schema:
            for i, v in enumerate(inst):
                errs += validate(v, schema["items"], f"{path}[{i}]")
    if isinstance(inst, str):
        if len(inst) < schema.get("minLength", 0) or len(inst) > schema.get("maxLength", 1 << 62):
            errs.append(f"{path}: length out of range")
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errs.append(f"{path}: pattern mismatch")
    if "minimum" in schema and _is("number", inst) and inst < schema["minimum"]:
        errs.append(f"{path}: below minimum")
    return errs
