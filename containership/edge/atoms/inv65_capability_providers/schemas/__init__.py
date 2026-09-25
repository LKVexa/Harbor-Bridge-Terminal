"""Versioned machine-readable schemas (M03) and a stdlib JSON-Schema subset validator.

The validator supports the draft 2020-12 keywords the shipped schemas use:
type, properties, required, additionalProperties(false), enum, const, pattern,
minLength, maxLength, minimum, maximum, items, minItems, maxItems, $ref (local
``#/$defs/...``), oneOf.  Unknown keywords make the validator raise, so a
schema can never silently use a keyword that is not enforced.
"""
from __future__ import annotations

import functools
import json
import pathlib
import re
from typing import Any

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent
_SUPPORTED = {
    "$schema", "$id", "$defs", "title", "description", "type", "properties", "required",
    "additionalProperties", "enum", "const", "pattern", "minLength", "maxLength", "minimum",
    "maximum", "items", "minItems", "maxItems", "$ref", "oneOf", "x-version", "x-compat",
}
_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


class SchemaError(ValueError):
    pass


@functools.lru_cache(maxsize=64)
def _load_text(name: str, version: str) -> str:
    return (SCHEMA_DIR / name / f"{version}.json").read_text(encoding="utf-8")


def load(name: str, version: str = "v1") -> dict:
    """Parsed schema (file read cached; a fresh dict each call so callers cannot mutate the cache)."""
    return json.loads(_load_text(name, version))


@functools.lru_cache(maxsize=64)
def _load_shared(name: str, version: str) -> dict:
    return json.loads(_load_text(name, version))


def names() -> list[str]:
    return sorted(p.name for p in SCHEMA_DIR.iterdir() if p.is_dir() and (p / "v1.json").exists())


def _type_ok(value: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[t])


def validate(instance: Any, schema: dict, *, root: dict | None = None, path: str = "$") -> list[str]:
    root = root if root is not None else schema
    errs: list[str] = []
    unknown = set(schema) - _SUPPORTED
    if unknown:
        raise SchemaError(f"unsupported schema keywords at {path}: {sorted(unknown)}")
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise SchemaError(f"only local $defs refs supported: {ref}")
        return validate(instance, root["$defs"][ref[8:]], root=root, path=path)
    if "oneOf" in schema:
        ok = [s for s in schema["oneOf"] if not validate(instance, s, root=root, path=path)]
        if len(ok) != 1:
            errs.append(f"{path}: matches {len(ok)} of oneOf (need exactly 1)")
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_type_ok(instance, x) for x in ts):
            return errs + [f"{path}: expected {t}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in {schema['enum']}")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(f"{path}: below {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errs.append(f"{path}: above {schema['maximum']}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errs.append(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for i, v in enumerate(instance):
                errs += validate(v, schema["items"], root=root, path=f"{path}[{i}]")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for r in schema.get("required", []):
            if r not in instance:
                errs.append(f"{path}: missing required '{r}'")
        if schema.get("additionalProperties") is False:
            for k in instance:
                if k not in props:
                    errs.append(f"{path}: unexpected property '{k}'")
        elif isinstance(schema.get("additionalProperties"), dict):
            for k, v in instance.items():
                if k not in props:
                    errs += validate(v, schema["additionalProperties"], root=root, path=f"{path}.{k}")
        for k, sub in props.items():
            if k in instance:
                errs += validate(instance[k], sub, root=root, path=f"{path}.{k}")
    return errs


def check(instance: Any, name: str, version: str = "v1") -> None:
    errs = validate(instance, _load_shared(name, version))  # validate() never mutates the schema
    if errs:
        raise SchemaError(f"{name}/{version}: " + "; ".join(errs[:10]))
