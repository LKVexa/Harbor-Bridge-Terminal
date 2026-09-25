"""Metrics, structured logs, trace context, decision explanations, redaction (WS 12).

Stdlib only.  Metric names/units are stable and labels are drawn from bounded
enumerations; tenant and guest identifiers are never metric labels -- they are
pseudonymised (keyed hash) before appearing in logs.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import math
import re
import secrets
import threading
import time
from typing import Any, Callable, Mapping

# ---------------------------------------------------------------- redaction
_SECRET_KEY_RE = re.compile(r"(secret|token|password|passwd|private_key|credential|authorization|api_key|bearer)", re.I)
_SECRET_VALUE_RES = [
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"(?i)(token|password|secret|api_key)=([^\s&;]+)"),
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"),  # JWT-shaped
    re.compile(r"inv32tok\.[A-Za-z0-9_.=-]+"),  # this package's own tokens
    re.compile(r"(?<![A-Za-z0-9])/(?:home|root|etc|var|srv|opt|Users)/[^\s'\"]+"),  # host paths
]
REDACTED = "[REDACTED]"


def redact_text(text: str) -> str:
    for rx in _SECRET_VALUE_RES:
        text = rx.sub(REDACTED, text)
    return text


def redact(value: Any) -> Any:
    """Recursively redact secret-looking keys and values."""
    if isinstance(value, Mapping):
        return {k: (REDACTED if _SECRET_KEY_RE.search(str(k)) and not str(k).endswith("_ref") else redact(v))
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


class Pseudonymizer:
    """Keyed, stable pseudonyms for tenant/guest IDs in logs and diagnostics."""

    def __init__(self, key: bytes | None = None) -> None:
        self._key = key or secrets.token_bytes(32)

    def __call__(self, kind: str, value: str | None) -> str | None:
        if value is None:
            return None
        digest = hmac.new(self._key, f"{kind}:{value}".encode(), hashlib.sha256).hexdigest()[:16]
        return f"{kind[0]}-{digest}"


# ---------------------------------------------------------------- metrics
LATENCY_BUCKETS_S = (0.00001, 0.00005, 0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, math.inf)

METRIC_DEFS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    # name: (type, unit, allowed label keys)
    "inv32_requests_total": ("counter", "1", ("operation", "outcome")),
    "inv32_refusals_total": ("counter", "1", ("reason",)),
    "inv32_retries_total": ("counter", "1", ("dependency",)),
    "inv32_circuit_open_total": ("counter", "1", ("dependency",)),
    "inv32_decision_latency_seconds": ("histogram", "s", ("operation",)),
    "inv32_provider_latency_seconds": ("histogram", "s", ("operation",)),
    "inv32_end_to_end_latency_seconds": ("histogram", "s", ("operation",)),
    "inv32_queue_wait_seconds": ("histogram", "s", ("priority",)),
    "inv32_reconcile_latency_seconds": ("histogram", "s", ()),
    "inv32_inflight_operations": ("gauge", "1", ()),
    "inv32_guest_count": ("gauge", "1", ()),
    "inv32_memory_mib": ("gauge", "MiB", ("kind",)),
    "inv32_audit_backlog": ("gauge", "1", ()),
    "inv32_lease_age_seconds": ("gauge", "s", ()),
    "inv32_quarantines_active": ("gauge", "1", ("scope",)),
}
REFUSAL_REASONS = {
    "reserve_breach", "floor_breach", "authorization_denied", "authentication_failed", "stale_expected_state",
    "replay_conflict", "guest_refused", "provider_timeout", "quarantined", "emergency_disabled", "overloaded",
    "quota_exceeded", "circuit_open", "audit_integrity_error", "fencing_rejected", "not_owner", "other",
}


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple, float] = {}
        self._gauges: dict[tuple, float] = {}
        self._hist: dict[tuple, list[int]] = {}
        self._hist_sum: dict[tuple, float] = {}

    @staticmethod
    def _key(name: str, labels: Mapping[str, str]) -> tuple:
        if name not in METRIC_DEFS:
            raise KeyError(f"undeclared metric {name}")
        allowed = METRIC_DEFS[name][2]
        if set(labels) - set(allowed):
            raise ValueError(f"{name}: label keys {sorted(set(labels) - set(allowed))} not allowed")
        for v in labels.values():
            if len(str(v)) > 64:
                raise ValueError("label value too long (unbounded cardinality guard)")
        if name == "inv32_refusals_total" and labels.get("reason") not in REFUSAL_REASONS:
            labels = {"reason": "other"}
        return (name, tuple(sorted(labels.items())))

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        k = self._key(name, labels)
        with self._lock:
            self._counters[k] = self._counters.get(k, 0.0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        k = self._key(name, labels)
        with self._lock:
            self._gauges[k] = float(value)

    def observe(self, name: str, seconds: float, **labels: str) -> None:
        k = self._key(name, labels)
        with self._lock:
            buckets = self._hist.setdefault(k, [0] * len(LATENCY_BUCKETS_S))
            for i, bound in enumerate(LATENCY_BUCKETS_S):
                if seconds <= bound:
                    buckets[i] += 1
                    break
            self._hist_sum[k] = self._hist_sum.get(k, 0.0) + seconds

    def value(self, name: str, **labels: str) -> float:
        k = self._key(name, labels)
        with self._lock:
            if k in self._counters:
                return self._counters[k]
            if k in self._gauges:
                return self._gauges[k]
            if k in self._hist:
                return float(sum(self._hist[k]))
        return 0.0

    def exposition(self) -> str:
        """Prometheus text exposition format."""
        lines: list[str] = []
        with self._lock:
            for name, (mtype, unit, _) in sorted(METRIC_DEFS.items()):
                lines.append(f"# TYPE {name} {mtype}")
                lines.append(f"# UNIT {name} {unit}")
                store = {"counter": self._counters, "gauge": self._gauges}.get(mtype)
                if store is not None:
                    for (n, labels), v in sorted(store.items()):
                        if n == name:
                            lines.append(f"{name}{_fmt_labels(labels)} {v}")
                else:
                    for (n, labels), buckets in sorted(self._hist.items()):
                        if n != name:
                            continue
                        cum = 0
                        for bound, count in zip(LATENCY_BUCKETS_S, buckets, strict=True):
                            cum += count
                            le = "+Inf" if math.isinf(bound) else repr(bound)
                            lines.append(f"{name}_bucket{_fmt_labels(labels + (('le', le),))} {cum}")
                        lines.append(f"{name}_sum{_fmt_labels(labels)} {self._hist_sum[(n, labels)]}")
                        lines.append(f"{name}_count{_fmt_labels(labels)} {cum}")
        return "\n".join(lines) + "\n"


def _fmt_labels(labels: tuple) -> str:
    if not labels:
        return ""
    return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}"


# ---------------------------------------------------------------- tracing
_TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass(frozen=True)
class TraceContext:
    """W3C Trace Context (traceparent) carrier."""

    trace_id: str
    span_id: str
    sampled: bool = True

    @classmethod
    def new(cls) -> TraceContext:
        return cls(secrets.token_hex(16), secrets.token_hex(8), True)

    @classmethod
    def parse(cls, header: str | None) -> TraceContext:
        """Parse an untrusted traceparent; malformed input yields a fresh root (never raises)."""
        if isinstance(header, str) and len(header) == 55:
            m = _TRACEPARENT_RE.match(header)
            if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
                return cls(m.group(1), m.group(2), m.group(3) == "01")
        return cls.new()

    def child(self) -> TraceContext:
        return TraceContext(self.trace_id, secrets.token_hex(8), self.sampled)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


@dataclass
class Span:
    name: str
    ctx: TraceContext
    parent_span_id: str | None
    start: float
    end: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


class Tracer:
    """In-process span recorder with error/latency-biased bounded retention."""

    ALLOWED_ATTRS = {"operation", "outcome", "code", "phase", "priority"}

    def __init__(self, capacity: int = 2048, slow_threshold_s: float = 0.05) -> None:
        self.spans: deque[Span] = deque(maxlen=capacity)
        self.slow_threshold_s = slow_threshold_s
        self._lock = threading.Lock()

    def span(self, name: str, parent: TraceContext) -> _SpanCM:
        return _SpanCM(self, name, parent)

    def _finish(self, span: Span) -> None:
        attrs = span.attributes
        duration = (span.end or span.start) - span.start
        keep = span.ctx.sampled or attrs.get("outcome") not in (None, "success") or duration >= self.slow_threshold_s
        if keep:
            with self._lock:
                self.spans.append(span)

    def names(self, trace_id: str) -> list[str]:
        with self._lock:
            return [s.name for s in self.spans if s.ctx.trace_id == trace_id]


class _SpanCM:
    def __init__(self, tracer: Tracer, name: str, parent: TraceContext) -> None:
        self.tracer = tracer
        self.span = Span(name, parent.child(), parent.span_id, time.perf_counter(), attributes={})

    def set(self, **attrs: Any) -> None:
        for k, v in attrs.items():
            if k in Tracer.ALLOWED_ATTRS:  # baggage cannot inject arbitrary high-cardinality data
                self.span.attributes[k] = str(v)[:64]

    def __enter__(self) -> _SpanCM:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc is not None and "outcome" not in self.span.attributes:
            self.set(outcome="error", code=getattr(exc, "code", "internal_error"))
        self.span.end = time.perf_counter()
        self.tracer._finish(self.span)


# ---------------------------------------------------------------- logging
SEVERITIES = ("DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL")


class StructuredLogger:
    """JSON-lines logger: machine fields separate from the operator message, redacted."""

    def __init__(self, component: str, sink: Callable[[str], None] | None = None, *,
                 pseudonymizer: Pseudonymizer | None = None, capacity: int = 4096) -> None:
        self.component = component
        self.records: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._sink = sink
        self._pseudo = pseudonymizer or Pseudonymizer()

    def log(self, severity: str, message: str, *, host: str | None = None, tenant: str | None = None,
            guest: str | None = None, operation_id: str | None = None, trace_id: str | None = None,
            epoch: int | None = None, config_digest: str | None = None, outcome: str | None = None,
            audit_sequence: int | None = None, audit_hash: str | None = None, **fields: Any) -> dict[str, Any]:
        if severity not in SEVERITIES:
            raise ValueError("unknown severity")
        record = {
            "ts": time.time(),
            "severity": severity,
            "component": self.component,
            "host": host,
            "tenant_ref": self._pseudo("tenant", tenant),
            "guest_ref": self._pseudo("guest", guest),
            "operation_id": operation_id,
            "trace_id": trace_id,
            "controller_epoch": epoch,
            "config_digest": config_digest,
            "outcome": outcome,
            "audit_sequence": audit_sequence,
            "audit_hash": audit_hash,
            "fields": redact(fields),
            "message": redact_text(message),
        }
        self.records.append(record)
        if self._sink:
            self._sink(json.dumps(record, sort_keys=True, default=str))
        return record


# ---------------------------------------------------------------- explainability
class ExplainStore:
    """Bounded store of structured decision inputs keyed by operation ID."""

    def __init__(self, capacity: int = 10000) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._order: deque[str] = deque()
        self._capacity = capacity
        self._lock = threading.Lock()

    def record(self, operation_id: str, decision: Mapping[str, Any]) -> None:
        with self._lock:
            if operation_id not in self._items:
                self._order.append(operation_id)
            self._items[operation_id] = redact(dict(decision))
            while len(self._order) > self._capacity:
                self._items.pop(self._order.popleft(), None)

    def explain(self, operation_id: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._items.get(operation_id)
            return dict(item) if item else None


# ---------------------------------------------------------------- telemetry policy (retention/sampling/export)
TELEMETRY_POLICY = {
    "schema": "PK_TELEMETRY_POLICY/1",
    "retention_days": {"metrics": 30, "logs": 14, "traces": 7, "explain": 30, "audit": "see store.RETENTION"},
    "sampling": {"traces_success": "head-sampled per traceparent flag", "traces_error": 1.0,
                 "traces_slow": 1.0, "slow_threshold_seconds": 0.05},
    "cardinality": {"metric_label_values_max_len": 64, "tenant_or_guest_ids_as_labels": False},
    "privacy": {"tenant_guest_ids": "keyed pseudonyms in logs; raw IDs only in access-controlled audit",
                "secrets": "redacted by telemetry.redact at every sink"},
    "export": {"transport": "TLS 1.3 required (deployment)", "buffering": "bounded in-memory deques; drop-oldest",
               "outage_behaviour": "control continues; telemetry dropped and counted (degraded mode TELEMETRY_DOWN)"},
    "deletion": {"mechanism": "retention expiry at the sink", "audited": True},
}
