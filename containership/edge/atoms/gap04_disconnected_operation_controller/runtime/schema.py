"""Minimal dependency-free JSON Schema (2020-12 subset) validator for contract tests
and runtime input checks. Supported: type (incl. lists), const, enum, required,
properties, additionalProperties (bool or schema), items, minItems, maxItems,
minLength, maxLength, pattern, minimum, maximum, $ref to local $defs."""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
_T = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(t, v):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _T[t])


def validate(v, s, root=None, path="$") -> list[str]:
    root = root or s
    errs: list[str] = []
    if "$ref" in s:
        ref = s["$ref"].split("/")[-1]
        return validate(v, root["$defs"][ref], root, path)
    if "type" in s:
        ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_is(t, v) for t in ts):
            return [f"{path}: expected {ts}, got {type(v).__name__}"]
    if "const" in s and v != s["const"]:
        errs.append(f"{path}: const mismatch")
    if "enum" in s and v not in s["enum"]:
        errs.append(f"{path}: not in enum")
    if isinstance(v, str):
        if len(v) < s.get("minLength", 0) or len(v) > s.get("maxLength", 1 << 30):
            errs.append(f"{path}: length out of range")
        if "pattern" in s and not re.search(s["pattern"], v):
            errs.append(f"{path}: pattern mismatch")
    if _is("number", v):
        if "minimum" in s and v < s["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in s and v > s["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(v, list):
        if len(v) < s.get("minItems", 0) or len(v) > s.get("maxItems", 1 << 30):
            errs.append(f"{path}: item count out of range")
        if "items" in s:
            for i, x in enumerate(v):
                errs += validate(x, s["items"], root, f"{path}[{i}]")
    if isinstance(v, dict):
        for r in s.get("required", []):
            if r not in v:
                errs.append(f"{path}: missing {r}")
        props = s.get("properties", {})
        ap = s.get("additionalProperties", True)
        for k, x in v.items():
            if k in props:
                errs += validate(x, props[k], root, f"{path}.{k}")
            elif ap is False:
                errs.append(f"{path}: unexpected property {k}")
            elif isinstance(ap, dict):
                errs += validate(x, ap, root, f"{path}.{k}")
    return errs


def load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name.replace('/', '-')}.schema.json").read_text())


def check(doc: dict, name: str | None = None) -> None:
    name = name or doc.get("schema") or doc.get("version")
    errs = validate(doc, load(name))
    if errs:
        raise ValueError(f"{name}: " + "; ".join(errs[:10]))
