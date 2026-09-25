"""Metrics, structured logs, trace propagation, decision records and explain
(INV-40-C071..C080).

* Metrics: counters/gauges/histograms keyed by bounded label sets; label
  cardinality is capped (C075) and tenant ids are hashed in exported labels.
* Logs: JSON lines with stable node/tenant/workload/component/operation ids;
  secret-looking fields are redacted before emission.
* Trace: W3C ``traceparent`` parse/propagate; child span ids per operation.
* Decisions: every automated decision (admit, shed, refuse, retry, quarantine,
  rollback) records inputs, policy, and reason; ``explain(id)`` renders it.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
import time
from collections import defaultdict, deque

MAX_SERIES = 2000
BUCKETS_MS = (100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000, 64000)
_TP = re.compile(r"00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})")
_SECRET = re.compile(r"(token|secret|password|credential|key)", re.I)


def tenant_label(t: str) -> str:
    return "t-" + hashlib.sha256(t.encode()).hexdigest()[:12]


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.counters = defaultdict(int)
        self.gauges = {}
        self.hist = defaultdict(lambda: [0] * (len(BUCKETS_MS) + 1))
        self.dropped_series = 0

    def _key(self, name, labels):
        k = (name, tuple(sorted((labels or {}).items())))
        n = len(self.counters) + len(self.gauges) + len(self.hist)
        if k not in self.counters and k not in self.gauges and k not in self.hist and n >= MAX_SERIES:
            self.dropped_series += 1
            return None
        return k

    def inc(self, name, labels=None, n=1):
        with self._lock:
            k = self._key(name, labels)
            if k:
                self.counters[k] += n

    def set(self, name, value, labels=None):
        with self._lock:
            k = self._key(name, labels)
            if k:
                self.gauges[k] = value

    def observe(self, name, ms, labels=None):
        with self._lock:
            k = self._key(name, labels)
            if k:
                i = next((i for i, b in enumerate(BUCKETS_MS) if ms <= b), len(BUCKETS_MS))
                self.hist[k][i] += 1

    def snapshot(self) -> dict:
        with self._lock:
            f = lambda k: {"name": k[0], "labels": dict(k[1])}  # noqa: E731
            return {"counters": [dict(f(k), value=v) for k, v in self.counters.items()],
                    "gauges": [dict(f(k), value=v) for k, v in self.gauges.items()],
                    "histograms": [dict(f(k), buckets_ms=list(BUCKETS_MS), counts=v) for k, v in self.hist.items()],
                    "dropped_series": self.dropped_series}


def parse_traceparent(tp: str | None) -> tuple[str, str]:
    m = _TP.fullmatch(tp or "")
    if not m or m.group(1) == "0" * 32:
        return secrets.token_hex(16), secrets.token_hex(8)
    return m.group(1), m.group(2)


def child_traceparent(trace_id: str) -> tuple[str, str]:
    span = secrets.token_hex(8)
    return span, f"00-{trace_id}-{span}-01"


def _redact(v, k=""):
    if _SECRET.search(k):
        return "[REDACTED]"
    if isinstance(v, dict):
        return {kk: _redact(vv, kk) for kk, vv in v.items()}
    if isinstance(v, list):
        return [_redact(x) for x in v]
    return v


class Logger:
    def __init__(self, node: str, component: str = "INV-40", sink=None, max_lines: int = 10000):
        self.node, self.component = node, component
        self.lines: deque = deque(maxlen=max_lines)
        self.sink = sink
        self.sink_failures = 0

    def log(self, level: str, op: str, msg: str, *, tenant=None, workload=None, trace_id=None, **fields):
        rec = {"ts": round(time.time(), 3), "level": level, "node": self.node, "component": self.component,
               "operation": op, "tenant": tenant_label(tenant) if tenant else None, "workload": workload,
               "trace_id": trace_id, "msg": msg, **_redact(fields)}
        line = json.dumps(rec, sort_keys=True, default=str)
        self.lines.append(line)
        if self.sink:
            try:
                self.sink(line)
            except Exception:  # noqa: BLE001 - telemetry export is noncritical (C056)
                self.sink_failures += 1
        return rec


class Decisions:
    def __init__(self, maxlen: int = 5000):
        self._d: dict[str, dict] = {}
        self._order: deque = deque(maxlen=maxlen)

    def record(self, kind: str, outcome: str, reason: str, *, inputs: dict, policy: str, trace_id=None) -> str:
        did = "d-" + secrets.token_hex(6)
        if len(self._order) == self._order.maxlen:
            self._d.pop(self._order[0], None)
        self._order.append(did)
        self._d[did] = {"id": did, "kind": kind, "outcome": outcome, "reason": reason,
                        "inputs": _redact(inputs), "policy": policy, "trace_id": trace_id, "ts": time.time()}
        return did

    def get(self, did):
        return self._d.get(did)

    def all(self):
        return [self._d[i] for i in self._order if i in self._d]

    def explain(self, did: str) -> str:
        d = self._d.get(did)
        if not d:
            return f"no decision {did}"
        ins = ", ".join(f"{k}={v}" for k, v in sorted(d["inputs"].items()))
        return (f"[{d['id']}] {d['kind']} -> {d['outcome']}\n  because: {d['reason']}\n"
                f"  policy:  {d['policy']}\n  inputs:  {ins}\n  trace:   {d['trace_id']}")
