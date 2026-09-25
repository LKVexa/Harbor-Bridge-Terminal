"""Metrics, structured logs, trace propagation, decision records and explain view
(components 73-80).  Stdlib only; exporters are adapters over :meth:`Metrics.snapshot`.
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import time
from bisect import insort
from collections import deque
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable

_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
_SECRET_KEYS = ("password", "secret", "token", "authorization", "key", "credential")
OVERFLOW_LABEL = "__overflow__"


class Metrics:
    """Counters, gauges and bounded-reservoir histograms with a per-metric label-cardinality cap."""

    def __init__(self, max_label_values: int = 1000, reservoir: int = 2048) -> None:
        self.max_label_values = max_label_values
        self.reservoir = reservoir
        self.counters: dict[tuple[str, tuple], float] = {}
        self.gauges: dict[tuple[str, tuple], float] = {}
        self.hists: dict[tuple[str, tuple], list[float]] = {}
        self._labelsets: dict[str, set[tuple]] = {}
        self.cardinality_overflows = 0
        self._lock = RLock()

    def _key(self, name: str, labels: dict[str, str] | None) -> tuple[str, tuple]:
        ls = tuple(sorted((labels or {}).items()))
        seen = self._labelsets.setdefault(name, set())
        if ls not in seen:
            if len(seen) >= self.max_label_values:
                self.cardinality_overflows += 1
                ls = (("overflow", OVERFLOW_LABEL),)
            seen.add(ls)
        return name, ls

    def inc(self, name: str, v: float = 1.0, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            self.counters[k] = self.counters.get(k, 0.0) + v

    def set(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            self.gauges[self._key(name, labels)] = v

    def observe(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            h = self.hists.setdefault(self._key(name, labels), [])
            insort(h, v)
            if len(h) > self.reservoir:  # keep distribution shape: drop alternating extremes' neighbours
                del h[len(h) // 2]

    def quantile(self, name: str, q: float, **labels: str) -> float | None:
        h = self.hists.get((name, tuple(sorted(labels.items()))))
        if not h:
            return None
        return h[min(len(h) - 1, int(q * len(h)))]

    def counter(self, name: str, **labels: str) -> float:
        return self.counters.get((name, tuple(sorted(labels.items()))), 0.0)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            def fmt(d):
                return [{"name": n, "labels": dict(ls), "value": v} for (n, ls), v in sorted(d.items())]
            return {"counters": fmt(self.counters), "gauges": fmt(self.gauges),
                    "histograms": [{"name": n, "labels": dict(ls), "count": len(h),
                                    "p50": h[len(h) // 2], "p99": h[min(len(h) - 1, int(.99 * len(h)))]}
                                   for (n, ls), h in sorted(self.hists.items()) if h],
                    "cardinality_overflows": self.cardinality_overflows}

    def prometheus(self) -> str:
        lines = []
        for (n, ls), v in sorted(self.counters.items()):
            lab = ",".join(f'{k}="{val}"' for k, val in ls)
            lines.append(f"inv54_{n}{{{lab}}} {v}")
        for (n, ls), v in sorted(self.gauges.items()):
            lab = ",".join(f'{k}="{val}"' for k, val in ls)
            lines.append(f"inv54_{n}{{{lab}}} {v}")
        return "\n".join(lines) + "\n"


def _redact(obj: Any, key: str = "") -> Any:
    if isinstance(obj, dict):
        return {k: _redact(v, k) for k, v in obj.items()}
    if any(s in key.lower() for s in _SECRET_KEYS) and not (isinstance(obj, str) and obj.startswith("secret://")):
        return "***REDACTED***"
    return obj


class StructuredLogger:
    """JSON-lines logger with mandatory fields and secret redaction; payload bodies never logged."""

    def __init__(self, component: str = "inv54", sink: Callable[[str], None] | None = None,
                 level: str = "INFO", clock: Callable[[], float] = time.time, max_buffer: int = 10_000) -> None:
        self.component = component
        self.level = logging.getLevelName(level)
        self.clock = clock
        self.buffer: deque[dict[str, Any]] = deque(maxlen=max_buffer)
        self._sink = sink

    def log(self, level: str, event: str, *, trace: "TraceContext | None" = None, **fields: Any) -> dict[str, Any]:
        if logging.getLevelName(level) < self.level:
            return {}
        rec = {"ts": round(self.clock(), 6), "level": level, "component": self.component, "event": event,
               "version": _version()}
        if trace:
            rec["trace_id"], rec["span_id"] = trace.trace_id, trace.span_id
        fields.pop("payload", None)
        rec.update(_redact(fields))
        self.buffer.append(rec)
        if self._sink:
            self._sink(json.dumps(rec, sort_keys=True, default=str))
        return rec


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    sampled: bool = True

    @classmethod
    def new(cls, sample_ratio: float = 1.0) -> "TraceContext":
        return cls(secrets.token_hex(16), secrets.token_hex(8), secrets.randbelow(10_000) < sample_ratio * 10_000)

    @classmethod
    def parse(cls, header: str | None) -> "TraceContext | None":
        m = _TRACEPARENT.fullmatch(header or "")
        if not m or m[1] == "0" * 32 or m[2] == "0" * 16:
            return None
        return cls(m[1], m[2], bool(int(m[3], 16) & 1))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), self.sampled)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


@dataclass
class Decision:
    ts: float
    request_id: str
    op: str
    tenant: str
    outcome: str
    reasons: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)


class DecisionLog:
    """Bounded record of *why* each request was admitted/refused (components 77, 78)."""

    def __init__(self, capacity: int = 10_000) -> None:
        self.records: deque[Decision] = deque(maxlen=capacity)

    def add(self, d: Decision) -> None:
        d.inputs = _redact(d.inputs)
        self.records.append(d)

    def explain(self, request_id: str) -> str:
        for d in reversed(self.records):
            if d.request_id == request_id:
                lines = [f"request {d.request_id}: {d.op} tenant={d.tenant} -> {d.outcome}"]
                lines += [f"  because: {r}" for r in d.reasons]
                return "\n".join(lines)
        return f"request {request_id}: no decision retained (evicted or never seen)"


def _version() -> str:
    try:
        from . import __version__
        return __version__
    except Exception:  # pragma: no cover
        return "unknown"


def build_lineage() -> dict[str, str]:
    """Release/infrastructure lineage labels attached to health + telemetry (component 79)."""
    return {"component_version": _version(),
            "build_digest": os.environ.get("INV54_BUILD_DIGEST", "unset"),
            "config_digest": os.environ.get("INV54_CONFIG_DIGEST", "unset"),
            "site": os.environ.get("INV54_SITE", "unset"),
            "environment": os.environ.get("INV54_ENV", "unset")}
