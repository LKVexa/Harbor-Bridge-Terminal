"""M58-M63 - metrics, structured logs, trace context, status, decision records.

- Metrics: counters/gauges/histograms with a fixed label allow-list and a hard
  series cap per metric (cardinality guard); identities never become labels.
- Logs: JSON lines, redacted, bounded, with trace/span ids and config digest.
- Trace context: W3C ``traceparent`` parse/emit and child-span propagation.
- Diagnostics: high-cardinality detail is queryable only through an authorized,
  paginated, bounded interface (never through metric labels).
- Decision records: why a placement/failover/refusal happened, with rule ids.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import deque

from .errors import redact, redact_detail

ALLOWED_LABELS = {"host", "outcome", "code", "operation", "tenant_class", "region", "state"}
MAX_SERIES_PER_METRIC = 64
BUCKETS = (0.0005, 0.001, 0.002, 0.003, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict = {}
        self.gauges: dict = {}
        self.hists: dict = {}
        self.dropped_series = 0

    def _key(self, store, name, labels):
        bad = set(labels) - ALLOWED_LABELS
        if bad:
            raise ValueError(f"label(s) {sorted(bad)} not allowed on metrics (cardinality policy)")
        key = (name, tuple(sorted(labels.items())))
        if key not in store and sum(1 for k in store if k[0] == name) >= MAX_SERIES_PER_METRIC:
            self.dropped_series += 1
            return (name, (("overflow", "true"),))
        return key

    def inc(self, name, n=1, **labels):
        with self._lock:
            k = self._key(self.counters, name, labels)
            self.counters[k] = self.counters.get(k, 0) + n

    def set(self, name, value, **labels):
        with self._lock:
            self.gauges[self._key(self.gauges, name, labels)] = value

    def observe(self, name, value, **labels):
        with self._lock:
            k = self._key(self.hists, name, labels)
            h = self.hists.setdefault(k, {"count": 0, "sum": 0.0, "buckets": [0] * (len(BUCKETS) + 1)})
            h["count"] += 1
            h["sum"] += value
            for i, b in enumerate(BUCKETS):
                if value <= b:
                    h["buckets"][i] += 1
                    break
            else:
                h["buckets"][-1] += 1

    def exposition(self) -> str:
        """Prometheus text format."""
        def lab(t):
            return "{" + ",".join(f'{k}="{v}"' for k, v in t) + "}" if t else ""
        out = []
        with self._lock:
            for (n, t), v in sorted(self.counters.items()):
                out.append(f"inv60_{n}_total{lab(t)} {v}")
            for (n, t), v in sorted(self.gauges.items()):
                out.append(f"inv60_{n}{lab(t)} {v}")
            for (n, t), h in sorted(self.hists.items()):
                acc = 0
                for b, c in zip(list(BUCKETS) + ["+Inf"], h["buckets"]):
                    acc += c
                    lt = tuple(list(t) + [("le", str(b))])
                    out.append(f"inv60_{n}_bucket{lab(lt)} {acc}")
                out.append(f"inv60_{n}_count{lab(t)} {h['count']}")
                out.append(f"inv60_{n}_sum{lab(t)} {round(h['sum'], 6)}")
        return "\n".join(out) + "\n"


_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


class TraceContext:
    def __init__(self, trace_id: str | None = None, span_id: str | None = None, sampled: bool = True,
                 parent: str | None = None):
        self.trace_id = trace_id or os.urandom(16).hex()
        self.span_id = span_id or os.urandom(8).hex()
        self.sampled = sampled
        self.parent = parent

    @classmethod
    def parse(cls, header: str | None) -> "TraceContext":
        m = _TP.match(header or "")
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return cls()  # invalid/absent -> new root (never trust malformed input)
        return cls(m.group(1), os.urandom(8).hex(), bool(int(m.group(3), 16) & 1), parent=m.group(2))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, os.urandom(8).hex(), self.sampled, parent=self.span_id)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


class Logger:
    MAX_LINE = 2048

    def __init__(self, sink=None, *, component="inv60", config_digest: str | None = None, max_buffer=10_000):
        self.sink = sink
        self.buffer: deque = deque(maxlen=max_buffer)
        self.component, self.config_digest = component, config_digest

    def log(self, level: str, event: str, *, trace: TraceContext | None = None, security: bool = False, **fields):
        rec = {"ts": round(time.time(), 6), "level": level, "event": event, "component": self.component,
               "security": security, "config_digest": self.config_digest,
               "trace_id": trace.trace_id if trace else None, "span_id": trace.span_id if trace else None,
               "fields": redact_detail(fields)}
        line = json.dumps(rec, sort_keys=True)
        if len(line) > self.MAX_LINE:
            rec["fields"] = {"_truncated": True}
            line = json.dumps(rec, sort_keys=True)
        self.buffer.append(rec)
        if self.sink:
            self.sink.write(line + "\n")
        return rec


class DecisionLog:
    def __init__(self, max_records=10_000):
        self.records: deque = deque(maxlen=max_records)

    def record(self, kind: str, subject: str, outcome: str, reasons: list, *, rules=(), trace=None, extra=None):
        rec = {"kind": kind, "subject": subject, "outcome": outcome, "reasons": [redact(str(r)) for r in reasons][:32],
               "rules": list(rules), "trace_id": trace.trace_id if trace else None, "at": round(time.time(), 6),
               "extra": redact_detail(extra or {})}
        self.records.append(rec)
        return rec

    def query(self, *, kind=None, subject=None, limit=50, offset=0) -> list:
        limit = max(1, min(limit, 200))
        rows = [r for r in self.records if (kind is None or r["kind"] == kind) and (subject is None or r["subject"] == subject)]
        return rows[offset:offset + limit]


TELEMETRY_POLICY = {
    "version": "inv60-telemetry/1.0.0",
    "metrics": {"retention_days": 30, "labels_allowed": sorted(ALLOWED_LABELS), "max_series_per_metric": MAX_SERIES_PER_METRIC},
    "logs": {"retention_days": 30, "security_logs_retention_days": 365, "redaction": "errors.redact/redact_detail",
             "max_line_bytes": Logger.MAX_LINE},
    "traces": {"default_sample_ratio": 0.1, "always_sample": ["errors", "security_denials"], "retention_days": 7},
    "privacy": "no tenant payloads, secrets, tokens or full identities in telemetry; identities appear only as key fingerprints",
    "export": "OTLP/Prometheus pull; export endpoint configured per site overlay (telemetry.export_endpoint)",
}
