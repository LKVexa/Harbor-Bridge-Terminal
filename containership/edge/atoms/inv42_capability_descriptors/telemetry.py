"""MC-020..MC-024 - health, metrics, structured logging, tracing, operator explain.

All adapters consume the redacted ``PK_DESCRIPTOR_EVENT/1`` stream produced by
``DescriptorTable(observer=...)``; none of them can see bearer material.  Use
:func:`fanout` to attach several sinks to one table.
"""
from __future__ import annotations

import contextvars
import json
import logging
import re
import secrets
import threading
import time

try:
    from . import descriptors as _d
    from .outcomes import classify
except ImportError:  # flat import (tests/tools)
    import descriptors as _d  # type: ignore
    from outcomes import classify  # type: ignore

# ---------------------------------------------------------------- fan-out

def fanout(*sinks):
    def observer(event):
        for sink in sinks:
            try:
                sink(event)
            except Exception:  # noqa: BLE001
                pass
    return observer

# ---------------------------------------------------------------- tracing (MC-023)
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
_current = contextvars.ContextVar("inv42_trace", default=None)


def parse_traceparent(header: str | None):
    """Strict W3C traceparent parser; invalid input yields None (start new trace)."""
    if not isinstance(header, str) or len(header) != 55:
        return None
    m = _TRACEPARENT.fullmatch(header)
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
        return None
    return {"trace_id": m.group(1), "parent_id": m.group(2), "flags": m.group(3)}


class span:
    """Context manager attaching trace ids to every event emitted inside it."""

    def __init__(self, traceparent: str | None = None):
        parent = parse_traceparent(traceparent)
        self.trace_id = parent["trace_id"] if parent else secrets.token_hex(16)
        self.span_id = secrets.token_hex(8)
        self.flags = parent["flags"] if parent else "01"

    def __enter__(self):
        self._token = _current.set(self)
        return self

    def __exit__(self, *exc):
        _current.reset(self._token)
        return False

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"


def with_trace(sink):
    def observer(event):
        cur = _current.get()
        if cur is not None:
            event = {**event, "trace_id": cur.trace_id, "span_id": cur.span_id}
        sink(event)
    return observer

# ---------------------------------------------------------------- metrics (MC-021)
BUCKETS_NS = (1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000, 10_000_000)


class Metrics:
    """Thread-safe counters + latency histograms, exportable as Prometheus text."""

    def __init__(self):
        self._lock = threading.Lock()
        self.ops: dict[tuple[str, str], int] = {}
        self.hist: dict[str, list[int]] = {}
        self.sum_ns: dict[str, int] = {}
        self.last_event_ts = 0.0

    def __call__(self, event):
        op, outcome, dur = event["op"], event["outcome"], int(event.get("duration_ns") or 0)
        with self._lock:
            self.ops[(op, outcome)] = self.ops.get((op, outcome), 0) + 1
            h = self.hist.setdefault(op, [0] * (len(BUCKETS_NS) + 1))
            for i, b in enumerate(BUCKETS_NS):
                if dur <= b:
                    h[i] += 1
                    break
            else:
                h[-1] += 1
            self.sum_ns[op] = self.sum_ns.get(op, 0) + dur
            self.last_event_ts = event.get("ts", time.time())

    def prometheus(self, tables=()) -> str:
        out = ["# HELP inv42_operations_total Descriptor operations by outcome",
               "# TYPE inv42_operations_total counter"]
        with self._lock:
            for (op, oc), n in sorted(self.ops.items()):
                out.append(f'inv42_operations_total{{op="{op}",outcome="{oc}",class="{classify_code(oc)}"}} {n}')
            out += ["# HELP inv42_operation_duration_seconds Operation latency",
                    "# TYPE inv42_operation_duration_seconds histogram"]
            for op, h in sorted(self.hist.items()):
                cum = 0
                for b, n in zip(BUCKETS_NS, h):
                    cum += n
                    out.append(f'inv42_operation_duration_seconds_bucket{{op="{op}",le="{b/1e9:g}"}} {cum}')
                cum += h[-1]
                out.append(f'inv42_operation_duration_seconds_bucket{{op="{op}",le="+Inf"}} {cum}')
                out.append(f'inv42_operation_duration_seconds_sum{{op="{op}"}} {self.sum_ns[op]/1e9:.9f}')
                out.append(f'inv42_operation_duration_seconds_count{{op="{op}"}} {cum}')
        out += ["# TYPE inv42_table_live gauge", "# TYPE inv42_table_saturation_ratio gauge"]
        for t in tables:
            st = t.status()
            out.append(f'inv42_table_live{{table_fp="{t.fingerprint}"}} {st["live"]}')
            out.append(f'inv42_table_saturation_ratio{{table_fp="{t.fingerprint}"}} {st["live"]/st["table_limit"]:.6f}')
            out.append(f'inv42_session_saturation_ratio{{table_fp="{t.fingerprint}"}} '
                       f'{st["issued"]/st["session_allocation_limit"]:.6f}')
        out.append(f"inv42_emergency_disabled {int(_d.is_disabled())}")
        return "\n".join(out) + "\n"


