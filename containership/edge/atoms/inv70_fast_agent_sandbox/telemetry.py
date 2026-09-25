"""Observability for INV-70 (C072 metrics, C073 logs, C074 traces, C075 diagnostics, C079 policy).

Dependency-free.  Every signal is bounded: label sets are allow-listed, label
values are length-capped, the log/diagnostic buffers are ring buffers, and
payload-like fields are redacted before they are ever stored.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from collections import deque

# ---------------------------------------------------------------- C079 policy
TELEMETRY_POLICY = {
    "policy_version": "1",
    "metrics": {"retention_days": 30, "sampling": "none (aggregated counters/histograms)",
                "allowed_labels": ["reason", "status", "tenant", "profile", "backend", "phase"]},
    "logs": {"retention_days": 14, "sampling": "all audit-relevant events; debug off in prod",
             "buffer_events": 10_000},
    "traces": {"retention_days": 7, "sampling": "parent-based; default ratio 0.1; errors always kept"},
    "diagnostics": {"retention_days": 3, "sampling": "opt-in per tenant with TTL, ratio-capped",
                    "buffer_events": 2_000},
    "privacy": {"never_exported": ["program operands", "host-call arguments", "host-call results",
                                    "secrets", "tokens", "exception messages"],
                "tenant_ids": "exported only as salted SHA-256 prefix outside the tenant's own view"},
    "export": {"format": "JSON lines / Prometheus text exposition", "transport": "pull by the "
               "GAP-09 observability collector; no push from the sandbox"},
}

MAX_LABEL_VALUE = 64
_SECRETISH = re.compile(r"(?i)(secret|token|password|passwd|key|credential|authorization)")


def _clip(v: object) -> str:
    s = str(v)
    return s if len(s) <= MAX_LABEL_VALUE else s[:MAX_LABEL_VALUE]


def tenant_pseudonym(tenant: str, salt: str = "inv70") -> str:
    return hashlib.sha256(f"{salt}:{tenant}".encode()).hexdigest()[:12]


def redact(obj: object, depth: int = 0) -> object:
    """Return a JSON-safe copy with secret-looking keys and payload fields removed."""
    if depth > 4:
        return "<truncated>"
    if isinstance(obj, dict):
        out = {}
        for k, v in list(obj.items())[:64]:
            ks = _clip(k)
            if _SECRETISH.search(ks) or ks in ("args", "argument", "result_value", "program", "payload"):
                out[ks] = "<redacted>"
            else:
                out[ks] = redact(v, depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        return [redact(v, depth + 1) for v in list(obj)[:64]]
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    return _clip(obj) if not _SECRETISH.search(str(obj)[:256]) else "<redacted>"


# ---------------------------------------------------------------- C072 metrics
class Metrics:
    """Counter + histogram registry with an allow-listed, bounded label space."""

    BUCKETS = (1, 5, 10, 50, 100, 500, 1_000, 5_000, 10_000, 100_000)
    MAX_SERIES = 5_000

    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict[tuple, int] = {}
        self.hists: dict[tuple, list] = {}
        self.dropped_series = 0

    def _key(self, name: str, labels: dict) -> tuple:
        allowed = TELEMETRY_POLICY["metrics"]["allowed_labels"]
        bad = [k for k in labels if k not in allowed]
        if bad:
            raise ValueError(f"label not allow-listed: {bad[0]}")
        return (name,) + tuple(sorted((k, _clip(v)) for k, v in labels.items()))

    def inc(self, name: str, n: int = 1, **labels) -> None:
        key = self._key(name, labels)
        with self._lock:
            if key not in self.counters and len(self.counters) + len(self.hists) >= self.MAX_SERIES:
                self.dropped_series += 1
                return
            self.counters[key] = self.counters.get(key, 0) + n

    def observe(self, name: str, value: float, **labels) -> None:
        key = self._key(name, labels)
        with self._lock:
            h = self.hists.get(key)
            if h is None:
                if len(self.counters) + len(self.hists) >= self.MAX_SERIES:
                    self.dropped_series += 1
                    return
                h = self.hists[key] = [0] * (len(self.BUCKETS) + 1) + [0.0, 0]
            idx = next((i for i, b in enumerate(self.BUCKETS) if value <= b), len(self.BUCKETS))
            h[idx] += 1
            h[-2] += value
            h[-1] += 1

    def value(self, name: str, **labels) -> int:
        return self.counters.get(self._key(name, labels), 0)

    def exposition(self) -> str:
        """Prometheus text exposition."""
        def fmt(key):
            name, *lbl = key
            inner = ",".join(f'{k}="{v}"' for k, v in lbl)
            return name, (f"{{{inner}}}" if inner else "")
        lines = []
        with self._lock:
            for key, v in sorted(self.counters.items()):
                n, l = fmt(key)
                lines.append(f"inv70_{n}_total{l} {v}")
            for key, h in sorted(self.hists.items()):
                n, l = fmt(key)
                cum = 0
                for i, b in enumerate(self.BUCKETS):
                    cum += h[i]
                    le = f'le="{b}"'
                    lines.append(f"inv70_{n}_bucket{{{(l[1:-1] + ',') if l else ''}{le}}} {cum}")
                lines.append(f"inv70_{n}_sum{l} {h[-2]}")
                lines.append(f"inv70_{n}_count{l} {h[-1]}")
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- C074 traces
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


class TraceContext:
    """W3C trace-context (traceparent) parse/propagate; malformed input starts a new trace."""

    def __init__(self, trace_id: str, span_id: str, sampled: bool, parent_span_id: str | None = None):
        self.trace_id, self.span_id, self.sampled, self.parent_span_id = trace_id, span_id, sampled, parent_span_id

    @classmethod
    def from_header(cls, header: str | None, sample_ratio: float = 0.1) -> "TraceContext":
        m = _TRACEPARENT.match(header or "")
        if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
            return cls(m.group(1), os.urandom(8).hex(), bool(int(m.group(3), 16) & 1), m.group(2))
        sampled = int.from_bytes(os.urandom(2), "big") / 65535 < sample_ratio
        return cls(os.urandom(16).hex(), os.urandom(8).hex(), sampled)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, os.urandom(8).hex(), self.sampled, self.span_id)


# ---------------------------------------------------------------- C073 logs
class StructuredLog:
    """JSON-lines logger; every record carries run_id/trace_id/tenant correlation fields."""

    REQUIRED = ("ts", "level", "event", "run_id", "trace_id", "component", "version")

    def __init__(self, version: str, capacity: int = 10_000, sink=None):
        self.version = version
        self.records: deque = deque(maxlen=capacity)
        self.sink = sink

    def emit(self, level: str, event: str, *, run_id: str, trace_id: str, **fields) -> dict:
        rec = {"ts": round(time.time(), 6), "level": level, "event": event, "run_id": run_id,
               "trace_id": trace_id, "component": "INV-70", "version": self.version}
        rec.update(redact(fields))
        self.records.append(rec)
        if self.sink is not None:
            self.sink.write(json.dumps(rec, sort_keys=True) + "\n")
        return rec


# ---------------------------------------------------------------- C075 diagnostics
class DiagnosticChannel:
    """Opt-in, TTL-bounded, ratio-capped, redacted high-cardinality channel.

    Diagnostics are only captured for tenants with an unexpired enablement grant;
    per-run detail never flows into the metrics label space.
    """

    def __init__(self, capacity: int = 2_000, max_per_minute: int = 600, clock=time.monotonic):
        self.buffer: deque = deque(maxlen=capacity)
        self.grants: dict[str, float] = {}
        self.max_per_minute = max_per_minute
        self._window = (0.0, 0)
        self.clock = clock
        self.suppressed = 0

    def enable(self, tenant: str, ttl_s: float) -> None:
        if not 0 < ttl_s <= 3600:
            raise ValueError("diagnostic grant TTL must be in (0, 3600] seconds")
        self.grants[tenant] = self.clock() + ttl_s

    def record(self, tenant: str, **detail) -> bool:
        now = self.clock()
        if self.grants.get(tenant, 0) <= now:
            return False
        start, n = self._window
        if now - start >= 60:
            start, n = now, 0
        if n >= self.max_per_minute:
            self.suppressed += 1
            self._window = (start, n)
            return False
        self._window = (start, n + 1)
        self.buffer.append({"t": now, "tenant": tenant_pseudonym(tenant), **redact(detail)})
        return True
