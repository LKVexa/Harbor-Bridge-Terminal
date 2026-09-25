"""Generate JSON Schemas for every public boundary format (MC-10) from the code itself.

``--check`` exits 1 if the checked-in ``schemas/`` differ from what the code
generates, so schemas cannot silently drift from the implementation.
"""
from __future__ import annotations

import json
import os
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(PKG))

from inv57_durable_execution import config, errors, identity, status  # noqa: E402
from inv57_durable_execution.durable import HISTORY_EVENT_SCHEMA  # noqa: E402

S = "https://json-schema.org/draft/2020-12/schema"


def build() -> dict[str, dict]:
    idf = {"type": "string", "pattern": identity._FIELD_RE.pattern.join("^$"),
           "maxLength": identity.MAX_FIELD_LEN}
    cfg_props = {}
    for k, (typ, default, rule) in config.SCHEMA.items():
        p = {"type": {int: "integer", float: "number", str: "string", bool: "boolean"}[typ], "default": default}
        if isinstance(rule, tuple):
            p["minimum"], p["maximum"] = rule
        elif isinstance(rule, set):
            p["enum"] = sorted(rule)
        if k.endswith("_secret_ref"):
            p["pattern"] = "^(secretref://.+)?$"
        cfg_props[k] = p
    return {
        "identity": {"$schema": S, "$id": identity.IDENTITY_SCHEMA, "type": "object",
                     "additionalProperties": False, "required": ["schema", *identity._FIELDS],
                     "properties": {"schema": {"const": identity.IDENTITY_SCHEMA},
                                    **{f: idf for f in identity._FIELDS}}},
        "history_event": {"$schema": S, "$id": HISTORY_EVENT_SCHEMA, "type": "object",
                          "additionalProperties": False,
                          "required": ["schema", "seq", "kind", "activity_id", "name", "fingerprint",
                                       "payload", "prev_digest", "digest"],
                          "properties": {"schema": {"const": HISTORY_EVENT_SCHEMA},
                                         "seq": {"type": "integer", "minimum": 0},
                                         "kind": {"enum": ["completed", "failed", "started"]},
                                         "activity_id": {"type": "string", "minLength": 1},
                                         "name": {"type": "string", "minLength": 1},
                                         "fingerprint": {"type": ["string", "null"]},
                                         "payload": {"type": ["object", "null"]},
                                         "prev_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                                         "digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}},
        "error": {"$schema": S, "$id": errors.ERROR_MODEL_SCHEMA, "type": "object",
                  "additionalProperties": False,
                  "required": ["schema", "code", "type", "category", "retryable", "http_status",
                               "summary", "detail"],
                  "properties": {"schema": {"const": errors.ERROR_MODEL_SCHEMA},
                                 "code": {"enum": [r["code"] for r in errors.registry()] + ["INV57-E999"]},
                                 "type": {"type": "string"},
                                 "category": {"enum": sorted({r["category"] for r in errors.registry()})},
                                 "retryable": {"enum": sorted({r["retryable"] for r in errors.registry()})},
                                 "http_status": {"type": "integer"}, "summary": {"type": "string"},
                                 "detail": {"type": ["string", "null"]}}},
        "status": {"$schema": S, "$id": status.STATUS_SCHEMA, "type": "object",
                   "required": ["schema", "version", "mode", "ready", "live", "config", "environment",
                                "site", "history_schema", "capabilities", "dependencies"],
                   "properties": {"schema": {"const": status.STATUS_SCHEMA},
                                  "mode": {"enum": ["degraded", "frozen", "ready"]},
                                  "capabilities": {"type": "array", "items": {"enum": list(status.CAPABILITIES)}}}},
        "config": {"$schema": S, "$id": config.CONFIG_SCHEMA, "type": "object",
                   "additionalProperties": False, "properties": cfg_props},
    }


def main() -> int:
    out = os.path.join(PKG, "schemas")
    os.makedirs(out, exist_ok=True)
    drift = []
    for name, schema in build().items():
        text = json.dumps(schema, indent=1, sort_keys=True) + "\n"
        path = os.path.join(out, f"{name}.schema.json")
        if "--check" in sys.argv:
            if not os.path.exists(path) or open(path).read() != text:
                drift.append(name)
        else:
            open(path, "w").write(text)
    if drift:
        print("schema drift:", drift)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
