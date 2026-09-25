"""Metrics, structured logs, W3C trace context, decision records and a
tamper-evident audit chain (C049, C072-C076).

Everything is bounded (queues, label cardinality, histogram reservoirs) and a
failing sink never breaks the primitive: the failure is counted and surfaces as
DEGRADED status (C056).
"""
from __future__ import annotations

import collections
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from typing import Any, Callable, Mapping

from .errors import redact, redact_text

LOG_SCHEMA = "PK_FUTURE_LOG/1"
AUDIT_SCHEMA = "PK_FUTURE_AUDIT/1"
DECISION_SCHEMA = "PK_FUTURE_DECISION/1"
SEVERITIES = ("debug", "info", "warning", "error", "critical")

# Metric contract (C072): name -> (kind, unit, allowed label keys)
METRICS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "inv18_futures_created_total": ("counter", "1", ("tenant_class",)),
    "inv18_values_resolved_total": ("counter", "1", ()),
    "inv18_errors_resolved_total": ("counter", "1", ()),
    "inv18_abandonments_total": ("counter", "1", ("reason",)),
    "inv18_cancellations_total": ("counter", "1", ()),
    "inv18_takes_total": ("counter", "1", ()),
    "inv18_double_resolutions_total": ("counter", "1", ()),
    "inv18_double_takes_total": ("counter", "1", ()),
    "inv18_rejections_total": ("counter", "1", ("code",)),
    "inv18_limit_hits_total": ("counter", "1", ("limit",)),
    "inv18_invariant_violations_total": ("counter", "1", ()),
    "inv18_telemetry_dropped_total": ("counter", "1", ("sink",)),
    "inv18_futures_open": ("gauge", "1", ()),
    "inv18_resolution_latency_seconds": ("histogram", "s", ()),
    "inv18_receive_latency_seconds": ("histogram", "s", ()),
}
MAX_LABEL_VALUES = 32
RESERVOIR = 4096


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict[tuple, float] = collections.defaultdict(float)
        self.gauges: dict[tuple, float] = {}
        self.hist: dict[tuple, collections.deque] = {}
        self.hist_count: dict[tuple, int] = collections.defaultdict(int)
        self._label_values: dict[tuple[str, str], set] = collections.defaultdict(set)

    def _key(self, name: str, labels: Mapping[str, str] | None) -> tuple:
        if name not in METRICS:
            raise KeyError(f"undeclared metric {name}")
        allowed = METRICS[name][2]
        items = []
        for k in allowed:
            v = str((labels or {}).get(k, ""))[:64]
            seen = self._label_values[(name, k)]
            if v not in seen:
                if len(seen) >= MAX_LABEL_VALUES:
                    v = "other"          # bounded cardinality
                seen.add(v)
            items.append((k, v))
        return (name, tuple(items))

    def inc(self, name: str, n: float = 1, **labels: str) -> None:
        with self._lock:
            self.counters[self._key(name, labels)] += n

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self.gauges[self._key(name, labels)] = value

    def observe(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            self.hist.setdefault(k, collections.deque(maxlen=RESERVOIR)).append(value)
            self.hist_count[k] += 1

    def counter(self, name: str, **labels: str) -> float:
        with self._lock:
            if labels:
                return self.counters.get(self._key(name, labels), 0.0)
            return sum(v for (n, _), v in self.counters.items() if n == name)

    def gauge(self, name: str) -> float:
        with self._lock:
            return sum(v for (n, _), v in self.gauges.items() if n == name)

    def percentiles(self, name: str, ps=(50, 95, 99)) -> dict[str, float]:
        with self._lock:
            vals = sorted(v for (n, _), d in self.hist.items() if n == name for v in d)
        if not vals:
            return {}
        out = {f"p{p}": vals[min(len(vals) - 1, int(round(p / 100 * (len(vals) - 1))))] for p in ps}
        out["max"] = vals[-1]
        out["n"] = len(vals)
        return out

    def snapshot(self) -> dict:
        with self._lock:
            c = [{"name": n, "labels": dict(l), "value": v} for (n, l), v in sorted(self.counters.items())]
            g = [{"name": n, "labels": dict(l), "value": v} for (n, l), v in sorted(self.gauges.items())]
        return {"counters": c, "gauges": g,
                "histograms": {n: self.percentiles(n) for n, s in METRICS.items() if s[0] == "histogram"}}


# --------------------------------------------------------------------------- traces
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


class TraceContext:
    """W3C Trace Context (``traceparent``) subset (C074)."""

    __slots__ = ("trace_id", "span_id", "parent_id", "flags")

    def __init__(self, trace_id: str, span_id: str, parent_id: str | None = None, flags: str = "01"):
        self.trace_id, self.span_id, self.parent_id, self.flags = trace_id, span_id, parent_id, flags

    @classmethod
    def new(cls) -> "TraceContext":
        return cls(secrets.token_hex(16), secrets.token_hex(8))

    @classmethod
    def parse(cls, header: str | None) -> "TraceContext":
        """Untrusted input: invalid/all-zero headers are replaced by a fresh root."""
        if not isinstance(header, str) or len(header) != 55:
            return cls.new()
        m = _TRACEPARENT.match(header)
        if not m or set(m.group(1)) == {"0"} or set(m.group(2)) == {"0"}:
            return cls.new()
        return cls(m.group(1), secrets.token_hex(8), parent_id=m.group(2), flags=m.group(3))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), parent_id=self.span_id, flags=self.flags)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"


