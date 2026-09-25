"""Versioned wire protocol for INV-53 (components 12, 15, 17, 18, 19).

The protocol is JSON over any byte transport.  ``REQUEST_FIELDS`` is the single
normative definition; ``json_schemas()`` renders it as JSON Schema (draft 2020-12)
and ``schemas/*.json`` are generated from it (a test fails if they drift).

Compatibility policy (docs/spec/COMPATIBILITY.md): a *minor* protocol revision may
only add optional request fields and new outcome codes; removing or re-typing a
field, or changing an existing code's meaning, requires a new major version.
Servers accept every version in ``SUPPORTED``; clients offer a list and the
highest mutual version wins (``negotiate``).
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

WIRE_MAJOR = "inv53.wire/1"
SUPPORTED = ("inv53.wire/1",)
OPS = ("put", "receive", "ack", "nack", "extend", "redrive", "health", "explain")

MAX_ID = 512
MAX_NAME = 128
MAX_REASON = 256

# field -> (json type, required-for ops, description)
REQUEST_FIELDS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "v": ("string", OPS, "Protocol version; must be one of SUPPORTED."),
    "op": ("string", OPS, "Operation."),
    "tenant": ("string", OPS, "Tenant namespace (isolation boundary)."),
    "queue": ("string", OPS, "Queue name inside the tenant."),
    "request_id": ("string", (), "Caller-chosen idempotency / correlation id."),
    "message": ("object", ("put",), "Message; must carry a string 'id'."),
    "id": ("string", ("ack", "nack", "extend", "redrive", "explain"), "Message id."),
    "lease": ("string", ("ack", "nack", "extend"), "Opaque lease fencing token."),
    "now": ("number", (), "Deprecated since 5.1.0: accepted for compatibility and ignored; the broker's clock times leases."),
    "extension": ("number", ("extend",), "Visibility extension in seconds."),
    "requeue": ("boolean", (), "nack only: requeue (default) or dead-letter."),
    "reason": ("string", (), "nack only: reason code."),
    "traceparent": ("string", (), "W3C trace context."),
    "auth": ("object", (), "Authentication block {kid, principal, ts, nonce, mac}."),
}

_PY = {"string": str, "object": dict, "number": (int, float), "boolean": bool}


class ProtocolError(ValueError):
    def __init__(self, code: str, reason: str) -> None:
        super().__init__(reason)
        self.code = code


def negotiate(offered: Any) -> str:
    if not isinstance(offered, (list, tuple)) or not offered:
        raise ProtocolError("E_PROTOCOL_VERSION", "client must offer a non-empty list of versions")
    mutual = [v for v in SUPPORTED if v in offered]
    if not mutual:
        raise ProtocolError("E_PROTOCOL_VERSION", f"no mutual version; server supports {list(SUPPORTED)}")
    return max(mutual)


def _name(value: Any, field: str, limit: int) -> None:
    if not isinstance(value, str) or not value or len(value) > limit or not value.isprintable() \
            or value != value.strip() or "/" in value:
        raise ProtocolError("E_VALIDATION", f"{field} must be a printable name of 1..{limit} chars without '/'")
    if value in (".", "..") or "\\" in value or ":" in value:
        raise ProtocolError("E_VALIDATION", f"{field} must not be a path component such as '.' or '..'")


def validate_request(req: Any) -> dict[str, Any]:
    if not isinstance(req, Mapping):
        raise ProtocolError("E_VALIDATION", "request must be a JSON object")
    unknown = set(req) - set(REQUEST_FIELDS)
    if unknown:
        raise ProtocolError("E_VALIDATION", f"unknown field(s) {sorted(unknown)}")
    if req.get("v") not in SUPPORTED:
        raise ProtocolError("E_PROTOCOL_VERSION", f"unsupported version {req.get('v')!r}")
    op = req.get("op")
    if op not in OPS:
        raise ProtocolError("E_VALIDATION", f"unknown op {op!r}")
    for field, (typ, required, _) in REQUEST_FIELDS.items():
        if field not in req:
            if op in required:
                raise ProtocolError("E_VALIDATION", f"{op} requires {field!r}")
            continue
        val = req[field]
        if typ != "boolean" and isinstance(val, bool) or not isinstance(val, _PY[typ]):
            raise ProtocolError("E_VALIDATION", f"{field} must be {typ}")
        if typ == "number" and not isfinite(float(val)):
            raise ProtocolError("E_VALIDATION", f"{field} must be finite")
    _name(req["tenant"], "tenant", MAX_NAME)
    _name(req["queue"], "queue", MAX_NAME)
    for f, limit in (("id", MAX_ID), ("lease", 128), ("reason", MAX_REASON), ("request_id", 128),
                     ("traceparent", 55)):
        if f in req and (not req[f] or len(req[f]) > limit):
            raise ProtocolError("E_VALIDATION", f"{f} must be 1..{limit} chars")
    if "extension" in req and req["extension"] <= 0:
        raise ProtocolError("E_VALIDATION", "extension must be > 0")
    if op == "put":
        mid = req["message"].get("id")
        if not isinstance(mid, str) or not mid.strip() or len(mid) > MAX_ID:
            raise ProtocolError("E_VALIDATION", "message.id must be a non-empty string <= 512 chars")
        headers = req["message"].get("headers")
        if headers is not None and (not isinstance(headers, dict)
                                    or not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items())):
            raise ProtocolError("E_VALIDATION", "message.headers must be an object of string values")
    if ("requeue" in req or "reason" in req) and op != "nack":
        raise ProtocolError("E_VALIDATION", "requeue/reason are only valid for nack")
    return dict(req)


def response(outcome: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"v": WIRE_MAJOR, "outcome": dict(outcome), **extra}


def json_schemas() -> dict[str, dict[str, Any]]:
    props = {}
    for f, (typ, _, desc) in REQUEST_FIELDS.items():
        props[f] = {"type": typ, "description": desc}
    props["v"]["enum"] = list(SUPPORTED)
    props["op"]["enum"] = list(OPS)
    all_of = []
    for op in OPS:
        req = [f for f, (_, r, _) in REQUEST_FIELDS.items() if op in r]
        all_of.append({"if": {"properties": {"op": {"const": op}}}, "then": {"required": req}})
    request = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "inv53.wire/1/request",
               "type": "object", "additionalProperties": False, "properties": props, "allOf": all_of}
    delivery = {"type": "object", "additionalProperties": False, "required": ["message", "lease", "deadline", "attempt"],
                "properties": {"message": {"type": "object"}, "lease": {"type": "string"},
                               "deadline": {"type": "number"}, "attempt": {"type": "integer", "minimum": 1}}}
    resp = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "inv53.wire/1/response",
            "type": "object", "required": ["v", "outcome"],
            "properties": {"v": {"const": WIRE_MAJOR},
                           "outcome": {"type": "object", "required": ["code", "kind", "retryable", "reason"],
                                       "properties": {"code": {"type": "string"}, "kind": {"type": "string"},
                                                      "retryable": {"type": "boolean"}, "reason": {"type": "string"},
                                                      "data": {"type": "object"}}},
                           "delivery": delivery, "explain": {"type": "object"}, "health": {"type": "object"}}}
    return {"request.schema.json": request, "response.schema.json": resp}
