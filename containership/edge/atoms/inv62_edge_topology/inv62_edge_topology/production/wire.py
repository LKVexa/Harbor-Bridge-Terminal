"""PK_TOPO_* wire contracts: typed schemas, canonical codec, limits and
version negotiation (MC-012, MC-017, MC-018).

The schemas below are the single source of truth; ``tools/export_schemas.py``
writes them to ``schemas/*.schema.json`` and CI fails if the files drift.
"""
from __future__ import annotations

import json
from typing import Any

from . import errors
from .schema import SchemaViolation, Validator

# ----------------------------------------------------------------- limits
MAX_PAYLOAD_BYTES = 256 * 1024
MAX_JSON_DEPTH = 16
MAX_MUTATIONS_PER_APPLY = 1_000
MAX_CANDIDATES = 16
MAX_CONSTRAINT_EXCLUDES = 64
MAX_DEADLINE_MS = 60_000
DEFAULT_DEADLINE_MS = 2_000

IDENT = {"type": "string", "minLength": 1, "maxLength": 128, "pattern": r"[A-Za-z0-9\-_.:]+"}
CAPS = {"type": "array", "items": {"$ref": "#/$defs/ident"}, "maxItems": 64, "uniqueItems": True}

# ----------------------------------------------------------- versioning
SUPPORTED: dict[str, tuple[int, ...]] = {
    "PK_TOPO_GRAPH": (1,),
    "PK_TOPO_NEAREST": (1,),
    "PK_TOPO_PARTITION": (1,),
}
#: Optional features a peer may request.  Unknown *required* features are refused.
FEATURES: dict[str, frozenset[str]] = {
    "PK_TOPO_GRAPH": frozenset({"atomic-apply", "cas-revision"}),
    "PK_TOPO_NEAREST": frozenset({"residency", "explain", "staleness"}),
    "PK_TOPO_PARTITION": frozenset({"fencing", "lease"}),
}

_ENVELOPE_COMMON = {
    "protocol": {"type": "string", "pattern": r"PK_TOPO_(GRAPH|NEAREST|PARTITION)/[0-9]{1,3}"},
    "accept_versions": {"type": "array", "items": {"type": "integer", "minimum": 1, "maximum": 999}, "minItems": 1, "maxItems": 8},
    "required_features": {"type": "array", "items": {"$ref": "#/$defs/ident"}, "maxItems": 16, "uniqueItems": True},
    "tenant": {"$ref": "#/$defs/ident"},
    "request_id": {"type": "string", "minLength": 8, "maxLength": 64, "pattern": r"[A-Za-z0-9\-_]+"},
    "idempotency_key": {"type": "string", "minLength": 8, "maxLength": 64, "pattern": r"[A-Za-z0-9\-_]+"},
    "deadline_ms": {"type": "integer", "minimum": 1, "maximum": MAX_DEADLINE_MS},
    "traceparent": {"type": "string", "pattern": r"00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}"},
    "credential": {"type": "string", "minLength": 16, "maxLength": 4096},
}


def _envelope(protocol: str, ops: dict[str, dict[str, Any]]) -> dict[str, Any]:
    alternatives = []
    for op, body in ops.items():
        alternatives.append({
            "type": "object",
            "required": ["protocol", "op", "tenant", "request_id", "credential", "body"],
            "additionalProperties": False,
            "properties": {**_ENVELOPE_COMMON, "op": {"const": op}, "body": body},
        })
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:inv62:{protocol.lower()}:request:1",
        "title": f"{protocol}/1 request",
        "$defs": {"ident": IDENT},
        "oneOf": alternatives,
    }


