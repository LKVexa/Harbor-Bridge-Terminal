"""Wire decoding for the bulk-data submit interface (INV-35-C022, C029, C082).

Decoding is schema-checked first, then converted into the ``io_model`` ring
view.  Duplicate slot indices are refused (a hostile encoder could otherwise
shadow one descriptor with another).  Schema-level refusals surface as
INV35-E100/E101/E106 so callers still see only stable codes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..io_model import Descriptor
from .errors import Inv35Error
from .schema_check import SchemaError, validate

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "submit" / "descriptor_chain.request.schema.json"
_SCHEMA: dict[str, Any] | None = None


def request_schema() -> dict[str, Any]:
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _SCHEMA


def decode_submit(doc: object) -> dict[str, Any]:
    try:
        validate(doc, request_schema())
    except SchemaError as exc:
        text = str(exc)
        code = "INV35-E101" if ("head" in text or "index" in text) else "INV35-E106" if "descriptors[" in text else "INV35-E100"
        raise Inv35Error(code, f"schema: {text}") from exc
    ring: dict[int, Descriptor] = {}
    for d in doc["descriptors"]:
        if d["index"] in ring:
            raise Inv35Error("INV35-E101", f"duplicate slot {d['index']}")
        ring[d["index"]] = Descriptor(d["index"], d["address"], d["length"], d.get("next_index"))
    return {"queue": doc["queue"], "tenant": doc["tenant"], "head": doc["head"], "chain": ring,
            "idempotency_key": doc.get("idempotency_key"), "traceparent": doc.get("traceparent")}
