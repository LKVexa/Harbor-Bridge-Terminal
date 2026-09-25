"""Checklists 37, 38, 39: metrics, structured redacted logs, trace context.

* :class:`Metrics` - thread-safe counters, gauges and fixed-bucket latency
  histograms with Prometheus text exposition (``render()``).  Label values
  are bounded (``MAX_SERIES``) so a hostile caller cannot explode cardinality;
  overflow lands in a single ``__overflow__`` series and is itself counted.
* :class:`StructuredLogger` - JSON lines with stable ``node``, ``tenant``,
  ``workload``, ``op_id`` and ``trace_id`` fields.  Tenant identifiers are
  pseudonymised with a keyed hash when redaction is on (the default), and a
  denylist of secret-bearing keys is always scrubbed.
* W3C ``traceparent`` parsing/propagation (``parse_traceparent``,
  ``child_traceparent``).  Malformed headers are replaced by a fresh root
  trace rather than trusted.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sys
import threading
import time

BUCKETS_S = (0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
MAX_SERIES = 2000
SECRET_KEYS = frozenset({"secret", "key", "token", "password", "authorization", "mac", "_secret", "cookie"})

_LABEL_RE = re.compile(r"[^a-zA-Z0-9_:.\-]")


def _lv(v) -> str:
    return _LABEL_RE.sub("_", str(v))[:128]


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._c: dict[tuple, float] = {}
        self._g: dict[tuple, float] = {}
        self._h: dict[tuple, list] = {}
        self._series = 0

    def _key(self, name: str, labels: dict) -> tuple:
        return (name, tuple(sorted((k, _lv(v)) for k, v in labels.items())))

    def _admit(self, store: dict, key: tuple) -> tuple:
        if key in store:
            return key
        if self._series >= MAX_SERIES:
            self._c[("inv43_metric_series_overflow_total", ())] = self._c.get(("inv43_metric_series_overflow_total", ()), 0) + 1
            return (key[0], (("series", "__overflow__"),))
        self._series += 1
        return key

    def inc(self, name: str, value: float = 1.0, **labels) -> None:
        with self._lock:
            k = self._admit(self._c, self._key(name, labels))
            self._c[k] = self._c.get(k, 0.0) + value

    def set(self, name: str, value: float, **labels) -> None:
        with self._lock:
            k = self._admit(self._g, self._key(name, labels))
            self._g[k] = float(value)

    def observe(self, name: str, seconds: float, **labels) -> None:
        with self._lock:
            k = self._admit(self._h, self._key(name, labels))
            h = self._h.setdefault(k, [0] * (len(BUCKETS_S) + 1) + [0.0, 0])
            for i, b in enumerate(BUCKETS_S):
                if seconds <= b:
                    h[i] += 1
            h[len(BUCKETS_S)] += 1  # +Inf
            h[-2] += seconds
            h[-1] += 1

    def value(self, name: str, **labels) -> float:
        with self._lock:
            k = self._key(name, labels)
            return self._c.get(k, self._g.get(k, 0.0))

    def render(self) -> str:
        def fmt(labels):
            return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}" if labels else ""
        out = []
        with self._lock:
            for (n, l), v in sorted(self._c.items()):
                out.append(f"{n}{fmt(l)} {v}")
            for (n, l), v in sorted(self._g.items()):
                out.append(f"{n}{fmt(l)} {v}")
            for (n, l), h in sorted(self._h.items()):
                for i, b in enumerate(BUCKETS_S):
                    out.append(f"{n}_bucket{fmt(l + (('le', str(b)),))} {h[i]}")
                out.append(f"{n}_bucket{fmt(l + (('le', '+Inf'),))} {h[len(BUCKETS_S)]}")
                out.append(f"{n}_sum{fmt(l)} {h[-2]}")
                out.append(f"{n}_count{fmt(l)} {h[-1]}")
        return "\n".join(out) + "\n"


class StructuredLogger:
    def __init__(self, stream=None, *, redact_tenants: bool = True, pseudonym_key: bytes | None = None,
                 clock=time.time) -> None:
        self._stream = stream if stream is not None else sys.stderr
        self._redact = redact_tenants
        self._pk = pseudonym_key or secrets.token_bytes(32)
        self._clock = clock
        self._lock = threading.Lock()

    def pseudonym(self, tenant: str) -> str:
        return "t_" + hmac.new(self._pk, tenant.encode(), hashlib.sha256).hexdigest()[:16]

    def _scrub(self, obj):
        if isinstance(obj, dict):
            return {k: ("[REDACTED]" if k.lower() in SECRET_KEYS else self._scrub(v)) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._scrub(x) for x in obj]
        if isinstance(obj, bytes):
            return "[BYTES REDACTED]"
        return obj

    def log(self, level: str, event: str, *, node=None, tenants=(), workload=None, op_id=None,
            trace_id=None, **fields) -> dict:
        ts = list(tenants)
        if self._redact:
            # workload ids routinely embed tenant names (found by SecretLeakageTest), so they are
            # pseudonymised with the same key; the explain surface keeps the real ids behind authz.
            ts = [self.pseudonym(t) for t in ts]
            workload = None if workload is None else "w_" + self.pseudonym(str(workload))[2:]
        rec = {"ts": self._clock(), "level": level, "event": event, "component": "INV-43",
               "node": node, "tenants": ts, "workload": workload, "op_id": op_id,
               "trace_id": trace_id, **self._scrub(fields)}
        line = json.dumps(rec, sort_keys=True, default=str)
        with self._lock:
            self._stream.write(line + "\n")
        return rec


_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def new_traceparent() -> str:
    return f"00-{secrets.token_hex(16)}-{secrets.token_hex(8)}-01"


def parse_traceparent(header: str | None) -> tuple[str, str, bool]:
    """Return ``(trace_id, parent_span_id, trusted)``; untrusted -> fresh root."""
    if isinstance(header, str):
        m = _TP.match(header.strip())
        if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
            return m.group(1), m.group(2), True
    tp = new_traceparent()
    return tp[3:35], tp[36:52], False


def child_traceparent(trace_id: str) -> str:
    return f"00-{trace_id}-{secrets.token_hex(8)}-01"
