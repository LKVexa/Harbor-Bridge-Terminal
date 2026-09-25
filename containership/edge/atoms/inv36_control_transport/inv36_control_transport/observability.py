"""Observability: metrics, structured logs, trace context, spans, explain view (MC-12).

Everything here is bounded and non-blocking so a telemetry outage can never
stall control traffic (MC-12.026): the exporter buffer drops oldest and counts
drops; label cardinality is capped with an ``other`` overflow bucket
(MC-12.010); logs redact secrets/payloads and rate-limit repeats while keeping
counters (MC-12.013/.014).
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import secrets
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Mapping, TextIO

# Histogram buckets in seconds (MC-12.011): 10us .. 10s
LATENCY_BUCKETS_S = (1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2, 5e-2, 0.1, 0.5, 1.0, 5.0, 10.0)
BYTES_BUCKETS = (64, 256, 1024, 4096, 16384, 65536, 65566)
MAX_LABEL_VALUES = 64
ALLOWED_LABELS = frozenset({"reason", "direction", "operation", "state", "dependency", "priority", "code",
                            "breaker", "outcome", "tenant_class", "stage"})

METRICS_CATALOG: dict[str, tuple[str, str, str]] = {
    # name: (type, unit, help)
    "inv36_frames_total": ("counter", "frames", "frames sealed/opened by direction"),
    "inv36_frame_bytes": ("histogram", "bytes", "wire frame size"),
    "inv36_handshakes_total": ("counter", "handshakes", "handshake outcomes by outcome/code"),
    "inv36_auth_failures_total": ("counter", "frames", "AEAD authentication failures"),
    "inv36_integrity_failures_total": ("counter", "events", "replay/out-of-order/format failures by reason"),
    "inv36_authz_denials_total": ("counter", "operations", "authorization denials by reason"),
    "inv36_reconnects_total": ("counter", "connections", "reconnect attempts"),
    "inv36_queue_depth": ("gauge", "items", "admission queue depth"),
    "inv36_dropped_total": ("counter", "items", "shed/dropped work by priority"),
    "inv36_active_sessions": ("gauge", "sessions", "established sessions"),
    "inv36_latency_seconds": ("histogram", "seconds", "latency by stage (connect/handshake/seal/open/dispatch)"),
    "inv36_breaker_state": ("gauge", "state", "0 closed, 1 half-open, 2 open, by breaker"),
    "inv36_saturation_ratio": ("gauge", "ratio", "queue depth / high-water mark"),
    "inv36_process_rss_bytes": ("gauge", "bytes", "resident set size"),
    "inv36_process_open_fds": ("gauge", "fds", "open file descriptors"),
    "inv36_process_threads": ("gauge", "threads", "live threads"),
    "inv36_process_cpu_seconds": ("gauge", "seconds", "process CPU time"),
    "inv36_telemetry_dropped_total": ("counter", "events", "telemetry events dropped by bounded exporter"),
    "inv36_quarantine_active": ("gauge", "directives", "active quarantine directives"),
}


def _labels_key(labels: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(labels.items()))


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, dict[tuple, float]] = collections.defaultdict(dict)
        self._gauges: dict[str, dict[tuple, float]] = collections.defaultdict(dict)
        self._hist: dict[str, dict[tuple, list]] = collections.defaultdict(dict)
        self._label_values: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
        self._memo: dict[tuple, tuple] = {}

    def _clean(self, name: str, labels: Mapping[str, str] | None) -> tuple:
        # Memoised label normalisation (profiling showed ~9 % of e2e time here); bounded memo.
        memo_key = (name, tuple(sorted((labels or {}).items())))
        hit = self._memo.get(memo_key)
        if hit is not None:
            return hit
        key = self._clean_slow(name, labels)
        if len(self._memo) < 4096:
            self._memo[memo_key] = key
        return key

    def _clean_slow(self, name: str, labels: Mapping[str, str] | None) -> tuple:
        if name not in METRICS_CATALOG:
            raise KeyError(f"metric {name} not in catalog")
        out = {}
        for k, v in (labels or {}).items():
            if k not in ALLOWED_LABELS:
                raise KeyError(f"label {k} not allowed (unbounded cardinality risk)")
            v = str(v)[:48]
            seen = self._label_values[(name, k)]
            if v not in seen:
                if len(seen) >= MAX_LABEL_VALUES:
                    v = "other"
                seen.add(v)
            out[k] = v
        return _labels_key(out)

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            key = self._clean(name, labels)
            self._counters[name][key] = self._counters[name].get(key, 0.0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self._gauges[name][self._clean(name, labels)] = float(value)

    def observe(self, name: str, value: float, **labels: str) -> None:
        buckets = BYTES_BUCKETS if name == "inv36_frame_bytes" else LATENCY_BUCKETS_S
        with self._lock:
            key = self._clean(name, labels)
            h = self._hist[name].setdefault(key, [[0] * (len(buckets) + 1), 0.0, 0, buckets])
            idx = next((i for i, b in enumerate(buckets) if value <= b), len(buckets))
            h[0][idx] += 1
            h[1] += value
            h[2] += 1

    def value(self, name: str, **labels: str) -> float:
        with self._lock:
            key = _labels_key({k: str(v) for k, v in labels.items()})
            return self._counters[name].get(key, self._gauges[name].get(key, 0.0))

    def sample_process(self) -> None:
        try:
            with open("/proc/self/statm") as fh:
                rss = int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
            fds = len(os.listdir("/proc/self/fd"))
        except (OSError, ValueError):
            rss, fds = 0, 0
        self.set("inv36_process_rss_bytes", rss)
        self.set("inv36_process_open_fds", fds)
        self.set("inv36_process_threads", threading.active_count())
        self.set("inv36_process_cpu_seconds", time.process_time())

    def exposition(self) -> str:
        """Prometheus text format 0.0.4."""
        lines: list[str] = []
        with self._lock:
            for name, (typ, unit, help_) in sorted(METRICS_CATALOG.items()):
                lines.append(f"# HELP {name} {help_} ({unit})")
                lines.append(f"# TYPE {name} {typ}")
                if typ == "histogram":
                    for key, (counts, total, n, buckets) in sorted(self._hist[name].items()):
                        lab = ",".join(f'{k}="{v}"' for k, v in key)
                        acc = 0
                        for b, c in zip(list(buckets) + ["+Inf"], counts, strict=True):
                            acc += c
                            sep = "," if lab else ""
                            lines.append(f'{name}_bucket{{{lab}{sep}le="{b}"}} {acc}')
                        lines.append(f"{name}_sum{{{lab}}} {total}")
                        lines.append(f"{name}_count{{{lab}}} {n}")
                else:
                    series = self._counters[name] if typ == "counter" else self._gauges[name]
                    for key, v in sorted(series.items()):
                        lab = ",".join(f'{k}="{v2}"' for k, v2 in key)
                        lines.append(f"{name}{{{lab}}} {v}")
        return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------------
# Structured logging
# ------------------------------------------------------------------------------------------
_REDACT = re.compile(r"(secret|shared|private|plaintext|payload|password|token|key_bytes|credential_raw)", re.I)
LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40, "security": 50}
SECURITY_EVENTS_ALWAYS = {"auth_failure", "integrity_failure", "authz_denied", "quarantine", "killswitch",
                          "handshake_failure", "replay"}


def pseudonymize(value: str, salt: bytes) -> str:
    """Stable per-deployment pseudonym for tenant/workload IDs (MC-12.024)."""
    return "p_" + hashlib.blake2s(value.encode(), key=salt[:32], digest_size=8).hexdigest()


def redact(obj: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "<depth>"
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return f"<bytes:{len(obj)}>"
    if isinstance(obj, Mapping):
        return {str(k)[:64]: ("<redacted>" if _REDACT.search(str(k)) else redact(v, depth + 1))
                for k, v in list(obj.items())[:32]}
    if isinstance(obj, (list, tuple, set)):
        return [redact(v, depth + 1) for v in list(obj)[:32]]
    if isinstance(obj, str):
        return obj[:512]
    return obj


@dataclass
class StructuredLogger:
    component: str = "inv36-control-transport"
    version: str = ""
    node: str = ""
    build_digest: str = ""
    level: str = "info"
    stream: TextIO = field(default_factory=lambda: sys.stderr)
    rate_window_s: float = 10.0
    rate_max: int = 5
    pseudonym_salt: bytes = field(default_factory=lambda: secrets.token_bytes(32), repr=False)
    clock: Callable[[], float] = time.time
    mono: Callable[[], float] = time.monotonic
    suppressed: dict[str, int] = field(default_factory=lambda: collections.defaultdict(int), init=False)
    _windows: dict[str, tuple[float, int]] = field(default_factory=dict, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    ring: Deque[dict] = field(default_factory=lambda: collections.deque(maxlen=512), init=False, repr=False)

    def log(self, severity: str, event: str, *, reason: str = "", tenant: str = "", workload: str = "",
            session: str = "", operation_id: str = "", duration_s: float | None = None, **fields: Any) -> dict | None:
        security = event in SECURITY_EVENTS_ALWAYS or severity == "security"
        if not security and LEVELS.get(severity, 20) < LEVELS.get(self.level, 20):
            return None
        key = f"{severity}|{event}|{reason}"
        with self._lock:
            start, n = self._windows.get(key, (self.mono(), 0))
            if self.mono() - start > self.rate_window_s:
                if self.suppressed.get(key):
                    fields["suppressed_repeats"] = self.suppressed.pop(key)
                start, n = self.mono(), 0
            n += 1
            self._windows[key] = (start, n)
            if len(self._windows) > 4096:
                self._windows.clear()
            if n > self.rate_max:
                self.suppressed[key] += 1
                return None
        rec = {
            "ts": round(self.clock(), 6), "mono": round(self.mono(), 6), "severity": severity,
            "component": self.component, "version": self.version, "build": self.build_digest, "node": self.node,
            "event": event, "reason": reason,
            "tenant": pseudonymize(tenant, self.pseudonym_salt) if tenant else "",
            "workload": pseudonymize(workload, self.pseudonym_salt) if workload else "",
            "session": session, "operation_id": operation_id,
        }
        if duration_s is not None:
            rec["duration_ms"] = round(duration_s * 1000, 3)
        rec["fields"] = redact(fields)
        line = json.dumps(rec, sort_keys=True, ensure_ascii=True, default=str)
        self.ring.append(rec)
        try:
            self.stream.write(line + "\n")
        except (OSError, ValueError):
            pass  # logging must never break control traffic
        return rec


# ------------------------------------------------------------------------------------------
# Tracing
# ------------------------------------------------------------------------------------------
_TP = re.compile(r"00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})\Z")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    flags: str = "01"

    @classmethod
    def new(cls) -> "TraceContext":
        return cls(secrets.token_hex(16), secrets.token_hex(8))

    @classmethod
    def parse(cls, header: str) -> "TraceContext | None":
        m = _TP.match(header or "")
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return None
        return cls(m.group(1), m.group(2), m.group(3))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), self.flags)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"


def accept_trace(header: str, *, trusted_peer: bool) -> TraceContext:
    """Sanitize trace context at a trust boundary (MC-12.017).

    Context from an authenticated in-estate peer is continued; anything else
    starts a new trace so external callers cannot join or poison internal traces.
    """
    parsed = TraceContext.parse(header) if trusted_peer else None
    return parsed.child() if parsed else TraceContext.new()


@dataclass
class Tracer:
    capacity: int = 1024
    spans: Deque[dict] = field(default_factory=lambda: collections.deque(maxlen=1024), init=False)
    metrics: MetricsRegistry | None = None

    def span(self, name: str, ctx: TraceContext, **attrs: Any):
        tracer = self

        class _Span:
            def __enter__(self_inner):
                self_inner.t0 = time.perf_counter()
                self_inner.ctx = ctx.child()
                return self_inner

            def __exit__(self_inner, et, ev, tb):
                dur = time.perf_counter() - self_inner.t0
                tracer.spans.append({"name": name, "trace_id": ctx.trace_id, "span_id": self_inner.ctx.span_id,
                                     "parent": ctx.span_id, "duration_s": dur, "status": "error" if et else "ok",
                                     "attrs": redact(attrs)})
                if tracer.metrics is not None:
                    tracer.metrics.observe("inv36_latency_seconds", dur, stage=name)
                return False

        return _Span()


SPAN_NAMES = ("connect", "handshake", "policy", "key_service", "seal", "socket_write", "socket_read", "open",
              "dispatch")


@dataclass
class BoundedExporter:
    """Never-blocking telemetry buffer; drops oldest when the backend is down."""

    capacity: int = 4096
    send: Callable[[list[dict]], None] | None = None
    metrics: MetricsRegistry | None = None
    queue: Deque[dict] = field(default_factory=collections.deque, init=False)
    dropped: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def offer(self, event: dict) -> None:
        with self._lock:
            if len(self.queue) >= self.capacity:
                self.queue.popleft()
                self.dropped += 1
                if self.metrics:
                    self.metrics.inc("inv36_telemetry_dropped_total")
            self.queue.append(event)

    def flush(self, max_batch: int = 512) -> int:
        with self._lock:
            batch = [self.queue.popleft() for _ in range(min(max_batch, len(self.queue)))]
        if not batch or self.send is None:
            return 0
        try:
            self.send(batch)
            return len(batch)
        except Exception:  # noqa: BLE001 - backend failure must not propagate
            with self._lock:
                for ev in reversed(batch):
                    if len(self.queue) < self.capacity:
                        self.queue.appendleft(ev)
                    else:
                        self.dropped += 1
            return 0


TELEMETRY_POLICY = {
    "retention": {"metrics": {"prod": "400d (downsampled after 30d)", "nonprod": "30d"},
                  "logs": {"prod": "30d", "nonprod": "7d"}, "traces": {"prod": "7d", "nonprod": "3d"},
                  "security_audit": "see audit_log.RETENTION_POLICY"},
    "sampling": {"traces": "1% head sampling; 100% for errors, auth/integrity failures and quarantine",
                 "logs": "no sampling for severity>=warning or security events; repeats rate-limited with counts"},
    "privacy": "tenant/workload IDs pseudonymized with a per-deployment salt; payloads and keys never exported",
    "export": {"endpoint": "config.telemetry_endpoint (https required in prod/stage)",
               "auth": "mTLS workload identity", "buffer": "config.telemetry_buffer events, drop-oldest",
               "backend_down": "control traffic continues; drops counted in inv36_telemetry_dropped_total"},
}
