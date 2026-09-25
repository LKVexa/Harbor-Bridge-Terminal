"""Metrics registry, structured logs with redaction, trace context and health
(Sections 16-17, REQ-OBS-*).  Stdlib only; exporters are adapters.
"""
from __future__ import annotations

import json
import re
import secrets
import threading
import time
from typing import Final

METRICS_VERSION: Final[str] = "INV41_METRICS/1"
LOG_SCHEMA: Final[str] = "INV41_LOG/1"
HEALTH_SCHEMA: Final[str] = "INV41_HEALTH/1"
REASON_SCHEMA: Final[str] = "INV41_REASON/1"

COUNTERS: Final[dict] = {
    "inv41_grants_total": "grants minted", "inv41_binds_total": "holders bound",
    "inv41_attenuations_total": "attenuations", "inv41_wraps_total": "membrane wraps",
    "inv41_revocations_total": "membrane revocations", "inv41_uses_allowed_total": "allowed uses",
    "inv41_uses_denied_total": "denied uses", "inv41_invalid_references_total": "invalid/forged references",
    "inv41_cross_authority_total": "cross-authority rejections", "inv41_auth_failures_total": "authentication failures",
    "inv41_overload_rejections_total": "admission rejections",
}
HISTOGRAMS: Final[dict] = {"inv41_operation_latency_seconds": "critical operation latency",
                           "inv41_dependency_latency_seconds": "external dependency latency"}
GAUGES: Final[dict] = {"inv41_active_authorities": "authorities", "inv41_in_flight_checks": "in-flight checks",
                       "inv41_degraded_dependencies": "degraded dependencies", "inv41_queue_depth": "queue depth"}
ALLOWED_LABELS: Final[dict] = {"op": {"grant", "bind", "attenuate", "wrap", "revoke", "use", "config", "auth"},
                               "outcome": {"success", "denied", "invalid", "revoked", "stale", "unavailable",
                                           "retryable", "degraded", "terminal", "internal-fault"},
                               "code": None}
MAX_SERIES: Final[int] = 512
BUCKETS: Final[tuple] = (1e-6, 5e-6, 1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 1e-2, 1e-1, 1.0)

REDACT_KEYS: Final[frozenset] = frozenset({"seal", "token", "signature", "secret", "key", "password", "credential", "mac"})
_TOKENLIKE = re.compile(r"[A-Za-z0-9_\-]{40,}")


class CardinalityExceeded(RuntimeError):
    pass


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict = {}
        self.gauges: dict = {}
        self.hist: dict = {}

    def _key(self, name: str, labels: dict) -> tuple:
        for k, v in labels.items():
            allowed = ALLOWED_LABELS.get(k, "missing")
            if allowed == "missing":
                raise CardinalityExceeded(f"label {k!r} is not allowed")
            if allowed is not None and v not in allowed:
                raise CardinalityExceeded(f"label value {v!r} not in bounded domain")
            if allowed is None and not re.fullmatch(r"INV41-E\d{3}", str(v)):
                raise CardinalityExceeded("code label must be a stable error code")
        key = (name, tuple(sorted(labels.items())))
        if key not in self.counters and key not in self.hist and len(self.counters) + len(self.hist) >= MAX_SERIES:
            raise CardinalityExceeded("series limit reached")
        return key

    def inc(self, name: str, n: int = 1, **labels) -> None:
        if name not in COUNTERS:
            raise KeyError(name)
        with self._lock:
            key = self._key(name, labels)
            self.counters[key] = self.counters.get(key, 0) + n

    def set_gauge(self, name: str, value: float) -> None:
        if name not in GAUGES:
            raise KeyError(name)
        with self._lock:
            self.gauges[name] = value

    def add_gauge(self, name: str, delta: float) -> None:
        with self._lock:
            self.gauges[name] = self.gauges.get(name, 0) + delta

    def observe(self, name: str, seconds: float, **labels) -> None:
        if name not in HISTOGRAMS:
            raise KeyError(name)
        with self._lock:
            key = self._key(name, labels)
            h = self.hist.setdefault(key, {"count": 0, "sum": 0.0, "buckets": [0] * (len(BUCKETS) + 1)})
            h["count"] += 1
            h["sum"] += seconds
            for i, b in enumerate(BUCKETS):
                if seconds <= b:
                    h["buckets"][i] += 1
                    break
            else:
                h["buckets"][-1] += 1

    def total(self, name: str) -> int:
        return sum(v for (n, _l), v in self.counters.items() if n == name)

    def exposition(self) -> str:
        lines = [f"# {METRICS_VERSION}"]
        for (name, labels), v in sorted(self.counters.items()):
            lab = ",".join(f'{k}="{val}"' for k, val in labels)
            lines.append(f"{name}{{{lab}}} {v}")
        for name, v in sorted(self.gauges.items()):
            lines.append(f"{name} {v}")
        for (name, labels), h in sorted(self.hist.items()):
            lab = ",".join(f'{k}="{val}"' for k, val in labels)
            lines.append(f"{name}_count{{{lab}}} {h['count']}")
            lines.append(f"{name}_sum{{{lab}}} {h['sum']:.9f}")
        return "\n".join(lines) + "\n"


