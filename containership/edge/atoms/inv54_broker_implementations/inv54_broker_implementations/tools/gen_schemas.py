"""Regenerate machine-readable schemas from the runtime (component 18). CI fails on drift."""
from __future__ import annotations

import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
mod = __import__(PKG.name, fromlist=["errors", "config"])
from importlib import import_module  # noqa: E402

errors = import_module(f"{PKG.name}.errors")
config = import_module(f"{PKG.name}.config")
S = "https://json-schema.org/draft/2020-12/schema"


def schemas() -> dict[str, dict]:
    reg = errors.registry()
    out = {}
    out["error.schema.json"] = {
        "$schema": S, "$id": "urn:inv54:PK_BROKER_ERROR/1", "title": "INV-54 error", "type": "object",
        "required": ["schema", "code", "outcome", "retryable", "status", "message", "details"],
        "additionalProperties": False,
        "properties": {"schema": {"const": errors.ERROR_SCHEMA}, "code": {"enum": sorted(reg)},
                       "outcome": {"enum": [o.value for o in errors.Outcome]}, "retryable": {"type": "boolean"},
                       "status": {"type": "integer"}, "message": {"type": "string"},
                       "details": {"type": "object"}},
        "x-codes": {k: {"outcome": v.outcome.value, "status": v.http_status, "summary": v.summary}
                    for k, v in sorted(reg.items())}}
    props = {}
    for k, v in config.DEFAULTS.items():
        t = "object" if isinstance(v, dict) else "string"
        props[k] = {"type": t}
    props["schema"] = {"const": config.CONFIG_SCHEMA_VERSION}
    props["profile"] = {"enum": list(config.PROFILES)}
    props["provider"] = {"type": "object", "required": ["kind"],
                         "properties": {"kind": {"enum": list(config.PROVIDERS)},
                                        "endpoints": {"type": "array", "items": {"type": "string"}},
                                        "options": {"type": "object"}}}
    props["limits"] = {"type": "object", "properties": {
        k: {"type": "integer", "minimum": 1, "maximum": config.HARD_LIMITS.get(
            k if k.startswith("max_") else "max_partitions")} for k in config.DEFAULTS["limits"] if k != "overflow_policy"}}
    props["limits"]["properties"]["overflow_policy"] = {"enum": ["reject", "drop_oldest"]}
    out["config.schema.json"] = {"$schema": S, "$id": "urn:inv54:" + config.CONFIG_SCHEMA_VERSION,
                                 "title": "INV-54 configuration", "type": "object",
                                 "additionalProperties": False, "properties": props,
                                 "x-secret-reference-pattern": config.SECRET_REF.pattern}
    out["message.schema.json"] = {
        "$schema": S, "$id": "urn:inv54:PK_BROKER_LOG/1.1#record", "title": "INV-54 log record / fan-out envelope",
        "type": "object", "required": ["tenant", "dest", "value"], "additionalProperties": False,
        "properties": {"tenant": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"},
                       "dest": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"},
                       "key": {"type": "string"}, "value": {},
                       "idempotency_key": {"type": "string", "maxLength": 256},
                       "traceparent": {"type": "string", "pattern": "^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$"},
                       "position": {"type": "string", "description": "partition:offset (log) or provider handle"}}}
    out["offset.schema.json"] = {
        "$schema": S, "$id": "urn:inv54:PK_BROKER_OFFSET/1.0", "type": "object",
        "required": ["tenant", "stream", "consumer", "partition", "offset"], "additionalProperties": False,
        "properties": {"tenant": {"type": "string"}, "stream": {"type": "string"}, "consumer": {"type": "string"},
                       "partition": {"type": "integer", "minimum": 0}, "offset": {"type": "integer", "minimum": 0}}}
    out["health.schema.json"] = {
        "$schema": S, "$id": "urn:inv54:health/1", "type": "object",
        "required": ["schema", "live", "ready", "state", "version", "config_digest", "dependencies", "saturation"],
        "properties": {"schema": {"const": "inv54.health/1"}}}
    return out


if __name__ == "__main__":
    check = "--check" in sys.argv
    drift = []
    for name, sch in schemas().items():
        p = PKG / "schemas" / name
        text = json.dumps(sch, indent=2, sort_keys=True) + "\n"
        if check:
            if not p.exists() or p.read_text() != text:
                drift.append(name)
        else:
            p.write_text(text)
    if drift:
        print("schema drift:", drift)
        sys.exit(1)
    print("schemas ok" if check else "schemas written")
