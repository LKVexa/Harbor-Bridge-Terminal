"""Versioned wire contracts and version negotiation (C021, C022, C027, C028, C085).

Every externally visible INV-52 contract has an identifier ``NAME/MAJOR`` and a
JSON Schema under ``schemas/``.  ``parse_publish_request`` is the single entry
point for untrusted bytes (HTTP body, broker frame): size is checked before
parsing, JSON errors and nesting bombs become ``PK_MSG_ENVELOPE_INVALID``, and
nothing else escapes.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Iterable, Mapping

from .runtime import (DEFAULT_MAX_JSON_DEPTH, DEFAULT_MAX_PAYLOAD_BYTES, IncompleteEnvelope, MessagingError,
                      json_depth, validate_envelope)

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent / "schemas"
SUPPORTED: dict[str, tuple[int, ...]] = {
    "PK_MSG_ENVELOPE": (1,),
    "PK_MSG_PUBLISH": (1,),
    "PK_MSG_SUBSCRIBE": (1,),
    "PK_MSG_CONFIG": (1,),
    "PK_MSG_DECISION": (1,),
    "PK_MSG_HEALTH": (1,),
}
SCHEMA_FILES = {
    "PK_MSG_ENVELOPE/1": "PK_MSG_ENVELOPE_1.schema.json",
    "PK_MSG_PUBLISH/1": "PK_MSG_PUBLISH_1.schema.json",
    "PK_MSG_SUBSCRIBE/1": "PK_MSG_SUBSCRIBE_1.schema.json",
    "PK_MSG_CONFIG/1": "PK_MSG_CONFIG_1.schema.json",
    "PK_MSG_DECISION/1": "PK_MSG_DECISION_1.schema.json",
    "PK_MSG_HEALTH/1": "PK_MSG_HEALTH_1.schema.json",
}


class VersionUnsupported(MessagingError, ValueError):
    code = "PK_MSG_VERSION_UNSUPPORTED"


def parse_contract_id(value: Any) -> tuple[str, int]:
    if not isinstance(value, str) or value.count("/") != 1:
        raise VersionUnsupported("contract id must look like NAME/MAJOR")
    name, major = value.split("/")
    if not major.isdigit() or name not in SUPPORTED:
        raise VersionUnsupported(f"unknown contract {value!r}")
    if int(major) not in SUPPORTED[name]:
        raise VersionUnsupported(f"{value} unsupported; supported majors {SUPPORTED[name]}",
                                 details={"supported": list(SUPPORTED[name])})
    return name, int(major)


def negotiate(contract: str, offered: Iterable[Any]) -> int:
    """Highest mutually supported major; a peer with no overlap is refused (C027)."""
    ours = set(SUPPORTED.get(contract, ()))
    common = ours.intersection(v for v in offered if isinstance(v, int) and not isinstance(v, bool))
    if not common:
        raise VersionUnsupported(f"no common {contract} version", details={"ours": sorted(ours)})
    return max(common)


def load_schema(contract_id: str) -> dict[str, Any]:
    parse_contract_id(contract_id)
    return json.loads((SCHEMA_DIR / SCHEMA_FILES[contract_id]).read_text(encoding="utf-8"))


def parse_publish_request(raw: bytes | str, *, max_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES + 4096,
                          max_depth: int = DEFAULT_MAX_JSON_DEPTH + 2) -> dict[str, Any]:
    """Parse ``PK_MSG_PUBLISH/1``: {"contract", "app", "topic", "message"}."""
    data = raw.encode("utf-8", "surrogatepass") if isinstance(raw, str) else raw
    if not isinstance(data, (bytes, bytearray)):
        raise IncompleteEnvelope("request must be bytes or text")
    if len(data) > max_bytes:
        raise IncompleteEnvelope("request exceeds size limit", details={"bytes": len(data), "limit": max_bytes})
    try:
        obj = json.loads(data)
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise IncompleteEnvelope("request is not valid JSON", details={"error_type": type(exc).__name__}) from exc
    if not isinstance(obj, dict):
        raise IncompleteEnvelope("request must be an object")
    if json_depth(obj) > max_depth:
        raise IncompleteEnvelope("request nesting exceeds limit")
    name, _ = parse_contract_id(obj.get("contract"))
    if name != "PK_MSG_PUBLISH":
        raise IncompleteEnvelope("expected a PK_MSG_PUBLISH request")
    extra = set(obj) - {"contract", "app", "topic", "message"}
    if extra:
        raise IncompleteEnvelope("unknown request fields", details={"fields": sorted(extra)})
    for f in ("app", "topic"):
        if not isinstance(obj.get(f), str) or not obj[f].strip() or len(obj[f]) > 512:
            raise IncompleteEnvelope(f"{f} is required", details={"field": f})
    validate_envelope(obj.get("message"))
    return obj


def check_against_schema(obj: Any, schema: Mapping[str, Any], path: str = "$") -> list[str]:
    """Minimal JSON-Schema subset checker (type/required/properties/enum/min/max,
    additionalProperties false, items) so the shipped schemas are executable in
    the stdlib-only test suite.  Not a general validator."""
    errs: list[str] = []
    types = schema.get("type")
    tmap = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool,
            "null": type(None)}
    if types:
        tl = types if isinstance(types, list) else [types]
        ok = any(isinstance(obj, tmap[t]) and not (t in ("integer", "number") and isinstance(obj, bool)) for t in tl)
        if not ok:
            return [f"{path}: expected {types}"]
    if "enum" in schema and obj not in schema["enum"]:
        errs.append(f"{path}: not in enum")
    if isinstance(obj, str):
        if len(obj) < schema.get("minLength", 0) or len(obj) > schema.get("maxLength", 1 << 62):
            errs.append(f"{path}: length out of range")
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if "minimum" in schema and obj < schema["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in schema and obj > schema["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(obj, dict):
        for r in schema.get("required", []):
            if r not in obj:
                errs.append(f"{path}: missing {r}")
        props = schema.get("properties", {})
        for k, v in obj.items():
            if k in props:
                errs.extend(check_against_schema(v, props[k], f"{path}.{k}"))
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected {k}")
    if isinstance(obj, list) and "items" in schema:
        for i, v in enumerate(obj):
            errs.extend(check_against_schema(v, schema["items"], f"{path}[{i}]"))
    return errs
