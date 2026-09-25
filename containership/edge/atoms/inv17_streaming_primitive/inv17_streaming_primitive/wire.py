"""Schema-validated wire messages for INV-17's public interfaces (C021-C022, C082).

``describe`` renders PK_STREAM/1; ``apply_credit`` and ``apply_close`` accept
PK_STREAM_CREDIT/1 and PK_STREAM_CLOSE/1 documents, validate them against the shipped
JSON Schemas, negotiate the version, and apply them to a ``Stream``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .configuration import validate
from .control import negotiate
from .stream import Stream, StreamError

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
SCHEMAS = {"PK_STREAM": "pk_stream.v1.schema.json", "PK_STREAM_CREDIT": "pk_stream_credit.v1.schema.json",
           "PK_STREAM_CLOSE": "pk_stream_close.v1.schema.json", "PK_STREAM_ERROR": "pk_stream_error.v1.schema.json"}


class WireInvalid(StreamError, ValueError):
    code = "PK_STREAM_WIRE_INVALID"


def schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / SCHEMAS[name]).read_text(encoding="utf-8"))


def check(name: str, doc: Any) -> None:
    errors = validate(doc, schema(name))
    if errors:
        raise WireInvalid(f"{name} document invalid", errors=errors[:10])


def describe(s: Stream) -> dict[str, Any]:
    doc = {"interface": "PK_STREAM", "version": 1, "stream_id": s.stream_id, "element_type": s.element_type.__name__,
           "tenant": s.tenant, "workload": s.workload,
           "limits": {"max_credit": s.config.max_credit, "max_buffer": s.config.max_buffer,
                      "idempotency_window": s.config.idempotency_window}, "state": s.state}
    check("PK_STREAM", doc)
    return doc


def _preflight(name: str, s: Stream, doc: Mapping[str, Any]) -> None:
    if not isinstance(doc, Mapping):
        raise WireInvalid("message must be an object")
    if isinstance(doc.get("version"), int):
        negotiate(name, [doc["version"]])
    check(name, dict(doc))
    if doc["stream_id"] != s.stream_id:
        raise WireInvalid("message addressed to a different stream", stream_id=doc["stream_id"])


def apply_credit(s: Stream, doc: Mapping[str, Any]) -> None:
    _preflight("PK_STREAM_CREDIT", s, doc)
    s.grant(doc["credit"])


def apply_close(s: Stream, doc: Mapping[str, Any]) -> None:
    _preflight("PK_STREAM_CLOSE", s, doc)
    {"end": s.end, "drop_reader": s.drop_reader, "drop_writer": s.drop_writer}[doc["kind"]]()


def error_envelope(exc: StreamError) -> dict[str, Any]:
    doc = exc.as_dict()
    doc["details"] = json.loads(json.dumps(doc["details"], default=str))
    check("PK_STREAM_ERROR", doc)
    return doc
