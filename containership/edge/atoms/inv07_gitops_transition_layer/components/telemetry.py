"""Metrics (35), structured logging (36), tracing (37), explain records (38).

Metrics
  ``Registry`` of counters, gauges and fixed-bucket histograms with a hard
  label-cardinality cap per metric (overflow goes to ``__overflow__`` and
  increments ``inv07_metric_label_overflow_total``); Prometheus text format
  exposition.  The HTTP endpoint (``server.py``) requires a bearer token when
  ``telemetry.metrics_require_auth`` is on.

Logging
  ``EventLog`` emits ``PK_GITOPS_EVENT/1`` JSON lines with stable ``code``,
  severity, tenant/site, correlation id, trace/span ids; every record passes
  ``redact.scrub``; oversize records are truncated; a failing sink never
  raises into the controller (the drop is counted instead).

Tracing
  W3C ``traceparent`` parsing/generation; ``Tracer.span`` context manager
  records name, parent, duration, status and bounded attributes; spans are
  exported to a pluggable sink (OTLP collector adapter slot -- BLOCKED without
  a collector) and kept in a bounded ring for the explain view.

Explain
  ``ExplainStore`` persists one read-only record per reconciliation decision
  (JSONL) linking revision, signer, provenance, policy version/digest, live
  delta, actions, overrides, audit sequence numbers and trace id.
"""
from __future__ import annotations

import collections
import json
import os
import re
import secrets
import threading
import time
from contextlib import contextmanager

from .redact import scrub

EVENT_SCHEMA = "PK_GITOPS_EVENT/1"
DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60)
_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")


class Registry:
    def __init__(self, *, max_series: int = 200) -> None:
        self.max_series = max_series
        self._m: dict[str, dict] = {}
        self._lock = threading.Lock()
        self.counter("inv07_metric_label_overflow_total", "label sets dropped by the cardinality cap")

    def _def(self, name, kind, help, buckets=None):
        if not _NAME.match(name):
            raise ValueError("bad metric name")
        with self._lock:
            self._m.setdefault(name, {"kind": kind, "help": help, "series": {}, "buckets": buckets})
        return name

    def counter(self, name, help=""):
        return self._def(name, "counter", help)

    def gauge(self, name, help=""):
        return self._def(name, "gauge", help)

    def histogram(self, name, help="", buckets=DEFAULT_BUCKETS):
        return self._def(name, "histogram", help, tuple(buckets))

    def _series(self, name, labels):
        m = self._m[name]
        key = tuple(sorted((k, str(v)[:64]) for k, v in (labels or {}).items()))
        if key not in m["series"] and len(m["series"]) >= self.max_series:
            ov = self._m["inv07_metric_label_overflow_total"]["series"]
            ov[()] = ov.get((), 0) + 1
            key = (("__overflow__", "true"),)
        return m, key

    def inc(self, name, v=1.0, **labels):
        with self._lock:
            m, k = self._series(name, labels)
            m["series"][k] = m["series"].get(k, 0) + v

    def set(self, name, v, **labels):
        with self._lock:
            m, k = self._series(name, labels)
            m["series"][k] = v

    def observe(self, name, v, **labels):
        with self._lock:
            m, k = self._series(name, labels)
            s = m["series"].setdefault(k, {"b": [0] * len(m["buckets"]), "sum": 0.0, "count": 0})
            for i, b in enumerate(m["buckets"]):
                if v <= b:
                    s["b"][i] += 1
            s["sum"] += v
            s["count"] += 1

    def value(self, name, **labels):
        k = tuple(sorted((a, str(b)) for a, b in labels.items()))
        return self._m[name]["series"].get(k)

    def exposition(self) -> str:
        out = []
        esc = lambda s: s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
        with self._lock:
            for name in sorted(self._m):
                m = self._m[name]
                out.append(f"# HELP {name} {m['help']}")
                out.append(f"# TYPE {name} {m['kind']}")
                for key, val in sorted(m["series"].items()):
                    lab = ",".join(f'{a}="{esc(b)}"' for a, b in key)
                    if m["kind"] == "histogram":
                        for b, c in zip(m["buckets"], val["b"]):
                            out.append(f'{name}_bucket{{{lab + "," if lab else ""}le="{b}"}} {c}')
                        out.append(f'{name}_bucket{{{lab + "," if lab else ""}le="+Inf"}} {val["count"]}')
                        out.append(f"{name}_sum{{{lab}}} {val['sum']}")
                        out.append(f"{name}_count{{{lab}}} {val['count']}")
                    else:
                        out.append(f"{name}{{{lab}}} {val}" if lab else f"{name} {val}")
        return "\n".join(out) + "\n"


