"""Metrics, structured logs, trace propagation, decision records and explain
views (INV-63-C071..C080).  Stdlib only; exporters are pluggable sinks."""
from __future__ import annotations

import bisect
import hashlib
import json
import os
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .security import redact

# ---------------------------------------------------------------- metrics (C072)
_BUCKETS_MS = (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000)
MAX_LABEL_SETS = 2000   # cardinality guard (C075)


class Metrics:
    def __init__(self) -> None:
        self.counters: dict[tuple[str, tuple], float] = {}
        self.gauges: dict[tuple[str, tuple], float] = {}
        self.hist: dict[tuple[str, tuple], list[float]] = {}
        self.dropped_series = 0
        self._lock = threading.Lock()

    def _key(self, name: str, labels: dict[str, str] | None, store: dict) -> tuple | None:
        k = (name, tuple(sorted((labels or {}).items())))
        if k not in store and len(store) >= MAX_LABEL_SETS:
            self.dropped_series += 1
            return None
        return k

    def inc(self, name: str, v: float = 1, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels, self.counters)
            if k:
                self.counters[k] = self.counters.get(k, 0) + v

    def set(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels, self.gauges)
            if k:
                self.gauges[k] = v

    def observe(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels, self.hist)
            if k:
                lst = self.hist.setdefault(k, [])
                bisect.insort(lst, v)
                if len(lst) > 10_000:           # bounded memory (C067)
                    del lst[::2]

    def quantile(self, name: str, q: float, **labels: str) -> float | None:
        lst = self.hist.get((name, tuple(sorted(labels.items()))))
        if not lst:
            return None
        return lst[min(len(lst) - 1, int(q * len(lst)))]

    def get(self, name: str, **labels: str) -> float:
        k = (name, tuple(sorted(labels.items())))
        return self.counters.get(k, self.gauges.get(k, 0.0))

    def exposition(self) -> str:
        """Prometheus text format."""
        lines = []

        def fmt(labels):
            return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}" if labels else ""
        for (n, l), v in sorted(self.counters.items()):
            lines.append(f"inv63_{n}_total{fmt(l)} {v}")
        for (n, l), v in sorted(self.gauges.items()):
            lines.append(f"inv63_{n}{fmt(l)} {v}")
        for (n, l), vals in sorted(self.hist.items()):
            for b in _BUCKETS_MS:
                lines.append(f"inv63_{n}_bucket{fmt(l + (('le', str(b)),))} {bisect.bisect_right(vals, b)}")
            lines.append(f"inv63_{n}_count{fmt(l)} {len(vals)}")
            lines.append(f"inv63_{n}_sum{fmt(l)} {sum(vals)}")
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- tracing (C074)
def new_trace_id(rng: random.Random | None = None) -> str:
    return (rng.getrandbits(128) if rng else int.from_bytes(os.urandom(16), "big")).to_bytes(16, "big").hex()


def new_span_id() -> str:
    return os.urandom(8).hex()


@dataclass
class SpanContext:
    trace_id: str
    span_id: str
    sampled: bool = True

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"

    @staticmethod
    def parse(tp: str | None, sampling: float = 1.0) -> "SpanContext":
        """W3C traceparent; malformed or all-zero ids start a new trace."""
        try:
            v, t, s, f = (tp or "").split("-")
            if v == "00" and len(t) == 32 and len(s) == 16 and int(t, 16) and int(s, 16):
                return SpanContext(t, s, bool(int(f, 16) & 1))   # remote parent
        except ValueError:
            pass
        return SpanContext(new_trace_id(), new_span_id(), random.random() < sampling)


@dataclass
class Span:
    name: str
    ctx: SpanContext
    parent: str | None
    start: float
    end: float | None = None
    attrs: dict[str, Any] = field(default_factory=dict)
    status: str = "OK"


