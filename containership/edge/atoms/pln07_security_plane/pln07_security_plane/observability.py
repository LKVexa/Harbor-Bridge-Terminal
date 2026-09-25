"""Audit pipeline, structured logs, metrics, tracing and redaction
(MC-40 .. MC-45, MC-20, MC-43, MC-47).

Everything is stdlib and in-process; exporters are pluggable callables so a
deployment can ship to OpenTelemetry/Prometheus/SIEM without changing callers.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------- redaction --
SECRET_KEYS = re.compile(r"(secret|token|password|passwd|key|signature|sig|credential)", re.I)
MAX_LABEL_VALUES = 64  # cardinality guard per metric label


def redact(value: Any, _depth: int = 0) -> Any:
    """Recursively redact secret-looking keys; bound depth and string size."""
    if _depth > 6:
        return "<truncated>"
    if isinstance(value, dict):
        return {k: ("<redacted>" if SECRET_KEYS.search(str(k)) else redact(v, _depth + 1))
                for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact(v, _depth + 1) for v in list(value)[:64]]
    if isinstance(value, (bytes, bytearray)):
        return "<bytes>"
    if isinstance(value, str) and len(value) > 512:
        return value[:512] + "...<truncated>"
    return value


def pseudonymize(value: str, salt: bytes = b"pln07") -> str:
    """Stable short pseudonym for high-cardinality identifiers in diagnostics."""
    return hashlib.sha256(salt + value.encode()).hexdigest()[:12]


# ------------------------------------------------------------------ tracing --
_trace: contextvars.ContextVar[dict | None] = contextvars.ContextVar("pln07_trace", default=None)


def current_context() -> dict:
    ctx = _trace.get()
    if ctx is None:
        ctx = {"trace_id": secrets.token_hex(16), "span_id": secrets.token_hex(8)}
        _trace.set(ctx)
    return ctx


def from_traceparent(header: str | None) -> dict:
    """Accept a W3C ``traceparent`` header; malformed input starts a new trace."""
    m = re.fullmatch(r"00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}", header or "")
    ctx = {"trace_id": m.group(1), "parent_span": m.group(2)} if m else {"trace_id": secrets.token_hex(16)}
    ctx["span_id"] = secrets.token_hex(8)
    _trace.set(ctx)
    return ctx


def traceparent() -> str:
    c = current_context()
    return f"00-{c['trace_id']}-{c['span_id']}-01"


class span:
    """Context manager recording a timed span into ``Telemetry.spans``."""

    def __init__(self, telemetry: "Telemetry", name: str):
        self.t, self.name = telemetry, name

    def __enter__(self):
        parent = current_context()
        self.token = _trace.set({"trace_id": parent["trace_id"], "span_id": secrets.token_hex(8),
                                 "parent_span": parent["span_id"]})
        self.start = time.perf_counter_ns()
        return self

    def __exit__(self, et, ev, tb):
        ctx = _trace.get()
        self.t.record_span({**ctx, "name": self.name,
                            "duration_ns": time.perf_counter_ns() - self.start,
                            "error": et.__name__ if et else None})
        _trace.reset(self.token)
        return False


# ------------------------------------------------------------------ metrics --
@dataclass
class Metrics:
    counters: dict[tuple, int] = field(default_factory=dict)
    histograms: dict[str, list[int]] = field(default_factory=dict)
    _label_values: dict[str, set] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _label(self, key: str, value: str) -> str:
        seen = self._label_values.setdefault(key, set())
        if value in seen or len(seen) < MAX_LABEL_VALUES:
            seen.add(value)
            return value
        return "__overflow__"

    def inc(self, name: str, **labels: str) -> None:
        with self._lock:
            key = (name, tuple(sorted((k, self._label(k, str(v))) for k, v in labels.items())))
            self.counters[key] = self.counters.get(key, 0) + 1

    def observe(self, name: str, value_ns: int) -> None:
        with self._lock:
            h = self.histograms.setdefault(name, [])
            h.append(value_ns)
            if len(h) > 10000:  # bounded reservoir
                del h[: len(h) - 10000]

    def percentile(self, name: str, p: float) -> int | None:
        data = sorted(self.histograms.get(name, []))
        if not data:
            return None
        return data[min(len(data) - 1, int(round(p / 100 * (len(data) - 1))))]

    def prometheus(self) -> str:
        out = []
        with self._lock:
            for (name, labels), v in sorted(self.counters.items()):
                lbl = ",".join(f'{k}="{val}"' for k, val in labels)
                out.append(f"{name}{{{lbl}}} {v}")
            for name in sorted(self.histograms):
                for p in (50, 95, 99):
                    out.append(f'{name}_ns{{quantile="0.{p}"}} {self.percentile(name, p)}')
        return "\n".join(out) + "\n"


# -------------------------------------------------------------- audit chain --
@dataclass
class AuditLog:
    """Tamper-evident, hash-chained decision/audit events (MC-44)."""

    sink: Callable[[str], None] | None = None
    events: list[dict] = field(default_factory=list)
    _head: str = "0" * 64
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def emit(self, action: str, outcome: str, code: str, **fields: Any) -> dict:
        ctx = current_context()
        with self._lock:
            body = {"type": "PK_AUDIT/1", "seq": len(self.events) + 1, "ts": int(time.time()),
                    "action": action, "outcome": outcome, "code": code,
                    "trace_id": ctx["trace_id"], "span_id": ctx["span_id"],
                    "fields": redact(fields), "prev": self._head}
            body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            self._head = body["hash"]
            self.events.append(body)
        if self.sink:
            self.sink(json.dumps(body, sort_keys=True))
        return body

    def verify(self) -> bool:
        head = "0" * 64
        for ev in self.events:
            b = {k: v for k, v in ev.items() if k != "hash"}
            if b["prev"] != head or hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest() != ev["hash"]:
                return False
            head = ev["hash"]
        return True


@dataclass
class Telemetry:
    metrics: Metrics = field(default_factory=Metrics)
    audit: AuditLog = field(default_factory=AuditLog)
    log_sink: Callable[[str], None] | None = None
    spans: list[dict] = field(default_factory=list)
    sample_rate: float = 1.0  # MC-47: span sampling
    max_spans: int = 5000

    def log(self, level: str, msg: str, **fields: Any) -> dict:
        ctx = current_context()
        rec = {"ts": time.time(), "level": level, "component": "PLN-07", "msg": msg,
               "trace_id": ctx["trace_id"], "span_id": ctx["span_id"], **redact(fields)}
        if self.log_sink:
            self.log_sink(json.dumps(rec, sort_keys=True, default=str))
        return rec

    def record_span(self, s: dict) -> None:
        if self.sample_rate < 1.0 and int(s["trace_id"][:8], 16) / 0xFFFFFFFF > self.sample_rate:
            return
        self.spans.append(s)
        if len(self.spans) > self.max_spans:
            del self.spans[: len(self.spans) - self.max_spans]
