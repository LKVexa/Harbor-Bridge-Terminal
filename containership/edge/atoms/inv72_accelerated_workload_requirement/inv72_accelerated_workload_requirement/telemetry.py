"""Metrics, structured logs and trace context for INV-72 (C072-C075, C079).

* ``Metrics`` - counters, gauges and fixed-bucket latency histograms; label sets are bounded
  (``max_series``) so a hostile caller cannot explode cardinality.  Tenant labels are pseudonymised.
  ``render()`` gives Prometheus text exposition; ``snapshot()`` gives JSON.  Series are pre-registered
  so absence of traffic reads as 0, not as missing (a lesson from INV-67).
* ``Logger`` - one JSON object per line with stable keys: ts, level, component, node, tenant (pseudonym),
  workload, operation, decision_id, trace_id, span_id, code, msg.  All values pass through ``redact``.
* ``TraceContext`` - W3C ``traceparent`` parse/generate; malformed headers start a new trace instead of
  being trusted or crashing.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
import threading
import time
from bisect import bisect_left
from dataclasses import dataclass, field
from typing import Callable, TextIO

from .redaction import pseudonym, redact

BUCKETS_MS = (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 1000)
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    sampled: bool = True

    @classmethod
    def parse(cls, header: str | None) -> "TraceContext":
        m = _TP.match(header or "") if isinstance(header, str) and len(header) <= 64 else None
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return cls.new()
        return cls(m.group(1), secrets.token_hex(8), bool(int(m.group(3), 16) & 1))

    @classmethod
    def new(cls) -> "TraceContext":
        return cls(secrets.token_hex(16), secrets.token_hex(8), True)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


@dataclass
class Metrics:
    tenant_key: bytes = field(default_factory=lambda: os.urandom(16))
    max_series: int = 2000
    counters: dict = field(default_factory=dict)
    gauges: dict = field(default_factory=dict)
    hists: dict = field(default_factory=dict)
    dropped_series: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        for name in ("accel_matched_total", "accel_refused_total", "accel_errors_total", "accel_shed_total",
                     "accel_reserved_total", "accel_released_total"):
            self.counters[(name, ())] = 0
        for name in ("accel_inflight", "accel_partitions_shared", "accel_inventory_age_seconds",
                     "accel_active_reservations", "accel_quarantined_devices", "accel_saturation_ratio"):
            self.gauges[(name, ())] = 0.0

    def _key(self, name: str, labels: dict) -> tuple | None:
        lab = []
        for k, v in sorted(labels.items()):
            v = pseudonym(v, self.tenant_key) if k == "tenant" else str(v)[:64]
            lab.append((k, v))
        key = (name, tuple(lab))
        total = len(self.counters) + len(self.gauges) + len(self.hists)
        if key not in self.counters and key not in self.gauges and key not in self.hists and total >= self.max_series:
            self.dropped_series += 1
            return None
        return key

    def inc(self, name: str, n: float = 1, **labels) -> None:
        with self._lock:
            k = self._key(name, labels)
            if k:
                self.counters[k] = self.counters.get(k, 0) + n
            self.counters[(name, ())] = self.counters.get((name, ()), 0) + (n if labels else 0)

    def set(self, name: str, v: float, **labels) -> None:
        with self._lock:
            k = self._key(name, labels)
            if k:
                self.gauges[k] = float(v)

    def observe(self, name: str, ms: float, **labels) -> None:
        with self._lock:
            k = self._key(name, labels)
            if not k:
                return
            h = self.hists.setdefault(k, {"buckets": [0] * (len(BUCKETS_MS) + 1), "sum": 0.0, "count": 0, "max": 0.0})
            h["buckets"][bisect_left(BUCKETS_MS, ms)] += 1
            h["sum"] += ms
            h["count"] += 1
            h["max"] = max(h["max"], ms)

    def quantile(self, name: str, q: float) -> float | None:
        """Upper-bound estimate from buckets, merged across label sets."""
        merged = [0] * (len(BUCKETS_MS) + 1)
        n = 0
        for (nm, _), h in self.hists.items():
            if nm == name:
                merged = [a + b for a, b in zip(merged, h["buckets"])]
                n += h["count"]
        if not n:
            return None
        target, acc = q * n, 0
        for i, c in enumerate(merged):
            acc += c
            if acc >= target:
                return BUCKETS_MS[i] if i < len(BUCKETS_MS) else float("inf")
        return float("inf")

    def snapshot(self) -> dict:
        with self._lock:
            f = lambda d: [{"name": k[0], "labels": dict(k[1]), "value": v} for k, v in sorted(d.items())]
            return {"counters": f(self.counters), "gauges": f(self.gauges),
                    "histograms": [{"name": k[0], "labels": dict(k[1]), **v} for k, v in sorted(self.hists.items())],
                    "dropped_series": self.dropped_series}

    def render(self) -> str:
        out = []
        esc = lambda s: str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        lab = lambda l: "{" + ",".join(f'{k}="{esc(v)}"' for k, v in l) + "}" if l else ""
        with self._lock:
            for (n, l), v in sorted(self.counters.items()):
                out.append(f"{n}{lab(l)} {v}")
            for (n, l), v in sorted(self.gauges.items()):
                out.append(f"{n}{lab(l)} {v}")
            for (n, l), h in sorted(self.hists.items()):
                acc = 0
                for b, c in zip(list(BUCKETS_MS) + ["+Inf"], h["buckets"]):
                    acc += c
                    out.append(f"{n}_bucket{lab(l + (('le', str(b)),))} {acc}")
                out.append(f"{n}_sum{lab(l)} {h['sum']}")
                out.append(f"{n}_count{lab(l)} {h['count']}")
        return "\n".join(out) + "\n"


@dataclass
class Logger:
    stream: TextIO | None = None
    node: str = "local"
    tenant_key: bytes = field(default_factory=lambda: os.urandom(16))
    level: str = "info"
    sample_rate: float = 1.0
    clock: Callable[[], float] = time.time
    failures: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40}

    def log(self, level: str, operation: str, msg: str, *, tenant: str | None = None, workload: str | None = None,
            decision_id: str | None = None, trace: TraceContext | None = None, code: str | None = None, **extra) -> dict | None:
        if self.LEVELS[level] < self.LEVELS[self.level]:
            return None
        if level in ("debug", "info") and self.sample_rate < 1.0 and secrets.randbelow(10_000) >= self.sample_rate * 10_000:
            return None
        rec = {"ts": self.clock(), "level": level, "component": "INV-72", "node": self.node,
               "tenant": pseudonym(tenant, self.tenant_key) if tenant else None, "workload": workload,
               "operation": operation, "decision_id": decision_id,
               "trace_id": trace.trace_id if trace else None, "span_id": trace.span_id if trace else None,
               "code": code, "msg": msg, "extra": redact(extra)}
        stream = self.stream if self.stream is not None else sys.stderr
        try:
            with self._lock:
                stream.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        except Exception:
            self.failures += 1   # telemetry loss never fails a decision (degraded, C056)
        return rec
