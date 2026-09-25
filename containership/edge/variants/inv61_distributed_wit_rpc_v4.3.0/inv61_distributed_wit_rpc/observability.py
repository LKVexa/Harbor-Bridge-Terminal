"""M14/M15/M16/M17/M18 - health/readiness, metrics exporter, structured
logging with redaction, W3C trace-context propagation and telemetry policy
enforcement.  Stdlib only; the exposition format is Prometheus text 0.0.4.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass, field
import json
import logging
import os
import re
import secrets
import threading
import time
from typing import Any, Callable, Iterable

# ------------------------------------------------------------- metrics (M15)
LATENCY_BUCKETS_S = (0.00005, 0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005,
                     0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
_LABEL_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
OVERFLOW = "__overflow__"


class Metrics:
    """Counters, gauges and histograms with a hard per-metric series cap.

    Label values beyond ``max_series`` collapse into ``__overflow__`` so a
    hostile caller cannot explode cardinality (M15/M18).  Only low-cardinality
    labels (interface, function, status, tenant-class) are ever used; request
    IDs, nonces and raw tenant IDs are never labels.
    """

    def __init__(self, max_series: int = 1000) -> None:
        self.max_series = max_series
        self._lock = threading.Lock()
        self._c: dict[str, dict[tuple, float]] = {}
        self._g: dict[str, dict[tuple, float]] = {}
        self._h: dict[str, dict[tuple, list]] = {}
        self._help: dict[str, tuple[str, str]] = {}

    def describe(self, name: str, kind: str, help_: str) -> None:
        self._help[name] = (kind, help_)

    def _key(self, store: dict, name: str, labels: dict[str, str]) -> tuple:
        for k in labels:
            if not _LABEL_RE.match(k):
                raise ValueError(f"bad label {k}")
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        series = store.setdefault(name, {})
        if key not in series and len(series) >= self.max_series:
            key = tuple((k, OVERFLOW) for k, _ in key)
        return key

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            k = self._key(self._c, name, labels)
            self._c[name][k] = self._c[name].get(k, 0.0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            k = self._key(self._g, name, labels)
            self._g[name][k] = value

    def observe(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            k = self._key(self._h, name, labels)
            h = self._h[name].get(k)
            if h is None:
                h = self._h[name][k] = [[0] * (len(LATENCY_BUCKETS_S) + 1), 0.0, 0]
            h[0][bisect.bisect_left(LATENCY_BUCKETS_S, value)] += 1
            h[1] += value
            h[2] += 1

    def counter(self, name: str, **labels: str) -> float:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        return self._c.get(name, {}).get(key, 0.0)

    def quantile(self, name: str, q: float, **labels: str) -> float:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        h = self._h.get(name, {}).get(key)
        if not h or h[2] == 0:
            return 0.0
        target, run = q * h[2], 0
        for i, n in enumerate(h[0]):
            run += n
            if run >= target:
                return LATENCY_BUCKETS_S[i] if i < len(LATENCY_BUCKETS_S) else float("inf")
        return float("inf")

    @staticmethod
    def _fmt(labels: tuple, extra: Iterable[tuple[str, str]] = ()) -> str:
        items = list(labels) + list(extra)
        if not items:
            return ""
        esc = lambda s: s.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
        return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in items) + "}"

    def render(self) -> str:
        lines: list[str] = []
        with self._lock:
            for kind, store in (("counter", self._c), ("gauge", self._g)):
                for name in sorted(store):
                    k, h = self._help.get(name, (kind, name))
                    lines += [f"# HELP {name} {h}", f"# TYPE {name} {kind}"]
                    for lab, v in sorted(store[name].items()):
                        lines.append(f"{name}{self._fmt(lab)} {v:g}")
            for name in sorted(self._h):
                _, h = self._help.get(name, ("histogram", name))
                lines += [f"# HELP {name} {h}", f"# TYPE {name} histogram"]
                for lab, (buckets, total, count) in sorted(self._h[name].items()):
                    run = 0
                    for i, b in enumerate(LATENCY_BUCKETS_S):
                        run += buckets[i]
                        lines.append(f"{name}_bucket{self._fmt(lab, [('le', repr(b))])} {run}")
                    lines.append(f"{name}_bucket{self._fmt(lab, [('le', '+Inf')])} {count}")
                    lines.append(f"{name}_sum{self._fmt(lab)} {total:.9g}")
                    lines.append(f"{name}_count{self._fmt(lab)} {count}")
        return "\n".join(lines) + "\n"


# ------------------------------------------------------------- logging (M16)
REDACT_KEYS = frozenset({"mac", "secret", "token", "password", "args", "result", "key", "nonce",
                         "authorization", "cookie", "tls_key", "audit_key", "keyring"})
LOG_SCHEMA = "inv61-log/1"


class StructuredLogger:
    """One JSON object per line with a stable schema and mandatory redaction."""

    def __init__(self, node: str, component: str = "INV-61", sink: Callable[[str], None] | None = None,
                 level: str = "INFO", max_line: int = 8192) -> None:
        self.node, self.component = node, component
        self.level = getattr(logging, level)
        self.max_line = max_line
        self._sink = sink or (lambda line: print(line, flush=True))
        self._lock = threading.Lock()
        self.dropped = 0

    @staticmethod
    def redact(fields: dict[str, Any]) -> dict[str, Any]:
        out = {}
        for k, v in fields.items():
            if k.lower() in REDACT_KEYS or any(s in k.lower() for s in ("secret", "passw", "token")):
                out[k] = "<redacted>"
            elif isinstance(v, (bytes, bytearray)):
                out[k] = f"<{len(v)} bytes>"
            elif isinstance(v, dict):
                out[k] = StructuredLogger.redact(v)
            else:
                out[k] = v
        return out

    def log(self, level: str, event: str, **fields: Any) -> None:
        lv = getattr(logging, level)
        if lv < self.level:
            return
        rec = {"schema": LOG_SCHEMA, "ts": round(time.time(), 6), "level": level, "node": self.node,
               "component": self.component, "event": event, **self.redact(fields)}
        line = json.dumps(rec, sort_keys=True, separators=(",", ":"), default=str)
        if len(line) > self.max_line:
            line = json.dumps({"schema": LOG_SCHEMA, "ts": rec["ts"], "level": level, "node": self.node,
                               "component": self.component, "event": event, "truncated": True})
        try:
            with self._lock:
                self._sink(line)
        except Exception:
            self.dropped += 1  # logging must never break the data path

    def info(self, event: str, **f: Any) -> None:
        self.log("INFO", event, **f)

    def warning(self, event: str, **f: Any) -> None:
        self.log("WARNING", event, **f)

    def error(self, event: str, **f: Any) -> None:
        self.log("ERROR", event, **f)


# ------------------------------------------------------------- tracing (M17)
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    sampled: bool

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), self.sampled)

    @staticmethod
    def new(sampled: bool) -> "TraceContext":
        return TraceContext(secrets.token_hex(16), secrets.token_hex(8), sampled)

    @staticmethod
    def parse(tp: str | None) -> "TraceContext | None":
        """Strict W3C traceparent parsing; invalid input -> None (start new trace)."""
        if not isinstance(tp, str) or len(tp) != 55:
            return None
        m = _TP.match(tp)
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return None
        return TraceContext(m.group(1), m.group(2), bool(int(m.group(3), 16) & 1))


@dataclass
class Span:
    name: str
    ctx: TraceContext
    parent_span_id: str | None
    start: float = field(default_factory=time.time)
    end: float | None = None
    attrs: dict[str, Any] = field(default_factory=dict)
    status: str = "unset"


class Tracer:
    """In-process span recorder with a bounded buffer and an export allow-list."""

    ALLOWED_ATTRS = frozenset({"rpc.interface", "rpc.function", "rpc.status", "rpc.version",
                               "net.peer", "tenant.class"})

    def __init__(self, sample_rate: float = 0.1, capacity: int = 10_000) -> None:
        self.sample_rate, self.capacity = sample_rate, capacity
        self.finished: list[Span] = []
        self._lock = threading.Lock()
        self.dropped = 0

    def start(self, name: str, parent: TraceContext | None) -> Span:
        if parent is None:
            ctx = TraceContext.new(secrets.randbelow(10_000) < self.sample_rate * 10_000)
            return Span(name, ctx, None)
        return Span(name, parent.child(), parent.span_id)

    def finish(self, span: Span, status: str, **attrs: Any) -> None:
        span.end, span.status = time.time(), status
        span.attrs.update({k: v for k, v in attrs.items() if k in self.ALLOWED_ATTRS})
        if not span.ctx.sampled:
            return
        with self._lock:
            if len(self.finished) >= self.capacity:
                self.dropped += 1
                return
            self.finished.append(span)


# ------------------------------------------------------------- health (M14)
@dataclass
class DependencyCheck:
    name: str
    probe: Callable[[], bool]
    critical: bool = True


class Health:
    """Liveness (process can make progress) vs readiness (safe to take traffic)."""

    def __init__(self, version: str, stall_after_s: float = 30.0) -> None:
        self.version = version
        self.stall_after_s = stall_after_s
        self.started = time.time()
        self.last_progress = time.monotonic()
        self.checks: list[DependencyCheck] = []
        self.draining = False
        self.disabled = False
        self.config_digest: str | None = None
        self.capabilities: list[str] = []

    def heartbeat(self) -> None:
        self.last_progress = time.monotonic()

    def liveness(self) -> dict[str, Any]:
        stalled = time.monotonic() - self.last_progress > self.stall_after_s
        return {"status": "fail" if stalled else "pass", "stalled": stalled}

    def readiness(self) -> dict[str, Any]:
        deps = {}
        ready = not (self.draining or self.disabled)
        for c in self.checks:
            try:
                ok = bool(c.probe())
            except Exception:
                ok = False
            deps[c.name] = "pass" if ok else ("fail" if c.critical else "warn")
            if c.critical and not ok:
                ready = False
        return {"status": "pass" if ready else "fail", "version": self.version,
                "config_digest": self.config_digest, "draining": self.draining,
                "disabled": self.disabled, "dependencies": deps,
                "capabilities": sorted(self.capabilities),
                "uptime_s": round(time.time() - self.started, 3)}


# ------------------------------------------------------ telemetry policy (M18)
@dataclass(frozen=True)
class TelemetryPolicy:
    """Machine-checkable subset of docs/TELEMETRY_POLICY.md."""
    log_retention_days: int = 30
    audit_retention_days: int = 400
    trace_retention_days: int = 7
    metrics_retention_days: int = 90
    export_allowlist: tuple[str, ...] = ()
    raw_tenant_ids_in_metrics: bool = False

    def exporter_allowed(self, endpoint: str) -> bool:
        return endpoint in self.export_allowlist

    @staticmethod
    def tenant_class(tenant: str, classes: dict[str, str] | None = None) -> str:
        """Map a raw tenant ID to a low-cardinality class label."""
        return (classes or {}).get(tenant, "standard")