def redact(value):
    if isinstance(value, dict):
        return {k: ("<redacted>" if k.lower() in REDACT_KEYS else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return _TOKENLIKE.sub("<redacted>", value)
    return value


class StructuredLogger:
    """JSON-lines logger.  Successful ops are sampled; security failures never are."""

    def __init__(self, *, component_version: str, sink=None, success_sample_every: int = 1) -> None:
        self.version = component_version
        self.sink = sink if sink is not None else []
        self.every = max(1, success_sample_every)
        self._n = 0
        self._lock = threading.Lock()

    def log(self, severity: str, operation: str, outcome: str, reason: str, correlation_id: str, **fields) -> str | None:
        with self._lock:
            if outcome == "success":
                self._n += 1
                if self._n % self.every:
                    return None
            rec = {"schema": LOG_SCHEMA, "ts": round(time.time(), 6), "severity": severity,
                   "component": "INV-41", "version": self.version, "operation": operation,
                   "outcome": outcome, "reason": reason, "correlation_id": correlation_id, **redact(fields)}
            line = json.dumps(rec, sort_keys=True)
            if isinstance(self.sink, list):
                self.sink.append(line)
            else:
                self.sink(line)
            return line


_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_traceparent(header: str | None) -> dict:
    """W3C trace-context parse; invalid headers start a new trace.  Never used for authorization."""
    if isinstance(header, str):
        m = _TRACEPARENT.match(header.strip())
        if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
            return {"trace_id": m.group(1), "parent_id": m.group(2), "flags": m.group(3)}
    return {"trace_id": secrets.token_hex(16), "parent_id": None, "flags": "01"}


def child_traceparent(ctx: dict) -> tuple[str, str]:
    span = secrets.token_hex(8)
    return span, f"00-{ctx['trace_id']}-{span}-{ctx['flags']}"


class Tracer:
    def __init__(self) -> None:
        self.spans: list = []
        self._lock = threading.Lock()

    def span(self, name: str, ctx: dict, **attrs):
        tracer = self

        class _Span:
            def __enter__(self_inner):
                self_inner.span_id, _ = child_traceparent(ctx)
                self_inner.t0 = time.perf_counter()
                self_inner.attrs = dict(redact(attrs))
                return self_inner

            def __exit__(self_inner, et, ev, tb):
                rec = {"name": name, "trace_id": ctx["trace_id"], "parent_id": ctx.get("parent_id"),
                       "span_id": self_inner.span_id, "duration_s": time.perf_counter() - self_inner.t0,
                       "status": "error" if et else "ok", **self_inner.attrs}
                with tracer._lock:
                    tracer.spans.append(rec)
                return False
        return _Span()