_MUTATION = {
    "oneOf": [
        {"type": "object", "additionalProperties": False, "required": ["kind", "node", "tier"],
         "properties": {"kind": {"const": "add_node"}, "node": {"$ref": "#/$defs/ident"},
                        "tier": {"enum": ["cloud", "region", "site", "device"]},
                        "site": {"$ref": "#/$defs/ident"}, "parent": {"$ref": "#/$defs/ident"},
                        "residency": {"$ref": "#/$defs/ident"}, "caps": CAPS}},
        {"type": "object", "additionalProperties": False, "required": ["kind", "node"],
         "properties": {"kind": {"const": "remove_node"}, "node": {"$ref": "#/$defs/ident"}}},
        {"type": "object", "additionalProperties": False, "required": ["kind", "a", "b", "latency_ms"],
         "properties": {"kind": {"const": "connect"}, "a": {"$ref": "#/$defs/ident"}, "b": {"$ref": "#/$defs/ident"},
                        "latency_ms": {"type": "number", "minimum": 0, "maximum": 3_600_000},
                        "up": {"type": "boolean"}, "measured_at": {"type": "number", "minimum": 0}}},
        {"type": "object", "additionalProperties": False, "required": ["kind", "a", "b"],
         "properties": {"kind": {"const": "disconnect"}, "a": {"$ref": "#/$defs/ident"}, "b": {"$ref": "#/$defs/ident"}}},
        {"type": "object", "additionalProperties": False, "required": ["kind", "a", "b", "up"],
         "properties": {"kind": {"const": "set_link_state"}, "a": {"$ref": "#/$defs/ident"}, "b": {"$ref": "#/$defs/ident"},
                        "up": {"type": "boolean"}, "measured_at": {"type": "number", "minimum": 0}}},
        {"type": "object", "additionalProperties": False, "required": ["kind", "a", "b", "ok", "at"],
         "properties": {"kind": {"const": "probe"}, "a": {"$ref": "#/$defs/ident"}, "b": {"$ref": "#/$defs/ident"},
                        "ok": {"type": "boolean"}, "latency_ms": {"type": "number", "minimum": 0, "maximum": 3_600_000},
                        "at": {"type": "number", "minimum": 0}}},
    ]
}

REQUEST_SCHEMAS: dict[str, dict[str, Any]] = {
    "PK_TOPO_GRAPH": _envelope("PK_TOPO_GRAPH", {
        "apply": {"type": "object", "additionalProperties": False, "required": ["mutations"],
                  "properties": {"expected_revision": {"type": "integer", "minimum": 0},
                                 "mutations": {"type": "array", "minItems": 1, "maxItems": MAX_MUTATIONS_PER_APPLY,
                                               "items": _MUTATION}}},
        "get": {"type": "object", "additionalProperties": False,
                "properties": {"include_links": {"type": "boolean"}}},
    }),
    "PK_TOPO_NEAREST": _envelope("PK_TOPO_NEAREST", {
        "resolve": {"type": "object", "additionalProperties": False, "required": ["origin", "capability"],
                    "properties": {"origin": {"$ref": "#/$defs/ident"}, "capability": {"$ref": "#/$defs/ident"},
                                   "constraints": {"type": "object", "additionalProperties": False, "properties": {
                                       "residency": {"type": "array", "items": {"$ref": "#/$defs/ident"}, "minItems": 1, "maxItems": 16, "uniqueItems": True},
                                       "max_latency_ms": {"type": "number", "minimum": 0},
                                       "exclude": {"type": "array", "items": {"$ref": "#/$defs/ident"}, "maxItems": MAX_CONSTRAINT_EXCLUDES, "uniqueItems": True},
                                       "same_site_only": {"type": "boolean"},
                                       "prefer": {"enum": ["latency", "cost"]}}},
                                   "explain": {"type": "boolean"}}},
    }),
    "PK_TOPO_PARTITION": _envelope("PK_TOPO_PARTITION", {
        "status": {"type": "object", "additionalProperties": False, "required": ["site"],
                   "properties": {"site": {"$ref": "#/$defs/ident"}, "cloud": {"$ref": "#/$defs/ident"}}},
        "acquire": {"type": "object", "additionalProperties": False, "required": ["site", "candidate"],
                    "properties": {"site": {"$ref": "#/$defs/ident"}, "candidate": {"$ref": "#/$defs/ident"},
                                   "cloud": {"$ref": "#/$defs/ident"}}},
        "renew": {"type": "object", "additionalProperties": False, "required": ["site", "candidate", "fencing_token"],
                  "properties": {"site": {"$ref": "#/$defs/ident"}, "candidate": {"$ref": "#/$defs/ident"},
                                 "fencing_token": {"type": "integer", "minimum": 1}}},
        "validate_token": {"type": "object", "additionalProperties": False, "required": ["site", "fencing_token"],
                           "properties": {"site": {"$ref": "#/$defs/ident"}, "fencing_token": {"type": "integer", "minimum": 1}}},
    }),
}

