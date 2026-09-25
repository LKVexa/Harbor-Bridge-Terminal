"""Metrics, structured logs and traces (checklist #72, #73, #74, #75, #79).

* Metrics: counters + fixed-bucket histograms with a hard label-cardinality cap;
  exported in Prometheus text format.  Secret NAMES are not labels (unbounded
  and potentially sensitive) - only tenant, op, outcome, reason.
* Logs: one JSON object per line; every record passes ``scrub`` which refuses
  ``_SecretValue`` and masks credential-shaped substrings.
* Traces: minimal W3C-traceparent-compatible spans kept in a bounded ring.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import deque

from ..reference import _SecretValue

BUCKETS_MS = (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 1000)
_CRED = re.compile(
    r"(?i)(hvs\.[A-Za-z0-9_-]{20,}|s\.[A-Za-z0-9]{24}|AKIA[0-9A-Z]{16}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:password|secret|token)\s*[=:]\s*\S+)")


class Metrics:
    def __init__(self, max_series: int = 2_000):
        self.max_series = max_series
        self.counters: dict[tuple, float] = {}
        self.hist: dict[tuple, list[int]] = {}
        self.hist_sum: dict[tuple, float] = {}
        self.dropped = 0
        self._lock = threading.Lock()

    def _key(self, name, labels):
        return (name, tuple(sorted(labels.items())))

    def inc(self, name, n=1.0, **labels):
        k = self._key(name, labels)
        with self._lock:
            if k not in self.counters and len(self.counters) + len(self.hist) >= self.max_series:
                self.dropped += 1
                return
            self.counters[k] = self.counters.get(k, 0.0) + n

    def observe_ms(self, name, ms, **labels):
        k = self._key(name, labels)
        with self._lock:
            if k not in self.hist and len(self.counters) + len(self.hist) >= self.max_series:
                self.dropped += 1
                return
            b = self.hist.setdefault(k, [0] * (len(BUCKETS_MS) + 1))
            for i, ub in enumerate(BUCKETS_MS):
                if ms <= ub:
                    b[i] += 1
                    break
            else:
                b[-1] += 1
            self.hist_sum[k] = self.hist_sum.get(k, 0.0) + ms

    def get(self, name, **labels):
        return self.counters.get(self._key(name, labels), 0.0)

    def quantile_ms(self, name, q, **labels):
        b = self.hist.get(self._key(name, labels))
        if not b:
            return None
        total, acc = sum(b), 0
        for i, c in enumerate(b):
            acc += c
            if acc >= q * total:
                return BUCKETS_MS[i] if i < len(BUCKETS_MS) else float("inf")

    def prometheus(self) -> str:
        def lab(t):
            return "{" + ",".join(f'{k}="{v}"' for k, v in t) + "}" if t else ""
        out = []
        with self._lock:
            for (n, t), v in sorted(self.counters.items()):
                out.append(f"inv55_{n}_total{lab(t)} {v:g}")
            for (n, t), b in sorted(self.hist.items()):
                acc = 0
                for i, ub in enumerate(BUCKETS_MS):
                    acc += b[i]
                    out.append(f"inv55_{n}_ms_bucket{lab(t + (('le', str(ub)),))} {acc}")
                acc += b[-1]
                out.append(f"inv55_{n}_ms_bucket{lab(t + (('le', '+Inf'),))} {acc}")
                out.append(f"inv55_{n}_ms_count{lab(t)} {acc}")
                out.append(f"inv55_{n}_ms_sum{lab(t)} {self.hist_sum[(n, t)]:g}")
            out.append(f"inv55_telemetry_series_dropped_total {self.dropped}")
        return "\n".join(out) + "\n"


def scrub(obj):
    if isinstance(obj, _SecretValue):
        raise ValueError("secret value reached the logger")
    if isinstance(obj, str):
        return _CRED.sub("[REDACTED]", obj)
    if isinstance(obj, dict):
        return {str(k): scrub(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [scrub(v) for v in obj]
    return obj


class JsonLogger:
    def __init__(self, stream=None, *, ring: int = 1000, sample_debug: float = 0.0):
        self.stream, self.ring = stream, deque(maxlen=ring)
        self.sample_debug = sample_debug

    def log(self, level: str, event: str, **fields):
        rec = scrub({"ts": time.time(), "level": level, "event": event, **fields})
        line = json.dumps(rec, sort_keys=True, default=str)
        self.ring.append(line)
        if self.stream is not None:
            self.stream.write(line + "\n")
        return rec


class Tracer:
    def __init__(self, keep: int = 1000):
        self.spans = deque(maxlen=keep)

    @staticmethod
    def new_trace_id() -> str:
        return os.urandom(16).hex()

    def span(self, name, trace_id, parent=None):
        tr = self

        class _S:
            def __enter__(s):
                s.id, s.t0 = os.urandom(8).hex(), time.perf_counter()
                s.attrs = {}
                return s

            def __exit__(s, et, ev, tb):
                tr.spans.append({"trace_id": trace_id, "span_id": s.id, "parent": parent, "name": name,
                                 "ms": (time.perf_counter() - s.t0) * 1000,
                                 "status": "error" if et else "ok", **scrub(s.attrs)})
        return _S()

    @staticmethod
    def traceparent(trace_id, span_id):
        return f"00-{trace_id}-{span_id}-01"
