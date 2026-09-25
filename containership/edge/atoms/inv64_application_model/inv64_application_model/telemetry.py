"""Metrics, structured logs and W3C trace context (MC-24; C072-C075).

* :class:`Metrics` — counters, gauges and fixed-bucket histograms. Each metric
  has a hard series ceiling; label sets beyond it collapse into one
  ``overflow="true"`` series and bump ``inv64_telemetry_label_overflow_total``,
  so a hostile identifier can never grow memory without bound. Tenant or
  workload IDs are *not* metric labels (see METRICS catalog); they go to logs.
* :class:`StructuredLog` — JSON records with a fixed schema (``LOG_FIELDS``),
  every value passed through :func:`redaction.redact`, held in a bounded ring
  with a dropped-record counter, optionally mirrored to a sink callable whose
  failures are counted rather than raised.
* :func:`parse_traceparent` / :func:`child_traceparent` — W3C Trace Context
  level 1; malformed inbound headers start a new trace instead of propagating junk.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import deque
from typing import Callable, Mapping

from .redaction import redact

TELEMETRY_CONTRACT = "PK_APP_TELEMETRY/1"
MAX_SERIES_PER_METRIC = 200
LATENCY_BUCKETS_MS = (0.25, 0.5, 1, 2, 5, 10, 25, 50, 100, 250, 1000, float("inf"))

# name -> (type, unit, allowed label keys, SLO linkage)
METRICS: dict[str, tuple[str, str, tuple[str, ...], str]] = {
    "inv64_requests_total": ("counter", "1", ("operation", "outcome"), "availability"),
    "inv64_rejections_total": ("counter", "1", ("operation", "code"), "fail-at-submit"),
    "inv64_latency_ms": ("histogram", "ms", ("operation",), "validation p99 < 5ms"),
    "inv64_inflight": ("gauge", "1", (), "saturation"),
    "inv64_admission_rejected_total": ("counter", "1", ("reason",), "saturation"),
    "inv64_retries_total": ("counter", "1", ("operation",), "dependency health"),
    "inv64_retry_budget_exhausted_total": ("counter", "1", (), "dependency health"),
    "inv64_timeouts_total": ("counter", "1", ("operation",), "latency"),
    "inv64_cancellations_total": ("counter", "1", ("operation",), "latency"),
    "inv64_authn_total": ("counter", "1", ("outcome",), "security"),
    "inv64_authz_decisions_total": ("counter", "1", ("decision",), "security"),
    "inv64_dependency_failures_total": ("counter", "1", ("dependency",), "dependency health"),
    "inv64_audit_dropped_total": ("counter", "1", (), "audit integrity (critical)"),
    "inv64_audit_buffered": ("gauge", "1", (), "audit integrity"),
    "inv64_crypto_failures_total": ("counter", "1", ("kind",), "security"),
    "inv64_activation_total": ("counter", "1", ("result",), "change safety"),
    "inv64_rollback_total": ("counter", "1", ("trigger",), "change safety"),
    "inv64_bytes_decoded_total": ("counter", "By", ("operation",), "efficiency"),
    "inv64_log_dropped_total": ("counter", "1", (), "telemetry self-health"),
    "inv64_telemetry_sink_errors_total": ("counter", "1", ("sink",), "telemetry self-health"),
    "inv64_telemetry_label_overflow_total": ("counter", "1", ("metric",), "telemetry self-health"),
}

LOG_FIELDS = ("ts", "severity", "node", "tenant", "workload", "component", "operation", "trace_id",
              "span_id", "correlation_id", "outcome", "code", "duration_ms", "detail")
SEVERITIES = ("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL")


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._series: dict[str, dict[tuple, float | list]] = {}

    def _key(self, name: str, labels: Mapping[str, str]) -> tuple:
        spec = METRICS.get(name)
        if spec is None:
            raise KeyError(f"metric {name!r} not in catalog (telemetry contract change requires review)")
        allowed = spec[2]
        extra = set(labels) - set(allowed)
        if extra:
            raise KeyError(f"labels {sorted(extra)} not allowed on {name}")
        key = tuple((k, str(labels.get(k, ""))[:64]) for k in allowed)
        series = self._series.setdefault(name, {})
        if key not in series and len(series) >= MAX_SERIES_PER_METRIC:
            if name != "inv64_telemetry_label_overflow_total":
                o = self._series.setdefault("inv64_telemetry_label_overflow_total", {})
                ok = (("metric", name),)
                o[ok] = o.get(ok, 0) + 1
            return (("overflow", "true"),)
        return key

    def inc(self, name: str, value: float = 1, **labels) -> None:
        with self._lock:
            k = self._key(name, labels)
            s = self._series[name]
            s[k] = s.get(k, 0) + value

    def set(self, name: str, value: float, **labels) -> None:
        with self._lock:
            k = self._key(name, labels)
            self._series[name][k] = value

    def observe(self, name: str, value: float, **labels) -> None:
        with self._lock:
            k = self._key(name, labels)
            s = self._series[name]
            h = s.get(k)
            if h is None:
                h = s[k] = [0] * len(LATENCY_BUCKETS_MS) + [0.0, 0]
            for i, b in enumerate(LATENCY_BUCKETS_MS):
                if value <= b:
                    h[i] += 1
            h[-2] += value
            h[-1] += 1

    def get(self, name: str, **labels) -> float:
        with self._lock:
            spec = METRICS[name]
            key = tuple((k, str(labels.get(k, ""))[:64]) for k in spec[2])
            v = self._series.get(name, {}).get(key, 0)
            return v[-1] if isinstance(v, list) else v

    def snapshot(self) -> dict:
        with self._lock:
            return {n: {json.dumps(dict(k), sort_keys=True): (list(v) if isinstance(v, list) else v)
                        for k, v in s.items()} for n, s in self._series.items()}

    def exposition(self) -> str:
        """Prometheus text format."""
        out = []
        with self._lock:
            for name in sorted(self._series):
                typ, unit, _, _ = METRICS[name]
                out.append(f"# TYPE {name} {typ}")
                for key, v in sorted(self._series[name].items()):
                    lab = ",".join(f'{k}="{val}"' for k, val in key)
                    if isinstance(v, list):
                        for i, b in enumerate(LATENCY_BUCKETS_MS):
                            le = "+Inf" if b == float("inf") else repr(b)
                            sep = "," if lab else ""
                            out.append(f'{name}_bucket{{{lab}{sep}le="{le}"}} {v[i]}')
                        out.append(f"{name}_sum{{{lab}}} {v[-2]}")
                        out.append(f"{name}_count{{{lab}}} {v[-1]}")
                    else:
                        out.append(f"{name}{{{lab}}} {v}")
        return "\n".join(out) + "\n"


class StructuredLog:
    def __init__(self, *, capacity: int = 10_000, node: str = "local", sink: Callable[[str], None] | None = None,
                 metrics: Metrics | None = None, clock=time.time):
        self._ring: deque[dict] = deque(maxlen=capacity)
        self._node = node
        self._sink = sink
        self._metrics = metrics
        self._clock = clock
        self._lock = threading.Lock()
        self.dropped = 0

    def emit(self, severity: str, operation: str, *, outcome: str, code: str | None = None, **fields) -> dict:
        if severity not in SEVERITIES:
            severity = "INFO"
        rec = {k: None for k in LOG_FIELDS}
        rec.update({"ts": round(self._clock(), 6), "severity": severity, "node": self._node,
                    "component": "INV-64", "operation": operation, "outcome": outcome, "code": code})
        detail = {}
        for k, v in fields.items():
            if k in rec and k not in ("ts", "severity", "node", "component"):
                rec[k] = v
            else:
                detail[k] = v
        rec["detail"] = detail or None
        rec = redact(rec)
        with self._lock:
            if len(self._ring) == self._ring.maxlen:
                self.dropped += 1
                if self._metrics:
                    self._metrics.inc("inv64_log_dropped_total")
            self._ring.append(rec)
        if self._sink is not None:
            try:
                self._sink(json.dumps(rec, sort_keys=True))
            except Exception:  # telemetry must never take the request path down
                if self._metrics:
                    self._metrics.inc("inv64_telemetry_sink_errors_total", sink="log")
        return rec

    def records(self, *, tenant: str | None = None) -> list[dict]:
        """Records visible to a viewer scoped to ``tenant`` (None = platform operator)."""
        with self._lock:
            return [r for r in self._ring if tenant is None or r.get("tenant") == tenant]


_TP_RE = re.compile(r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def new_trace_id() -> str:
    return os.urandom(16).hex()


def new_span_id() -> str:
    return os.urandom(8).hex()


def parse_traceparent(header: str | None) -> tuple[str, str, str] | None:
    """Return ``(trace_id, parent_span_id, flags)`` or None if absent/invalid."""
    if not header or not isinstance(header, str):
        return None
    m = _TP_RE.fullmatch(header.strip().lower())
    if not m or m.group(1) == "ff" or set(m.group(2)) == {"0"} or set(m.group(3)) == {"0"}:
        return None
    return m.group(2), m.group(3), m.group(4)


def child_traceparent(inbound: str | None) -> tuple[str, str, str]:
    """Return ``(traceparent_to_send, trace_id, span_id)`` continuing or starting a trace."""
    parsed = parse_traceparent(inbound)
    trace_id = parsed[0] if parsed else new_trace_id()
    flags = parsed[2] if parsed else "01"
    span = new_span_id()
    return f"00-{trace_id}-{span}-{flags}", trace_id, span
