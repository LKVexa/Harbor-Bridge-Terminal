"""INV-38-C074 — Trace-context propagation with baggage sanitization (model)."""
from __future__ import annotations
import re
from dataclasses import dataclass

_TRACEID = re.compile(r"^[0-9a-f]{32}$")
_SPANID = re.compile(r"^[0-9a-f]{16}$")
_PRIVILEGED = frozenset({"admin", "tenant_override", "capability"})

class TraceError(ValueError):
    code = "PK_BYPASS_TRACE_INVALID"

@dataclass(frozen=True)
class SpanContext:
    trace_id: str
    span_id: str
    sampled: bool = False

def parse_incoming(trace_id: str, span_id: str, baggage: dict) -> tuple[SpanContext, dict]:
    if not _TRACEID.match(trace_id or "") or not _SPANID.match(span_id or ""):
        raise TraceError("malformed trace/span id")
    # Untrusted callers may not set privileged baggage (C074-T05).
    safe = {k: v for k, v in baggage.items() if k not in _PRIVILEGED}
    return SpanContext(trace_id, span_id), safe

SPAN_NAMES = ("register", "post", "queue_wait", "provider_submit",
              "completion", "fallback", "retry", "config_txn")