# --------------------------------------------------------------------------- logs
class StructuredLog:
    """Bounded, rate-limited, redacted JSON log (C073, C075, C079)."""

    def __init__(self, *, component: str, version: str, maxlen: int = 10_000, rate_per_s: int = 1000,
                 sink: Callable[[str], None] | None = None, clock=time.monotonic, metrics: Metrics | None = None):
        self.component, self.version = component, version
        self.records: collections.deque = collections.deque(maxlen=maxlen)
        self.rate, self._clock = rate_per_s, clock
        self._window, self._count = 0.0, 0
        self.sink, self.metrics = sink, metrics
        self.sink_failed = False
        self.dropped = 0
        self._lock = threading.Lock()

    def emit(self, severity: str, operation: str, *, code: str | None = None, future_id: str | None = None,
             trace: TraceContext | None = None, config_revision: str | None = None,
             tenant: str | None = None, **fields: Any) -> dict | None:
        if severity not in SEVERITIES:
            severity = "error"
        now = self._clock()
        with self._lock:
            if now - self._window >= 1.0:
                self._window, self._count = now, 0
            self._count += 1
            if self._count > self.rate and severity not in ("error", "critical"):
                self.dropped += 1
                if self.metrics:
                    self.metrics.inc("inv18_telemetry_dropped_total", sink="log_rate")
                return None
        rec = {"schema": LOG_SCHEMA, "ts": time.time(), "severity": severity, "component": self.component,
               "version": self.version, "operation": operation, "code": code,
               "future_id": future_id, "trace_id": trace.trace_id if trace else None,
               "span_id": trace.span_id if trace else None, "config_revision": config_revision,
               "tenant": hashlib.sha256(tenant.encode()).hexdigest()[:12] if tenant else None,
               "fields": redact({k: v for k, v in fields.items() if k not in ("payload", "value")})}
        with self._lock:
            self.records.append(rec)
        if self.sink is not None:
            try:
                self.sink(json.dumps(rec, sort_keys=True))
                self.sink_failed = False
            except Exception:
                self.sink_failed = True
                self.dropped += 1
                if self.metrics:
                    self.metrics.inc("inv18_telemetry_dropped_total", sink="log_sink")
        return rec


LOG_REQUIRED = ("schema", "ts", "severity", "component", "version", "operation", "code", "future_id",
                "trace_id", "config_revision", "fields")


