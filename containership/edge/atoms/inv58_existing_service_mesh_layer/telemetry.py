"""Metrics, structured logs, trace propagation, diagnostic privacy (MC-025, C072–C075).

* Metrics cover rate/errors/latency/saturation/backlog/resource with bounded
  label cardinality — excess label values collapse into ``__overflow__``.
* Structured log records carry stable node/tenant/workload/component/operation
  identifiers.  High-cardinality or identifying values (subjects, SANs, source
  workloads) are emitted as keyed pseudonyms, never raw, unless the operator
  explicitly disables redaction in a non-production diagnostic build.
* W3C ``traceparent`` is validated strictly and propagated as a child span.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
from bisect import bisect_left
from threading import RLock
from typing import Callable

from .secret_refs import redact

COMPONENT = "INV-58"
OVERFLOW = "__overflow__"
LATENCY_BUCKETS_S = (0.00001, 0.00005, 0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")

METRIC_CATALOG = {
    "inv58_requests_total": ("counter", ("operation", "tenant", "outcome")),
    "inv58_errors_total": ("counter", ("operation", "code")),
    "inv58_latency_seconds": ("histogram", ("operation",)),
    "inv58_effective_attempts": ("histogram", ("tenant",)),
    "inv58_bypass_flows_total": ("counter", ("tenant",)),
    "inv58_identity_unmapped_total": ("counter", ("reason",)),
    "inv58_authz_decisions_total": ("counter", ("operation", "code")),
    "inv58_admission_shed_total": ("counter", ("tenant",)),
    "inv58_inflight": ("gauge", ()),
    "inv58_saturation_ratio": ("gauge", ()),
    "inv58_route_registry_size": ("gauge", ("tenant",)),
    "inv58_bypass_backlog": ("gauge", ()),
    "inv58_breaker_state": ("gauge", ("dependency",)),
    "inv58_config_activations_total": ("counter", ("result",)),
    "inv58_audit_records": ("gauge", ()),
}


class Metrics:
    def __init__(self, max_label_values: int = 1000):
        self._max = max_label_values
        self._seen: dict[tuple[str, str], set] = {}
        self._counters: dict[tuple, float] = {}
        self._gauges: dict[tuple, float] = {}
        self._hist: dict[tuple, list] = {}
        self._lock = RLock()

    def _labels(self, name: str, labels: dict) -> tuple:
        kind, keys = METRIC_CATALOG[name]
        if set(labels) != set(keys):
            raise ValueError(f"{name} requires labels {keys}")
        out = []
        for k in keys:
            v = str(labels[k])[:128]
            seen = self._seen.setdefault((name, k), set())
            if v not in seen and len(seen) >= self._max:
                v = OVERFLOW
            else:
                seen.add(v)
            out.append((k, v))
        return (name, tuple(out))

    def inc(self, name: str, n: float = 1, **labels) -> None:
        with self._lock:
            key = self._labels(name, labels)
            self._counters[key] = self._counters.get(key, 0) + n

    def set(self, name: str, value: float, **labels) -> None:
        with self._lock:
            self._gauges[self._labels(name, labels)] = float(value)

    def observe(self, name: str, value: float, **labels) -> None:
        with self._lock:
            key = self._labels(name, labels)
            h = self._hist.setdefault(key, [0] * (len(LATENCY_BUCKETS_S) + 1) + [0.0, 0])
            h[bisect_left(LATENCY_BUCKETS_S, value)] += 1
            h[-2] += value
            h[-1] += 1

    def value(self, name: str, **labels) -> float:
        with self._lock:
            key = (name, tuple((k, str(labels[k])) for k in METRIC_CATALOG[name][1]))
            return self._counters.get(key, self._gauges.get(key, 0.0))

    def export(self) -> dict:
        with self._lock:
            return {
                "counters": [{"name": n, "labels": dict(l), "value": v} for (n, l), v in sorted(self._counters.items())],
                "gauges": [{"name": n, "labels": dict(l), "value": v} for (n, l), v in sorted(self._gauges.items())],
                "histograms": [{"name": n, "labels": dict(l), "buckets": list(zip(LATENCY_BUCKETS_S + (float("inf"),), h[:-2])),
                                "sum": h[-2], "count": h[-1]} for (n, l), h in sorted(self._hist.items())],
            }

    def prometheus(self) -> str:
        lines = []
        for rec in self.export()["counters"] + self.export()["gauges"]:
            lab = ",".join(f'{k}="{v}"' for k, v in rec["labels"].items())
            lines.append(f"{rec['name']}{{{lab}}} {rec['value']}")
        return "\n".join(lines) + "\n"


class TraceContext:
    __slots__ = ("trace_id", "span_id", "flags")

    def __init__(self, trace_id: str, span_id: str, flags: str = "01"):
        self.trace_id, self.span_id, self.flags = trace_id, span_id, flags

    @classmethod
    def parse(cls, header: str | None) -> "TraceContext | None":
        if not isinstance(header, str):
            return None
        m = _TRACEPARENT.fullmatch(header.strip())
        if not m or set(m.group(1)) == {"0"} or set(m.group(2)) == {"0"}:
            return None
        return cls(m.group(1), m.group(2), m.group(3))

    @classmethod
    def new(cls) -> "TraceContext":
        return cls(os.urandom(16).hex(), os.urandom(8).hex())

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, os.urandom(8).hex(), self.flags)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"


class Pseudonymizer:
    def __init__(self, key: bytes):
        if len(key) < 16:
            raise ValueError("pseudonym key too short")
        self._key = key

    def __call__(self, value: str | None) -> str | None:
        if value is None:
            return None
        return "p:" + hmac.new(self._key, str(value).encode(), hashlib.sha256).hexdigest()[:16]


class StructuredLogger:
    """JSON-lines logger with a fixed envelope; bounded in-memory ring."""

    PSEUDONYMIZED = ("subject", "san", "src", "workload", "actor")

    def __init__(self, node: str, pseudo: Pseudonymizer, sink: Callable[[str], None] | None = None,
                 max_records: int = 5_000, clock: Callable[[], float] = time.time, redact_hc: bool = True):
        self.node, self._pseudo, self._sink = node, pseudo, sink
        self._ring: list[dict] = []
        self._max = max_records
        self.clock = clock
        self.redact_hc = redact_hc
        self._lock = RLock()

    def log(self, level: str, event: str, *, operation: str, tenant: str | None = None,
            trace: TraceContext | None = None, correlation_id: str | None = None, **fields) -> dict:
        safe = {}
        for k, v in fields.items():
            if self.redact_hc and k in self.PSEUDONYMIZED:
                safe[k] = self._pseudo(v)
            else:
                safe[k] = v
        rec = {
            "ts": round(self.clock(), 6), "level": level, "component": COMPONENT, "node": self.node,
            "tenant": tenant, "operation": operation, "event": event,
            "trace_id": trace.trace_id if trace else None, "span_id": trace.span_id if trace else None,
            "correlation_id": correlation_id, "fields": redact(safe),
        }
        line = json.dumps(rec, sort_keys=True, default=str)
        with self._lock:
            self._ring.append(rec)
            del self._ring[:-self._max]
        if self._sink:
            self._sink(line)
        return rec

    def records(self) -> list[dict]:
        with self._lock:
            return list(self._ring)
