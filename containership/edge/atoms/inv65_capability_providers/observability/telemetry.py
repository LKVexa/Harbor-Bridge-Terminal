"""Metrics, structured logging, tracing and explainability (M21).

- Metrics: counters/gauges/histograms with a label allowlist and a hard series
  cap per metric (cardinality guard) -- component/tenant ids are NOT labels by
  default; overflow folds into ``__overflow__``.  Prometheus text exposition.
- Logging: JSON lines; any key matching the secret-key rule, and any
  ``SecretValue``, is redacted before emission.
- Tracing: W3C traceparent parse/generate; spans recorded with bounded attrs.
- Explain: every allow/deny decision gets a structured, bounded explanation.
"""
from __future__ import annotations

import collections
import json
import random
import re
import secrets
import threading
import time

from ..provider import _is_forbidden_secret_key

LABEL_ALLOW = {"contract", "op", "code", "outcome", "state", "tenant_class", "link_state"}
MAX_SERIES = 200
RESERVOIR = 4096
BUCKETS = (0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)


class Metrics:
    def __init__(self):
        self._c: dict = {}
        self._g: dict = {}
        self._h: dict = {}
        self._lock = threading.Lock()
        self.dropped_labels = 0

    def _key(self, table, name, labels):
        lab = {}
        for k, v in sorted((labels or {}).items()):
            if k in LABEL_ALLOW:
                lab[k] = str(v)[:64]
            else:
                self.dropped_labels += 1
        key = (name, tuple(sorted(lab.items())))
        series = sum(1 for k in table if k[0] == name)
        if key not in table and series >= MAX_SERIES:
            key = (name, (("__overflow__", "1"),))
        return key

    def inc(self, name, labels=None, v=1.0):
        with self._lock:
            k = self._key(self._c, name, labels)
            self._c[k] = self._c.get(k, 0.0) + v

    def gauge(self, name, v, labels=None):
        with self._lock:
            self._g[self._key(self._g, name, labels)] = float(v)

    def observe(self, name, seconds, labels=None):
        with self._lock:
            k = self._key(self._h, name, labels)
            h = self._h.setdefault(k, {"b": [0] * len(BUCKETS), "sum": 0.0, "count": 0, "samples": [], "rng": random.Random(0)})
            for i, b in enumerate(BUCKETS):
                if seconds <= b:
                    h["b"][i] += 1
            h["sum"] += seconds
            h["count"] += 1
            if len(h["samples"]) < RESERVOIR:  # bounded reservoir sample (Algorithm R) for quantiles
                h["samples"].append(seconds)
            else:
                j = h["rng"].randrange(h["count"])
                if j < RESERVOIR:
                    h["samples"][j] = seconds

    def counter(self, name, labels=None) -> float:
        with self._lock:
            return self._c.get((name, tuple(sorted((labels or {}).items()))), 0.0)

    def quantile(self, name, q, labels=None):
        with self._lock:
            h = self._h.get((name, tuple(sorted((labels or {}).items()))))
            if not h or not h["samples"]:
                return None
            s = sorted(h["samples"])
            return s[min(len(s) - 1, int(q * len(s)))]

    def exposition(self) -> str:
        out = []
        with self._lock:
            def lab(t, extra=()):
                items = list(t) + list(extra)
                return "{" + ",".join(f'{k}="{v}"' for k, v in items) + "}" if items else ""
            for (n, t), v in sorted(self._c.items()):
                out.append(f"{n}_total{lab(t)} {v}")
            for (n, t), v in sorted(self._g.items()):
                out.append(f"{n}{lab(t)} {v}")
            for (n, t), h in sorted(self._h.items(), key=lambda x: x[0]):
                for b, c in zip(BUCKETS, h["b"]):
                    out.append(f"{n}_bucket{lab(t, [('le', b)])} {c}")
                out.append(f"{n}_bucket{lab(t, [('le', '+Inf')])} {h['count']}")
                out.append(f"{n}_sum{lab(t)} {h['sum']}")
                out.append(f"{n}_count{lab(t)} {h['count']}")
        return "\n".join(out) + "\n"


def redact(obj, depth=0):
    if depth > 8:
        return "<truncated>"
    if type(obj).__name__ == "SecretValue":
        return "<redacted>"
    if isinstance(obj, dict):
        return {k: ("<redacted>" if isinstance(k, str) and _is_forbidden_secret_key(k) else redact(v, depth + 1))
                for k, v in list(obj.items())[:64]}
    if isinstance(obj, (list, tuple)):
        return [redact(v, depth + 1) for v in list(obj)[:64]]
    if isinstance(obj, str):
        return re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+", r"\1<redacted>", obj)[:1024]
    return obj


class JsonLogger:
    def __init__(self, sink=None):
        self.sink = sink if sink is not None else []
        self._lock = threading.Lock()

    def log(self, level: str, event: str, **fields):
        rec = {"ts": round(time.time(), 6), "level": level, "event": event, **redact(fields)}
        line = json.dumps(rec, sort_keys=True, default=str)
        with self._lock:
            if isinstance(self.sink, list):
                self.sink.append(line)
            else:
                self.sink.write(line + "\n")
        return rec


_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-0[01]$")


def parse_traceparent(tp: str | None) -> tuple[str, str]:
    m = _TP.match(tp or "")
    if not m or m.group(1) == "0" * 32:
        return secrets.token_hex(16), ""
    return m.group(1), m.group(2)


class Tracer:
    def __init__(self, cap=2048):
        self.spans: collections.deque = collections.deque(maxlen=cap)  # ring buffer: newest spans kept
        self._lock = threading.Lock()

    def span(self, name, trace_id, parent="", **attrs):
        tracer = self

        class _S:
            def __enter__(s):
                s.id, s.t = secrets.token_hex(8), time.perf_counter()
                return s

            def __exit__(s, et, ev, tb):
                rec = {"trace_id": trace_id, "span_id": s.id, "parent": parent, "name": name,
                       "dur_s": time.perf_counter() - s.t, "status": "error" if et else "ok",
                       "attrs": redact({k: v for k, v in list(attrs.items())[:16]})}
                with tracer._lock:
                    tracer.spans.append(rec)
                return False
        return _S()


def explain(decision: str, stage: str, code: str | None = None, **facts) -> dict:
    return {"decision": decision, "stage": stage, "code": code, "facts": redact(facts)}
