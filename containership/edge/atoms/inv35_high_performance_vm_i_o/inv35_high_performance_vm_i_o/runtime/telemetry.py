"""Metrics, structured logs, trace context, decision reasons and explain view.

Covers INV-35-C072 (metrics), C073 (structured logs with stable correlation
identifiers), C074 (W3C trace-context propagation), C075 (cardinality caps and
redaction), C076 (structured reason records) and C077 (operator explain view).
Everything is dependency-free; exporters (Prometheus text, JSON lines) are
formats, not network clients.
"""
from __future__ import annotations

from bisect import bisect_left
from collections import deque
from dataclasses import dataclass, field
import json
import re
import secrets
from threading import RLock
import time

from .security import redact

MAX_SERIES_PER_METRIC = 256
LATENCY_BUCKETS_US = (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 5000, 10000)
OVERFLOW_LABEL = "__overflow__"


class Metrics:
    def __init__(self) -> None:
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._hist: dict[tuple[str, tuple[tuple[str, str], ...]], list[int]] = {}
        self._series: dict[str, int] = {}
        self._lock = RLock()

    def _key(self, name: str, labels: dict[str, str]) -> tuple[str, tuple[tuple[str, str], ...]]:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        known = key in self._counters or key in self._gauges or key in self._hist
        if not known:
            if self._series.get(name, 0) >= MAX_SERIES_PER_METRIC:
                return (name, ((OVERFLOW_LABEL, "1"),))
            self._series[name] = self._series.get(name, 0) + 1
        return key

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            key = self._key(name, labels)
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self._gauges[self._key(name, labels)] = float(value)

    def observe_us(self, name: str, micros: float, **labels: str) -> None:
        with self._lock:
            key = self._key(name, labels)
            buckets = self._hist.setdefault(key, [0] * (len(LATENCY_BUCKETS_US) + 1))
            buckets[bisect_left(LATENCY_BUCKETS_US, micros)] += 1

    def counter(self, name: str, **labels: str) -> float:
        return self._counters.get((name, tuple(sorted((k, str(v)) for k, v in labels.items()))), 0.0)

    def gauge(self, name: str, **labels: str) -> float:
        return self._gauges.get((name, tuple(sorted((k, str(v)) for k, v in labels.items()))), 0.0)

    def exposition(self) -> str:
        """Prometheus text exposition format 0.0.4."""
        def fmt(labels: tuple[tuple[str, str], ...], extra: str = "") -> str:
            parts = [f'{k}="{_escape(v)}"' for k, v in labels]
            if extra:
                parts.append(extra)
            return "{" + ",".join(parts) + "}" if parts else ""

        lines: list[str] = []
        with self._lock:
            for (name, labels), v in sorted(self._counters.items()):
                lines.append(f"inv35_{name}_total{fmt(labels)} {v:g}")
            for (name, labels), v in sorted(self._gauges.items()):
                lines.append(f"inv35_{name}{fmt(labels)} {v:g}")
            for (name, labels), buckets in sorted(self._hist.items()):
                cum = 0
                for bound, count in zip(LATENCY_BUCKETS_US + (float("inf"),), buckets):
                    cum += count
                    le = "+Inf" if bound == float("inf") else f"{bound}"
                    le_label = 'le="' + le + '"'
                    lines.append(f"inv35_{name}_bucket{fmt(labels, le_label)} {cum}")
                lines.append(f"inv35_{name}_count{fmt(labels)} {cum}")
        return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# ---------------------------------------------------------------------------
# Trace context (W3C traceparent)
# ---------------------------------------------------------------------------

_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    span_id: str
    flags: str = "01"

    @classmethod
    def new(cls) -> "TraceContext":
        return cls(secrets.token_hex(16), secrets.token_hex(8))

    @classmethod
    def parse(cls, header: object) -> "TraceContext":
        """Parse untrusted input; malformed or all-zero ids start a fresh trace."""
        if isinstance(header, str):
            m = _TRACEPARENT.match(header.strip())
            if m and set(m.group(1)) != {"0"} and set(m.group(2)) != {"0"}:
                return cls(m.group(1), m.group(2), m.group(3))
        return cls.new()

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), self.flags)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"


# ---------------------------------------------------------------------------
# Structured logs + reason records
# ---------------------------------------------------------------------------

LOG_SCHEMA = "INV35_LOG/1"
REASON_SCHEMA = "INV35_DECISION/1"


@dataclass
class StructuredLog:
    capacity: int = 4096
    records: deque = field(default_factory=deque)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def emit(self, level: str, event: str, *, trace: TraceContext | None = None, **fields: object) -> dict[str, object]:
        record = {
            "schema": LOG_SCHEMA,
            "ts": time.time(),
            "level": level,
            "event": event,
            "trace_id": trace.trace_id if trace else None,
            "span_id": trace.span_id if trace else None,
            **redact(fields),
        }
        with self._lock:
            self.records.append(record)
            while len(self.records) > self.capacity:
                self.records.popleft()
        return record

    def jsonl(self) -> str:
        return "".join(json.dumps(r, sort_keys=True) + "\n" for r in self.records)


def decision(action: str, outcome: str, code: str, *, inputs: dict[str, object], rule: str,
             trace: TraceContext | None = None) -> dict[str, object]:
    """A structured reason for an automated decision (admit/refuse/shed/quarantine)."""
    return {
        "schema": REASON_SCHEMA,
        "action": action,
        "outcome": outcome,
        "code": code,
        "rule": rule,
        "inputs": redact(inputs),
        "trace_id": trace.trace_id if trace else None,
        "ts": time.time(),
    }


def explain(decisions: list[dict[str, object]], *, queue: str | None = None, limit: int = 20) -> str:
    """Human-readable operator explain view regenerated from reason records."""
    rows = [d for d in decisions if queue is None or d["inputs"].get("queue") == queue][-limit:]
    if not rows:
        return "no decisions recorded"
    out = [f"{'action':<12} {'outcome':<10} {'code':<11} rule"]
    for d in rows:
        out.append(f"{d['action']:<12} {d['outcome']:<10} {d['code']:<11} {d['rule']}")
    return "\n".join(out)
