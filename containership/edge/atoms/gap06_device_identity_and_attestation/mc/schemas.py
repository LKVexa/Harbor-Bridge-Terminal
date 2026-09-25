"""MC-05: typed external schemas for PK_NODE_IDENTITY/1, PK_ATTESTATION/1 and
PK_ACCEPTED_MEASUREMENTS/1, with a strict stdlib validator.

Rules: unknown fields rejected (closed schemas); integer/str/bytes-hex types
enforced; max lengths enforced; ``schema`` field must name a supported version.
Compatibility: a /1 server accepts only /1 messages; additive changes require
/2 (documented in docs/SCHEMAS.md).  The JSON Schema documents in
``schemas/*.schema.json`` are generated from these definitions.
"""
from __future__ import annotations

import json

from .errors import fail

HEX = "hex"
T = {  # field -> (type, required, maxlen)
    "PK_NODE_IDENTITY/1": {
        "schema": (str, True, 32), "node": (str, True, 255), "ek_cert_pem": (str, True, 16384),
        "ak_public_pem": (str, True, 4096), "site": (str, True, 128), "idempotency_key": (str, True, 64)},
    "PK_ATTESTATION/1": {
        "schema": (str, True, 32), "node": (str, True, 255), "nonce": (HEX, True, 128),
        "attest": (HEX, True, 8192), "signature": (HEX, True, 2048), "pcrs": (dict, True, 24),
        "event_log": (HEX, False, 8 * 1024 * 1024), "ima": (str, False, 4 * 1024 * 1024),
        "idempotency_key": (str, True, 64)},
    "PK_ACCEPTED_MEASUREMENTS/1": {
        "schema": (str, True, 32), "policy": (dict, True, 0), "signatures": (dict, True, 16),
        "idempotency_key": (str, True, 64)},
}
MAX_MESSAGE = 10 * 1024 * 1024


def validate(msg) -> dict:
    if isinstance(msg, (bytes, str)):
        if len(msg) > MAX_MESSAGE:
            raise fail("E_SCHEMA", "message too large")
        try:
            msg = json.loads(msg)
        except Exception as exc:
            raise fail("E_SCHEMA", "not JSON") from exc
    if not isinstance(msg, dict):
        raise fail("E_SCHEMA", "message must be an object")
    spec = T.get(msg.get("schema"))
    if spec is None:
        raise fail("E_SCHEMA", f"unsupported schema {msg.get('schema')!r}")
    extra = set(msg) - set(spec)
    if extra:
        raise fail("E_SCHEMA", f"unknown fields {sorted(extra)}")
    for name, (typ, req, maxlen) in spec.items():
        if name not in msg:
            if req:
                raise fail("E_SCHEMA", f"missing {name}")
            continue
        v = msg[name]
        if typ is HEX:
            if not isinstance(v, str) or len(v) % 2 or any(c not in "0123456789abcdef" for c in v):
                raise fail("E_SCHEMA", f"{name} must be lowercase hex")
        elif not isinstance(v, typ) or isinstance(v, bool):
            raise fail("E_SCHEMA", f"{name} must be {typ.__name__}")
        if maxlen and hasattr(v, "__len__") and len(v) > maxlen:
            raise fail("E_SCHEMA", f"{name} exceeds {maxlen}")
    if msg["schema"] == "PK_ATTESTATION/1":
        for k, v in msg["pcrs"].items():
            if not k.isdigit() or int(k) > 23 or not isinstance(v, str) or len(v) != 64:
                raise fail("E_SCHEMA", "pcrs must map '0'..'23' to 64-hex sha256 values")
    return msg


def json_schema(name: str) -> dict:
    props, req = {}, []
    for f, (typ, r, maxlen) in T[name].items():
        if typ is HEX:
            p = {"type": "string", "pattern": "^([0-9a-f]{2})*$"}
        else:
            p = {"type": {str: "string", dict: "object", int: "integer"}[typ]}
        if maxlen and typ in (str, HEX):
            p["maxLength"] = maxlen
        if f == "schema":
            p["const"] = name
        props[f] = p
        if r:
            req.append(f)
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"urn:pk:{name}",
            "title": name, "type": "object", "additionalProperties": False, "properties": props, "required": req}
