"""MC45 / MC46 / MC47 / MC48 — metrics, structured logs, tracing and health.

Stdlib-only.  Metrics render in Prometheus text exposition format with bounded label
cardinality; logs are JSON lines with secret redaction; spans propagate W3C
``traceparent``; health/readiness are aggregated from named checks and can be served
over HTTP with :func:`serve_http`.
"""
from __future__ import annotations

import contextvars
import json
import logging
import re
import secrets
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Iterator

_SECRET_KEY_RE = re.compile(r"(pass(word)?|secret|token|authorization|api[_-]?key|private[_-]?key|credential|cookie)", re.I)
_SECRET_VAL_RE = re.compile(r"(Bearer\s+[A-Za-z0-9._~+/=-]+|Basic\s+[A-Za-z0-9+/=]+|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
REDACTED = "[REDACTED]"


def redact(obj):
    """Recursively redact secret-named keys and secret-shaped values."""
    if isinstance(obj, dict):
        return {k: (REDACTED if isinstance(k, str) and _SECRET_KEY_RE.search(k) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in obj]
    if isinstance(obj, str):
        return _SECRET_VAL_RE.sub(REDACTED, obj)
    return obj


# --- MC45 metrics ------------------------------------------------------------------
class CardinalityExceeded(ValueError):
    pass


@dataclass
class _Metric:
    name: str
    kind: str
    help: str
    labels: tuple[str, ...]
    buckets: tuple[float, ...] = ()
    series: dict = field(default_factory=dict)


class Metrics:
    _NAME_RE = re.compile(r"[a-zA-Z_:][a-zA-Z0-9_:]*\Z")

    def __init__(self, max_series_per_metric: int = 1000) -> None:
        self._m: dict[str, _Metric] = {}
        self._lock = threading.Lock()
        self.max_series = max_series_per_metric

    def _reg(self, name, kind, help_, labels, buckets=()):
        if not self._NAME_RE.fullmatch(name):
            raise ValueError(f"bad metric name {name}")
        with self._lock:
            m = self._m.get(name)
            if m is None:
                m = self._m[name] = _Metric(name, kind, help_, tuple(labels), tuple(buckets))
            elif m.kind != kind or m.labels != tuple(labels):
                raise ValueError(f"metric {name} re-registered differently")
            return m

    def counter(self, name, help_, labels=()):
        self._reg(name, "counter", help_, labels)
        return lambda value=1.0, **lv: self._add(name, lv, value)

    def gauge(self, name, help_, labels=()):
        self._reg(name, "gauge", help_, labels)
        return lambda value, **lv: self._set(name, lv, value)

    def histogram(self, name, help_, labels=(), buckets=(0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10)):
        self._reg(name, "histogram", help_, labels, buckets)
        return lambda value, **lv: self._observe(name, lv, value)

    def _key(self, m, lv):
        if set(lv) != set(m.labels):
            raise ValueError(f"{m.name}: labels must be exactly {m.labels}")
        key = tuple(str(lv[k]) for k in m.labels)
        if key not in m.series and len(m.series) >= self.max_series:
            raise CardinalityExceeded(f"{m.name}: label cardinality limit reached")
        return key

    def _add(self, name, lv, value):
        if value < 0:
            raise ValueError("counters only increase")
        with self._lock:
            m = self._m[name]
            k = self._key(m, lv)
            m.series[k] = m.series.get(k, 0.0) + value

    def _set(self, name, lv, value):
        with self._lock:
            m = self._m[name]
            m.series[self._key(m, lv)] = float(value)

    def _observe(self, name, lv, value):
        with self._lock:
            m = self._m[name]
            k = self._key(m, lv)
            s = m.series.setdefault(k, {"b": [0] * len(m.buckets), "sum": 0.0, "count": 0})
            for i, b in enumerate(m.buckets):
                if value <= b:
                    s["b"][i] += 1
            s["sum"] += value
            s["count"] += 1

    @staticmethod
    def _fmt_labels(names, vals, extra=()):
        pairs = list(zip(names, vals)) + list(extra)
        if not pairs:
            return ""
        esc = lambda v: v.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
        return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in pairs) + "}"

    def render(self) -> str:
        out = []
        with self._lock:
            for m in sorted(self._m.values(), key=lambda x: x.name):
                out.append(f"# HELP {m.name} {m.help}")
                out.append(f"# TYPE {m.name} {m.kind}")
                for k, v in sorted(m.series.items()):
                    if m.kind == "histogram":
                        for b, c in zip(m.buckets, v["b"]):
                            out.append(f"{m.name}_bucket{self._fmt_labels(m.labels, k, [('le', repr(float(b)))])} {c}")
                        out.append(f"{m.name}_bucket{self._fmt_labels(m.labels, k, [('le', '+Inf')])} {v['count']}")
                        out.append(f"{m.name}_sum{self._fmt_labels(m.labels, k)} {v['sum']}")
                        out.append(f"{m.name}_count{self._fmt_labels(m.labels, k)} {v['count']}")
                    else:
                        out.append(f"{m.name}{self._fmt_labels(m.labels, k)} {v}")
        return "\n".join(out) + "\n"


# --- MC47 tracing -------------------------------------------------------------------
_current_span: contextvars.ContextVar["Span | None"] = contextvars.ContextVar("span", default=None)
_TRACEPARENT_RE = re.compile(r"00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})\Z")


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    start: float
    end: float | None = None
    attrs: dict = field(default_factory=dict)
    status: str = "ok"

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-01"


class Tracer:
    def __init__(self, exporter: Callable[[Span], None] | None = None, max_buffer: int = 10000) -> None:
        self.finished: list[Span] = []
        self._exporter = exporter
        self._max = max_buffer
        self._lock = threading.Lock()

    @contextmanager
    def span(self, name: str, *, traceparent: str | None = None, **attrs) -> Iterator[Span]:
        parent = _current_span.get()
        trace_id, parent_id = None, None
        if traceparent and (m := _TRACEPARENT_RE.fullmatch(traceparent)):
            trace_id, parent_id = m.group(1), m.group(2)
        elif parent:
            trace_id, parent_id = parent.trace_id, parent.span_id
        sp = Span(name, trace_id or secrets.token_hex(16), secrets.token_hex(8), parent_id, time.time(), attrs=redact(attrs))
        tok = _current_span.set(sp)
        try:
            yield sp
        except BaseException as exc:
            sp.status = f"error:{type(exc).__name__}"
            raise
        finally:
            sp.end = time.time()
            _current_span.reset(tok)
            with self._lock:
                self.finished.append(sp)
                del self.finished[:-self._max]
            if self._exporter:
                self._exporter(sp)


def current_trace_id() -> str | None:
    s = _current_span.get()
    return s.trace_id if s else None


# --- MC46 structured logging --------------------------------------------------------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": round(record.created, 6), "level": record.levelname, "logger": record.name,
                   "msg": redact(record.getMessage())}
        tid = current_trace_id()
        if tid:
            payload["trace_id"] = tid
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload["fields"] = redact(extra)
        if record.exc_info:
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, sort_keys=True, default=str)


