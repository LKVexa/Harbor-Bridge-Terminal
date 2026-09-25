"""Metrics, structured logs and trace-context propagation (MC-050, MC-051, MC-052, MC-054).

* Metrics: counters/gauges/histograms with a bounded label-set per metric (excess
  series collapse into ``{overflow="true"}`` rather than growing without bound),
  exported in Prometheus text format 0.0.4 at ``/metrics``.
* Logs: one JSON object per line, schema ``PK_ECP_LOG/1``, stable keys
  (``ts, level, event, request_id, trace_id, span_id, tenant, lattice, org``).
  Only allowlisted keys are emitted; tokens, signatures, keys and raw manifests
  are never logged.  ``redact_subjects`` hashes principal subjects (privacy).
* Tracing: W3C ``traceparent`` parse/generate; spans are recorded with parent
  links to an in-process exporter (bounded ring) and the context is forwarded
  on every outbound adapter call.  An OTLP exporter is an adapter slot.
"""
from __future__ import annotations

import collections
import hashlib
import io
import json
import os
import re
import sys
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional, TextIO

_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
BUCKETS_MS = (0.5, 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000)


class Metrics:
    def __init__(self, max_series: int = 1000):
        self.max_series = max_series
        self._c: dict[str, dict[tuple, float]] = collections.defaultdict(dict)
        self._g: dict[str, dict[tuple, float]] = collections.defaultdict(dict)
        self._h: dict[str, dict[tuple, list]] = collections.defaultdict(dict)
        self._help: dict[str, tuple[str, str]] = {}
        self._lock = threading.Lock()

    def _key(self, store: dict, name: str, labels: dict[str, str]) -> tuple:
        key = tuple(sorted((k, str(v)[:64]) for k, v in labels.items()))
        if key not in store[name] and len(store[name]) >= self.max_series:
            return (("overflow", "true"),)
        return key

    def describe(self, name: str, kind: str, help_: str) -> None:
        self._help[name] = (kind, help_)

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            k = self._key(self._c, name, labels)
            self._c[name][k] = self._c[name].get(k, 0.0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self._g[name][self._key(self._g, name, labels)] = float(value)

    def observe(self, name: str, value_ms: float, **labels: str) -> None:
        with self._lock:
            k = self._key(self._h, name, labels)
            h = self._h[name].get(k)
            if h is None:
                h = self._h[name][k] = [[0] * len(BUCKETS_MS), 0.0, 0]
            for i, b in enumerate(BUCKETS_MS):
                if value_ms <= b:
                    h[0][i] += 1
            h[1] += value_ms
            h[2] += 1

    def value(self, name: str, **labels: str) -> float:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        with self._lock:
            return self._c.get(name, {}).get(key, self._g.get(name, {}).get(key, 0.0))

    def series_count(self) -> int:
        with self._lock:
            return sum(len(v) for d in (self._c, self._g, self._h) for v in d.values())

    def render(self) -> str:
        def lbl(key: tuple, extra: str = "") -> str:
            parts = [f'{k}="{v}"' for k, v in key] + ([extra] if extra else [])
            return "{" + ",".join(parts) + "}" if parts else ""
        lines = []
        with self._lock:
            for kind, store in (("counter", self._c), ("gauge", self._g)):
                for name in sorted(store):
                    h = self._help.get(name, (kind, name))
                    lines += [f"# HELP {name} {h[1]}", f"# TYPE {name} {kind}"]
                    lines += [f"{name}{lbl(k)} {v:g}" for k, v in sorted(store[name].items())]
            for name in sorted(self._h):
                lines += [f"# HELP {name} {self._help.get(name, ('histogram', name))[1]}", f"# TYPE {name} histogram"]
                for k, (counts, total, n) in sorted(self._h[name].items()):
                    for b, c in zip(BUCKETS_MS, counts, strict=True):
                        le = 'le="%g"' % b
                        lines.append(f"{name}_bucket{lbl(k, le)} {c}")
                    inf = 'le="+Inf"'
                    lines.append(f"{name}_bucket{lbl(k, inf)} {n}")
                    lines.append(f"{name}_sum{lbl(k)} {total:g}")
                    lines.append(f"{name}_count{lbl(k)} {n}")
        return "\n".join(lines) + "\n"


LOG_KEYS = frozenset({"ts", "level", "event", "request_id", "decision_id", "trace_id", "span_id", "tenant", "lattice",
                      "org", "subject", "admitted", "codes", "latency_ms", "generation", "dependency", "state",
                      "mode", "scope", "seq", "count", "component", "version", "role", "epoch", "error"})
_LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40}