def validate_log(rec: Mapping[str, Any]) -> list[str]:
    errs = [f"missing {k}" for k in LOG_REQUIRED if k not in rec]
    if rec.get("schema") != LOG_SCHEMA:
        errs.append("bad schema")
    if rec.get("severity") not in SEVERITIES:
        errs.append("bad severity")
    blob = json.dumps(rec)
    if "SENTINEL-SECRET" in blob:
        errs.append("secret leaked")
    return errs


# --------------------------------------------------------------------------- audit
class AuditChain:
    """Append-only hash chain; optional HMAC seal when a key is supplied (C049)."""

    def __init__(self, *, maxlen: int | None = None, key: bytes | None = None):
        self.events: list[dict] = []
        self._lock = threading.Lock()
        self._key = key
        self.head = "0" * 64

    @staticmethod
    def _hash(ev: Mapping[str, Any]) -> str:
        body = {k: v for k, v in ev.items() if k not in ("hash", "mac")}
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def append(self, action: str, *, actor: str = "system", target: str | None = None, result: str = "ok",
               correlation_id: str | None = None, **details: Any) -> dict:
        with self._lock:
            ev = {"schema": AUDIT_SCHEMA, "seq": len(self.events), "event_id": secrets.token_hex(8),
                  "ts": time.time(), "actor": actor, "action": action, "target": target, "result": result,
                  "correlation_id": correlation_id, "details": redact(details), "prev": self.head}
            ev["hash"] = self._hash(ev)
            if self._key:
                ev["mac"] = hmac.new(self._key, ev["hash"].encode(), hashlib.sha256).hexdigest()
            self.events.append(ev)
            self.head = ev["hash"]
            return ev

    def verify(self, events: list[dict] | None = None) -> tuple[bool, str]:
        events = self.events if events is None else events
        prev = "0" * 64
        for i, ev in enumerate(events):
            if ev.get("seq") != i:
                return False, f"sequence gap at {i}"
            if ev.get("prev") != prev:
                return False, f"chain break at {i}"
            if self._hash(ev) != ev.get("hash"):
                return False, f"hash mismatch at {i}"
            if self._key and not hmac.compare_digest(
                    hmac.new(self._key, ev["hash"].encode(), hashlib.sha256).hexdigest(), ev.get("mac", "")):
                return False, f"mac mismatch at {i}"
            prev = ev["hash"]
        return True, "ok"


# --------------------------------------------------------------------------- decisions
DECISION_REASONS = {
    "RESOLVE_REJECTED": "a resolution was refused",
    "TAKE_REJECTED": "a second receiver was refused",
    "ABANDON_TRANSITION": "a writer was dropped without resolving",
    "CANCEL_TRANSITION": "a receiver cancelled",
    "COMPAT_REJECTED": "a peer offered no compatible contract version",
    "AUTHN_REJECTED": "authentication failed",
    "AUTHZ_REJECTED": "capability check failed",
    "OVERLOAD_REJECTED": "admission limit reached",
    "DEGRADED_MODE": "component entered degraded mode",
    "DISABLED_REJECTED": "component or tenant disabled",
    "PRECEDENCE_APPLIED": "a constraint-precedence rule decided a conflict",
}


class DecisionLog:
    """Bounded machine-readable automated-decision records (C076)."""

    def __init__(self, maxlen: int = 1024):
        self.records: collections.deque = collections.deque(maxlen=maxlen)

    def record(self, reason: str, *, code: str | None, config_revision: str | None, policy_version: str,
               correlation_id: str | None = None, **state: Any) -> dict:
        if reason not in DECISION_REASONS:
            raise KeyError(f"undeclared decision reason {reason}")
        rec = {"schema": DECISION_SCHEMA, "ts": time.time(), "reason": reason, "code": code,
               "config_revision": config_revision, "policy_version": policy_version,
               "correlation_id": correlation_id, "state": redact(state)}
        self.records.append(rec)
        return rec

    def summary(self) -> dict[str, int]:
        c: dict[str, int] = collections.Counter(r["reason"] for r in self.records)
        return dict(c)


def redact_value(v: Any) -> str:
    return redact_text(repr(v))
