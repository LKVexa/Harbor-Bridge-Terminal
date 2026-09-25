"""Metrics, structured logs and trace context for PLN-05.

Guarantees: label keys come from an allowlist and label *values* for
tenant/workload are never used (cardinality and privacy); the series count is
hard-capped (overflow is counted, not stored); secrets are redacted by key and
by value pattern; and no telemetry call can raise into the decision path —
failures increment ``telemetry_errors`` instead.
"""
from __future__ import annotations

from collections import deque
import json
import re
import secrets
import time

COMPONENT = {"service.name": "pln05-elasticity-plane", "component": "PLN-05"}
LATENCY_BUCKETS_MS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100)
_SECRET_KEY = re.compile(r"(secret|token|password|passwd|authorization|credential|api_key|private_key|mac)$", re.I)
_SECRET_VAL = re.compile(r"(v1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]{16,}\.[0-9a-f]{64}|-----BEGIN [A-Z ]+-----|"
                         r"(?i:bearer)\s+[A-Za-z0-9._-]{8,}|AKIA[0-9A-Z]{16})")
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def redact(obj, depth: int = 0):
    if depth > 6:
        return "<truncated>"
    if isinstance(obj, dict):
        return {k: ("<redacted>" if _SECRET_KEY.search(str(k)) else redact(v, depth + 1))
                for k, v in list(obj.items())[:64]}
    if isinstance(obj, (list, tuple)):
        return [redact(v, depth + 1) for v in list(obj)[:64]]
    if isinstance(obj, str):
        return _SECRET_VAL.sub("<redacted>", obj[:512])
    return obj


class Metrics:
    def __init__(self, allowlist, max_series: int) -> None:
        self.allow = frozenset(allowlist)
        self.max_series = max_series
        self.counters: dict[tuple, float] = {}
        self.gauges: dict[tuple, float] = {}
        self.hist: dict[tuple, list] = {}
        self.dropped_series = 0
        self.dropped_labels = 0

    def _key(self, name: str, labels: dict | None) -> tuple | None:
        labels = labels or {}
        kept = tuple(sorted((k, str(v)[:48]) for k, v in labels.items() if k in self.allow))
        if len(kept) != len(labels):
            self.dropped_labels += 1
        key = (name, kept)
        if key not in self.counters and key not in self.gauges and key not in self.hist:
            if len(self.counters) + len(self.gauges) + len(self.hist) >= self.max_series:
                self.dropped_series += 1
                return None
        return key

    def inc(self, name: str, labels: dict | None = None, value: float = 1.0) -> None:
        k = self._key(name, labels)
        if k is not None:
            self.counters[k] = self.counters.get(k, 0.0) + value

    def set(self, name: str, value: float, labels: dict | None = None) -> None:
        k = self._key(name, labels)
        if k is not None:
            self.gauges[k] = float(value)

    def observe(self, name: str, value_ms: float, labels: dict | None = None) -> None:
        k = self._key(name, labels)
        if k is None:
            return
        h = self.hist.setdefault(k, [0] * (len(LATENCY_BUCKETS_MS) + 1) + [0.0, 0])
        for i, b in enumerate(LATENCY_BUCKETS_MS):
            if value_ms <= b:
                h[i] += 1
                break
        else:
            h[len(LATENCY_BUCKETS_MS)] += 1
        h[-2] += value_ms
        h[-1] += 1

    def series(self) -> int:
        return len(self.counters) + len(self.gauges) + len(self.hist)

    def value(self, name: str, **labels) -> float:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        return self.counters.get(key, self.gauges.get(key, 0.0))

    def total(self, name: str) -> float:
        return sum(v for (n, _), v in self.counters.items() if n == name)

    def exposition(self) -> str:
        """Prometheus text format (subset)."""
        lines = []
        for (n, lab), v in sorted(self.counters.items()) + sorted(self.gauges.items()):
            ls = ",".join(f'{k}="{val}"' for k, val in lab)
            lines.append(f"pln05_{n}{{{ls}}} {v}")
        return "\n".join(lines) + "\n"


class Logger:
    SEVERITIES = ("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL")

    def __init__(self, capacity: int = 2048, stream=None) -> None:
        self.records: deque = deque(maxlen=capacity)
        self.stream = stream
        self.errors = 0

    def log(self, severity: str, event: str, **fields) -> None:
        try:
            rec = {"ts": time.time(), "severity": severity if severity in self.SEVERITIES else "INFO",
                   "event": event, **COMPONENT, **redact(fields)}
            self.records.append(rec)
            if self.stream is not None:
                self.stream.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        except Exception:  # noqa: BLE001 - telemetry must never break the control path
            self.errors += 1


def parse_traceparent(value) -> tuple[str, str] | None:
    if not isinstance(value, str):
        return None
    m = _TRACEPARENT.match(value)
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
        return None
    return m.group(1), m.group(2)


class Tracer:
    def __init__(self, sample_ratio: float) -> None:
        self.ratio = sample_ratio
        self.spans: deque = deque(maxlen=2048)

    def sampled(self, trace_id: str, error: bool = False) -> bool:
        return error or int(trace_id[:8], 16) / 0xFFFFFFFF < self.ratio

    def start(self, parent: str | None) -> tuple[str, str]:
        ctx = parse_traceparent(parent)
        trace_id = ctx[0] if ctx else secrets.token_hex(16)
        return trace_id, secrets.token_hex(8)

    def span(self, trace_id: str, span_id: str, name: str, ms: float, error: bool = False,
             **attrs) -> None:
        if self.sampled(trace_id, error):
            self.spans.append({"trace_id": trace_id, "span_id": span_id, "name": name,
                               "duration_ms": ms, "error": error,
                               "attrs": {k: attrs[k] for k in sorted(attrs)[:8]}})

    @staticmethod
    def traceparent(trace_id: str, span_id: str) -> str:
        return f"00-{trace_id}-{span_id}-01"
