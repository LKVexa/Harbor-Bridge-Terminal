"""Versioned external contracts PK_FUTURE/1, PK_FUTURE_RESOLVE/1,
PK_FUTURE_ABANDON/1 (+ ERROR/STATUS) with a stdlib validator, canonical
encoding, size limits and version negotiation (C022, C027, C028, C029).

The schema dictionaries below are the single source of truth; ``schemas/*.json``
are generated from them by ``tools/gen_schemas.py`` and a test proves they match.

Evolution rules: within a major version fields are only *added* as optional and
only inside ``ext``; unknown top-level fields are rejected (strict), unknown
``ext`` members are ignored.  A breaking change bumps the major (``/2``).
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

from .errors import ERROR_SCHEMA, Rejected

CONTRACT_MAJOR = 1
SUPPORTED_MAJORS = (1,)            # N; N-1 does not exist yet (first wire release)
MAX_ID = 128
ID_PATTERN = r"^[A-Za-z0-9._:-]{1,128}$"
_TRACE = r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$"

_common = {
    "schema": {"type": "string"},
    "future_id": {"type": "string", "pattern": ID_PATTERN},
    "correlation_id": {"type": "string", "pattern": ID_PATTERN},
    "traceparent": {"type": "string", "pattern": _TRACE},
    "epoch": {"type": "integer", "minimum": 0},
    "idempotency_key": {"type": "string", "pattern": ID_PATTERN},
    "ext": {"type": "object"},
}

SCHEMAS: dict[str, dict] = {
    "PK_FUTURE/1": {
        "$id": "PK_FUTURE/1", "title": "typed one-shot handle", "type": "object",
        "additionalProperties": False,
        "required": ["schema", "future_id", "value_type", "epoch"],
        "properties": {**_common, "schema": {"const": "PK_FUTURE/1"},
                       "value_type": {"type": "string", "enum": ["str", "int", "float", "bool", "bytes", "object"]},
                       "tenant": {"type": "string", "pattern": ID_PATTERN}},
    },
    "PK_FUTURE_RESOLVE/1": {
        "$id": "PK_FUTURE_RESOLVE/1", "title": "value or error resolution", "type": "object",
        "additionalProperties": False,
        "required": ["schema", "future_id", "outcome", "epoch", "idempotency_key"],
        "properties": {**_common, "schema": {"const": "PK_FUTURE_RESOLVE/1"},
                       "outcome": {"type": "string", "enum": ["ok", "error"]},
                       "value": {},
                       "error": {"type": "object"}},
        "discriminator": {"outcome": {"ok": ["value"], "error": ["error"]}},
    },
    "PK_FUTURE_ABANDON/1": {
        "$id": "PK_FUTURE_ABANDON/1", "title": "writer dropped without resolving", "type": "object",
        "additionalProperties": False,
        "required": ["schema", "future_id", "epoch", "idempotency_key", "reason"],
        "properties": {**_common, "schema": {"const": "PK_FUTURE_ABANDON/1"},
                       "reason": {"type": "string", "enum": ["writer_dropped", "writer_crashed", "shutdown"]}},
    },
    ERROR_SCHEMA: {
        "$id": ERROR_SCHEMA, "title": "structured failure record", "type": "object",
        "additionalProperties": False,
        "required": ["schema", "code", "category", "retryable", "message", "details"],
        "properties": {"schema": {"const": ERROR_SCHEMA}, "code": {"type": "string", "pattern": r"^[A-Z_]{2,64}$"},
                       "category": {"type": "string"}, "retryable": {"type": "boolean"},
                       "message": {"type": "string", "maxLength": 600}, "details": {"type": "object"},
                       "cause": {"type": "object"}, "original_code": {"type": "string"}},
    },
    "PK_FUTURE_STATUS/1": {
        "$id": "PK_FUTURE_STATUS/1", "title": "component status", "type": "object",
        "additionalProperties": False,
        "required": ["schema", "component", "version", "state", "ready", "reasons", "config_revision",
                     "contract_versions", "capabilities", "dependencies", "limits", "policy_version"],
        "properties": {"schema": {"const": "PK_FUTURE_STATUS/1"}, "component": {"type": "string"},
                       "version": {"type": "string"},
                       "state": {"type": "string", "enum": ["HEALTHY", "DEGRADED", "FAILED"]},
                       "ready": {"type": "boolean"}, "reasons": {"type": "array"},
                       "config_revision": {"type": "string"}, "contract_versions": {"type": "array"},
                       "capabilities": {"type": "array"}, "dependencies": {"type": "object"},
                       "limits": {"type": "object"}, "policy_version": {"type": "string"},
                       "lineage": {"type": "object"}, "outstanding": {"type": "integer"},
                       "recent_decisions": {"type": "object"}},
    },
}

_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict, "array": list}


def validate(doc: Any, schema_id: str) -> list[str]:
    """Return a list of violations (empty = valid) for ``doc`` against ``schema_id``."""
    sch = SCHEMAS.get(schema_id)
    if sch is None:
        return [f"unknown schema {schema_id}"]
    if not isinstance(doc, dict):
        return ["document must be an object"]
    errs: list[str] = []
    props = sch["properties"]
    for r in sch.get("required", []):
        if r not in doc:
            errs.append(f"missing required field {r}")
    if sch.get("additionalProperties") is False:
        errs += [f"undeclared field {k}" for k in doc if k not in props]
    for k, v in doc.items():
        p = props.get(k)
        if p is None or not p:
            continue
        if "const" in p and v != p["const"]:
            errs.append(f"{k} must be {p['const']}")
            continue
        t = p.get("type")
        if t:
            py = _TYPES[t]
            if not isinstance(v, py) or (t in ("integer", "number") and isinstance(v, bool)):
                errs.append(f"{k} must be {t}")
                continue
        if "enum" in p and v not in p["enum"]:
            errs.append(f"{k} not in {p['enum']}")
        if "pattern" in p and not re.match(p["pattern"], v):
            errs.append(f"{k} malformed")
        if "maxLength" in p and len(v) > p["maxLength"]:
            errs.append(f"{k} too long")
        if "minimum" in p and v < p["minimum"]:
            errs.append(f"{k} below minimum")
    disc = sch.get("discriminator")
    if disc and not errs:
        for field, table in disc.items():
            need = table.get(doc.get(field), [])
            forbid = [f for opts in table.values() for f in opts if f not in need]
            errs += [f"{field}={doc.get(field)} requires {n}" for n in need if n not in doc]
            errs += [f"{field}={doc.get(field)} forbids {n}" for n in forbid if n in doc]
    return errs


def encode(doc: Mapping[str, Any]) -> bytes:
    """Canonical encoding: UTF-8 JSON, sorted keys, no insignificant whitespace."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def decode(blob: bytes, schema_id: str, *, max_bytes: int) -> dict:
    """Size limit is enforced *before* parsing (C028); then strict validation."""
    if not isinstance(blob, (bytes, bytearray)):
        raise Rejected("wire input must be bytes", code="INVALID_ARGUMENT")
    if len(blob) > max_bytes:
        raise Rejected("payload exceeds max_payload_bytes", code="RESOURCE_EXHAUSTED",
                       details={"size": len(blob), "limit": max_bytes})
    try:
        doc = json.loads(blob.decode("utf-8"), parse_constant=_no_nan)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise Rejected("malformed wire document", code="INVALID_ARGUMENT") from exc
    schema = doc.get("schema") if isinstance(doc, dict) else None
    if isinstance(schema, str) and schema.split("/")[0] == schema_id.split("/")[0] and schema != schema_id:
        raise Rejected(f"contract version {schema} not supported", code="INCOMPATIBLE_VERSION",
                       details={"offered": schema, "supported": schema_id})
    errs = validate(doc, schema_id)
    if errs:
        raise Rejected("schema violation", code="INVALID_ARGUMENT", details={"errors": "; ".join(errs[:6])})
    return doc


def _no_nan(x):
    raise ValueError(f"non-finite number {x}")


def negotiate(offered: list[int], supported: tuple[int, ...] = SUPPORTED_MAJORS) -> int:
    """Pick the highest common major; never silently downgrade semantics (C027)."""
    if not isinstance(offered, list) or not all(isinstance(v, int) and not isinstance(v, bool) for v in offered):
        raise Rejected("version offer must be a list of integers", code="INVALID_ARGUMENT")
    common = sorted(set(offered) & set(supported))
    if not common:
        side = "newer" if offered and min(offered) > max(supported) else "older"
        raise Rejected(f"no common contract version (peer is {side})", code="INCOMPATIBLE_VERSION",
                       details={"offered": str(offered), "supported": str(list(supported))})
    return common[-1]