def standard_metrics(r: Registry) -> Registry:
    r.counter("inv07_syncs_total", "reconciliations by outcome")
    r.counter("inv07_unsigned_refusals_total", "commits refused for signature/trust reasons")
    r.counter("inv07_drift_reverts_total", "out-of-band changes reverted")
    r.counter("inv07_policy_denials_total", "policy denials")
    r.counter("inv07_dependency_errors_total", "dependency errors by dependency")
    r.histogram("inv07_reconcile_seconds", "reconcile latency")
    r.histogram("inv07_verify_seconds", "signature+provenance verification latency")
    r.gauge("inv07_leader", "1 when this instance holds the lease")
    r.gauge("inv07_queue_saturation", "admission queue fill ratio")
    r.gauge("inv07_last_sync_timestamp_seconds", "unix time of last successful sync")
    r.gauge("inv07_frozen", "1 when reconciliation is frozen")
    r.gauge("inv07_circuit_open", "1 when a dependency circuit is open")
    r.counter("inv07_log_drops_total", "log records dropped by a failing sink")
    return r


class EventLog:
    def __init__(self, sink=None, *, tenant: str, site: str, level: str = "info", max_bytes: int = 8192,
                 metrics: Registry | None = None, clock=time.time) -> None:
        self.sink = sink or (lambda line: None)
        self.tenant, self.site, self.max_bytes, self.metrics, self.clock = tenant, site, max_bytes, metrics, clock
        self.levels = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}
        self.min = self.levels[level]

    def emit(self, code: str, severity: str, message: str, *, cid: str | None = None, trace_id: str | None = None,
             span_id: str | None = None, **fields) -> dict | None:
        if self.levels.get(severity, 20) < self.min:
            return None
        rec = {"schema": EVENT_SCHEMA, "ts": round(self.clock(), 3), "code": code, "severity": severity,
               "message": message, "tenant": self.tenant, "site": self.site, "cid": cid, "trace_id": trace_id,
               "span_id": span_id, "fields": fields}
        rec = scrub(rec)
        line = json.dumps(rec, sort_keys=True)
        if len(line) > self.max_bytes:
            rec["fields"] = {"<truncated>": True}
            line = json.dumps(rec, sort_keys=True)[: self.max_bytes]
        try:
            self.sink(line)
        except Exception:  # noqa: BLE001 - collector failure must not stop reconciliation
            if self.metrics:
                self.metrics.inc("inv07_log_drops_total")
        return rec


_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_traceparent(tp: str | None) -> tuple[str, str] | None:
    m = _TP.match(tp or "")
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
        return None
    return m.group(1), m.group(2)


class Tracer:
    def __init__(self, sink=None, *, ring: int = 2000, max_attrs: int = 16) -> None:
        self.sink, self.max_attrs = sink, max_attrs
        self.spans: collections.deque = collections.deque(maxlen=ring)
        self._local = threading.local()

    def current(self):
        st = getattr(self._local, "stack", None)
        return st[-1] if st else None

    @contextmanager
    def span(self, name: str, *, traceparent: str | None = None, **attrs):
        st = self._local.__dict__.setdefault("stack", [])
        parent = st[-1] if st else None
        ext = parse_traceparent(traceparent) if parent is None else None
        trace_id = parent["trace_id"] if parent else (ext[0] if ext else secrets.token_hex(16))
        sp = {"name": name, "trace_id": trace_id, "span_id": secrets.token_hex(8),
              "parent": parent["span_id"] if parent else (ext[1] if ext else None),
              "attrs": scrub(dict(list(attrs.items())[: self.max_attrs])), "status": "ok",
              "start": time.time()}
        st.append(sp)
        t0 = time.perf_counter()
        try:
            yield sp
        except BaseException as exc:
            sp["status"] = "error"
            sp["error"] = getattr(exc, "code", type(exc).__name__)
            raise
        finally:
            sp["duration"] = time.perf_counter() - t0
            st.pop()
            self.spans.append(sp)
            if self.sink:
                try:
                    self.sink(sp)
                except Exception:  # noqa: BLE001
                    pass

    @staticmethod
    def traceparent(sp: dict) -> str:
        return f"00-{sp['trace_id']}-{sp['span_id']}-01"


class ExplainStore:
    def __init__(self, path: str | None = None, *, capacity: int = 10_000) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._recs: collections.deque = collections.deque(maxlen=capacity)
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    if line.endswith("\n"):
                        self._recs.append(json.loads(line))

    def record(self, rec: dict) -> dict:
        rec = scrub({"schema": "PK_GITOPS_EXPLAIN/1", **rec})
        with self._lock:
            self._recs.append(rec)
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
        return rec

    def get(self, decision_id: str) -> dict | None:
        with self._lock:
            return next((dict(r) for r in reversed(self._recs) if r.get("decision_id") == decision_id), None)

    def recent(self, n: int = 20) -> list[dict]:
        with self._lock:
            return [dict(r) for r in list(self._recs)[-n:]]
