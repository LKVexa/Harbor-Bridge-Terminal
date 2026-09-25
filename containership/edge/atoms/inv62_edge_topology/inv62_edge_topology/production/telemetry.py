"""Structured metrics, logs and traces with cardinality and privacy
governance (MC-062 .. MC-065, MC-068, MC-069).

* Metrics: counters, gauges and fixed-bucket histograms.  Each label key has a
  value budget; values beyond it collapse into ``__overflow__`` so a hostile
  tenant cannot explode series cardinality.
* Logs: one JSON object per line with a stable schema (``LOG_FIELDS``).
  Keys that look secret are redacted; node names are HMAC-pseudonymised
  unless ``expose_node_names`` is true.
* Traces: W3C ``traceparent`` accepted and propagated; head sampling.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, TextIO
from collections.abc import Callable

LOG_SCHEMA_VERSION = 1
LOG_FIELDS = ("v", "ts", "level", "event", "component", "tenant", "op", "outcome", "code", "request_id",
              "trace_id", "span_id", "node", "site", "decision_id", "revision", "config_generation", "release",
              "duration_ms", "mode", "detail")
_SECRETISH = re.compile(r"(secret|credential|token|password|key)(?!_id)", re.I)
LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40}
LATENCY_BUCKETS_MS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 1000)
OVERFLOW = "__overflow__"


class Metrics:
    def __init__(self, max_label_values: int = 1000):
        self.max_label_values = max_label_values
        self._lock = threading.Lock()
        self.counters: dict[tuple, float] = defaultdict(float)
        self.gauges: dict[tuple, float] = {}
        self.hists: dict[tuple, list[int]] = {}
        self.hist_sums: dict[tuple, float] = defaultdict(float)
        self._seen: dict[str, set[str]] = defaultdict(set)

    def _labels(self, labels: dict[str, str]) -> tuple:
        out = []
        for k, v in sorted(labels.items()):
            v = str(v)
            seen = self._seen[k]
            if v not in seen:
                if len(seen) >= self.max_label_values:
                    v = OVERFLOW
                else:
                    seen.add(v)
            out.append((k, v))
        return tuple(out)

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            self.counters[(name, self._labels(labels))] += value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self.gauges[(name, self._labels(labels))] = value

    def observe(self, name: str, value_ms: float, **labels: str) -> None:
        with self._lock:
            key = (name, self._labels(labels))
            buckets = self.hists.setdefault(key, [0] * (len(LATENCY_BUCKETS_MS) + 1))
            for i, bound in enumerate(LATENCY_BUCKETS_MS):
                if value_ms <= bound:
                    buckets[i] += 1
                    break
            else:
                buckets[-1] += 1
            self.hist_sums[key] += value_ms

    def get(self, name: str, **labels: str) -> float:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        return self.counters.get(key, self.gauges.get(key, 0.0))

    def exposition(self) -> str:
        """Prometheus text format (subset)."""
        def fmt(labels: tuple) -> str:
            return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}" if labels else ""
        lines = []
        with self._lock:
            for (n, l), v in sorted(self.counters.items()):
                lines.append(f"{n}_total{fmt(l)} {v}")
            for (n, l), v in sorted(self.gauges.items()):
                lines.append(f"{n}{fmt(l)} {v}")
            for (n, l), b in sorted(self.hists.items()):
                cum = 0
                for bound, count in zip([*LATENCY_BUCKETS_MS, "+Inf"], b, strict=True):
                    cum += count
                    lab = l + (("le", str(bound)),)
                    lines.append(f"{n}_bucket{fmt(lab)} {cum}")
                lines.append(f"{n}_sum{fmt(l)} {self.hist_sums[(n, l)]}")
                lines.append(f"{n}_count{fmt(l)} {cum}")
        return "\n".join(lines) + "\n"


def _redact(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return "…"
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if _SECRETISH.search(str(k)) else _redact(v, depth + 1)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, depth + 1) for v in value[:32]]
    if isinstance(value, str):
        if value.startswith("PKT1."):
            return "[REDACTED]"
        return value[:512]
    return value


class Logger:
    def __init__(self, *, sink: TextIO | list | None = None, level: str = "info", release: str = "",
                 pseudonym_key: bytes | None = None, expose_node_names: bool = False,
                 clock: Callable[[], float] = time.time):
        self.sink = sink if sink is not None else []
        self.level = LEVELS[level]
        self.release = release
        self._pkey = pseudonym_key or os.urandom(32)
        self.expose = expose_node_names
        self.clock = clock
        self._lock = threading.Lock()

    def pseudonym(self, name: str | None) -> str | None:
        if name is None or self.expose:
            return name
        return "n-" + hmac.new(self._pkey, name.encode(), hashlib.sha256).hexdigest()[:12]

    def log(self, level: str, event: str, **fields: Any) -> dict[str, Any] | None:
        if LEVELS[level] < self.level:
            return None
        rec: dict[str, Any] = {"v": LOG_SCHEMA_VERSION, "ts": round(self.clock(), 6), "level": level, "event": event,
                               "component": "INV-62", "release": self.release}
        for k, v in fields.items():
            if k not in LOG_FIELDS or v is None:
                continue
            if k == "node":
                v = self.pseudonym(v)
            rec[k] = _redact(v) if k == "detail" else (v if not isinstance(v, str) else v[:256])
        with self._lock:
            if isinstance(self.sink, list):
                self.sink.append(rec)
                del self.sink[:-10_000]
            else:
                self.sink.write(json.dumps(rec, sort_keys=True) + "\n")
        return rec


_TP = re.compile(r"00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})")


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    sampled: bool
    start: float
    end: float | None = None
    attrs: dict[str, Any] = field(default_factory=dict)

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


class Tracer:
    def __init__(self, sample_rate: float = 0.05, rng: random.Random | None = None, capacity: int = 5000):
        self.sample_rate = sample_rate
        self.rng = rng or random.Random()  # noqa: S311 - sampling/ids for traces, not secrets
        self.finished: list[Span] = []
        self.capacity = capacity
        self._lock = threading.Lock()

    def start(self, name: str, traceparent: str | None) -> Span:
        m = _TP.fullmatch(traceparent or "")
        if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
            trace_id, parent, sampled = m.group(1), m.group(2), m.group(3) == "01"
        else:
            trace_id, parent = f"{self.rng.getrandbits(128):032x}", None
            sampled = self.rng.random() < self.sample_rate
        return Span(trace_id, f"{self.rng.getrandbits(64):016x}", parent, name, sampled, time.perf_counter())

    def finish(self, span: Span, **attrs: Any) -> None:
        span.end = time.perf_counter()
        span.attrs.update(attrs)
        if span.sampled:
            with self._lock:
                self.finished.append(span)
                del self.finished[:-self.capacity]
