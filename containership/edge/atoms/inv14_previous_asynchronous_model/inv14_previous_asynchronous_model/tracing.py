"""W3C trace-context propagation across the poll boundary (component P1-11; C074).

A poll may carry a ``traceparent``.  The service validates it (W3C Trace Context
level 1, version 00), creates a child span id for the poll, and returns the child
``traceparent`` in the result.  Invalid inbound context is dropped and a fresh root
is started (never an error -- tracing must not change poll semantics), and the
drop is counted.  ``tracestate`` is carried opaque but bounded to 512 chars / 32
members per the spec.
"""
from __future__ import annotations

import re
import secrets

_TP = re.compile(r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
MAX_TRACESTATE = 512


class TraceContext:
    __slots__ = ("trace_id", "span_id", "parent_span_id", "flags", "tracestate", "inbound_valid")

    def __init__(self, trace_id, span_id, parent_span_id, flags, tracestate, inbound_valid):
        self.trace_id, self.span_id, self.parent_span_id = trace_id, span_id, parent_span_id
        self.flags, self.tracestate, self.inbound_valid = flags, tracestate, inbound_valid

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"

    def as_dict(self) -> dict:
        return {"traceparent": self.traceparent, "parent_span_id": self.parent_span_id,
                "tracestate": self.tracestate, "inbound_valid": self.inbound_valid}


def parse_traceparent(value: object):
    if not isinstance(value, str):
        return None
    m = _TP.match(value.strip())
    if not m:
        return None
    ver, tid, sid, flags = m.groups()
    if ver == "ff" or tid == "0" * 32 or sid == "0" * 16:
        return None
    return tid, sid, flags


def _bounded_tracestate(ts: object) -> str:
    if not isinstance(ts, str):
        return ""
    members = [m.strip() for m in ts.split(",") if m.strip()][:32]
    out = ",".join(members)
    return out if len(out) <= MAX_TRACESTATE else ""


def child_context(traceparent: object = None, tracestate: object = None) -> TraceContext:
    parsed = parse_traceparent(traceparent)
    span = secrets.token_hex(8)
    if parsed:
        tid, parent, flags = parsed
        return TraceContext(tid, span, parent, flags, _bounded_tracestate(tracestate), True)
    return TraceContext(secrets.token_hex(16), span, None, "01", "", traceparent is None)