RESPONSE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:inv62:pk_topo:response:1",
    "title": "PK_TOPO_*/1 response envelope",
    "$defs": {"ident": IDENT},
    "type": "object",
    "additionalProperties": False,
    "required": ["protocol", "request_id", "outcome"],
    "properties": {
        "protocol": {"type": "string"},
        "request_id": {"type": "string"},
        "outcome": {"enum": [o.value for o in errors.Outcome]},
        "revision": {"type": "integer", "minimum": 0},
        "result": {"type": "object"},
        "error": {"type": "object", "additionalProperties": False, "required": ["code", "outcome", "message", "retryable", "details"],
                  "properties": {"code": {"enum": sorted(errors.registry())}, "outcome": {"type": "string"},
                                 "message": {"type": "string", "maxLength": 512}, "retryable": {"type": "boolean"},
                                 "details": {"type": "object"}, "retry_after_ms": {"type": "integer", "minimum": 0},
                                 "correlation_id": {"type": "string"}}},
        "decision_id": {"type": "string"},
        "degraded_mode": {"type": "string"},
        "traceparent": {"type": "string"},
    },
}

_VALIDATORS = {name: Validator(schema) for name, schema in REQUEST_SCHEMAS.items()}
_RESPONSE_VALIDATOR = Validator(RESPONSE_SCHEMA)


# ---------------------------------------------------------------- codec
def _depth(value: Any, limit: int) -> None:
    stack = [(value, 1)]
    while stack:
        item, d = stack.pop()
        if d > limit:
            raise errors.TopoError(errors.PAYLOAD_TOO_LARGE, f"JSON nesting deeper than {limit}")
        if isinstance(item, dict):
            stack.extend((v, d + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, d + 1) for v in item)


def _reject_constant(token: str) -> Any:
    raise ValueError(f"non-finite number {token} is not permitted")


def _no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate key {key!r}")
        out[key] = value
    return out


def decode(raw: bytes | str) -> dict[str, Any]:
    """Parse untrusted bytes with size, depth, duplicate-key and NaN guards."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(raw, (bytes, bytearray)):
        raise errors.TopoError(errors.INVALID_REQUEST, "payload must be bytes")
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise errors.TopoError(errors.PAYLOAD_TOO_LARGE, f"payload exceeds {MAX_PAYLOAD_BYTES} bytes",
                               {"limit_bytes": MAX_PAYLOAD_BYTES, "size_bytes": len(raw)})
    try:
        text = bytes(raw).decode("utf-8", errors="strict")
        value = json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_no_dupes)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise errors.TopoError(errors.INVALID_REQUEST, "payload is not valid canonical JSON",
                               {"reason": type(exc).__name__}) from None
    _depth(value, MAX_JSON_DEPTH)
    if not isinstance(value, dict):
        raise errors.TopoError(errors.INVALID_REQUEST, "payload must be a JSON object")
    return value


def encode(value: dict[str, Any]) -> bytes:
    """Canonical encoding: sorted keys, no whitespace, UTF-8, finite numbers."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def negotiate(request: dict[str, Any]) -> tuple[str, int]:
    """Return (family, version) or raise UNSUPPORTED_VERSION (MC-017)."""
    protocol = request.get("protocol")
    if not isinstance(protocol, str) or "/" not in protocol:
        raise errors.TopoError(errors.INVALID_REQUEST, "protocol must be FAMILY/VERSION")
    family, _, ver = protocol.partition("/")
    if family not in SUPPORTED or not ver.isdigit():
        raise errors.TopoError(errors.UNSUPPORTED_VERSION, f"unknown protocol {protocol!r}",
                               {"supported": {k: list(v) for k, v in SUPPORTED.items()}})
    offered = {int(ver)}
    accept = request.get("accept_versions")
    if isinstance(accept, list):
        offered |= {v for v in accept if isinstance(v, int) and not isinstance(v, bool)}
    common = offered & set(SUPPORTED[family])
    if not common:
        raise errors.TopoError(errors.UNSUPPORTED_VERSION, f"no common version for {family}",
                               {"offered": sorted(offered), "supported": list(SUPPORTED[family])})
    required = request.get("required_features") or []
    missing = sorted(set(required) - FEATURES[family]) if isinstance(required, list) else []
    if missing:
        raise errors.TopoError(errors.UNSUPPORTED_VERSION, "required features not supported",
                               {"missing_features": missing, "supported_features": sorted(FEATURES[family])})
    return family, max(common)


def validate_request(request: dict[str, Any]) -> tuple[str, int]:
    family, version = negotiate(request)
    try:
        _VALIDATORS[family].validate(request)
    except SchemaViolation as exc:
        raise errors.TopoError(errors.INVALID_REQUEST, "request failed schema validation",
                               {"path": exc.path, "reason": exc.reason}) from None
    return family, version


def validate_response(response: dict[str, Any]) -> None:
    _RESPONSE_VALIDATOR.validate(response)
