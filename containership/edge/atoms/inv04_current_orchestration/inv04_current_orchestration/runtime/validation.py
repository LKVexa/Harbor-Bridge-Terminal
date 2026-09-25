"""Runtime schema validation at trust boundaries (component 23) and the
protocol-version negotiation used by the transport (component 25).

Implements the JSON Schema 2020-12 keywords the shipped PK_ORCH_* schemas use
(type, required, properties, additionalProperties, items, enum, minLength,
maxLength, minimum, uniqueItems) and fails closed on any other keyword so a
schema change cannot silently weaken validation.  Bounded: depth, size and
error-count limits protect against hostile payloads.
"""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache
from typing import Any

from .errors import IncompatibleProtocol, SchemaViolation

SCHEMA_DIR = pathlib.Path(__file__).resolve().parents[1] / "schemas"
SCHEMAS = {
    "PK_ORCH_RECONCILE/1": "PK_ORCH_RECONCILE_v1.schema.json",
    "PK_ORCH_DRAIN/1": "PK_ORCH_DRAIN_v1.schema.json",
    "PK_ORCH_INVENTORY/1": "PK_ORCH_INVENTORY_v1.schema.json",
    "PK_ORCH_ERROR/1": "PK_ORCH_ERROR_v1.schema.json",
}
SUPPORTED_KEYWORDS = frozenset({"$schema", "$id", "title", "description", "type", "required", "properties",
                                "additionalProperties", "items", "enum", "minLength", "maxLength", "minimum",
                                "uniqueItems", "default", "x-revision"})
MAX_DEPTH = 16
MAX_BYTES = 4 * 1024 * 1024
MAX_ITEMS = 100_000

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict:
    if name not in SCHEMAS:
        raise IncompatibleProtocol(f"unknown interface {name!r}", details={"interface": name})
    schema = json.loads((SCHEMA_DIR / SCHEMAS[name]).read_text(encoding="utf-8"))
    _check_keywords(schema)
    return schema


def _check_keywords(s: Any) -> None:
    if isinstance(s, dict):
        unknown = sorted(set(s) - SUPPORTED_KEYWORDS)
        if unknown:
            raise ValueError(f"schema keywords {unknown} are not supported by the runtime validator")
        for sub in (s.get("properties") or {}).values():
            _check_keywords(sub)
        for k in ("items", "additionalProperties"):
            if isinstance(s.get(k), dict):
                _check_keywords(s[k])


def errors_for(value: Any, schema: dict, path: str = "$", depth: int = 0, out: list[str] | None = None) -> list[str]:
    out = [] if out is None else out
    if len(out) >= 20:
        return out
    if depth > MAX_DEPTH:
        out.append(f"{path}: nesting exceeds {MAX_DEPTH}")
        return out
    t = schema.get("type")
    if t is not None and not _TYPES[t](value):
        out.append(f"{path}: expected {t}")
        return out
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: value not in enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            out.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append(f"{path}: longer than {schema['maxLength']}")
    if "minimum" in schema and _TYPES["number"](value) and value < schema["minimum"]:
        out.append(f"{path}: below minimum {schema['minimum']}")
    if isinstance(value, list):
        if len(value) > MAX_ITEMS:
            out.append(f"{path}: more than {MAX_ITEMS} items")
            return out
        if schema.get("uniqueItems"):
            seen = [json.dumps(v, sort_keys=True) for v in value]
            if len(seen) != len(set(seen)):
                out.append(f"{path}: items are not unique")
        if isinstance(schema.get("items"), dict):
            for i, v in enumerate(value):
                errors_for(v, schema["items"], f"{path}[{i}]", depth + 1, out)
    if isinstance(value, dict):
        if len(value) > MAX_ITEMS:
            out.append(f"{path}: more than {MAX_ITEMS} keys")
            return out
        for r in schema.get("required", []):
            if r not in value:
                out.append(f"{path}: missing required {r!r}")
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties", True)
        for k, v in value.items():
            if not isinstance(k, str):
                out.append(f"{path}: non-string key")
                continue
            if k in props:
                errors_for(v, props[k], f"{path}.{k}", depth + 1, out)
            elif addl is False:
                out.append(f"{path}: unexpected property {k[:64]!r}")
            elif isinstance(addl, dict):
                errors_for(v, addl, f"{path}.{k[:64]}", depth + 1, out)
    return out


def validate(interface: str, value: Any) -> Any:
    errs = errors_for(value, load_schema(interface))
    if errs:
        raise SchemaViolation(f"{interface} payload rejected", details={"interface": interface, "errors": errs[:20]})
    return value


def parse_and_validate(interface: str, raw: bytes | str) -> Any:
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise SchemaViolation(f"{interface} payload exceeds {MAX_BYTES} bytes")
    try:
        value = json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise SchemaViolation(f"{interface} payload is not valid JSON: {type(exc).__name__}") from None
    return validate(interface, value)


def _reject_constant(name: str) -> None:
    raise ValueError(f"non-standard JSON constant {name}")


# --------------------------------------------------------- negotiation (25)

SERVER_VERSIONS = {"PK_ORCH_RECONCILE": ["1.0"], "PK_ORCH_DRAIN": ["1.0", "1.1"],
                   "PK_ORCH_INVENTORY": ["1.0"], "PK_ORCH_ERROR": ["1.0", "1.1"]}
DEPRECATED: dict[str, str] = {}  # "PK_ORCH_X/1.0": "removal date"


def negotiate(interface: str, offered: list[str]) -> str:
    """Pick the highest mutually supported revision within the same major.
    Refuses an incompatible peer instead of silently downgrading across majors."""
    ours = SERVER_VERSIONS.get(interface)
    if not ours:
        raise IncompatibleProtocol(f"interface {interface} not served", details={"interface": interface})
    common = [v for v in ours if v in set(offered)]
    if not common:
        raise IncompatibleProtocol(f"no common revision for {interface}", details={"server": ours, "client": sorted(offered)})
    return max(common, key=lambda v: tuple(int(x) for x in v.split(".")))


def advertise() -> dict[str, list[str]]:
    return {k: list(v) for k, v in sorted(SERVER_VERSIONS.items())}
