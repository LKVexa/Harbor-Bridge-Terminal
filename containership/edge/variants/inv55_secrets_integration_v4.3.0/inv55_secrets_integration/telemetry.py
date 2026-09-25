"""Metrics, structured logging, tracing, decision ledger (checklist #72-#77, #75, #79).

* ``Metrics``: counters + fixed-bucket histograms, Prometheus text exposition.
  Label values are restricted to bounded enums (reason codes, outcomes, tenant ids
  from config) -- never secret names or values (bounded cardinality).
* ``JsonLogger``: one JSON object per line, every field passed through redaction.
* ``Tracer``: W3C ``traceparent`` parsing/propagation with in-memory span export.
* ``DecisionLedger``: bounded ring of explainable decisions for the operator view.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import json
import re
import secrets as _rand
import threading
from typing import Callable, TextIO

from .errors import redact_text

LATENCY_BUCKETS_S = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
_LABEL_OK = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


class Metrics:
    def __init__(self, max_series: int = 2_000) -> None:
        self._c: dict[tuple, float] = {}
        self._h: dict[tuple, list] = {}
        self._max = max_series
        self._lock = threading.Lock()
        self.dropped_series = 0

    @staticmethod
    def _key(name: str, labels: dict) -> tuple:
        for v in labels.values():
            if not _LABEL_OK.match(str(v)):
                raise ValueError("metric label value not in bounded alphabet")
        return (name, tuple(sorted(labels.items())))

    def inc(self, name: str, value: float = 1.0, **labels) -> None:
        k = self._key(name, labels)
        with self._lock:
            if k not in self._c and len(self._c) + len(self._h) >= self._max:
                self.dropped_series += 1
                return
            self._c[k] = self._c.get(k, 0.0) + value

    def observe(self, name: str, seconds: float, **labels) -> None:
        k = self._key(name, labels)
        with self._lock:
            h = self._h.get(k)
            if h is None:
                if len(self._c) + len(self._h) >= self._max:
                    self.dropped_series += 1
                    return
                h = self._h[k] = [[0] * len(LATENCY_BUCKETS_S), 0, 0.0]
            for i, b in enumerate(LATENCY_BUCKETS_S):
                if seconds <= b:
                    h[0][i] += 1
            h[1] += 1
            h[2] += seconds

    def counter(self, name: str, **labels) -> float:
        return self._c.get(self._key(name, labels), 0.0)

    def exposition(self) -> str:
        def fmt(labels: tuple, extra: str = "") -> str:
            parts = [f'{k}="{v}"' for k, v in labels]
            if extra:
                parts.append(extra)
            return "{" + ",".join(parts) + "}" if parts else ""
        out = []
        with self._lock:
            for (name, labels), v in sorted(self._c.items()):
                out.append(f"{name}{fmt(labels)} {v}")
            for (name, labels), (buckets, count, total) in sorted(self._h.items()):
                for b, n in zip(LATENCY_BUCKETS_S, buckets):
                    le = 'le="%s"' % b
                    out.append(f"{name}_bucket{fmt(labels, le)} {n}")
                inf = 'le="+Inf"'
                out.append(f"{name}_bucket{fmt(labels, inf)} {count}")
                out.append(f"{name}_count{fmt(labels)} {count}")
                out.append(f"{name}_sum{fmt(labels)} {total}")
        return "\n".join(out) + "\n"


class JsonLogger:
    def __init__(self, stream: TextIO, clock: Callable[[], float], component: str = "INV-55") -> None:
        self.stream, self.clock, self.component = stream, clock, component
        self._lock = threading.Lock()

    def log(self, level: str, event: str, **fields) -> None:
        rec = {"ts": self.clock(), "level": level, "component": self.component, "event": event}
        for k, v in fields.items():
            rec[k] = redact_text(v) if isinstance(v, str) else v
        line = json.dumps(rec, sort_keys=True, default=lambda o: redact_text(repr(o)))
        with self._lock:
            self.stream.write(line + "\n")


_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    start: float
    end: float | None = None
    attrs: dict = field(default_factory=dict)

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-01"


class Tracer:
    def __init__(self, clock: Callable[[], float], max_spans: int = 10_000) -> None:
        self.clock = clock
        self.finished: deque[Span] = deque(maxlen=max_spans)

    def start(self, name: str, traceparent: str | None = None, **attrs) -> Span:
        m = _TRACEPARENT.match(traceparent) if isinstance(traceparent, str) else None
        trace_id = m.group(1) if m and m.group(1) != "0" * 32 else _rand.token_hex(16)
        parent = m.group(2) if m else None
        safe = {k: redact_text(str(v)) for k, v in attrs.items()}
        return Span(trace_id, _rand.token_hex(8), parent, name, self.clock(), attrs=safe)

    def finish(self, span: Span, **attrs) -> None:
        span.attrs.update({k: redact_text(str(v)) for k, v in attrs.items()})
        span.end = self.clock()
        self.finished.append(span)


@dataclass(frozen=True)
class DecisionRecord:
    at: float
    request_id: str
    operation: str
    tenant: str
    subject: str
    secret: str
    outcome: str
    reason: str
    policy_digest: str
    config_digest: str
    release: str
    trace_id: str | None


class DecisionLedger:
    def __init__(self, limit: int = 10_000) -> None:
        self._d: deque[DecisionRecord] = deque(maxlen=limit)
        self._lock = threading.Lock()

    def add(self, rec: DecisionRecord) -> None:
        with self._lock:
            self._d.append(rec)

    def explain(self, request_id: str) -> dict | None:
        """Operator explain view (checklist #77)."""
        with self._lock:
            for r in reversed(self._d):
                if r.request_id == request_id:
                    return {
                        "request_id": r.request_id,
                        "decision": r.outcome,
                        "why": r.reason,
                        "who": {"tenant": r.tenant, "subject": r.subject},
                        "what": {"operation": r.operation, "secret": r.secret},
                        "evaluated_against": {"policy": r.policy_digest, "config": r.config_digest,
                                              "release": r.release},
                        "trace_id": r.trace_id,
                    }
        return None

    def __len__(self) -> int:
        return len(self._d)
