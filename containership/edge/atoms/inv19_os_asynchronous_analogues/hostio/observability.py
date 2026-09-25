"""MC-22 - Metrics, structured logs, tracing and decision explain records.

Metric safety: labels are validated against a per-metric allow-list with a
bounded value set (backend names, canonical codes, reasons); raw descriptors,
op ids, secrets and unaggregated tenant ids are rejected at registration.
Exposition is Prometheus text format.  Structured logs pass through
``security.redact`` and keep only ``PERMITTED_LOG_FIELDS``.  Trace context is
W3C ``traceparent`` compatible and propagated through operation metadata.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .security import PERMITTED_LOG_FIELDS, redact

MAX_SERIES_PER_METRIC = 256
_BAD_LABELS = {"fd", "op_id", "descriptor", "token", "secret", "key", "tenant", "workload", "payload"}

METRICS_SPEC = {
    "inv19_backend_selected": ("gauge", ("backend", "semantics"), "1"),
    "inv19_backend_selection_reason": ("gauge", ("backend", "reason"), "1"),
    "inv19_fallback_engagements_total": ("counter", ("reason",), "events"),
    "inv19_submit_total": ("counter", ("backend", "op"), "ops"),
    "inv19_reap_total": ("counter", ("backend", "kind"), "events"),
    "inv19_cancel_total": ("counter", ("backend", "outcome"), "ops"),
    "inv19_errors_total": ("counter", ("backend", "code"), "errors"),
    "inv19_untranslatable_errors_total": ("counter", ("backend",), "errors"),
    "inv19_queue_depth": ("gauge", ("backend", "queue"), "entries"),
    "inv19_quota_utilisation_ratio": ("gauge", ("resource",), "ratio"),
    "inv19_retry_total": ("counter", ("code",), "retries"),
    "inv19_timeout_total": ("counter", ("backend",), "ops"),
    "inv19_backend_health": ("gauge", ("backend", "state"), "1"),
    "inv19_reap_latency_seconds": ("histogram", ("backend",), "seconds"),
    "inv19_audit_export_failures_total": ("counter", (), "events"),
    "inv19_telemetry_dropped_total": ("counter", (), "events"),
    "inv19_tenant_class_ops_total": ("counter", ("tenant_class",), "ops"),
}
BUCKETS = (1e-6, 5e-6, 1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2, 0.1, 0.5, 1.0)


class CardinalityError(ValueError):
    pass


@dataclass
class Metrics:
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _v: dict[tuple, float] = field(default_factory=dict, init=False)
    _h: dict[tuple, list] = field(default_factory=dict, init=False)
    dropped: int = field(default=0, init=False)

    def _key(self, name: str, labels: dict[str, str]) -> tuple:
        if name not in METRICS_SPEC:
            raise KeyError(f"unregistered metric {name}")
        allowed = METRICS_SPEC[name][1]
        if set(labels) & _BAD_LABELS or set(labels) != set(allowed):
            raise CardinalityError(f"{name}: labels {sorted(labels)} != {list(allowed)}")
        for v in labels.values():
            if not re.match(r"^[A-Za-z0-9_.:-]{1,48}$", str(v)):
                raise CardinalityError(f"{name}: unsafe label value")
        key = (name, tuple(sorted(labels.items())))
        if key not in self._v and key not in self._h:
            n = sum(1 for k in list(self._v) + list(self._h) if k[0] == name)
            if n >= MAX_SERIES_PER_METRIC:
                self.dropped += 1
                raise CardinalityError(f"{name}: series cap {MAX_SERIES_PER_METRIC}")
        return key

    def inc(self, name: str, amount: float = 1.0, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            self._v[k] = self._v.get(k, 0.0) + amount

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self._v[self._key(name, labels)] = float(value)

    def observe(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            h = self._h.setdefault(k, [0] * (len(BUCKETS) + 1) + [0.0, 0])
            for i, b in enumerate(BUCKETS):
                if value <= b:
                    h[i] += 1
            h[len(BUCKETS)] += 1  # +Inf
            h[-2] += value
            h[-1] += 1

    def get(self, name: str, **labels: str) -> float:
        with self._lock:
            return self._v.get((name, tuple(sorted(labels.items()))), 0.0)

    def exposition(self) -> str:
        out: list[str] = []
        with self._lock:
            for name, (typ, _, unit) in METRICS_SPEC.items():
                out.append(f"# HELP {name} unit={unit}")
                out.append(f"# TYPE {name} {typ}")
                for (n, lab), v in sorted(self._v.items()):
                    if n == name:
                        ls = ",".join(f'{a}="{b}"' for a, b in lab)
                        out.append(f"{name}{{{ls}}} {v}" if ls else f"{name} {v}")
                for (n, lab), h in sorted(self._h.items()):
                    if n == name:
                        base = ",".join(f'{a}="{b}"' for a, b in lab)
                        for i, b in enumerate(BUCKETS):
                            out.append(f'{name}_bucket{{{base},le="{b}"}} {h[i]}')
                        out.append(f'{name}_bucket{{{base},le="+Inf"}} {h[len(BUCKETS)]}')
                        out.append(f"{name}_sum{{{base}}} {h[-2]}")
                        out.append(f"{name}_count{{{base}}} {h[-1]}")
        return "\n".join(out) + "\n"


def tenant_class(tenant_ops: int) -> str:
    """Aggregate tenants into a bounded class label instead of raw ids."""
    return "hot" if tenant_ops > 10000 else "warm" if tenant_ops > 100 else "cold"


@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    sampled: bool = True

    @staticmethod
    def new() -> "TraceContext":
        return TraceContext(os.urandom(16).hex(), os.urandom(8).hex())

    @staticmethod
    def parse(traceparent: str) -> "TraceContext | None":
        m = re.match(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$", traceparent or "")
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return None
        return TraceContext(m.group(1), m.group(2), bool(int(m.group(3), 16) & 1))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, os.urandom(8).hex(), self.sampled)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


@dataclass
class Tracer:
    max_spans: int = 4096
    spans: list[dict] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def span(self, name: str, parent: TraceContext | None, **attrs: Any) -> TraceContext:
        ctx = parent.child() if parent else TraceContext.new()
        with self._lock:
            self.spans.append({"name": name, "trace_id": ctx.trace_id, "span_id": ctx.span_id,
                               "parent": parent.span_id if parent else None, "ts": time.time(),
                               "attrs": redact(attrs)})
            del self.spans[:-self.max_spans]
        return ctx


@dataclass
class Logger:
    sink: list = field(default_factory=list)
    max_records: int = 8192
    release: str = "5.0.0"
    config_digest: str = ""

    def log(self, event: str, severity: str = "INFO", **fields: Any) -> dict:
        rec = {"event": event, "severity": severity, "ts": time.time(), "release": self.release,
               "config_digest": self.config_digest}
        for k, v in fields.items():
            if k in PERMITTED_LOG_FIELDS:
                rec[k] = v
        rec = redact(rec)
        self.sink.append(rec)
        del self.sink[:-self.max_records]
        return rec

    def dumps(self) -> str:
        return "\n".join(json.dumps(r, sort_keys=True) for r in self.sink)


@dataclass
class DecisionLog:
    """C076/C077 - every automated decision with its inputs and reason codes."""
    decisions: list[dict] = field(default_factory=list)

    def record(self, decision: str, chosen: str, inputs: dict, reasons: dict) -> dict:
        d = {"decision": decision, "chosen": chosen, "inputs": redact(inputs),
             "reasons": redact(reasons), "ts": time.time()}
        self.decisions.append(d)
        del self.decisions[:-1024]
        return d

    def explain(self) -> str:
        lines = []
        for d in self.decisions[-20:]:
            lines.append(f"[{d['decision']}] chose {d['chosen']}")
            for k, v in d["reasons"].items():
                lines.append(f"    {k}: {v}")
        return "\n".join(lines)


ALERT_RULES = [
    {"alert": "INV19UnknownHostErrors", "expr": "increase(inv19_untranslatable_errors_total[5m]) > 0", "severity": "page"},
    {"alert": "INV19PersistentFallback", "expr": "sum(inv19_backend_selected{backend=\"portable\"}) == 1 and on() inv19_fast_path_expected == 1", "for": "15m", "severity": "ticket"},
    {"alert": "INV19ErrorRate", "expr": "sum(rate(inv19_errors_total[5m])) / sum(rate(inv19_reap_total[5m])) > 0.05", "severity": "page"},
    {"alert": "INV19QueueSaturation", "expr": "max(inv19_quota_utilisation_ratio) > 0.9", "for": "5m", "severity": "page"},
    {"alert": "INV19ReapP99", "expr": "histogram_quantile(0.99, sum by (le,backend)(rate(inv19_reap_latency_seconds_bucket[5m]))) > 0.001", "severity": "ticket"},
    {"alert": "INV19BackendUnhealthy", "expr": "inv19_backend_health{state=\"unhealthy\"} == 1", "severity": "page"},
    {"alert": "INV19AuditExportFailure", "expr": "increase(inv19_audit_export_failures_total[5m]) > 0", "severity": "page"},
    {"alert": "INV19TelemetryDropped", "expr": "increase(inv19_telemetry_dropped_total[15m]) > 100", "severity": "ticket"},
]
TELEMETRY_POLICY = {"metrics_retention_days": 30, "logs_retention_days": 14, "traces_sampling": "parent-based, 1% head",
                    "privacy": "tenant/workload pseudonymised; no fds, payloads or secrets", "export": "Prometheus text + JSONL"}