def get_logger(name: str = "inv02", level: int = logging.INFO) -> logging.Logger:
    log = logging.getLogger(name)
    if not any(isinstance(h.formatter, JsonFormatter) for h in log.handlers):
        h = logging.StreamHandler()
        h.setFormatter(JsonFormatter())
        log.addHandler(h)
    log.setLevel(level)
    log.propagate = False
    return log


# --- MC48 health / readiness -----------------------------------------------------------
class Health:
    """``liveness`` = process can make progress; ``readiness`` = all readiness checks pass."""

    def __init__(self) -> None:
        self._checks: dict[str, tuple[Callable[[], bool], bool]] = {}

    def add(self, name: str, fn: Callable[[], bool], *, readiness: bool = True) -> None:
        self._checks[name] = (fn, readiness)

    def evaluate(self) -> dict:
        results = {}
        for name, (fn, _) in self._checks.items():
            try:
                results[name] = bool(fn())
            except Exception as exc:  # a failing check is unhealthy, not a crash
                results[name] = False
                results[f"{name}.error"] = type(exc).__name__
        ready = all(results.get(n, False) for n, (_, r) in self._checks.items() if r)
        live = all(results.get(n, False) for n, (_, r) in self._checks.items() if not r)
        return {"live": live, "ready": ready, "checks": results}


def serve_http(health: Health, metrics: Metrics, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """Serve ``/healthz``, ``/readyz`` and ``/metrics``.  Binds loopback by default."""

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/metrics":
                body, code, ct = metrics.render().encode(), 200, "text/plain; version=0.0.4"
            elif self.path in ("/healthz", "/readyz"):
                ev = health.evaluate()
                ok = ev["live"] if self.path == "/healthz" else ev["ready"]
                body, code, ct = json.dumps(ev).encode(), 200 if ok else 503, "application/json"
            else:
                body, code, ct = b"not found", 404, "text/plain"
            self.send_response(code)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer((host, port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
