"""Metrics, structured logs and trace-context propagation (INV-68 MC-26; C072-C076).

* :class:`Metrics` -- in-process counters, gauges and fixed-bucket histograms
  with a **cardinality ceiling** per metric (label sets beyond the ceiling are
  folded into ``{"overflow": "true"}`` and counted), exported as a JSON
  snapshot or Prometheus text exposition.  Label values are redacted and
  length-capped; tenant is the only high-cardinality label admitted and only on
  allow-listed metrics.
* :class:`StructuredLogger` -- one JSON object per line, fixed field set
  (``ts, level, event, correlation_id, trace_id, span_id, tenant, fields``),
  every value passed through :func:`redaction.redact`.  JSON encoding
  neutralises log injection (newlines/control characters are escaped).
* :func:`parse_traceparent` / :func:`child_traceparent` implement W3C Trace
  Context ``traceparent`` so a caller's trace continues through the packer.

Signals declared by the 4.2.0 contract (``hosts_used``, ``unplaced``,
``stranded_cpu``, ``stranded_mem``) are emitted as
``inv68_hosts_used``, ``inv68_unplaced_total``, ``inv68_stranded_cpu`` and
``inv68_stranded_mem`` alongside RED/USE metrics.  Names, types, units and
labels are catalogued in ``TELEMETRY_POLICY.md`` and ``ops/metrics.json``.
"""
from __future__ import annotations

import bisect
import json
import re
import secrets
import sys
import threading
import time
from typing import Any, Callable, Mapping, TextIO

from .redaction import redact, redact_text

LATENCY_BUCKETS_MS = (1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500)
MAX_SERIES_PER_METRIC = 200
MAX_LABEL_VALUE = 64
TENANT_LABELLED = frozenset({"inv68_requests_total", "inv68_request_latency_ms", "inv68_unplaced_total"})

_TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_traceparent(value: str | None) -> tuple[str, str] | None:
    if not isinstance(value, str):
        return None
    m = _TRACEPARENT_RE.fullmatch(value.strip())
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
        return None
    return m.group(1), m.group(2)


def child_traceparent(parent: str | None) -> tuple[str, str, str]:
    """Return ``(trace_id, span_id, traceparent)`` continuing *parent* when valid."""
    parsed = parse_traceparent(parent)
    trace_id = parsed[0] if parsed else secrets.token_hex(16)
    span_id = secrets.token_hex(8)
    return trace_id, span_id, f"00-{trace_id}-{span_id}-01"


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple], float] = {}
        self._gauges: dict[tuple[str, tuple], float] = {}
        self._hist: dict[tuple[str, tuple], list] = {}
        self._series: dict[str, set] = {}
        self.overflowed: dict[str, int] = {}

    def _labels(self, name: str, labels: Mapping[str, Any] | None) -> tuple:
        if not labels:
            return ()
        clean = []
        for k, v in sorted(labels.items()):
            if k == "tenant" and name not in TENANT_LABELLED:
                continue
            clean.append((str(k)[:32], redact_text(str(v))[:MAX_LABEL_VALUE]))
        key = tuple(clean)
        seen = self._series.setdefault(name, set())
        if key not in seen:
            if len(seen) >= MAX_SERIES_PER_METRIC:
                self.overflowed[name] = self.overflowed.get(name, 0) + 1
                return (("overflow", "true"),)
            seen.add(key)
        return key

    def inc(self, name: str, value: float = 1.0, labels: Mapping[str, Any] | None = None) -> None:
        with self._lock:
            key = (name, self._labels(name, labels))
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set(self, name: str, value: float, labels: Mapping[str, Any] | None = None) -> None:
        with self._lock:
            self._gauges[(name, self._labels(name, labels))] = float(value)

    def observe(self, name: str, value_ms: float, labels: Mapping[str, Any] | None = None) -> None:
        with self._lock:
            key = (name, self._labels(name, labels))
            h = self._hist.setdefault(key, [[0] * (len(LATENCY_BUCKETS_MS) + 1), 0.0, 0])
            h[0][bisect.bisect_left(LATENCY_BUCKETS_MS, value_ms)] += 1
            h[1] += value_ms
            h[2] += 1

    def value(self, name: str, labels: Mapping[str, Any] | None = None) -> float:
        key = (name, tuple(sorted((str(k), str(v)) for k, v in (labels or {}).items())))
        with self._lock:
            if key in self._counters:
                return self._counters[key]
            return self._gauges.get(key, 0.0)

    def total(self, name: str) -> float:
        with self._lock:
            return sum(v for (n, _), v in self._counters.items() if n == name)

    def snapshot(self) -> dict:
        with self._lock:
            def rows(d):
                return [{"name": n, "labels": dict(l), "value": v} for (n, l), v in sorted(d.items())]
            return {
                "schema": "PK_PACK_METRICS/1",
                "counters": rows(self._counters),
                "gauges": rows(self._gauges),
                "histograms": [{"name": n, "labels": dict(l), "buckets_ms": list(LATENCY_BUCKETS_MS),
                                "counts": list(h[0]), "sum": h[1], "count": h[2]}
                               for (n, l), h in sorted(self._hist.items())],
                "overflowed_series": dict(self.overflowed),
            }

    def prometheus(self) -> str:
        snap = self.snapshot()
        out: list[str] = []

        def fmt(labels):
            if not labels:
                return ""
            return "{" + ",".join(f'{k}="{json.dumps(v)[1:-1]}"' for k, v in labels.items()) + "}"
        for row in snap["counters"]:
            out.append(f"{row['name']}{fmt(row['labels'])} {row['value']:g}")
        for row in snap["gauges"]:
            out.append(f"{row['name']}{fmt(row['labels'])} {row['value']:g}")
        for h in snap["histograms"]:
            acc = 0
            for le, c in zip(list(h["buckets_ms"]) + ["+Inf"], h["counts"]):
                acc += c
                out.append(f"{h['name']}_bucket{fmt(dict(h['labels'], le=str(le)))} {acc}")
            out.append(f"{h['name']}_sum{fmt(h['labels'])} {h['sum']:g}")
            out.append(f"{h['name']}_count{fmt(h['labels'])} {h['count']}")
        return "\n".join(out) + "\n"


class StructuredLogger:
    LEVELS = ("debug", "info", "warning", "error", "critical")

    def __init__(self, stream: TextIO | None = None, *, component: str = "INV-68",
                 clock: Callable[[], float] = time.time, level: str = "info"):
        self.stream = stream if stream is not None else sys.stderr
        self.component = component
        self.clock = clock
        self.min_level = self.LEVELS.index(level)
        self._lock = threading.Lock()
        self.records: list[dict] = []  # bounded in-memory tail for support bundles
        self._tail = 500

    def log(self, level: str, event: str, *, correlation_id: str | None = None, trace_id: str | None = None,
            span_id: str | None = None, tenant: str | None = None, **fields: Any) -> dict:
        rec = {
            "ts": round(float(self.clock()), 6),
            "level": level,
            "component": self.component,
            "event": str(event)[:64],
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "tenant": tenant,
            "fields": redact(fields),
        }
        if self.LEVELS.index(level) >= self.min_level:
            with self._lock:
                self.stream.write(json.dumps(rec, sort_keys=True, ensure_ascii=True) + "\n")
                self.records.append(rec)
                if len(self.records) > self._tail:
                    del self.records[: len(self.records) - self._tail]
        return rec
