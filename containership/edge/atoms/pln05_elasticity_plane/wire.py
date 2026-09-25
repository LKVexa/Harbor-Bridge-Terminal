"""Boundary codec for the three PLN-05 interfaces.

The JSON Schema files under ``schemas/`` are the single source of truth; this
module interprets the subset of JSON Schema they use (type, const, enum,
required, properties, additionalProperties, minimum/maximum and the exclusive
forms, minLength/maxLength, pattern) and adds the cross-field rules listed in
each schema's ``x-cross-field``.  Nothing reaches business logic without
passing :func:`decode`.

Parser hardening: byte ceiling, bracket-depth pre-scan (so deeply nested input
cannot raise ``RecursionError``), duplicate-key rejection, and NaN/Infinity
rejection at the tokenizer.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re

from .errors import PlaneError

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
MAX_BYTES = 16 * 1024
MAX_DEPTH = 4
MAX_FIELDS = 32

_FILES = {
    "PK_DEMAND": "pk_demand_v1.json",
    "PK_CAPACITY_LIMITS": "pk_capacity_limits_v1.json",
    "PK_CAPACITY_TARGET": "pk_capacity_target_v1.json",
    "PK_ERROR": "error_v1.json",
}
SUPPORTED: dict[str, tuple[int, ...]] = {k: (1,) for k in _FILES}


def _load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / _FILES[name]).read_text(encoding="utf-8"))


SCHEMAS: dict[str, dict] = {k: _load(k) for k in _FILES}
_PATTERNS: dict[str, re.Pattern] = {}


def schema_checksums() -> dict[str, str]:
    """sha256 of each released schema file (published in release evidence)."""
    return {
        f"{k}/1": hashlib.sha256((SCHEMA_DIR / f).read_bytes()).hexdigest()
        for k, f in sorted(_FILES.items())
    }


def negotiate(family: str, peer_versions) -> int:
    """Return the highest mutually supported major version or raise E_SCHEMA_VERSION."""
    ours = set(SUPPORTED.get(family, ()))
    common = ours & {v for v in peer_versions if isinstance(v, int) and not isinstance(v, bool)}
    if not common:
        raise PlaneError("E_SCHEMA_VERSION", "no mutually supported schema version",
                         {"family": family if family in SUPPORTED else "unknown"})
    return max(common)


def _depth_ok(raw: bytes) -> bool:
    depth = 0
    in_str = esc = False
    for b in raw:
        if in_str:
            if esc:
                esc = False
            elif b == 0x5C:
                esc = True
            elif b == 0x22:
                in_str = False
        elif b == 0x22:
            in_str = True
        elif b in (0x7B, 0x5B):
            depth += 1
            if depth > MAX_DEPTH:
                return False
        elif b in (0x7D, 0x5D):
            depth -= 1
    return True


def _no_constants(token: str):
    raise ValueError("non-finite constant")


def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate key")
        out[k] = v
    return out


def parse_bytes(raw) -> dict:
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(raw, (bytes, bytearray)):
        raise PlaneError("E_SCHEMA_MALFORMED", "payload must be bytes")
    if len(raw) > MAX_BYTES:
        raise PlaneError("E_SCHEMA_TOO_LARGE", "payload exceeds byte ceiling", {"max_bytes": MAX_BYTES})
    if not _depth_ok(bytes(raw)):
        raise PlaneError("E_SCHEMA_TOO_DEEP", "payload nesting exceeds limit", {"max_depth": MAX_DEPTH})
    try:
        obj = json.loads(bytes(raw).decode("utf-8"), parse_constant=_no_constants,
                         object_pairs_hook=_pairs)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise PlaneError("E_SCHEMA_MALFORMED", "payload is not valid strict JSON") from None
    if not isinstance(obj, dict):
        raise PlaneError("E_SCHEMA_MALFORMED", "payload must be a JSON object")
    return obj


def _type_ok(value, t) -> bool:
    if isinstance(t, list):
        return any(_type_ok(value, x) for x in t)
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(float(value)))
    if t == "boolean":
        return isinstance(value, bool)
    if t == "object":
        return isinstance(value, dict)
    if t == "null":
        return value is None
    return False


def _check_field(name: str, value, spec: dict) -> None:
    def bad(why):
        raise PlaneError("E_SCHEMA_FIELD", f"field {name} {why}", {"field": name})

    if "const" in spec and value != spec["const"]:
        bad("has the wrong constant")
    if "enum" in spec and value not in spec["enum"]:
        bad("is not an allowed value")
    if "type" in spec and not _type_ok(value, spec["type"]):
        bad("has the wrong type")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in spec and value < spec["minimum"]:
            bad("is below minimum")
        if "maximum" in spec and value > spec["maximum"]:
            bad("is above maximum")
        if "exclusiveMinimum" in spec and value <= spec["exclusiveMinimum"]:
            bad("is not above exclusive minimum")
        if "exclusiveMaximum" in spec and value >= spec["exclusiveMaximum"]:
            bad("is not below exclusive maximum")
    if isinstance(value, str):
        if len(value) < spec.get("minLength", 0):
            bad("is too short")
        if "maxLength" in spec and len(value) > spec["maxLength"]:
            bad("is too long")
        if "pattern" in spec:
            pat = _PATTERNS.setdefault(spec["pattern"], re.compile(spec["pattern"]))
            if not pat.fullmatch(value):
                bad("does not match its pattern")


def validate(family: str, obj: dict) -> dict:
    """Validate an already-parsed object against ``family``/1; returns a copy without x- keys."""
    if family not in SCHEMAS:
        raise PlaneError("E_SCHEMA_VERSION", "unknown schema family")
    if not isinstance(obj, dict):
        raise PlaneError("E_SCHEMA_MALFORMED", "message must be an object")
    if len(obj) > MAX_FIELDS:
        raise PlaneError("E_SCHEMA_TOO_LARGE", "too many fields", {"max_fields": MAX_FIELDS})
    declared = obj.get("schema")
    if not isinstance(declared, str) or "/" not in declared:
        raise PlaneError("E_SCHEMA_VERSION", "missing schema identifier")
    fam, _, ver = declared.partition("/")
    if fam != family:
        raise PlaneError("E_SCHEMA_VERSION", "schema family mismatch", {"expected": family})
    if not ver.isdigit() or int(ver) not in SUPPORTED[family]:
        raise PlaneError("E_SCHEMA_VERSION", "unsupported schema version",
                         {"family": family, "supported": ",".join(map(str, SUPPORTED[family]))})
    schema = SCHEMAS[family]
    props = schema["properties"]
    clean = {}
    for key, value in obj.items():
        if not isinstance(key, str):
            raise PlaneError("E_SCHEMA_MALFORMED", "non-string key")
        if key.startswith("x-"):
            continue
        if key not in props:
            raise PlaneError("E_SCHEMA_UNKNOWN_CRITICAL", "unknown critical field",
                             {"field": key if re.fullmatch(r"[A-Za-z0-9_]{1,32}", key) else "<redacted>"})
        _check_field(key, value, props[key])
        clean[key] = value
    for req in schema["required"]:
        if req not in clean:
            raise PlaneError("E_SCHEMA_FIELD", f"missing required field {req}", {"field": req})
    if family == "PK_CAPACITY_LIMITS":
        if clean["floor"] > clean["ceiling"]:
            raise PlaneError("E_SCHEMA_FIELD", "floor exceeds ceiling", {"field": "floor"})
        if not clean["scale_down_at"] < clean["scale_up_at"]:
            raise PlaneError("E_SCHEMA_FIELD", "scale_down_at must be below scale_up_at",
                             {"field": "scale_down_at"})
    if family == "PK_CAPACITY_TARGET":
        if not clean["floor"] <= clean["target"] <= clean["ceiling"]:
            raise PlaneError("E_SCHEMA_FIELD", "target outside floor/ceiling", {"field": "target"})
    return clean


def decode(family: str, raw) -> dict:
    return validate(family, parse_bytes(raw))


def encode(family: str, obj: dict) -> bytes:
    """Validate then serialise canonically (sorted keys, no whitespace)."""
    validate(family, obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
