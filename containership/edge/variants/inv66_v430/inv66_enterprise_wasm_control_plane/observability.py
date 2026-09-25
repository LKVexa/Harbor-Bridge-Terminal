"""Metrics, structured logging, tracing and health (MC-049..MC-054).

* :class:`Metrics` - counters, gauges and fixed-bucket histograms with
  Prometheus text exposition (``/metrics``).  Label cardinality is bounded
  (tenant/lattice labels are capped; overflow collapses into ``__other__``).
* :class:`JsonLogger` - one JSON object per line, stable field schema
  ``PK_ECP_LOG/1``; secret-like keys and bearer tokens are redacted.
* :func:`parse_traceparent` / :func:`new_traceparent` - W3C Trace Context;
  spans are emitted as log events (``kind=span``) and propagated to adapters.
"""
from __future__ import annotations

import json
import re
import secrets
import sys
import threading
import time
from typing import IO, Any

BUCKETS_MS = (1, 2, 5, 10, 20, 50, 100, 250, 500, 1000)
MAX_LABEL_VALUES = 200
_REDACT_KEYS = re.compile(r"(token|secret|password|authorization|signature|key)$", re.I)
_BEARER = re.compile(r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")


class Metrics:
    def __init__(self):
        self._c: dict[tuple, float] = {}
        self._g: dict[tuple, float] = {}
        self._h: dict[tuple, list[float]] = {}
        self._seen: dict[str, set] = {}
        self._lock = threading.Lock()
        self.help: dict[str, str] = {}

    def _labels(self, labels: dict[str, str]) -> tuple:
        out = []
        for k, v in sorted(labels.items()):
            seen = self._seen.setdefault(k, set())
            if v not in seen and len(seen) >= MAX_LABEL_VALUES:
                v = "__other__"
            seen.add(v)
            out.append((k, str(v)))
        return tuple(out)

    def inc(self, name: str, n: float = 1, **labels: str) -> None:
        with self._lock:
            key = (name, self._labels(labels))
            self._c[key] = self._c.get(key, 0) + n

    def set(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            self._g[(name, self._labels(labels))] = v

    def observe_ms(self, name: str, ms: float, **labels: str) -> None:
        with self._lock:
            key = (name, self._labels(labels))
            h = self._h.setdefault(key, [0.0] * (len(BUCKETS_MS) + 2))  # buckets.., +Inf, sum
            for i, b in enumerate(BUCKETS_MS):
                if ms <= b:
                    h[i] += 1
            h[len(BUCKETS_MS)] += 1
            h[-1] += ms

    def value(self, name: str, **labels: str) -> float:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        return self._c.get(key, self._g.get(key, 0.0))

    def exposition(self) -> str:
        def fmt(lbl):
            return "{" + ",".join(f'{k}="{v}"' for k, v in lbl) + "}" if lbl else ""
        lines = []
        with self._lock:
            for (n, l), v in sorted(self._c.items()):
                lines.append(f"{n}_total{fmt(l)} {v}")
            for (n, l), v in sorted(self._g.items()):
                lines.append(f"{n}{fmt(l)} {v}")
            for (n, l), h in sorted(self._h.items()):
                for i, b in enumerate(BUCKETS_MS):
                    lines.append(f"{n}_bucket{fmt(l + (('le', str(b)),))} {h[i]}")
                lines.append(f"{n}_bucket{fmt(l + (('le', '+Inf'),))} {h[len(BUCKETS_MS)]}")
                lines.append(f"{n}_count{fmt(l)} {h[len(BUCKETS_MS)]}")
                lines.append(f"{n}_sum{fmt(l)} {h[-1]}")
        return "\n".join(lines) + "\n"


def redact(value: Any, key: str = "") -> Any:
    if key and _REDACT_KEYS.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return _BEARER.sub("<redacted-token>", value)
    return value


class JsonLogger:
    def __init__(self, stream: IO[str] | None = None, service: str = "inv66", min_level: str = "info"):
        self.stream = stream if stream is not None else sys.stderr
        self.service = service
        self.levels = {"debug": 10, "info": 20, "warn": 30, "error": 40}
        self.min = self.levels[min_level]
        self._lock = threading.Lock()

    def log(self, level: str, event: str, **fields: Any) -> None:
        if self.levels[level] < self.min:
            return
        rec = {"schema": "PK_ECP_LOG/1", "ts": round(time.time(), 6), "level": level,
               "service": self.service, "event": event, **redact(fields)}
        with self._lock:
            self.stream.write(json.dumps(rec, sort_keys=True, default=str) + "\n")


_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_traceparent(value: str | None) -> tuple[str, str] | None:
    m = _TP.match(value or "")
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
        return None
    return m.group(1), m.group(2)


def new_traceparent(trace_id: str | None = None) -> tuple[str, str, str]:
    trace_id = trace_id or secrets.token_hex(16)
    span = secrets.token_hex(8)
    return trace_id, span, f"00-{trace_id}-{span}-01"
