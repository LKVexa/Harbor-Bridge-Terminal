# INV-17 Trace Propagation

**Controls:** C074
**Owner:** UNASSIGNED — owner to fill

## Implemented

`observability::TraceContext` (W3C Trace Context `traceparent`, version `00` only):
- `TraceContext.parse(header)` — lower-cases/strips, matches `00-<32 hex>-<16 hex>-<2 hex>`; returns `None` for missing, malformed, or all-zero trace/span ids (never raises).
- `sampled` = flags bit 0.
- `TraceContext.new(sampled=True)` — random 128-bit trace id and 64-bit span id (`secrets`).
- `child()` — same trace id and sampled flag, new span id.
- `header()` — renders `00-<trace>-<span>-01|00`.
- `StructuredLogger.log(..., trace=ctx)` writes `trace_id`/`span_id` fields.

## Not implemented

- `tracestate` is ignored.
- `Stream` and `StreamRegistry` do not accept or store trace context; elements carry no trace
  metadata. Propagation across a stream is the caller's responsibility (e.g. carry the
  `traceparent` inside the element or alongside it in INV-20 HTTP headers).
- No span export (no OpenTelemetry dependency). Spans exist only as log correlation ids.
- Future `traceparent` versions (> `00`) are rejected rather than parsed forward-compatibly.

## Recommended usage

Parse on ingress (`parse`), create `child()` per registry operation, log with `trace=`; on
malformed input start a new trace with `TraceContext.new()`.

Tests (planned): `tests/test_observability.py`, `tests/test_property.py` (parser fuzzing).
