"""MC-17 formal schema artifacts: loader + a strict stdlib JSON-Schema-subset validator.

Supported keywords: type, required, properties, additionalProperties(false), enum, const,
items, minimum, minLength, pattern, oneOf(of types via "type" list).  Anything else in a
schema file is refused at load time so a schema can never silently weaken.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .errors import SchedulerError

DIR = Path(__file__).resolve().parent / "schemas"
KEYWORDS = {"$schema", "$id", "title", "description", "type", "required", "properties", "additionalProperties",
            "enum", "const", "items", "minimum", "minLength", "pattern"}
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _check_keywords(s: Any, path="#") -> None:
    if isinstance(s, dict):
        bad = set(s) - KEYWORDS
        if bad: raise ValueError(f"{path}: unsupported schema keywords {sorted(bad)}")
        for k, v in s.get("properties", {}).items(): _check_keywords(v, f"{path}/properties/{k}")
        if isinstance(s.get("items"), dict): _check_keywords(s["items"], f"{path}/items")


def load(schema_id: str) -> dict:
    name, ver = schema_id.split("/")
    doc = json.loads((DIR / f"{name}.v{ver}.json").read_text(encoding="utf-8"))
    _check_keywords(doc)
    return doc


def _is(v, t):
    if t == "integer": return isinstance(v, int) and not isinstance(v, bool)
    if t == "number": return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, TYPES[t])


def errors(instance: Any, schema: dict, path: str = "$") -> list[str]:
    out: list[str] = []
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_is(instance, x) for x in ts):
            return [f"{path}: expected {t}"]
    if "const" in schema and instance != schema["const"]: out.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]: out.append(f"{path}: not in enum")
    if "minimum" in schema and isinstance(instance, (int, float)) and instance < schema["minimum"]:
        out.append(f"{path}: below minimum")
    if "minLength" in schema and isinstance(instance, str) and len(instance) < schema["minLength"]:
        out.append(f"{path}: too short")
    if "pattern" in schema and isinstance(instance, str) and not re.search(schema["pattern"], instance):
        out.append(f"{path}: pattern mismatch")
    if isinstance(instance, dict):
        for k in schema.get("required", []):
            if k not in instance: out.append(f"{path}: missing {k}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in instance:
                if k not in props: out.append(f"{path}: unexpected {k}")
        for k, sub in props.items():
            if k in instance: out += errors(instance[k], sub, f"{path}.{k}")
    if isinstance(instance, list) and isinstance(schema.get("items"), dict):
        for i, v in enumerate(instance): out += errors(v, schema["items"], f"{path}[{i}]")
    return out


def validate(instance: Any, schema_id: str | None = None) -> None:
    sid = schema_id or (instance.get("schema") if isinstance(instance, dict) else None)
    if not sid: raise SchedulerError("SCHEMA_VIOLATION", "no schema id")
    try:
        sch = load(sid)
    except (FileNotFoundError, ValueError):
        raise SchedulerError("UNSUPPORTED_VERSION", f"no schema for {sid}") from None
    errs = errors(instance, sch)
    if errs: raise SchedulerError("SCHEMA_VIOLATION", "; ".join(errs[:10]), details={"errors": errs})
