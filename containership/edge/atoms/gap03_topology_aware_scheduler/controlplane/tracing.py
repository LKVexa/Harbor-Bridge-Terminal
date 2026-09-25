"""MC-021 - Distributed tracing propagation (W3C Trace Context level 1).

Ingress: validate ``traceparent`` (strict format, non-zero ids, version 00)
and ``tracestate``/baggage bounds; invalid -> start a fresh trace (never
trust).  Spans carry low-cardinality attributes only.  Sampling keeps every
error, slow, stale-conflict and security span; normal spans are
probabilistically sampled.  Exporter failure degrades to local correlation
(ids still propagate) with a drop counter.
"""
from __future__ import annotations

import contextvars
import os
import random
import re
import time

TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
MAX_TRACESTATE = 512
MAX_BAGGAGE_ITEMS, MAX_BAGGAGE_BYTES = 16, 1024
ALLOWED_ATTRS = {"result", "code", "candidate_count", "topology_generation", "ledger_revision", "dependency", "retry_count",
                 "config_generation", "stage"}
SPAN_NAMES = ("admission", "snapshot", "filter", "locality_score", "fairness", "cache", "durable_claim", "downstream_commit",
              "release", "audit")
SLOW_MS = 50.0
_current = contextvars.ContextVar("gap03_span", default=None)


def parse_traceparent(value: str | None):
    if not value or len(value) != 55:
        return None
    m = TRACEPARENT_RE.match(value)
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
        return None
    return {"trace_id": m.group(1), "parent_id": m.group(2), "flags": m.group(3)}


def parse_baggage(value: str | None) -> dict:
    if not value:
        return {}
    if len(value.encode()) > MAX_BAGGAGE_BYTES:
        return {}
    items = [i for i in value.split(",") if "=" in i][:MAX_BAGGAGE_ITEMS]
    return {k.strip()[:64]: v.strip()[:128] for k, v in (i.split("=", 1) for i in items)}


class Tracer:
    def __init__(self, exporter=None, *, sample_rate: float = 0.05, seed=None):
        self.exporter, self.sample_rate = exporter, sample_rate
        self.rng = random.Random(seed)
        self.finished: list[dict] = []
        self.dropped = 0
        self.enabled = True

    def start(self, name: str, *, headers: dict | None = None, txn: str | None = None):
        if name not in SPAN_NAMES and not name.startswith("gap03."):
            raise ValueError(f"unregistered span {name}")
        parent = _current.get()
        ctx = None
        if parent is None and headers is not None:
            ctx = parse_traceparent(headers.get("traceparent"))
        trace_id = parent["trace_id"] if parent else (ctx["trace_id"] if ctx else os.urandom(16).hex())
        span = {"name": name, "trace_id": trace_id, "span_id": os.urandom(8).hex(),
                "parent_id": parent["span_id"] if parent else (ctx["parent_id"] if ctx else None),
                "start": time.perf_counter(), "attrs": {}, "status": "ok", "txn": txn or (parent or {}).get("txn"),
                "tracestate": (headers or {}).get("tracestate", "")[:MAX_TRACESTATE] if not parent else parent.get("tracestate", "")}
        span["_token"] = _current.set(span)
        return span

    def attr(self, span, key, value):
        if key not in ALLOWED_ATTRS:
            raise ValueError(f"attribute {key} not allowed (cardinality/privacy)")
        span["attrs"][key] = value if isinstance(value, (int, bool)) else str(value)[:64]

    def end(self, span, *, error_code: str | None = None, security: bool = False, stale: bool = False):
        span["duration_ms"] = (time.perf_counter() - span.pop("start")) * 1000
        if error_code:
            span["status"], span["attrs"]["code"] = "error", error_code
        _current.reset(span.pop("_token"))
        keep = error_code or security or stale or span["duration_ms"] >= SLOW_MS or self.rng.random() < self.sample_rate
        if keep and self.enabled:
            try:
                if self.exporter:
                    self.exporter(span)
                self.finished.append(span)
            except Exception:  # noqa: BLE001 - exporter outage: keep local ids, count drop
                self.dropped += 1
        return span

    def inject(self, span) -> dict:
        return {"traceparent": f"00-{span['trace_id']}-{span['span_id']}-01", "tracestate": span.get("tracestate", "")}

    def wrap(self, fn):
        """Propagate the current context into another thread/async task."""
        ctx = contextvars.copy_context()
        return lambda *a, **k: ctx.run(fn, *a, **k)