def classify_code(code: str) -> str:
    return classify(type("E", (Exception,), {"code": code})() if code != "ok" else None).klass

# ---------------------------------------------------------------- health (MC-020)
SATURATION_DEGRADED = 0.90
STALL_SECONDS = 300.0


def health(tables, metrics: Metrics | None = None, *, now: float | None = None,
           expect_traffic: bool = False) -> dict:
    """Liveness/readiness verdict: ``ready`` | ``degraded`` | ``not_ready``."""
    now = time.time() if now is None else now
    reasons = []
    state = "ready"
    if _d.is_disabled():
        return {"status": "not_ready", "reasons": ["emergency_disabled"], "live": True}
    for t in tables:
        st = t.status()
        if st["destroyed"]:
            state, _ = "not_ready", reasons.append(f"{t.fingerprint}:destroyed")
            continue
        if st["live"] / st["table_limit"] >= SATURATION_DEGRADED:
            reasons.append(f"{t.fingerprint}:table_saturation")
        if st["issued"] / st["session_allocation_limit"] >= SATURATION_DEGRADED:
            reasons.append(f"{t.fingerprint}:session_saturation")
    if expect_traffic and metrics is not None and metrics.last_event_ts and now - metrics.last_event_ts > STALL_SECONDS:
        reasons.append("stalled")
    if state == "ready" and reasons:
        state = "degraded"
    return {"status": state, "reasons": reasons, "live": True}

# ---------------------------------------------------------------- logging (MC-022)
_HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
_HEX32 = re.compile(r"\b[0-9a-f]{32}\b")


def redact(text: str) -> str:
    """Scrub anything shaped like an auth tag or table id; neutralise control chars."""
    text = _HEX64.sub("[REDACTED-TAG]", text)
    text = _HEX32.sub("[REDACTED-ID]", text)
    return "".join(ch if ch >= " " and ch != "\x7f" else f"\\x{ord(ch):02x}" for ch in text)


class StructuredLogger:
    """Observer writing one JSON line per event to a stdlib logger (redacted)."""

    def __init__(self, logger: logging.Logger | None = None, *, sample_ok: float = 1.0):
        self.logger = logger or logging.getLogger("inv42")
        self.sample_ok = sample_ok

    def __call__(self, event):
        if event["outcome"] == "ok" and self.sample_ok < 1.0 and secrets.randbelow(10_000) >= self.sample_ok * 10_000:
            return
        oc = classify_code(event["outcome"])
        level = logging.INFO if oc == "success" else logging.WARNING
        self.logger.log(level, redact(json.dumps({**event, "class": oc}, sort_keys=True)))

# ---------------------------------------------------------------- explain (MC-024)

def explain(error: BaseException | None, *, table=None, release: dict | None = None) -> dict:
    """Operator decision view for one outcome, correlated with release lineage."""
    o = classify(error)
    view = {"code": o.code, "class": o.klass, "operator_action": o.action,
            "message": redact(str(error)) if error else "ok", "emergency_disabled": _d.is_disabled()}
    if table is not None:
        st = table.status()
        view["table"] = {"fp": table.fingerprint, "live": st["live"], "issued": st["issued"],
                         "destroyed": st["destroyed"]}
    if release:
        view["release"] = {k: release.get(k) for k in ("version", "protocol", "manifest_sha256", "commit")}
    return view
