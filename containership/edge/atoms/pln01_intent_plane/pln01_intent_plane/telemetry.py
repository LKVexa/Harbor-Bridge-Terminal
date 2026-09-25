"""Metrics, structured logging, trace propagation, and health surface.

MC-034 runtime metrics emitter (Prometheus text exposition, stdlib only);
MC-035 structured JSON logs with redaction, W3C ``traceparent`` propagation,
bounded label cardinality; MC-025 health / readiness / stall detection with a
dependency-status surface.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from bisect import bisect_left
from collections.abc import Callable
from typing import Any

from .secret_guard import redact_value

MAX_LABEL_SETS = 1000
OVERFLOW = "__overflow__"
DEFAULT_BUCKETS = (0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


class Metrics:
    """Counters, gauges, histograms with a hard cap on label-set cardinality."""

    def __init__(self, max_label_sets: int = MAX_LABEL_SETS) -> None:
        self._lock = threading.Lock()
        self.max_label_sets = max_label_sets
        self.counters: dict[str, dict[tuple, float]] = {}
        self.gauges: dict[str, dict[tuple, float]] = {}
        self.hists: dict[str, dict[tuple, list]] = {}
        self.help: dict[str, str] = {}

    def _key(self, store: dict[tuple, Any], labels: dict[str, str]) -> tuple:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        if key not in store and len(store) >= self.max_label_sets:
            return ((OVERFLOW, "true"),)
        return key

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            s = self.counters.setdefault(name, {})
            k = self._key(s, labels)
            s[k] = s.get(k, 0.0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            s = self.gauges.setdefault(name, {})
            s[self._key(s, labels)] = float(value)

    def observe(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            s = self.hists.setdefault(name, {})
            k = self._key(s, labels)
            h = s.setdefault(k, [[0] * (len(DEFAULT_BUCKETS) + 1), 0.0, 0])
            h[0][bisect_left(DEFAULT_BUCKETS, value)] += 1
            h[1] += value
            h[2] += 1

    def value(self, name: str, **labels: str) -> float:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        return self.counters.get(name, {}).get(key, self.gauges.get(name, {}).get(key, 0.0))

    @staticmethod
    def _fmt(labels: tuple, extra: tuple = ()) -> str:
        items = list(labels) + list(extra)
        if not items:
            return ""
        return "{" + ",".join(f'{k}="{str(v).replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))}"'
                              for k, v in items) + "}"

    def exposition(self) -> str:
        lines: list[str] = []
        with self._lock:
            for name, s in sorted(self.counters.items()):
                lines.append(f"# TYPE {name} counter")
                lines += [f"{name}{self._fmt(k)} {v}" for k, v in sorted(s.items())]
            for name, s in sorted(self.gauges.items()):
                lines.append(f"# TYPE {name} gauge")
                lines += [f"{name}{self._fmt(k)} {v}" for k, v in sorted(s.items())]
            for name, s in sorted(self.hists.items()):
                lines.append(f"# TYPE {name} histogram")
                for k, (buckets, total, count) in sorted(s.items()):
                    cum = 0
                    for bound, n in zip(list(DEFAULT_BUCKETS) + ["+Inf"], buckets):
                        cum += n
                        lines.append(f"{name}_bucket{self._fmt(k, (('le', bound),))} {cum}")
                    lines.append(f"{name}_sum{self._fmt(k)} {total}")
                    lines.append(f"{name}_count{self._fmt(k)} {count}")
        return "\n".join(lines) + "\n"


class TraceContext:
    """Minimal W3C trace-context propagation."""

    def __init__(self, trace_id: str, span_id: str, sampled: bool = True) -> None:
        self.trace_id, self.span_id, self.sampled = trace_id, span_id, sampled

    @classmethod
    def new(cls) -> "TraceContext":
        return cls(os.urandom(16).hex(), os.urandom(8).hex())

    @classmethod
    def parse(cls, header: str | None) -> "TraceContext":
        m = _TRACEPARENT.match(header or "")
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return cls.new()
        return cls(m.group(1), m.group(2), bool(int(m.group(3), 16) & 1))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, os.urandom(8).hex(), self.sampled)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


class StructuredLogger:
    """JSON-lines logger. Every record is redacted and carries trace ids."""

    def __init__(self, name: str = "pln01", sink: Callable[[str], None] | None = None, level: str = "INFO") -> None:
        self._logger = logging.getLogger(name)
        self.sink = sink
        self.level = logging.getLevelName(level)
        self.records: list[dict[str, Any]] = []
        self.max_records = 10_000

    def log(self, level: str, event: str, trace: TraceContext | None = None, **fields: Any) -> dict[str, Any]:
        if logging.getLevelName(level) < self.level:
            return {}
        record = {"ts": round(time.time(), 6), "level": level, "component": "PLN-01", "event": event}
        if trace is not None:
            record["trace_id"], record["span_id"] = trace.trace_id, trace.span_id
        record.update(redact_value(fields))
        line = json.dumps(record, sort_keys=True, default=str)
        self.records.append(record)
        del self.records[:-self.max_records]
        if self.sink:
            self.sink(line)
        else:
            self._logger.log(logging.getLevelName(level), line)
        return record


class Health:
    """Liveness, readiness, stall detection, and dependency status."""

    def __init__(self, *, stall_seconds: float = 30.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self.stall_seconds = stall_seconds
        self.started = clock()
        self.last_progress = clock()
        self.dependencies: dict[str, dict[str, Any]] = {}
        self.required: set[str] = set()
        self.ready_flag = False

    def heartbeat(self) -> None:
        self.last_progress = self._clock()

    def register_dependency(self, name: str, *, required: bool) -> None:
        self.dependencies[name] = {"status": "unknown", "detail": "", "checked_at": None}
        if required:
            self.required.add(name)

    def report_dependency(self, name: str, status: str, detail: str = "") -> None:
        if status not in ("up", "degraded", "down", "unknown"):
            raise ValueError("invalid dependency status")
        self.dependencies[name] = {"status": status, "detail": detail, "checked_at": self._clock()}

    def stalled(self) -> bool:
        return self._clock() - self.last_progress > self.stall_seconds

    def liveness(self) -> dict[str, Any]:
        return {"status": "fail" if self.stalled() else "pass",
                "seconds_since_progress": round(self._clock() - self.last_progress, 3)}

    def readiness(self) -> dict[str, Any]:
        blocking = sorted(n for n in self.required if self.dependencies[n]["status"] != "up")
        ok = self.ready_flag and not blocking and not self.stalled()
        return {"status": "pass" if ok else "fail", "blocking": blocking,
                "dependencies": {k: dict(v) for k, v in sorted(self.dependencies.items())}}
