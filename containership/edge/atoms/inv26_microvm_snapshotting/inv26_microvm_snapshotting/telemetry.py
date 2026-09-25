"""Metrics, structured logs, trace context, and health/readiness (INV-26 C071-C075, X012).

Carried from the owner's INV-68 v4.3.0 ``telemetry.py`` (Metrics with a
per-metric cardinality ceiling and redacted, length-capped labels;
StructuredLogger with a fixed field set; W3C ``traceparent``), renamed for
INV-26. Added here: :class:`Health` (liveness, readiness, version, config
revision, dependency status, active capability set) and the bounded,
non-blocking exporter contract (the logger writes to a bounded in-memory tail
and a stream; a failing stream is counted, never raised into a restore).

Metric catalog: ``ops/metrics.json`` (names, types, units, labels) —
checked against :data:`METRICS` by ``tools/rtm.py``.
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
TENANT_LABELLED = frozenset({"inv26_requests_total", "inv26_snapshots_captured_total", "inv26_refusals_total"})

METRICS = {
    "inv26_requests_total": ("counter", "1", ["op", "outcome", "code", "tenant"]),
    "inv26_request_latency_ms": ("histogram", "ms", ["op"]),
    "inv26_restore_ms": ("histogram", "ms", ["adapter"]),
    "inv26_capture_ms": ("histogram", "ms", ["adapter"]),
    "inv26_snapshots_captured_total": ("counter", "1", ["tenant", "fingerprint"]),
    "inv26_refusals_total": ("counter", "1", ["code", "tenant"]),
    "inv26_cross_tenant_refusals_total": ("counter", "1", []),
    "inv26_model_mismatches_total": ("counter", "1", []),
    "inv26_reseeds_total": ("counter", "1", []),
    "inv26_inflight": ("gauge", "1", []),
    "inv26_queue_depth": ("gauge", "1", []),
    "inv26_admission_rejected_total": ("counter", "1", ["reason"]),
    "inv26_retries_total": ("counter", "1", ["dependency"]),
    "inv26_breaker_state": ("gauge", "1", ["dependency"]),
    "inv26_dependency_up": ("gauge", "1", ["dependency"]),
    "inv26_stalled_operations": ("gauge", "1", []),
    "inv26_audit_dropped_total": ("counter", "1", []),
    "inv26_audit_buffered": ("gauge", "1", []),
    "inv26_log_export_failures_total": ("counter", "1", []),
    "inv26_stored_bytes": ("gauge", "bytes", []),
}

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
                "schema": "PK_SNAPSHOT_METRICS/1",
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

    def __init__(self, stream: TextIO | None = None, *, component: str = "INV-26",
                 clock: Callable[[], float] = time.time, level: str = "info"):
        self.stream = stream if stream is not None else sys.stderr
        self.component = component
        self.clock = clock
        self.min_level = self.LEVELS.index(level)
        self._lock = threading.Lock()
        self.records: list[dict] = []  # bounded in-memory tail for support bundles
        self.export_failures = 0
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
                try:
                    self.stream.write(json.dumps(rec, sort_keys=True, ensure_ascii=True) + "\n")
                except (OSError, ValueError):
                    self.export_failures += 1  # a blocked/broken collector never fails the operation
                self.records.append(rec)
                if len(self.records) > self._tail:
                    del self.records[: len(self.records) - self._tail]
        return rec


class Health:
    """Liveness/readiness document (PK_SNAPSHOT_HEALTH/1) for C071."""

    def __init__(self, *, version: str, profile: str, probes: Mapping[str, Callable[[], bool]],
                 critical: frozenset[str]):
        self.version, self.profile, self.probes, self.critical = version, profile, dict(probes), critical

    def document(self, *, config_revision: int | None, config_digest: str | None, capabilities: list[str],
                 disabled: bool, stalled: int = 0) -> dict:
        deps = {}
        for name, probe in sorted(self.probes.items()):
            try:
                deps[name] = "up" if probe() else "down"
            except Exception:  # a probe that raises is a down dependency, never a crash
                deps[name] = "down"
        critical_down = sorted(n for n in self.critical if deps.get(n) != "up")
        ready = not disabled and not critical_down and config_revision is not None
        degraded = sorted(n for n, v in deps.items() if v != "up" and n not in self.critical)
        return {
            "schema": "PK_SNAPSHOT_HEALTH/1",
            "live": True,
            "ready": ready,
            "status": "disabled" if disabled else ("not_ready" if not ready else ("degraded" if degraded else "ok")),
            "not_ready_reasons": (["emergency_disable"] if disabled else []) + [f"dependency_down:{n}" for n in critical_down]
                                 + ([] if config_revision is not None else ["no_active_config"]),
            "degraded_dependencies": degraded,
            "version": self.version,
            "profile": self.profile,
            "config": {"revision": config_revision, "digest": config_digest},
            "dependencies": deps,
            "capabilities": sorted(capabilities),
            "stalled_operations": stalled,
        }
