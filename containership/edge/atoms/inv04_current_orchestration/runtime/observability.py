"""Metrics, structured logs, traces, health probes, SLO measurement and
burn-rate alerting (components 44-49).

Dependency-free: metrics render in the Prometheus text exposition format,
logs are JSON lines with redaction, spans follow W3C trace-context IDs and can
be exported by any sink.  Label values are validated against an allow-list of
label *names* per metric so cardinality stays bounded (no pod names / UIDs as
labels).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Iterator

from .journal import redact

# ------------------------------------------------------------------ metrics (44)

MAX_SERIES_PER_METRIC = 500
DEFAULT_BUCKETS = (0.005, 0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 300)


class Metric:
    def __init__(self, name: str, help: str, kind: str, labels: tuple[str, ...], buckets=DEFAULT_BUCKETS):
        self.name, self.help, self.kind, self.labels, self.buckets = name, help, kind, labels, buckets
        self.values: dict[tuple, float] = {}
        self.hist: dict[tuple, list] = {}
        self._lock = threading.Lock()
        self.overflow = 0

    def _key(self, labels: dict) -> tuple | None:
        if set(labels) != set(self.labels):
            raise ValueError(f"{self.name}: labels {sorted(labels)} != {sorted(self.labels)}")
        key = tuple(str(labels[k])[:64] for k in self.labels)
        if key not in self.values and key not in self.hist and len(self.values) + len(self.hist) >= MAX_SERIES_PER_METRIC:
            self.overflow += 1
            return None
        return key

    def inc(self, n: float = 1, **labels) -> None:
        with self._lock:
            k = self._key(labels)
            if k is not None:
                self.values[k] = self.values.get(k, 0) + n

    def set(self, v: float, **labels) -> None:
        with self._lock:
            k = self._key(labels)
            if k is not None:
                self.values[k] = v

    def observe(self, v: float, **labels) -> None:
        with self._lock:
            k = self._key(labels)
            if k is None:
                return
            h = self.hist.setdefault(k, [[0] * len(self.buckets), 0.0, 0])
            for i, b in enumerate(self.buckets):
                if v <= b:
                    h[0][i] += 1
            h[1] += v
            h[2] += 1

    def get(self, **labels) -> float:
        return self.values.get(tuple(str(labels[k]) for k in self.labels), 0)


class Registry:
    def __init__(self) -> None:
        self.metrics: dict[str, Metric] = {}

    def _reg(self, name, help, kind, labels=(), **kw) -> Metric:
        if name not in self.metrics:
            self.metrics[name] = Metric(name, help, kind, tuple(labels), **kw)
        return self.metrics[name]

    def counter(self, name, help, labels=()):
        return self._reg(name, help, "counter", labels)

    def gauge(self, name, help, labels=()):
        return self._reg(name, help, "gauge", labels)

    def histogram(self, name, help, labels=(), buckets=DEFAULT_BUCKETS):
        return self._reg(name, help, "histogram", labels, buckets=buckets)

    def render(self) -> str:
        out = []
        for m in sorted(self.metrics.values(), key=lambda m: m.name):
            out.append(f"# HELP {m.name} {m.help}")
            out.append(f"# TYPE {m.name} {m.kind}")

            def fmt(key, extra="", m=m):
                parts = [f'{n}="{_esc(v)}"' for n, v in zip(m.labels, key, strict=True)]
                if extra:
                    parts.append(extra)
                return "{" + ",".join(parts) + "}" if parts else ""

            with m._lock:
                for key, v in sorted(m.values.items()):
                    out.append(f"{m.name}{fmt(key)} {_num(v)}")
                for key, (counts, total, n) in sorted(m.hist.items()):
                    for b, c in zip(m.buckets, counts, strict=True):
                        le = 'le="%s"' % b
                        out.append(f"{m.name}_bucket{fmt(key, le)} {c}")
                    inf = 'le="+Inf"'
                    out.append(f"{m.name}_bucket{fmt(key, inf)} {n}")
                    out.append(f"{m.name}_sum{fmt(key)} {_num(total)}")
                    out.append(f"{m.name}_count{fmt(key)} {n}")
        return "\n".join(out) + "\n"


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else repr(float(v))


def standard_metrics(reg: Registry) -> dict[str, Metric]:
    return {
        "replicas_desired": reg.gauge("inv04_replicas_desired", "Desired replicas", ("workload",)),
        "replicas_running": reg.gauge("inv04_replicas_running", "Running replicas", ("workload",)),
        "replica_drift": reg.gauge("inv04_replica_drift", "Desired minus running", ("workload",)),
        "reconcile_total": reg.counter("inv04_reconcile_total", "Reconcile attempts", ("outcome",)),
        "reconcile_seconds": reg.histogram("inv04_reconcile_duration_seconds", "Reconcile latency"),
        "drains_total": reg.counter("inv04_drains_total", "Drains by terminal outcome", ("outcome", "reason")),
        "drain_seconds": reg.histogram("inv04_drain_duration_seconds", "Drain latency", ("outcome",)),
        "budget_blocks": reg.counter("inv04_budget_blocks_total", "Drains or evictions refused by a budget"),
        "retries": reg.counter("inv04_retries_total", "Retried dependency calls", ("dependency",)),
        "api_errors": reg.counter("inv04_api_errors_total", "API errors by stable code", ("code",)),
        "capacity_failures": reg.counter("inv04_capacity_failures_total", "Preflight capacity refusals"),
        "queue_depth": reg.gauge("inv04_workqueue_depth", "Work queue depth"),
        "queue_inflight": reg.gauge("inv04_workqueue_inflight", "Work items being processed"),
        "queue_oldest": reg.gauge("inv04_workqueue_oldest_seconds", "Age of oldest queued item"),
        "leader": reg.gauge("inv04_leader", "1 when this replica holds the lease"),
        "informer_lag": reg.gauge("inv04_informer_lag", "Informer resourceVersion lag", ("kind",)),
    }


# --------------------------------------------------------------- logging (45)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        body = {"ts": round(record.created, 6), "level": record.levelname.lower(), "logger": record.name,
                "msg": record.getMessage()}
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            body.update(redact(fields))
        if record.exc_info:
            body["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else ""
        return json.dumps(body, sort_keys=True, default=str)


def get_logger(name: str = "inv04", stream=None) -> logging.Logger:
    log = logging.getLogger(name)
    if not any(getattr(h, "_inv04", False) for h in log.handlers):
        h = logging.StreamHandler(stream)
        h.setFormatter(JsonFormatter())
        h._inv04 = True  # type: ignore[attr-defined]
        log.addHandler(h)
        log.setLevel(os.environ.get("INV04_LOG_LEVEL", "INFO"))
        log.propagate = False
    return log


def log_event(log: logging.Logger, msg: str, *, level: int = logging.INFO, **fields) -> None:
    """Structured event. Standard fields: op_id, workload, node, phase, outcome, reason."""
    log.log(level, msg, extra={"fields": fields})


# --------------------------------------------------------------- tracing (46)


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    start: float
    end: float | None = None
    attrs: dict = field(default_factory=dict)
    status: str = "ok"


class Tracer:
    def __init__(self, sink: Callable[[Span], None] | None = None, *, clock: Callable[[], float] = time.time):
        self.sink = sink or (lambda s: None)
        self.clock = clock
        self._local = threading.local()
        self.finished: deque[Span] = deque(maxlen=10_000)

    @staticmethod
    def _id(n: int) -> str:
        return os.urandom(n).hex()

    def current(self) -> Span | None:
        stack = getattr(self._local, "stack", [])
        return stack[-1] if stack else None

    def traceparent(self) -> str:
        s = self.current()
        return f"00-{s.trace_id}-{s.span_id}-01" if s else ""

    @contextmanager
    def span(self, name: str, *, traceparent: str = "", **attrs) -> Iterator[Span]:
        parent = self.current()
        if parent is None and traceparent:
            parts = traceparent.split("-")
            trace_id, parent_id = (parts[1], parts[2]) if len(parts) == 4 and len(parts[1]) == 32 else (self._id(16), None)
        else:
            trace_id, parent_id = (parent.trace_id, parent.span_id) if parent else (self._id(16), None)
        s = Span(name, trace_id, self._id(8), parent_id, self.clock(), attrs=redact(attrs))
        stack = getattr(self._local, "stack", [])
        stack.append(s)
        self._local.stack = stack
        try:
            yield s
        except BaseException as exc:
            s.status = f"error:{getattr(exc, 'code', type(exc).__name__)}"
            raise
        finally:
            s.end = self.clock()
            stack.pop()
            self.finished.append(s)
            self.sink(s)


# ------------------------------------------------------------ health (47)


class Health:
    """Startup / liveness / readiness with named checks and degraded mode."""

    def __init__(self) -> None:
        self.checks: dict[str, Callable[[], tuple[bool, str]]] = {}
        self.started = False
        self.last_loop = time.monotonic()
        self.loop_timeout = 120.0

    def add(self, name: str, fn: Callable[[], tuple[bool, str]]) -> None:
        self.checks[name] = fn

    def heartbeat(self) -> None:
        self.last_loop = time.monotonic()

    def startup(self) -> tuple[int, dict]:
        return (200 if self.started else 503), {"started": self.started}

    def liveness(self) -> tuple[int, dict]:
        age = time.monotonic() - self.last_loop
        ok = age < self.loop_timeout
        return (200 if ok else 503), {"loop_age_s": round(age, 3)}

    def readiness(self) -> tuple[int, dict]:
        results = {}
        for name, fn in sorted(self.checks.items()):
            try:
                ok, detail = fn()
            except Exception as exc:  # noqa: BLE001
                ok, detail = False, type(exc).__name__
            results[name] = {"ok": ok, "detail": detail}
        ready = self.started and all(r["ok"] for r in results.values())
        degraded = [n for n, r in results.items() if not r["ok"]]
        return (200 if ready else 503), {"ready": ready, "degraded": degraded, "checks": results}


# --------------------------------------------------------- SLO engine (48)


class ConvergenceSLO:
    """Measures time from divergence detection to convergence per workload.

    ``observe(workload, desired, running)`` is called on every reconcile or
    watch update; a divergence episode opens when running != desired and closes
    when they match.  An episode longer than ``target_s`` is a bad event.
    Open episodes older than the target count as bad immediately (no hiding).
    """

    def __init__(self, target_s: float = 30.0, objective: float = 0.99, *, clock: Callable[[], float] = time.monotonic,
                 window: int = 10_000):
        self.target, self.objective, self.clock = target_s, objective, clock
        self.open: dict[str, float] = {}
        self.events: deque[tuple[float, bool]] = deque(maxlen=window)
        self.budget_breaches = 0
        self.drains = 0

    def observe(self, workload: str, desired: int, running: int) -> None:
        now = self.clock()
        if running != desired:
            self.open.setdefault(workload, now)
        elif workload in self.open:
            started = self.open.pop(workload)
            self.events.append((now, now - started <= self.target))

    def record_drain(self, breached_budget: bool) -> None:
        self.drains += 1
        if breached_budget:
            self.budget_breaches += 1

    def report(self) -> dict:
        now = self.clock()
        overdue = sum(1 for t in self.open.values() if now - t > self.target)
        good = sum(1 for _, ok in self.events if ok)
        total = len(self.events) + overdue
        ratio = good / total if total else 1.0
        return {"convergence_ratio": round(ratio, 6), "objective": self.objective, "episodes": total,
                "overdue_open": overdue, "error_budget_remaining": round(1 - (1 - ratio) / max(1e-9, 1 - self.objective), 6),
                "drain_budget_breaches": self.budget_breaches, "drains": self.drains,
                "availability_slo_met": self.budget_breaches == 0, "convergence_slo_met": ratio >= self.objective}

    def burn_rate(self, window_s: float) -> float:
        now = self.clock()
        recent = [ok for t, ok in self.events if now - t <= window_s]
        if not recent:
            return 0.0
        bad = 1 - sum(recent) / len(recent)
        return bad / max(1e-9, 1 - self.objective)


# ------------------------------------------------------------ alerting (49)


@dataclass(frozen=True)
class AlertRule:
    name: str
    long_window_s: float
    short_window_s: float
    burn_rate: float
    severity: str  # page | ticket


MULTIWINDOW_RULES = (
    AlertRule("convergence_fast_burn", 3600, 300, 14.4, "page"),
    AlertRule("convergence_slow_burn", 6 * 3600, 1800, 6.0, "page"),
    AlertRule("convergence_drift", 3 * 86400, 6 * 3600, 1.0, "ticket"),
)


def evaluate_alerts(slo: ConvergenceSLO, *, maintenance: bool = False, rules=MULTIWINDOW_RULES) -> list[dict]:
    fired = []
    if slo.budget_breaches:
        fired.append({"alert": "drain_budget_breach", "severity": "page", "route": "inv04-oncall",
                      "value": slo.budget_breaches})  # never suppressed: zero-budget objective
    for r in rules:
        if slo.burn_rate(r.long_window_s) >= r.burn_rate and slo.burn_rate(r.short_window_s) >= r.burn_rate:
            sev = "ticket" if maintenance and r.severity == "page" else r.severity
            fired.append({"alert": r.name, "severity": sev, "route": "inv04-oncall" if sev == "page" else "inv04-queue",
                          "burn_rate": round(slo.burn_rate(r.short_window_s), 3)})
    return fired
