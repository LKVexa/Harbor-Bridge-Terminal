"""Versioned typed schemas and a strict validator (INV-63-C022, C027, C028).

The schema documents live in ``schemas/*.json`` (one file per contract, name
``<ID>_v<major>.json``).  They are the single source of truth: this module
loads them, validates payloads against them, negotiates versions and exposes
their digests for fixture/conformance binding.

The validator implements the JSON-Schema subset the contracts use (type,
required, properties, additionalProperties, enum, const, pattern, minLength,
maxLength, minimum, maximum, items, minItems, maxItems, $ref to local defs)
and fails closed on any keyword it does not understand.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from typing import Any

from .errors import DeploymentError, ErrorCode

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"

# INV-63-C028 interface limits (also documented in docs/interfaces/LIMITS.md)
MAX_PAYLOAD_BYTES = 64 * 1024
MAX_DEPTH = 8

# INV-63-C016/C027: supported majors per contract; minors are additive only.
SUPPORTED: dict[str, tuple[int, ...]] = {
    "PK_DEPLOY_DESIRED": (1, 2),
    "PK_DEPLOY_DIFF": (1,),
    "PK_DEPLOY_ROLLOUT": (1,),
    "PK_DEPLOY_ERROR": (1,),
    "PK_DEPLOY_EVENT": (1,),
    "PK_DEPLOY_CONFIG": (1,),
    "PK_DEPLOY_REQUEST": (1,),
    "PK_DEPLOY_GATE": (1,),
}
DEPRECATED: dict[str, dict[int, str]] = {"PK_DEPLOY_DESIRED": {1: "2027-09-30"}}

_KNOWN = {"$schema", "$id", "title", "description", "type", "required", "properties",
          "additionalProperties", "enum", "const", "pattern", "minLength", "maxLength",
          "minimum", "maximum", "items", "minItems", "maxItems", "$ref", "$defs", "x-inv63"}

_cache: dict[str, dict[str, Any]] = {}


def schema_id(name: str, major: int) -> str:
    return f"{name}/{major}"


def load(name: str, major: int) -> dict[str, Any]:
    key = schema_id(name, major)
    if key not in _cache:
        path = SCHEMA_DIR / f"{name}_v{major}.json"
        if not path.is_file():
            raise DeploymentError(ErrorCode.UNSUPPORTED_VERSION, f"no schema {key}")
        _cache[key] = json.loads(path.read_text(encoding="utf-8"))
    return _cache[key]


def digest(name: str, major: int) -> str:
    path = SCHEMA_DIR / f"{name}_v{major}.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def all_schema_digests() -> dict[str, str]:
    out = {}
    for p in sorted(SCHEMA_DIR.glob("*_v*.json")):
        out[p.stem] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def parse_id(value: str) -> tuple[str, int]:
    m = re.fullmatch(r"([A-Z][A-Z0-9_]{2,63})/([1-9][0-9]{0,2})", value or "")
    if not m:
        raise DeploymentError(ErrorCode.SCHEMA_VIOLATION, f"malformed schema id {value!r}")
    return m.group(1), int(m.group(2))


def negotiate(name: str, peer_majors: list[int]) -> int:
    """INV-63-C027: pick the highest major both sides support, else fail closed."""
    ours = set(SUPPORTED.get(name, ()))
    common = ours & {int(v) for v in peer_majors if isinstance(v, int) and not isinstance(v, bool)}
    if not common:
        raise DeploymentError(ErrorCode.UNSUPPORTED_VERSION,
                              f"no common {name} version", {"ours": sorted(ours), "peer": sorted(peer_majors)})
    return max(common)


def _type_ok(value: Any, t: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(t, False)


def _validate(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str, depth: int) -> None:
    if depth > MAX_DEPTH:
        raise DeploymentError(ErrorCode.SCHEMA_VIOLATION, f"{path}: nesting deeper than {MAX_DEPTH}")
    unknown = set(schema) - _KNOWN
    if unknown:
        raise DeploymentError(ErrorCode.INTERNAL, f"schema uses unsupported keywords {sorted(unknown)}")
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            raise DeploymentError(ErrorCode.INTERNAL, f"non-local $ref {ref}")
        return _validate(value, root["$defs"][ref.split("/")[-1]], root, path, depth + 1)

    def fail(msg: str) -> None:
        raise DeploymentError(ErrorCode.SCHEMA_VIOLATION, f"{path or '$'}: {msg}", {"path": path or "$"})

    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_type_ok(value, x) for x in types):
            fail(f"expected {t}")
    if "const" in schema and value != schema["const"]:
        fail(f"must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        fail(f"must be one of {schema['enum']}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            fail("too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            fail("too long")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            fail("does not match pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            fail(f"below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            fail(f"above maximum {schema['maximum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            fail("too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            fail("too many items")
        if "items" in schema:
            for i, item in enumerate(value):
                _validate(item, schema["items"], root, f"{path}[{i}]", depth + 1)
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                fail(f"missing required property {req!r}")
        props = schema.get("properties", {})
        extra = set(value) - set(props)
        if extra and schema.get("additionalProperties", True) is False:
            fail(f"unexpected properties {sorted(extra)}")
        for k, v in value.items():
            if k in props:
                _validate(v, props[k], root, f"{path}.{k}", depth + 1)


def validate(payload: Any, schema_ref: str) -> dict[str, Any]:
    name, major = parse_id(schema_ref)
    if major not in SUPPORTED.get(name, ()):
        raise DeploymentError(ErrorCode.UNSUPPORTED_VERSION, f"{schema_ref} not supported",
                              {"supported": list(SUPPORTED.get(name, ()))})
    schema = load(name, major)
    _validate(payload, schema, schema, "", 0)
    return payload


def parse_bytes(raw: bytes, schema_ref: str) -> dict[str, Any]:
    """Untrusted wire entry point: size-limit, strict JSON parse, validate."""
    if not isinstance(raw, (bytes, bytearray)):
        raise DeploymentError(ErrorCode.INVALID_REQUEST, "payload must be bytes")
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise DeploymentError(ErrorCode.PAYLOAD_TOO_LARGE, f"payload {len(raw)} > {MAX_PAYLOAD_BYTES} bytes",
                              {"limit": MAX_PAYLOAD_BYTES})

    def no_dupes(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise DeploymentError(ErrorCode.SCHEMA_VIOLATION, f"duplicate key {k!r}")
            d[k] = v
        return d

    def bad_const(x):
        raise DeploymentError(ErrorCode.SCHEMA_VIOLATION, f"non-finite number {x}")

    try:
        text = bytes(raw).decode("utf-8")
        obj = json.loads(text, object_pairs_hook=no_dupes, parse_constant=bad_const)
    except DeploymentError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise DeploymentError(ErrorCode.SCHEMA_VIOLATION, f"unparseable payload: {type(exc).__name__}") from None
    return validate(obj, schema_ref)
