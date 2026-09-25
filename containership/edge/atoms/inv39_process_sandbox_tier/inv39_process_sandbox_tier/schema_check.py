"""MC-085 — dependency-free validator for the JSON-Schema subset used by INV-39 schemas."""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
_TYPES = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float),
          "boolean": bool, "null": type(None)}


def load_schema(schema_id: str) -> dict:
    name = schema_id.replace("/", "-") + ".schema.json"
    return json.loads((SCHEMA_DIR / name).read_text())


def _type_ok(v: Any, t) -> bool:
    ts = t if isinstance(t, list) else [t]
    for x in ts:
        py = _TYPES[x]
        if x in ("integer", "number") and isinstance(v, bool):
            continue
        if isinstance(v, py):
            return True
    return False


def errors(inst: Any, s: dict, path: str = "$") -> list[str]:
    out: list[str] = []
    if "const" in s and inst != s["const"]:
        out.append(f"{path}: expected const {s['const']!r}")
    if "enum" in s and inst not in s["enum"]:
        out.append(f"{path}: {inst!r} not in enum")
    if "type" in s and not _type_ok(inst, s["type"]):
        return out + [f"{path}: expected type {s['type']}"]
    if isinstance(inst, str):
        if len(inst) < s.get("minLength", 0):
            out.append(f"{path}: shorter than minLength")
        if "maxLength" in s and len(inst) > s["maxLength"]:
            out.append(f"{path}: longer than maxLength")
        if "pattern" in s and not re.search(s["pattern"], inst):
            out.append(f"{path}: does not match {s['pattern']}")
    if isinstance(inst, (int, float)) and not isinstance(inst, bool) and "minimum" in s and inst < s["minimum"]:
        out.append(f"{path}: below minimum")
    if isinstance(inst, list):
        if s.get("uniqueItems") and len({json.dumps(i, sort_keys=True) for i in inst}) != len(inst):
            out.append(f"{path}: items not unique")
        if "items" in s:
            for i, v in enumerate(inst):
                out += errors(v, s["items"], f"{path}[{i}]")
    if isinstance(inst, dict):
        for k in s.get("required", []):
            if k not in inst:
                out.append(f"{path}: missing {k}")
        props = s.get("properties", {})
        if s.get("additionalProperties") is False:
            for k in inst:
                if k not in props:
                    out.append(f"{path}: unexpected property {k}")
        for k, sub in props.items():
            if k in inst:
                out += errors(inst[k], sub, f"{path}.{k}")
    return out


def validate(inst: Any, schema_id: str | None = None) -> list[str]:
    sid = schema_id or (inst.get("schema") if isinstance(inst, dict) else None)
    if not isinstance(sid, str) or not re.fullmatch(r"PK_SANDBOX_[A-Z]+/[0-9]+", sid):
        return ["$: unknown or missing schema id"]
    try:
        return errors(inst, load_schema(sid))
    except FileNotFoundError:
        return [f"$: unsupported schema {sid}"]
