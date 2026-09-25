"""GAP02-MC-31 metrics exporter, MC-32 structured logging, MC-33 tracing hooks.

Metrics: Prometheus text exposition, label values drawn only from closed sets
(capability names from the declared set, probe names, error codes) so series
cardinality is bounded. Logging: one JSON object per line, no free-form PII
fields. Tracing: a minimal span API; if ``opentelemetry`` is importable it is
used, otherwise spans are recorded to an in-memory ring buffer (no-op cost).
"""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
import json
import logging
import threading
import time
from typing import Any, Iterable

from .errors import Code

STATE_VALUE = {"present": 1, "absent": 0, "unprobed": -1}
MAX_SERIES = 2048


class Metrics:
    def __init__(self, declared_capabilities: Iterable[str], probes: Iterable[str]):
        self.caps, self.probes = frozenset(declared_capabilities), frozenset(probes)
        self.codes = frozenset(c.value for c in Code)
        self._g: dict[tuple, float] = {}
        self._c: dict[tuple, float] = {}
        self._lock = threading.Lock()

    def _lbl(self, key: str, val: str, allowed: frozenset) -> str:
        return val if val in allowed else "other"

    def set_state(self, cap: str, state: str) -> None:
        with self._lock:
            k = ("gap02_capability_state", ("capability", self._lbl("c", cap, self.caps)))
            prev = self._g.get(k)
            self._g[k] = STATE_VALUE[state]
            if prev is not None and prev != STATE_VALUE[state]:
                self._inc("gap02_capability_changes_total", ("capability", k[1][1]))

    def _inc(self, name: str, *labels: tuple[str, str]) -> None:
        k = (name, *labels)
        if k not in self._c and len(self._c) >= MAX_SERIES:
            k = (name, ("overflow", "true"))
        self._c[k] = self._c.get(k, 0) + 1

    def probe_result(self, probe: str, code: str | None, latency_s: float) -> None:
        with self._lock:
            p = self._lbl("p", probe, self.probes)
            self._inc("gap02_probe_runs_total", ("probe", p))
            if code:
                self._inc("gap02_probe_failures_total", ("probe", p), ("code", self._lbl("e", code, self.codes)))
            self._g[("gap02_probe_latency_seconds", ("probe", p))] = latency_s

    def report_age(self, age: int) -> None:
        with self._lock:
            self._g[("gap02_report_age_seconds",)] = age

    def render(self) -> str:
        lines = []
        with self._lock:
            for kind, store in (("gauge", self._g), ("counter", self._c)):
                seen = set()
                for k in sorted(store, key=repr):
                    name, labels = k[0], k[1:]
                    if name not in seen:
                        lines.append(f"# TYPE {name} {kind}")
                        seen.add(name)
                    lab = ",".join(f'{a}="{b}"' for a, b in labels)
                    lines.append(f"{name}{{{lab}}} {store[k]}" if lab else f"{name} {store[k]}")
        return "\n".join(lines) + "\n"


class JsonFormatter(logging.Formatter):
    ALLOWED = ("event", "code", "capability", "probe", "generation", "sequence", "state", "latency_s", "trace_id")

    def format(self, r: logging.LogRecord) -> str:
        d = {"ts": round(r.created, 3), "level": r.levelname, "logger": r.name, "msg": r.getMessage()[:512]}
        for k in self.ALLOWED:
            if hasattr(r, k):
                d[k] = getattr(r, k)
        return json.dumps(d, sort_keys=True)


def get_logger(level: str = "INFO") -> logging.Logger:
    lg = logging.getLogger("gap02")
    if not any(isinstance(h.formatter, JsonFormatter) for h in lg.handlers):
        h = logging.StreamHandler()
        h.setFormatter(JsonFormatter())
        lg.addHandler(h)
    lg.setLevel(level)
    lg.propagate = False
    return lg


class Tracer:
    def __init__(self, capacity: int = 512):
        self.spans: deque[dict] = deque(maxlen=capacity)
        try:  # optional
            from opentelemetry import trace  # type: ignore
            self._otel = trace.get_tracer("gap02")
        except Exception:  # noqa: BLE001
            self._otel = None

    @contextmanager
    def span(self, name: str, **attrs: Any):
        t0 = time.perf_counter()
        rec = {"name": name, "attrs": {k: v for k, v in attrs.items() if isinstance(v, (str, int, float, bool))}}
        if self._otel is not None:
            with self._otel.start_as_current_span(name, attributes=rec["attrs"]):
                yield rec
        else:
            try:
                yield rec
            except BaseException as e:
                rec["error"] = type(e).__name__
                raise
            finally:
                rec["duration_ms"] = round((time.perf_counter() - t0) * 1000, 3)
                self.spans.append(rec)
