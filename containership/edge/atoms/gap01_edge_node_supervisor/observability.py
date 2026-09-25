"""Metrics exporter (31), structured logging (32), tracing hooks (33),
SLO measurement (36) and diagnostic snapshot redaction (35).

All stdlib.  Metrics are low-cardinality by construction: label values are
restricted to declared enums; unknown values collapse to ``other``.
"""
from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import threading
import time
import uuid
from collections import deque
from typing import Any
from collections.abc import Iterator

# ------------------------------------------------------------- metrics (31)
LABEL_DOMAINS = {
    "op": {"transition", "cordon", "uncordon", "drain", "drain_override", "report_health",
           "admit", "terminate", "emergency_enter", "emergency_exit", "disable", "status",
           "diagnostics", "reload_config", "cordon_ack", "control_plane_heartbeat"},
    "outcome": {"ok", "error", "replayed"},
    "code": None,  # filled from error catalog lazily
    "state": {"joining", "ready", "cordoned", "draining", "stopped"},
    "version": None,  # single value per process
}
LATENCY_BUCKETS = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)


class Metrics:
    def __init__(self) -> None:
        from .errors import ERROR_CATALOG
        LABEL_DOMAINS["code"] = set(ERROR_CATALOG) | {"none"}
        self._lock = threading.Lock()
        self.counters: dict[tuple, float] = {}
        self.gauges: dict[tuple, float] = {}
        self.hist: dict[tuple, list] = {}

    @staticmethod
    def _labels(labels: dict[str, str]) -> tuple:
        out = []
        for k, v in sorted(labels.items()):
            dom = LABEL_DOMAINS.get(k)
            out.append((k, v if dom is None or v in dom else "other"))
        return tuple(out)

    def inc(self, name: str, n: float = 1, **labels: str) -> None:
        key = (name, self._labels(labels))
        with self._lock:
            self.counters[key] = self.counters.get(key, 0) + n

    def set(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            self.gauges[(name, self._labels(labels))] = v

    def observe(self, name: str, v: float, **labels: str) -> None:
        key = (name, self._labels(labels))
        with self._lock:
            h = self.hist.setdefault(key, [0] * (len(LATENCY_BUCKETS) + 1) + [0.0, 0])
            for i, b in enumerate(LATENCY_BUCKETS):
                if v <= b:
                    h[i] += 1
            h[len(LATENCY_BUCKETS)] += 1  # +Inf
            h[-2] += v
            h[-1] += 1

    def get(self, name: str, **labels: str) -> float:
        key = (name, self._labels(labels))
        return self.counters.get(key, self.gauges.get(key, 0))

    def render(self) -> str:
        """Prometheus text exposition format 0.0.4."""
        def fmt(lbl: tuple, extra: tuple = ()) -> str:
            items = list(lbl) + list(extra)
            return "{" + ",".join(f'{k}="{v}"' for k, v in items) + "}" if items else ""
        lines: list[str] = []
        with self._lock:
            for (n, lb), v in sorted(self.counters.items()):
                lines.append(f"gap01_{n}_total{fmt(lb)} {v}")
            for (n, lb), v in sorted(self.gauges.items()):
                lines.append(f"gap01_{n}{fmt(lb)} {v}")
            for (n, lb), h in sorted(self.hist.items()):
                for i, b in enumerate(LATENCY_BUCKETS):
                    lines.append(f"gap01_{n}_bucket{fmt(lb, (('le', str(b)),))} {h[i]}")
                lines.append(f"gap01_{n}_bucket{fmt(lb, (('le', '+Inf'),))} {h[len(LATENCY_BUCKETS)]}")
                lines.append(f"gap01_{n}_sum{fmt(lb)} {h[-2]}")
                lines.append(f"gap01_{n}_count{fmt(lb)} {h[-1]}")
        return "\n".join(lines) + "\n"


# ------------------------------------------------------------- logging (32)
REDACT_KEYS = re.compile(r"(secret|token|key|password|sig|mac|credential)", re.I)


def redact(obj: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "<depth>"
    if isinstance(obj, dict):
        return {k: ("<redacted>" if REDACT_KEYS.search(str(k)) else redact(v, depth + 1))
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v, depth + 1) for v in obj[:100]]
    if isinstance(obj, str) and len(obj) > 1024:
        return obj[:1024] + "...<truncated>"
    return obj


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        doc = {"ts": round(record.created, 6), "level": record.levelname,
               "logger": record.name, "event_id": getattr(record, "event_id", "GAP01-LOG"),
               "msg": record.getMessage()}
        fields = getattr(record, "fields", None)
        if fields:
            doc.update(redact(fields))
        return json.dumps(doc, sort_keys=True, default=str)


def get_logger(stream=None) -> logging.Logger:
    log = logging.getLogger("gap01")
    if not log.handlers:
        h = logging.StreamHandler(stream)
        h.setFormatter(JsonFormatter())
        log.addHandler(h)
        log.setLevel(os.environ.get("GAP01_LOG_LEVEL", "INFO"))
        log.propagate = False
    return log


def log_event(log: logging.Logger, event_id: str, msg: str, level: int = logging.INFO,
              **fields: Any) -> None:
    log.log(level, msg, extra={"event_id": event_id, "fields": fields})


# ------------------------------------------------------------- tracing (33)
class Tracer:
    """Minimal W3C-traceparent compatible span recorder.  Exporters (OTLP)
    attach via ``exporter`` callable; the default keeps a bounded ring."""

    def __init__(self, exporter=None, ring: int = 1024) -> None:
        self.exporter = exporter
        self.spans: deque = deque(maxlen=ring)
        self._local = threading.local()

    @staticmethod
    def parse_traceparent(tp: str | None) -> tuple[str, str] | None:
        if not tp:
            return None
        m = re.fullmatch(r"00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}", tp)
        return (m.group(1), m.group(2)) if m else None

    @contextlib.contextmanager
    def span(self, name: str, traceparent: str | None = None, **attrs: Any) -> Iterator[dict]:
        parent = getattr(self._local, "current", None)
        ext = self.parse_traceparent(traceparent)
        trace_id = parent["trace_id"] if parent else (ext[0] if ext else uuid.uuid4().hex)
        sp = {"name": name, "trace_id": trace_id, "span_id": uuid.uuid4().hex[:16],
              "parent_id": parent["span_id"] if parent else (ext[1] if ext else None),
              "start": time.time(), "attrs": redact(attrs), "status": "ok"}
        self._local.current = sp
        try:
            yield sp
        except BaseException as exc:
            sp["status"] = "error"
            sp["error"] = type(exc).__name__
            raise
        finally:
            sp["end"] = time.time()
            self._local.current = parent
            self.spans.append(sp)
            if self.exporter:
                with contextlib.suppress(Exception):
                    self.exporter(sp)

    def traceparent(self) -> str | None:
        cur = getattr(self._local, "current", None)
        return f"00-{cur['trace_id']}-{cur['span_id']}-01" if cur else None


# ------------------------------------------------------------------ SLO (36)
class SLOTracker:
    """Measures the three README SLOs from observed events."""

    def __init__(self) -> None:
        self.illegal_transitions_applied = 0
        self.stopped_with_residents = 0
        self.cordons = 0
        self.cordon_late_placements = 0
        self.transition_attempts = 0

    def record_transition(self, frm: str, to: str, legal: bool, residents: int) -> None:
        self.transition_attempts += 1
        if not legal:
            self.illegal_transitions_applied += 1
        if to == "stopped" and residents:
            self.stopped_with_residents += 1

    def record_cordon_placement(self, late: bool) -> None:
        self.cordons += 1
        self.cordon_late_placements += late

    def report(self) -> dict:
        late_ratio = (self.cordon_late_placements / self.cordons) if self.cordons else 0.0
        return {
            "transition_legality": {"violations": self.illegal_transitions_applied,
                                    "budget": 0, "met": self.illegal_transitions_applied == 0},
            "drain_completeness": {"violations": self.stopped_with_residents,
                                   "budget": 0, "met": self.stopped_with_residents == 0},
            "cordon_latency": {"late_ratio": round(late_ratio, 4), "budget": 0.01,
                               "met": late_ratio <= 0.01},
        }
