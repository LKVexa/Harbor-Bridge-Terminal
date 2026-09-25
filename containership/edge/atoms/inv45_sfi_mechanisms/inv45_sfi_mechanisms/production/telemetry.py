"""Metrics, structured logs, trace propagation and decision explanations (C071-C079).

* **Metrics** - counters, gauges and fixed-bucket histograms with a bounded label
  space (``tenant`` is hashed into at most ``MAX_SERIES`` series; beyond that
  samples go to ``__overflow__``), exported in Prometheus text format.
* **Logs** - one JSON object per line with stable ``node``, ``component``,
  ``tenant``, ``workload``, ``operation`` and W3C ``trace_id``/``span_id``.
  Values pass the same allowlist/redaction as audit events.
* **Traces** - W3C ``traceparent`` parse/emit; a malformed header starts a new
  trace (it is never trusted as authority).  Tenant context is never inherited
  from the header.
* **Explain** - every automated decision is stored as a sanitized record linking
  inputs (digests), policy (profile/config digest), topology (node, engine) and
  the constraint that decided; ``explain(decision_id)`` renders it for operators.
"""
from __future__ import annotations

import json
import re
import secrets as _secrets
import socket
import sys
import threading
import time
from collections import deque
from typing import Any, Callable, Optional, TextIO

from .audit import redact

MAX_SERIES = 256
BUCKETS_MS = (1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self.gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self.hist: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}
        self.help: dict[str, tuple[str, str]] = {}

    def _key(self, name: str, labels: dict[str, str], store: dict[Any, Any]) -> tuple[str, tuple[tuple[str, str], ...]]:
        key = (name, tuple(sorted((k, str(v)[:64]) for k, v in labels.items())))
        if key not in store and sum(1 for k in store if k[0] == name) >= MAX_SERIES:
            key = (name, (("series", "__overflow__"),))
        return key

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels, self.counters)
            self.counters[k] = self.counters.get(k, 0.0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self.gauges[self._key(name, labels, self.gauges)] = value

    def observe_ms(self, name: str, ms: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels, self.hist)
            h = self.hist.setdefault(k, [0.0] * (len(BUCKETS_MS) + 2))  # buckets + count + sum
            for i, b in enumerate(BUCKETS_MS):
                if ms <= b:
                    h[i] += 1
            h[-2] += 1
            h[-1] += ms

    def get(self, name: str, **labels: str) -> float:
        k = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        return self.counters.get(k, self.gauges.get(k, 0.0))

    def prometheus(self) -> str:
        def lbl(ls: tuple[tuple[str, str], ...], extra: str = "") -> str:
            parts = [f'{k}="{v}"' for k, v in ls] + ([extra] if extra else [])
            return "{" + ",".join(parts) + "}" if parts else ""
        out = []
        with self._lock:
            for (n, ls), v in sorted(self.counters.items()):
                out.append(f"{n}_total{lbl(ls)} {v:g}")
            for (n, ls), v in sorted(self.gauges.items()):
                out.append(f"{n}{lbl(ls)} {v:g}")
            for (n, ls), h in sorted(self.hist.items()):
                for i, b in enumerate(BUCKETS_MS):
                    le = 'le="%s"' % b
                    out.append(f"{n}_bucket{lbl(ls, le)} {h[i]:g}")
                inf = 'le="+Inf"'
                out.append(f"{n}_bucket{lbl(ls, inf)} {h[-2]:g}")
                out.append(f"{n}_count{lbl(ls)} {h[-2]:g}")
                out.append(f"{n}_sum{lbl(ls)} {h[-1]:g}")
        return "\n".join(out) + "\n"


class Trace:
    __slots__ = ("trace_id", "span_id", "flags")

    def __init__(self, trace_id: str, span_id: str, flags: str = "01"):
        self.trace_id, self.span_id, self.flags = trace_id, span_id, flags

    @classmethod
    def new(cls) -> "Trace":
        return cls(_secrets.token_hex(16), _secrets.token_hex(8))

    @classmethod
    def from_header(cls, header: Optional[str]) -> "Trace":
        m = _TP.match(header or "")
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return cls.new()
        return cls(m.group(1), _secrets.token_hex(8), m.group(3))

    def child(self) -> "Trace":
        return Trace(self.trace_id, _secrets.token_hex(8), self.flags)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"


class Logger:
    LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40}

    def __init__(self, component: str = "inv45-sfi", level: str = "info", stream: Optional[TextIO] = None,
                 node: Optional[str] = None, clock: Callable[[], float] = time.time):
        self.component = component
        self.level = self.LEVELS[level]
        self.stream = stream or sys.stderr
        self.node = node or socket.gethostname()
        self.clock = clock
        self.records: deque[dict[str, Any]] = deque(maxlen=1000)  # bounded in-memory tail
        self._lock = threading.Lock()

    def log(self, level: str, operation: str, trace: Optional[Trace] = None, **fields: Any) -> dict[str, Any]:
        rec = {"ts": round(self.clock(), 6), "level": level, "node": self.node, "component": self.component,
               "operation": operation}
        if trace is not None:
            rec["trace_id"], rec["span_id"] = trace.trace_id, trace.span_id
        rec.update(redact(fields))
        if self.LEVELS[level] >= self.level:
            with self._lock:
                self.records.append(rec)
                self.stream.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")
        return rec


class Explainer:
    """Durable-in-memory decision records with bounded retention; persisted via audit."""

    def __init__(self, capacity: int = 10_000):
        self._d: dict[str, dict[str, Any]] = {}
        self._order: deque[str] = deque()
        self.capacity = capacity
        self._lock = threading.Lock()

    def record(self, *, decision: str, outcome: str, inputs: dict[str, Any], policy: dict[str, Any],
               topology: dict[str, Any], constraint: str, trace: Optional[Trace] = None) -> str:
        did = "dec_" + _secrets.token_hex(8)
        rec = {"decision_id": did, "decision": decision, "outcome": outcome,
               "inputs": redact(inputs), "policy": redact(policy), "topology": dict(topology),
               "deciding_constraint": constraint[:256], "trace_id": trace.trace_id if trace else None,
               "at": time.time()}
        with self._lock:
            self._d[did] = rec
            self._order.append(did)
            while len(self._order) > self.capacity:
                self._d.pop(self._order.popleft(), None)
        return did

    def get(self, did: str) -> Optional[dict[str, Any]]:
        return self._d.get(did)

    def explain(self, did: str) -> str:
        r = self._d.get(did)
        if r is None:
            return f"no decision {did} (expired from retention or unknown)"
        lines = [f"Decision {did}: {r['decision']} -> {r['outcome']}",
                 f"  deciding constraint: {r['deciding_constraint']}",
                 "  inputs:   " + ", ".join(f"{k}={v}" for k, v in sorted(r["inputs"].items())),
                 "  policy:   " + ", ".join(f"{k}={v}" for k, v in sorted(r["policy"].items())),
                 "  topology: " + ", ".join(f"{k}={v}" for k, v in sorted(r["topology"].items()))]
        if r["trace_id"]:
            lines.append(f"  trace:    {r['trace_id']}")
        return "\n".join(lines)
