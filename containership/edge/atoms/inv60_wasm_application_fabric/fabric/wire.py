"""M16/M23 - wire schemas and a minimal JSON-Schema (draft 2020-12 subset) validator.

Subset: type, required, properties, additionalProperties(false), enum, pattern,
minLength/maxLength, minimum/maximum, items, minItems/maxItems. The same subset
is implemented in fixtures/validate.mjs so a non-Python consumer checks the same
fixtures (cross-language conformance).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
_TYPES = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}


def load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text())


def validate(inst, schema: dict, path: str = "$") -> list[str]:
    errs: list[str] = []
    t = schema.get("type")
    if t:
        py = _TYPES[t]
        if isinstance(inst, bool) and t in ("integer", "number"):
            return [f"{path}: expected {t}"]
        if not isinstance(inst, py):
            return [f"{path}: expected {t}"]
    if "enum" in schema and inst not in schema["enum"]:
        errs.append(f"{path}: not in enum")
    if isinstance(inst, str):
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errs.append(f"{path}: pattern mismatch")
        if len(inst) < schema.get("minLength", 0):
            errs.append(f"{path}: too short")
        if "maxLength" in schema and len(inst) > schema["maxLength"]:
            errs.append(f"{path}: too long")
    if isinstance(inst, (int, float)) and not isinstance(inst, bool):
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
                errs += validate(v, schema["items"], f"{path}[{i}]")
    if isinstance(inst, dict):
        for r in schema.get("required", []):
            if r not in inst:
                errs.append(f"{path}: missing {r}")
        props = schema.get("properties", {})
        for k, v in inst.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unknown field {k}")
    return errs


MAX_WIRE_BYTES = 2 * 1024 * 1024


def decode(raw: bytes, schema_name: str) -> dict:
    """Bounded decode: size limit enforced BEFORE parsing (M22)."""
    from .errors import FabricError
    if len(raw) > MAX_WIRE_BYTES:
        raise FabricError("PAYLOAD_TOO_LARGE", "wire message over limit")
    try:
        inst = json.loads(raw)
    except Exception:
        raise FabricError("INVALID_ARGUMENT", "malformed JSON") from None
    errs = validate(inst, load(schema_name))
    if errs:
        raise FabricError("INVALID_ARGUMENT", "; ".join(errs[:8]))
    return inst
