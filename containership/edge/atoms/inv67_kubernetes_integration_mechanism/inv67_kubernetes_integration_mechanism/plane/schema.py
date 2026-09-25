"""Minimal, dependency-free JSON Schema (2020-12 subset) validator used by the
contract/conformance tests (item 48). Supports: type, const, enum, required,
properties, additionalProperties (bool/schema), items, minItems, minLength,
minimum, pattern, $ref to local $defs, oneOf/anyOf. Unknown keywords raise so
a schema can never silently use an unsupported rule."""
from __future__ import annotations

import re

_KNOWN = {"$schema", "$id", "title", "description", "type", "const", "enum", "required", "properties",
          "additionalProperties", "items", "minItems", "maxItems", "minLength", "maxLength", "minimum", "maximum",
          "pattern", "$ref", "$defs", "oneOf", "anyOf", "default", "format"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(t, v):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def errors(schema: dict, value, root: dict | None = None, path: str = "$") -> list[str]:
    root = root or schema
    unknown = set(schema) - _KNOWN
    if unknown:
        raise ValueError(f"unsupported schema keywords {sorted(unknown)} at {path}")
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise ValueError("only local $defs refs supported")
        return errors(root["$defs"][ref.split("/")[-1]], value, root, path)
    out = []
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_is(x, value) for x in ts):
            return [f"{path}: expected {t}"]
    if "const" in schema and value != schema["const"]:
        out.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: not in enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            out.append(f"{path}: too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append(f"{path}: too long")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{path}: pattern mismatch")
    if _is("number", value):
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            out.append(f"{path}: above maximum")
    if isinstance(value, dict):
        for r in schema.get("required", []):
            if r not in value:
                out.append(f"{path}: missing {r}")
        props = schema.get("properties", {})
        ap = schema.get("additionalProperties", True)
        for k, v in value.items():
            if k in props:
                out += errors(props[k], v, root, f"{path}.{k}")
            elif ap is False:
                out.append(f"{path}: unexpected property {k}")
            elif isinstance(ap, dict):
                out += errors(ap, v, root, f"{path}.{k}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            out.append(f"{path}: too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            out.append(f"{path}: too many items")
        if "items" in schema:
            for i, v in enumerate(value):
                out += errors(schema["items"], v, root, f"{path}[{i}]")
    for kw in ("oneOf", "anyOf"):
        if kw in schema:
            ok = [s for s in schema[kw] if not errors(s, value, root, path)]
            if (kw == "oneOf" and len(ok) != 1) or (kw == "anyOf" and not ok):
                out.append(f"{path}: {kw} mismatch")
    return out
