"""Metrics, structured logging, tracing and redaction (components 26, 27).

* ``Metrics``: counters / gauges / histograms with a *declared* label set per
  metric and a closed value set per label, so raw artifact / node / trace /
  signer ids can never become labels (MC-26-05). Prometheus text exposition.
* ``Logger``: JSON lines with a fixed schema; every untrusted string is
  length-capped and control-character escaped (log injection, MC-27-06);
  secret-bearing keys are redacted (MC-27-05); identifiers are hashed.
* ``Tracer``: W3C ``traceparent`` parse/emit, spans with parent linkage,
  error/security-preserving sampling (MC-27-02..04).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

SECRET_KEYS = re.compile(r"(?i)(token|secret|password|authorization|private|signature|cookie|seed|credential|api[-_]?key)")
MAX_FIELD = 512

VERDICTS = ("certified", "incompatible", "untested", "expired", "end-of-life", "revoked", "quarantined", "retest-required")
REJECTIONS = ("schema", "auth", "authz", "signature", "provenance", "attestation", "time", "conflict", "capacity", "internal", "duplicate")
OPS = ("ingest", "certify", "explain", "admission", "lifecycle", "revocation", "negotiate", "policy", "backup", "restore", "matrix")

METRIC_DEFS = {
    # name: (type, unit, help, {label: allowed values})
    "gap15_certifications_total": ("counter", "1", "Certification verdicts issued", {"verdict": VERDICTS}),
    "gap15_evidence_rejections_total": ("counter", "1", "Evidence rejected at ingestion", {"category": REJECTIONS}),
    "gap15_evidence_accepted_total": ("counter", "1", "Evidence accepted", {}),
    "gap15_requests_total": ("counter", "1", "API requests", {"op": OPS, "outcome": ("ok", "error")}),
    "gap15_request_seconds": ("histogram", "s", "API latency", {"op": OPS}),
    "gap15_matrix_coverage_ratio": ("gauge", "ratio", "Tested over requested keys", {}),
    "gap15_expiry_backlog": ("gauge", "1", "Certifications expired or expiring within horizon", {}),
    "gap15_eol_in_service": ("gauge", "1", "Admissions/nodes on EOL runtimes", {}),
    "gap15_revocation_propagation_seconds": ("gauge", "s", "Oldest unconfirmed revocation propagation", {}),
    "gap15_revision_conflicts_total": ("counter", "1", "Optimistic concurrency conflicts", {}),
    "gap15_queue_depth": ("gauge", "1", "Bounded queue depth", {"queue": ("ingest", "recert")}),
    "gap15_evidence_age_seconds": ("gauge", "s", "Oldest current positive evidence age", {}),
    "gap15_exporter_scrape_age_seconds": ("gauge", "s", "Seconds since last successful scrape", {}),
    "gap15_dropped_observations_total": ("counter", "1", "Observations dropped by the exporter", {}),
    "gap15_time_offset_seconds": ("gauge", "s", "Spread between trusted time sources", {}),
    "gap15_waivers_active": ("gauge", "1", "Active waivers", {"risk": ("low", "medium", "high")}),
    "gap15_conflicts_open": ("gauge", "1", "Open evidence conflict cases", {}),
    "gap15_audit_chain_ok": ("gauge", "bool", "1 when audit + ledger chains verify", {}),
}
BUCKETS = (0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)


class MetricError(ValueError):
    pass


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict = {}
        self._hist: dict = {}
        self.last_scrape: Optional[float] = None

    def _key(self, name: str, labels: dict) -> tuple:
        if name not in METRIC_DEFS:
            raise MetricError(f"undeclared metric {name}")
        allowed = METRIC_DEFS[name][3]
        if set(labels) != set(allowed):
            raise MetricError(f"{name}: labels {sorted(labels)} != declared {sorted(allowed)}")
        for k, v in labels.items():
            if v not in allowed[k]:
                self.inc("gap15_dropped_observations_total") if name != "gap15_dropped_observations_total" else None
                raise MetricError(f"{name}: label {k}={v!r} outside bounded set")
        return (name, tuple(sorted(labels.items())))

    def inc(self, name: str, n: int = 1, **labels) -> None:
        if METRIC_DEFS.get(name, ("",))[0] != "counter":
            raise MetricError(f"{name} is not a counter")
        k = self._key(name, labels)
        with self._lock:
            self._values[k] = self._values.get(k, 0) + n

    def set(self, name: str, value: float, **labels) -> None:
        if METRIC_DEFS.get(name, ("",))[0] != "gauge":
            raise MetricError(f"{name} is not a gauge")
        k = self._key(name, labels)
        with self._lock:
            self._values[k] = value

    def observe(self, name: str, value: float, **labels) -> None:
        if METRIC_DEFS.get(name, ("",))[0] != "histogram":
            raise MetricError(f"{name} is not a histogram")
        k = self._key(name, labels)
        with self._lock:
            h = self._hist.setdefault(k, {"buckets": [0] * len(BUCKETS), "sum": 0.0, "count": 0})
            for i, b in enumerate(BUCKETS):
                if value <= b:
                    h["buckets"][i] += 1
            h["sum"] += value
            h["count"] += 1

    def get(self, name: str, **labels) -> float:
        return self._values.get(self._key(name, labels), 0)

    def exposition(self) -> str:
        lines = []
        with self._lock:
            now = time.time()
            if self.last_scrape is not None:
                self._values[("gap15_exporter_scrape_age_seconds", ())] = round(now - self.last_scrape, 3)
            self.last_scrape = now
            for name, (typ, unit, help_, _) in sorted(METRIC_DEFS.items()):
                lines.append(f"# HELP {name} {help_} ({unit})")
                lines.append(f"# TYPE {name} {typ}")
                for (n, labels), v in sorted(self._values.items()):
                    if n == name:
                        lab = ",".join(f'{k}="{val}"' for k, val in labels)
                        lines.append(f"{name}{{{lab}}} {v}" if lab else f"{name} {v}")
                for (n, labels), h in sorted(self._hist.items()):
                    if n == name:
                        base = ",".join(f'{k}="{val}"' for k, val in labels)
                        cum = 0
                        for b, c in zip(BUCKETS, h["buckets"]):
                            cum = c
                            lines.append(f'{name}_bucket{{{base},le="{b}"}} {cum}')
                        lines.append(f'{name}_bucket{{{base},le="+Inf"}} {h["count"]}')
                        lines.append(f"{name}_sum{{{base}}} {h['sum']}")
                        lines.append(f"{name}_count{{{base}}} {h['count']}")
        return "\n".join(lines) + "\n"


def hash_id(value: str) -> str:
    return "h:" + hashlib.sha256(value.encode()).hexdigest()[:16]


def sanitize(value, depth: int = 0):
    if depth > 4:
        return "[depth-capped]"
    if isinstance(value, dict):
        return {str(k)[:64]: ("[redacted]" if SECRET_KEYS.search(str(k)) else sanitize(v, depth + 1))
                for k, v in list(value.items())[:32]}
    if isinstance(value, (list, tuple)):
        return [sanitize(v, depth + 1) for v in list(value)[:32]]
    if isinstance(value, str):
        v = value[:MAX_FIELD]
        return "".join(ch if 32 <= ord(ch) != 127 else f"\\x{ord(ch):02x}" for ch in v)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return sanitize(str(value), depth + 1)


@dataclass
class Logger:
    service: str
    build: str
    sink: list = field(default_factory=list)
    revisions: dict = field(default_factory=dict)  # schema/policy/matrix/truststore revisions (MC-27-08)

    def log(self, severity: str, event: str, *, trace: Optional["Span"] = None, **fields) -> dict:
        rec = {"ts": int(time.time()), "severity": severity, "event": sanitize(event), "service": self.service,
               "build": self.build, "revisions": dict(self.revisions)}
        if trace is not None:
            rec["trace_id"], rec["span_id"] = trace.trace_id, trace.span_id
        for k in ("artifact", "node", "signer", "subject"):
            if k in fields and isinstance(fields[k], str):
                fields[k] = hash_id(fields[k])
        rec["fields"] = sanitize(fields)
        line = json.dumps(rec, sort_keys=True, ensure_ascii=True)
        self.sink.append(line)
        return rec


_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    sampled: bool
    start: float = field(default_factory=time.perf_counter)
    end: Optional[float] = None
    status: str = "ok"
    attrs: dict = field(default_factory=dict)

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


class Tracer:
    def __init__(self, sample_ratio: float = 0.1) -> None:
        self.sample_ratio = sample_ratio
        self.finished: list = []
        self._lock = threading.Lock()

    def start(self, name: str, *, traceparent: Optional[str] = None, parent: Optional[Span] = None) -> Span:
        if parent is not None:
            return Span(name, parent.trace_id, os.urandom(8).hex(), parent.span_id, parent.sampled)
        if traceparent:
            m = _TP.match(traceparent)
            if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
                return Span(name, m.group(1), os.urandom(8).hex(), m.group(2), m.group(3) == "01")
        tid = os.urandom(16).hex()
        sampled = int(tid[:8], 16) / 0xFFFFFFFF < self.sample_ratio
        return Span(name, tid, os.urandom(8).hex(), None, sampled)

    def finish(self, span: Span, *, status: str = "ok", security: bool = False) -> None:
        span.end = time.perf_counter()
        span.status = status
        # tail rule: errors and security events are always kept (MC-27-04)
        if span.sampled or status != "ok" or security:
            with self._lock:
                self.finished.append(span)
                del self.finished[:-10000]