class Logger:
    def __init__(self, stream: "Optional[TextIO] | bool" = None, level: str = "info", redact_subjects: bool = False,
                 clock: Callable[[], float] = time.time):
        self.enabled = stream is not False
        self.stream: TextIO = stream if isinstance(stream, io.TextIOBase) or hasattr(stream, "write") else sys.stderr  # type: ignore[assignment]
        self.level = _LEVELS[level]
        self.redact_subjects = redact_subjects
        self.clock = clock
        self._lock = threading.Lock()

    def log(self, level: str, event: str, **fields: Any) -> dict[str, Any]:
        if _LEVELS[level] < self.level or not self.enabled:
            return {}
        rec = {"schema": "PK_ECP_LOG/1", "ts": round(self.clock(), 6), "level": level, "event": event}
        for k, v in fields.items():
            if k in LOG_KEYS and v is not None:
                if k == "subject" and self.redact_subjects:
                    v = "sha256:" + hashlib.sha256(str(v).encode()).hexdigest()[:16]
                rec[k] = v if isinstance(v, (int, float, bool)) else (v if isinstance(v, list) else str(v)[:256])
        with self._lock:
            self.stream.write(json.dumps(rec, sort_keys=True) + "\n")
            self.stream.flush()
        return rec


class Span:
    __slots__ = ("trace_id", "span_id", "parent_id", "name", "start", "end", "attrs", "sampled")

    def __init__(self, trace_id: str, span_id: str, parent_id: Optional[str], name: str, sampled: bool):
        self.trace_id, self.span_id, self.parent_id, self.name = trace_id, span_id, parent_id, name
        self.start: float = time.time()
        self.end: Optional[float] = None
        self.attrs: dict[str, Any] = {}
        self.sampled = sampled

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


class Tracer:
    def __init__(self, sample_ratio: float = 1.0, capacity: int = 10_000):
        self.sample_ratio = sample_ratio
        self.finished: collections.deque[Span] = collections.deque(maxlen=capacity)
        self._local = threading.local()

    @staticmethod
    def parse(tp: Optional[str]) -> Optional[tuple[str, str, bool]]:
        m = _TP.match(tp or "")
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return None
        return m.group(1), m.group(2), m.group(3) == "01"

    def current(self) -> Optional[Span]:
        stack = getattr(self._local, "stack", None)
        return stack[-1] if stack else None

    @contextmanager
    def span(self, name: str, traceparent: Optional[str] = None, **attrs: Any) -> Iterator[Span]:
        parent = self.current()
        if parent is not None:
            tid, pid, sampled = parent.trace_id, parent.span_id, parent.sampled
        elif (p := self.parse(traceparent)) is not None:
            tid, pid, sampled = p
        else:
            tid, pid = os.urandom(16).hex(), None
            sampled = int.from_bytes(os.urandom(2), "big") / 65535 < self.sample_ratio
        sp = Span(tid, os.urandom(8).hex(), pid, name, sampled)
        sp.attrs.update({k: v for k, v in attrs.items() if k in LOG_KEYS})
        stack = getattr(self._local, "stack", None)
        if stack is None:
            stack = self._local.stack = []
        stack.append(sp)
        try:
            yield sp
        finally:
            stack.pop()
            sp.end = time.time()
            if sp.sampled:
                self.finished.append(sp)

    def headers(self) -> dict[str, str]:
        sp = self.current()
        return {"traceparent": sp.traceparent()} if sp else {}
