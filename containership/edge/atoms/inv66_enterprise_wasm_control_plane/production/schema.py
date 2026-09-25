"""Stdlib validator for the JSON-Schema subset the INV-66 schemas use (MC-012/013/014/022).

Runtime validation must not depend on a third-party package, so this module
implements exactly the keywords present in ``schemas/*.schema.json``: ``type``,
``required``, ``properties``, ``additionalProperties`` (bool/schema), ``enum``,
``const``, ``pattern``, ``minLength``/``maxLength``, ``minimum``/``maximum``,
``items``, ``minItems``/``maxItems``, ``uniqueItems``, ``$ref`` to ``#/$defs/..``,
``oneOf``.  An unknown keyword makes ``load`` fail, so a schema can never silently
use a keyword this validator ignores.  The contract suite cross-checks results
against the reference ``jsonschema`` package when it is installed.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .errors import EcpError

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
_KNOWN = {"$schema", "$id", "title", "description", "type", "required", "properties", "additionalProperties",
          "enum", "const", "pattern", "minLength", "maxLength", "minimum", "maximum", "items", "minItems",
          "maxItems", "uniqueItems", "$ref", "$defs", "oneOf", "default", "x-version", "x-compat"}
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _check_keywords(s: Any, where: str) -> None:
    if isinstance(s, dict):
        unknown = set(s) - _KNOWN
        if unknown and where.split("/")[-1] not in ("properties", "$defs"):
            raise ValueError(f"schema {where} uses unsupported keywords {sorted(unknown)}")
        for k, v in s.items():
            _check_keywords(v, f"{where}/{k}")
    elif isinstance(s, list):
        for i, v in enumerate(s):
            _check_keywords(v, f"{where}/{i}")


@lru_cache(maxsize=None)
def load(name: str) -> dict[str, Any]:
    s = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text())
    _check_keywords(s, name)
    return s


def _is_type(v: Any, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def errors(instance: Any, schema: dict[str, Any], root: dict[str, Any] | None = None, path: str = "$") -> list[str]:
    root = root or schema
    out: list[str] = []
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            return [f"{path}: unsupported $ref {ref}"]
        return errors(instance, root["$defs"][ref[8:]], root, path)
    if "oneOf" in schema:
        n = sum(1 for sub in schema["oneOf"] if not errors(instance, sub, root, path))
        if n != 1:
            out.append(f"{path}: must match exactly one alternative (matched {n})")
        return out
    t = schema.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_is_type(instance, x) for x in ts):
            return [f"{path}: expected {t}"]
    if "const" in schema and instance != schema["const"]:
        out.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        out.append(f"{path}: not one of {schema['enum']}")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            out.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            out.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            out.append(f"{path}: does not match pattern")
    if _is_type(instance, "number"):
        if "minimum" in schema and instance < schema["minimum"]:
            out.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            out.append(f"{path}: above maximum {schema['maximum']}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            out.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            out.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(x, sort_keys=True) for x in instance]
            if len(seen) != len(set(seen)):
                out.append(f"{path}: items not unique")
        if "items" in schema:
            for i, item in enumerate(instance[:10_000]):
                out.extend(errors(item, schema["items"], root, f"{path}[{i}]"))
    if isinstance(instance, dict):
        for r in schema.get("required", []):
            if r not in instance:
                out.append(f"{path}: missing required '{r}'")
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties", True)
        for k, v in instance.items():
            if k in props:
                out.extend(errors(v, props[k], root, f"{path}.{k}"))
            elif addl is False:
                out.append(f"{path}: unexpected property '{k}'")
            elif isinstance(addl, dict):
                out.extend(errors(v, addl, root, f"{path}.{k}"))
    return out[:50]


def validate(instance: Any, name: str) -> None:
    errs = errors(instance, load(name))
    if errs:
        raise EcpError("ECP_SCHEMA_INVALID", f"{name}: {errs[0]}", field=errs[0].split(":")[0][:128],
                       count=len(errs))
