# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Metrics, structured logs, trace propagation, decision records (GAP-049..GAP-054).

* Metrics: counters/gauges/histograms with bounded label cardinality; tenant is
  hashed into a fixed number of buckets so high-cardinality detail never leaks raw
  tenant ids. Exported as Prometheus text.
* Logs: one JSON object per line with stable node/tenant/workload/component/
  operation ids, secret-redacted.
* Traces: W3C ``traceparent`` parse/validate/child-span.
* Decisions: INV30_DECISION/1 records explaining every automated allow/deny.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import time
from collections import defaultdict

from .secret_refs import redact

BUCKETS_MS = (0.01, 0.05, 0.1, 0.5, 1, 5, 10, 50, 100)
TENANT_BUCKETS = 64
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def tenant_bucket(tenant: str) -> str:
    return "t%02d" % (int(hashlib.sha256(tenant.encode()).hexdigest(), 16) % TENANT_BUCKETS)


class Metrics:
    MAX_SERIES = 10_000

    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict[tuple, float] = defaultdict(float)
        self.gauges: dict[tuple, float] = {}
        self.hist: dict[tuple, list[int]] = {}
        self.hist_sum: dict[tuple, float] = defaultdict(float)

    def _key(self, name, labels):
        return (name, tuple(sorted(labels.items())))

    def inc(self, name, value=1.0, **labels):
        with self._lock:
            k = self._key(name, labels)
            if k in self.counters or len(self.counters) < self.MAX_SERIES:
                self.counters[k] += value

    def set(self, name, value, **labels):
        with self._lock:
            self.gauges[self._key(name, labels)] = value

    def observe_ms(self, name, ms, **labels):
        with self._lock:
            k = self._key(name, labels)
            b = self.hist.setdefault(k, [0] * (len(BUCKETS_MS) + 1))
            for i, edge in enumerate(BUCKETS_MS):
                if ms <= edge:
                    b[i] += 1
                    break
            else:
                b[-1] += 1
            self.hist_sum[k] += ms

    def get(self, name, **labels):
        return self.counters.get(self._key(name, labels), 0.0)

    def prometheus(self) -> str:
        def lab(ls, extra=()):
            items = list(ls) + list(extra)
            return "{" + ",".join(f'{k}="{v}"' for k, v in items) + "}" if items else ""
        lines = []
        with self._lock:
            for (n, ls), v in sorted(self.counters.items()):
                lines.append(f"inv30_{n}_total{lab(ls)} {v}")
            for (n, ls), v in sorted(self.gauges.items()):
                lines.append(f"inv30_{n}{lab(ls)} {v}")
            for (n, ls), b in sorted(self.hist.items()):
                acc = 0
                for edge, c in zip(list(BUCKETS_MS) + ["+Inf"], b):
                    acc += c
                    lines.append(f"inv30_{n}_bucket{lab(ls, [('le', edge)])} {acc}")
                lines.append(f"inv30_{n}_count{lab(ls)} {acc}")
                lines.append(f"inv30_{n}_sum{lab(ls)} {self.hist_sum[(n, ls)]}")
        return "\n".join(lines) + "\n"


class Logger:
    def __init__(self, *, node: str, component="INV-30", stream=None, level="info"):
        self.node, self.component = node, component
        self.stream = stream if stream is not None else sys.stderr
        self.records: list[dict] = []
        self._lock = threading.Lock()

    def log(self, level: str, event: str, *, tenant="-", workload="-", operation="-", correlation_id="-",
            trace_id="-", **fields):
        rec = {"ts": round(time.time(), 6), "level": level, "event": event, "node": self.node,
               "component": self.component, "tenant_bucket": tenant_bucket(tenant) if tenant != "-" else "-",
               "workload": workload, "operation": operation, "correlation_id": correlation_id,
               "trace_id": trace_id, "fields": redact(fields)}
        with self._lock:
            self.records.append(rec)
            if len(self.records) > 10_000:
                del self.records[:5_000]
            if self.stream is not False:
                self.stream.write(json.dumps(rec, sort_keys=True) + "\n")
        return rec


def parse_traceparent(tp: str | None) -> tuple[str, str, str] | None:
    """Return (trace_id, parent_span_id, flags) or None for absent/invalid/all-zero."""
    if not tp:
        return None
    m = _TP.match(tp.strip().lower())
    if not m or set(m.group(1)) == {"0"} or set(m.group(2)) == {"0"}:
        return None
    return m.groups()


def child_traceparent(tp: str | None) -> tuple[str, str]:
    parsed = parse_traceparent(tp)
    trace_id = parsed[0] if parsed else os.urandom(16).hex()
    flags = parsed[2] if parsed else "01"
    span = os.urandom(8).hex()
    return trace_id, f"00-{trace_id}-{span}-{flags}"


class DecisionLog:
    def __init__(self, *, node: str, release: str, capacity: int = 10_000):
        self.node, self.release, self.capacity = node, release, capacity
        self.records: list[dict] = []
        self._lock = threading.Lock()

    def record(self, decision: str, reason: str, *, inputs: dict, policy: str, correlation_id: str) -> dict:
        rec = {"schema": "INV30_DECISION/1", "decision": decision, "reason": reason, "inputs": redact(inputs),
               "policy": policy, "correlation_id": correlation_id, "ts": round(time.time(), 6),
               "release": self.release, "node": self.node}
        with self._lock:
            self.records.append(rec)
            if len(self.records) > self.capacity:
                del self.records[: self.capacity // 2]
        return rec

    def explain(self, correlation_id: str) -> list[dict]:
        return [r for r in self.records if r["correlation_id"] == correlation_id]
