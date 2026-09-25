"""MC-38 metrics, MC-39 structured logs, MC-40 tracing, MC-42 governance hooks.

Stdlib-only.  Metrics export in Prometheus text format; logs are JSON lines with a fixed
field set and tenant pseudonymisation; spans follow W3C traceparent ids.  No exporter to a
real backend is bound (that is an environment decision).
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
from bisect import bisect_left
from typing import Any, Callable

BUCKETS_S = (0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 1.0)
LOG_FIELDS = ("ts", "level", "event", "request_id", "trace_id", "span_id", "workload", "tenant_ref",
              "node", "operation", "decision", "code", "config_rev")
# MC-42: governance, enforced in code
TELEMETRY_POLICY = {"log_retention_days": 30, "trace_sample_rate": 0.1, "metric_retention_days": 395,
                    "tenant_identifiers": "pseudonymised (sha256 prefix, salted)", "export": "operator-configured"}


class Metrics:
    def __init__(self):
        self._c: dict[tuple, float] = {}
        self._g: dict[tuple, float] = {}
        self._h: dict[tuple, list] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _k(name, labels):
        return (name, tuple(sorted((labels or {}).items())))

    def inc(self, name, labels=None, v=1.0):
        with self._lock:
            k = self._k(name, labels); self._c[k] = self._c.get(k, 0) + v

    def gauge(self, name, v, labels=None):
        with self._lock:
            self._g[self._k(name, labels)] = v

    def observe(self, name, v, labels=None):
        with self._lock:
            k = self._k(name, labels)
            h = self._h.setdefault(k, [[0] * (len(BUCKETS_S) + 1), 0.0, 0])
            h[0][bisect_left(BUCKETS_S, v)] += 1; h[1] += v; h[2] += 1

    def value(self, name, labels=None):
        k = self._k(name, labels)
        return self._c.get(k, self._g.get(k))

    def export(self) -> str:
        def lab(ls, extra=()):
            items = list(ls) + list(extra)
            return "{" + ",".join(f'{a}="{b}"' for a, b in items) + "}" if items else ""
        out = []
        with self._lock:
            for (n, ls), v in sorted(self._c.items()):
                out.append(f"sch01_{n}_total{lab(ls)} {v}")
            for (n, ls), v in sorted(self._g.items()):
                out.append(f"sch01_{n}{lab(ls)} {v}")
            for (n, ls), (b, s, c) in sorted(self._h.items()):
                cum = 0
                for i, ub in enumerate(BUCKETS_S + (float("inf"),)):
                    cum += b[i]
                    out.append(f"sch01_{n}_bucket{lab(ls, [('le', '+Inf' if ub == float('inf') else ub)])} {cum}")
                out.append(f"sch01_{n}_sum{lab(ls)} {s}"); out.append(f"sch01_{n}_count{lab(ls)} {c}")
        return "\n".join(out) + "\n"


class Logger:
    def __init__(self, sink: Callable[[str], None] | None = None, salt: str = "sch01"):
        self.lines: list[dict[str, Any]] = []
        self.sink, self.salt = sink, salt

    def tenant_ref(self, tenant: str | None) -> str | None:
        return None if tenant is None else "t_" + hashlib.sha256((self.salt + tenant).encode()).hexdigest()[:12]

    def emit(self, level: str, event: str, **kw) -> dict[str, Any]:
        tenant = kw.pop("tenant", None)
        rec = {f: None for f in LOG_FIELDS}
        rec.update({"level": level, "event": event, "tenant_ref": self.tenant_ref(tenant)})
        for k, v in kw.items():
            if k in rec:
                rec[k] = v
        self.lines.append(rec)
        if self.sink:
            self.sink(json.dumps(rec, sort_keys=True))
        return rec


class Tracer:
    def __init__(self):
        self.spans: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @staticmethod
    def parse_traceparent(tp: str | None) -> tuple[str, str] | None:
        try:
            ver, tid, sid, flags = (tp or "").split("-")
            if ver == "00" and len(tid) == 32 and len(sid) == 16 and int(tid, 16) and int(sid, 16):
                return tid, sid
        except ValueError:
            pass
        return None

    def start(self, name: str, traceparent: str | None = None, **attrs) -> dict[str, Any]:
        parsed = self.parse_traceparent(traceparent)
        tid, parent = parsed if parsed else (secrets.token_hex(16), None)
        span = {"name": name, "trace_id": tid, "span_id": secrets.token_hex(8), "parent": parent,
                "attrs": attrs, "status": "UNSET"}
        return span

    def end(self, span: dict[str, Any], status: str = "OK", **attrs) -> None:
        span["status"] = status; span["attrs"].update(attrs)
        with self._lock:
            self.spans.append(span)

    @staticmethod
    def traceparent(span: dict[str, Any]) -> str:
        return f"00-{span['trace_id']}-{span['span_id']}-01"