class Tracer:
    def __init__(self, sink: Callable[[Span], None] | None = None, max_spans: int = 10_000):
        self.spans: list[Span] = []
        self.sink = sink
        self.max_spans = max_spans

    def span(self, name: str, parent: SpanContext, **attrs: Any) -> Span:
        sp = Span(name, SpanContext(parent.trace_id, new_span_id(), parent.sampled), parent.span_id,
                  time.monotonic(), attrs=redact(attrs))
        return sp

    def finish(self, sp: Span, status: str = "OK") -> None:
        sp.end, sp.status = time.monotonic(), status
        if sp.ctx.sampled:
            self.spans.append(sp)
            if len(self.spans) > self.max_spans:
                del self.spans[: len(self.spans) // 2]
            if self.sink:
                self.sink(sp)


# ---------------------------------------------------------------- logs (C073, C075)
REQUIRED_LOG_FIELDS = ("ts", "level", "event", "node", "tenant", "workload", "component", "operation", "trace_id")


class Logger:
    def __init__(self, node: str, sink: Callable[[str], None] | None = None, max_records: int = 50_000):
        self.node = node
        self.records: list[dict[str, Any]] = []
        self.sink = sink
        self.max_records = max_records

    def log(self, level: str, event: str, *, tenant: str = "-", workload: str = "-", component: str = "INV-63",
            operation: str = "-", trace_id: str = "-", **fields: Any) -> dict[str, Any]:
        rec = {"ts": time.time(), "level": level, "event": event, "node": self.node, "tenant": tenant,
               "workload": workload, "component": component, "operation": operation, "trace_id": trace_id}
        rec.update(redact(fields))
        self.records.append(rec)
        if len(self.records) > self.max_records:
            del self.records[: len(self.records) // 2]
        if self.sink:
            self.sink(json.dumps(rec, sort_keys=True, default=str))
        return rec


def export_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Export view for shared sinks: tenant ids pseudonymised, secrets already redacted (C075/C079)."""
    out = []
    for r in records:
        r = dict(r)
        if r.get("tenant") not in (None, "-"):
            r["tenant"] = tenant_hash(r["tenant"])
        out.append(r)
    return out


def tenant_hash(tenant: str) -> str:
    """Stable pseudonymous tenant id for shared/exported diagnostics (C075/C079)."""
    return "t-" + hashlib.sha256(("inv63:" + tenant).encode()).hexdigest()[:12]


# ---------------------------------------------------------------- decisions / explain (C076, C077, C078)
@dataclass
class Decision:
    seq: int
    ts: float
    tenant: str
    component: str
    action: str
    reason: str
    inputs: dict[str, Any]
    policies: list[str]
    constraints: dict[str, Any]
    trace_id: str
    release: str | None = None
    topology_digest: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class DecisionLog:
    def __init__(self, max_records: int = 100_000):
        self.items: list[Decision] = []
        self.max_records = max_records

    def record(self, **kw: Any) -> Decision:
        d = Decision(seq=len(self.items) + 1, ts=time.time(), **kw)
        if not d.reason:
            raise ValueError("every automated decision needs a reason")
        self.items.append(d)
        if len(self.items) > self.max_records:
            del self.items[: len(self.items) // 2]
        return d

    def explain(self, tenant: str, component: str, limit: int = 20) -> dict[str, Any]:
        rows = [d for d in self.items if d.tenant == tenant and d.component == component][-limit:]
        return {
            "schema": "INV63_EXPLAIN/1",
            "tenant": tenant,
            "component": component,
            "decisions": [{
                "seq": d.seq, "action": d.action, "why": d.reason, "inputs": d.inputs,
                "policies": d.policies, "constraints": d.constraints, "trace_id": d.trace_id,
                "release": d.release, "topology": d.topology_digest,
            } for d in rows],
            "text": "\n".join(f"#{d.seq} {d.action}: {d.reason} [policies: {', '.join(d.policies) or '-'}]" for d in rows),
        }


def topology_digest(hosts: dict[str, str]) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(hosts, sort_keys=True).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- alert classification (C080)
ALERT_CLASSES = ("ordinary_load", "degradation", "policy_rejection", "dependency_failure", "security_event", "stall")

ERROR_TO_ALERT = {
    "INV63-E-OVERLOADED": "degradation", "INV63-E-QUOTA": "ordinary_load",
    "INV63-E-POLICY": "policy_rejection", "INV63-E-FORBIDDEN": "security_event",
    "INV63-E-UNAUTHENTICATED": "security_event", "INV63-E-REPLAY": "security_event",
    "INV63-E-TENANT-ISOLATION": "security_event", "INV63-E-ARTIFACT-UNTRUSTED": "security_event",
    "INV63-E-DEPENDENCY-UNAVAILABLE": "dependency_failure", "INV63-E-CONTROL-PLANE-OFFLINE": "dependency_failure",
    "INV63-E-CIRCUIT-OPEN": "dependency_failure", "INV63-E-STALE-EPOCH": "security_event",
}


def classify_alert(code: str) -> str:
    return ERROR_TO_ALERT.get(code, "degradation")
