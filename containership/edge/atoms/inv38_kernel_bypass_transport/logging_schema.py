"""INV-38-C073 — Structured logging schema, redaction, and injection safety.

Emits bounded, enumerated structured log records.  Secret and tenant-sensitive
fields are redacted before serialization (C073-T03) and free-text is control-char
escaped so untrusted strings are encoded as data, not structure (C073-T05).
"""
from __future__ import annotations

import json

LOG_SCHEMA_VERSION = "log/1"
LEVELS = ("DEBUG", "INFO", "WARN", "ERROR", "SECURITY")

# Enumerated, aggregatable event names (C073-T02).
EVENTS = frozenset({
    "register", "deregister", "post", "poll", "fallback", "rejection",
    "provider_error", "recovery", "config_activation", "health_change",
})

_REDACT_KEYS = frozenset({"payload", "key", "mr_key", "credential", "secret", "token", "addr"})


def _escape(value: object) -> object:
    if isinstance(value, str):
        return value.encode("unicode_escape").decode("ascii")
    return value


def redact(fields: dict) -> dict:
    out = {}
    for k, v in fields.items():
        if k in _REDACT_KEYS:
            out[k] = "<redacted>"
        else:
            out[k] = _escape(v)
    return out


def make_record(*, level: str, event: str, operation_id: str, reason_code: str,
                tenant: str = "-", workload: str = "-", node: str = "-",
                generation: int = 0, extra: dict | None = None) -> dict:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r}")
    if event not in EVENTS:
        raise ValueError(f"unknown event {event!r}")
    rec = {
        "schema": LOG_SCHEMA_VERSION,
        "level": level,
        "event": event,
        "component": "INV-38",
        "node": node,
        "tenant": tenant,
        "workload": workload,
        "operation_id": operation_id,
        "generation": generation,
        "reason_code": reason_code,
    }
    if extra:
        rec.update(redact(extra))
    return rec


def serialize(rec: dict) -> str:
    return json.dumps(rec, sort_keys=True, separators=(",", ":"))
