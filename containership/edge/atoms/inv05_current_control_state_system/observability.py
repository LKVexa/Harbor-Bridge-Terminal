"""Metrics, structured logging, tracing and decision explanations
(MC-032, MC-033, MC-034, MC-035, MC-036).

* Metrics: fixed catalog (:data:`METRIC_CATALOG`) with names, units, types,
  allowed labels and owners; label cardinality is capped per metric -- excess
  series collapse into ``{overflow="true"}`` rather than growing unbounded.
  Prometheus text exposition via :meth:`Metrics.render`.
* Logging: schema ``cstate.log/1`` JSON lines with stable ``event_id``s, central
  redaction, per-event token-bucket storm suppression, and audited dynamic
  level changes.
* Tracing: W3C ``traceparent`` parse/propagate, spans with allow-listed
  attributes, parent-based + error-biased sampling, deadline attribute.
* Explain: machine-readable decision records independent of prose, redacted,
  bounded ring buffer, retrievable only through an authorized admin call.
"""
from __future__ import annotations

import json
import os
import random
import re
import resource
import sys
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, TextIO

from .security import redact

# ------------------------------------------------------------------ metric catalog
# name: (type, unit, labels, help, telemetry class)
METRIC_CATALOG: dict[str, tuple[str, str, tuple[str, ...], str, str]] = {
    "cstate_requests_total": ("counter", "1", ("op", "result"), "Requests by operation and result class", "internal"),
    "cstate_txn_conflicts_total": ("counter", "1", (), "Transactions whose compares failed", "internal"),
    "cstate_retries_total": ("counter", "1", ("op",), "Client-declared retries (x-cstate-attempt>1)", "internal"),
    "cstate_request_duration_seconds": ("histogram", "s", ("op",), "Server-side latency by op class", "internal"),
    "cstate_revision": ("gauge", "1", (), "Current store revision", "internal"),
    "cstate_compact_revision": ("gauge", "1", (), "Current compaction revision", "internal"),
    "cstate_compaction_lag_revisions": ("gauge", "1", (), "revision - compact_revision", "internal"),
    "cstate_history_events": ("gauge", "1", (), "Retained history events", "internal"),
    "cstate_keys": ("gauge", "1", (), "Live keys", "internal"),
    "cstate_compacted_refusals_total": ("counter", "1", (), "Reads/watches refused due to compaction", "internal"),
    "cstate_watches_active": ("gauge", "1", (), "Open watch streams", "internal"),
    "cstate_watch_backlog_events": ("gauge", "1", (), "Queued undelivered watch events (sum)", "internal"),
    "cstate_watch_slow_consumer_cancels_total": ("counter", "1", (), "Watches cancelled as slow consumers", "internal"),
    "cstate_leases_active": ("gauge", "1", (), "Active leases", "internal"),
    "cstate_leases_expired_total": ("counter", "1", (), "Leases expired", "internal"),
    "cstate_wal_bytes": ("gauge", "By", (), "Bytes in current WAL generation", "internal"),
    "cstate_wal_fsync_seconds": ("histogram", "s", (), "WAL append+fsync latency", "internal"),
    "cstate_authn_failures_total": ("counter", "1", ("reason",), "Authentication failures", "internal"),
    "cstate_authz_denials_total": ("counter", "1", ("action",), "Authorization denials", "internal"),
    "cstate_admin_ops_total": ("counter", "1", ("action",), "Administrative operations", "internal"),
    "cstate_inflight_requests": ("gauge", "1", (), "In-flight requests", "internal"),
    "cstate_state": ("gauge", "1", ("state",), "1 for the current serving state", "internal"),
    "process_resident_memory_bytes": ("gauge", "By", (), "Peak RSS", "internal"),
    "process_cpu_seconds_total": ("counter", "s", (), "CPU time", "internal"),
    "process_open_fds": ("gauge", "1", (), "Open file descriptors", "internal"),
    "process_threads": ("gauge", "1", (), "Python threads", "internal"),
    "cstate_net_bytes_total": ("counter", "By", ("dir",), "Transport bytes received/sent (bodies + stream frames)", "internal"),
    "cstate_net_connections_total": ("counter", "1", ("result",), "Accepted connections by TLS handshake result", "internal"),
}
DEFAULT_BUCKETS = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class Metrics:
    def __init__(self, max_series_per_metric: int = 64) -> None:
        self.max_series = max_series_per_metric
        self._lock = threading.Lock()
        self._values: dict[str, dict[tuple[str, ...], Any]] = {n: {} for n in METRIC_CATALOG}

    def _key(self, name: str, labels: dict[str, str]) -> tuple[str, ...]:
        spec = METRIC_CATALOG.get(name)
        if spec is None:
            raise KeyError(f"metric {name} not in catalog")
        if set(labels) != set(spec[2]):
            raise ValueError(f"metric {name} requires labels {spec[2]}")
        k = tuple(str(labels[l])[:64] for l in spec[2])
        series = self._values[name]
        if k not in series and len(series) >= self.max_series:
            return tuple("overflow" for _ in spec[2])
        return k

    def inc(self, name: str, n: float = 1.0, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            self._values[name][k] = self._values[name].get(k, 0.0) + n

    def set(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            self._values[name][self._key(name, labels)] = float(v)

    def observe(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            h = self._values[name].setdefault(k, {"buckets": [0] * len(DEFAULT_BUCKETS), "sum": 0.0, "count": 0})
            for i, b in enumerate(DEFAULT_BUCKETS):
                if v <= b:
                    h["buckets"][i] += 1
            h["sum"] += v
            h["count"] += 1

    def get(self, name: str, **labels: str) -> Any:
        with self._lock:
            return self._values[name].get(tuple(str(labels[l]) for l in METRIC_CATALOG[name][2]))

    def quantile(self, name: str, q: float, **labels: str) -> float:
        h = self.get(name, **labels)
        if not h or not h["count"]:
            return 0.0
        target = q * h["count"]
        for i, c in enumerate(h["buckets"]):
            if c >= target:
                return DEFAULT_BUCKETS[i]
        return float("inf")

    def sample_process(self) -> None:
        ru = resource.getrusage(resource.RUSAGE_SELF)
        self.set("process_resident_memory_bytes", ru.ru_maxrss * (1 if sys.platform == "darwin" else 1024))
        with self._lock:
            self._values["process_cpu_seconds_total"][()] = ru.ru_utime + ru.ru_stime
        try:
            self.set("process_open_fds", len(os.listdir("/proc/self/fd")))
        except OSError:
            pass
        self.set("process_threads", threading.active_count())

    def render(self) -> str:
        out = []
        with self._lock:
            for name, (typ, unit, labels, help_, _cls) in METRIC_CATALOG.items():
                out.append(f"# HELP {name} {help_} (unit: {unit})")
                out.append(f"# TYPE {name} {typ}")
                for k, v in sorted(self._values[name].items()):
                    lab = ",".join(f'{l}="{_esc(x)}"' for l, x in zip(labels, k))
                    if typ == "histogram":
                        acc = 0
                        for b, c in zip(DEFAULT_BUCKETS, v["buckets"]):
                            acc = c
                            out.append(f'{name}_bucket{{{lab + "," if lab else ""}le="{b}"}} {acc}')
                        out.append(f'{name}_bucket{{{lab + "," if lab else ""}le="+Inf"}} {v["count"]}')
                        out.append(f"{name}_sum{{{lab}}} {v['sum']}")
                        out.append(f"{name}_count{{{lab}}} {v['count']}")
                    else:
                        out.append(f"{name}{{{lab}}} {v}" if lab else f"{name} {v}")
        return "\n".join(out) + "\n"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# ------------------------------------------------------------------ logging
LOG_SCHEMA = "cstate.log/1"
LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40, "CRITICAL": 50}
EVENT_IDS = {  # stable ids for lifecycle/security events (MC-033-03)
    "CS1000": "service.start", "CS1001": "service.ready", "CS1002": "service.stop",
    "CS1100": "request.completed", "CS1101": "request.failed",
    "CS1200": "recovery.completed", "CS1201": "recovery.torn_tail_truncated",
    "CS1300": "compaction.completed", "CS1400": "lease.expired",
    "CS2000": "authn.failed", "CS2001": "authz.denied", "CS2002": "admin.action",
    "CS2003": "loglevel.changed", "CS2004": "break_glass.used", "CS2005": "policy.rollout",
    "CS3000": "store.failed_closed", "CS3001": "watch.slow_consumer", "CS3002": "backup.completed",
    "CS3003": "restore.completed", "CS3004": "config.activated", "CS9000": "log.suppressed",
}


class NullStream:
    def write(self, _: str) -> int:
        return 0

    def flush(self) -> None:
        return None


class StructuredLogger:
    def __init__(self, stream: TextIO | None = None, *, level: str = "INFO", component: str = "inv05",
                 per_event_rate: float = 50.0, burst: int = 100, clock: Callable[[], float] = time.time) -> None:
        self.stream = stream if stream is not None else sys.stderr
        self.level = level
        self.component = component
        self.clock = clock
        self.rate, self.burst = per_event_rate, burst
        self._buckets: dict[str, list[float]] = {}
        self._suppressed: dict[str, int] = {}
        self._lock = threading.Lock()
        self.records: deque[dict[str, Any]] = deque(maxlen=2000)  # in-process tail for diagnostics/tests

    def set_level(self, level: str, *, actor: str) -> None:
        if level not in LEVELS:
            raise ValueError("unknown level")
        old = self.level
        self.level = level
        self.log("WARN", "CS2003", "log level changed", actor=actor, old=old, new=level)

    def log(self, severity: str, event_id: str, message: str, **fields: Any) -> None:
        if LEVELS[severity] < LEVELS[self.level]:
            return
        if event_id not in EVENT_IDS:
            raise ValueError(f"unregistered event id {event_id}")
        now = self.clock()
        with self._lock:
            tokens, last = self._buckets.get(event_id, [float(self.burst), now])
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            if tokens < 1 and severity not in ("ERROR", "CRITICAL"):
                self._buckets[event_id] = [tokens, now]
                self._suppressed[event_id] = self._suppressed.get(event_id, 0) + 1
                return
            self._buckets[event_id] = [tokens - 1, now]
            suppressed = self._suppressed.pop(event_id, 0)
        rec = {"schema": LOG_SCHEMA, "ts": round(now, 6), "severity": severity, "component": self.component,
               "event_id": event_id, "event": EVENT_IDS[event_id], "message": message, **redact(fields)}
        if suppressed:
            rec["suppressed_since_last"] = suppressed
        self.records.append(rec)
        try:
            self.stream.write(json.dumps(rec, default=str, sort_keys=True) + "\n")
        except Exception:
            pass


# ------------------------------------------------------------------ tracing
TRACEPARENT_RE = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
SPAN_ATTR_ALLOW = frozenset({"op", "result", "revision", "backend", "code", "branch", "events", "watch_id",
                             "deadline_ms", "attempt", "records", "namespace_hash", "policy_version"})


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str
    sampled: bool
    start: float
    end: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "OK"

    def set(self, **attrs: Any) -> None:
        for k, v in attrs.items():
            if k in SPAN_ATTR_ALLOW and isinstance(v, (int, float, str, bool)):
                self.attributes[k] = v if not isinstance(v, str) else v[:128]

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


class Tracer:
    """Parent-based head sampling at ``ratio``; errors are always retained (tail bias)."""

    def __init__(self, ratio: float = 0.1, max_spans: int = 10_000, rng: random.Random | None = None) -> None:
        self.ratio = ratio
        self.rng = rng or random.Random()
        self.finished: deque[Span] = deque(maxlen=max_spans)
        self._local = threading.local()

    @staticmethod
    def parse(traceparent: str | None) -> tuple[str, str, bool] | None:
        if not traceparent:
            return None
        m = TRACEPARENT_RE.match(traceparent.strip().lower())
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return None
        return m.group(1), m.group(2), m.group(3) == "01"

    def current(self) -> Span | None:
        stack = getattr(self._local, "stack", None)
        return stack[-1] if stack else None

    @contextmanager
    def span(self, name: str, traceparent: str | None = None, **attrs: Any) -> Iterator[Span]:
        parent = self.current()
        ctx = self.parse(traceparent) if parent is None else (parent.trace_id, parent.span_id, parent.sampled)
        if ctx:
            trace_id, parent_id, sampled = ctx
        else:
            trace_id, parent_id = os.urandom(16).hex(), ""
            sampled = self.rng.random() < self.ratio
        sp = Span(name, trace_id, os.urandom(8).hex(), parent_id, sampled, time.time())
        sp.set(**attrs)
        stack = getattr(self._local, "stack", None)
        if stack is None:
            stack = self._local.stack = []
        stack.append(sp)
        try:
            yield sp
        except BaseException as exc:
            sp.status = "ERROR"
            sp.set(code=getattr(exc, "code", type(exc).__name__))
            raise
        finally:
            sp.end = time.time()
            stack.pop()
            if sp.sampled or sp.status == "ERROR":
                self.finished.append(sp)


# ------------------------------------------------------------------ explain
EXPLAIN_SCHEMA = "cstate.explain/1"


class ExplainStore:
    def __init__(self, capacity: int = 5000) -> None:
        self._buf: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._by_id: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def add(self, rec: dict[str, Any]) -> None:
        rec = redact({"schema": EXPLAIN_SCHEMA, **rec})
        with self._lock:
            if len(self._buf) == self._buf.maxlen and self._buf:
                old = self._buf[0]
                self._by_id.pop(old.get("request_id", ""), None)
            self._buf.append(rec)
            if rec.get("request_id"):
                self._by_id[rec["request_id"]] = rec

    def get(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._by_id.get(request_id)
