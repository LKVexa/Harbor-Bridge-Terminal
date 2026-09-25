"""Metrics, structured logs, trace correlation and redaction (MC-48, MC-49, MC-35 partial).

Stdlib only.  Log records are JSON with a fixed field allowlist; any other
field is dropped, and string values that look like credentials are redacted.
Tenant identity appears only as ``WorkflowIdentity.log_ref()`` (a truncated
hash), never raw.  Exposition is Prometheus text format.
"""
from __future__ import annotations

import json
import re
import secrets
import threading
import time
from typing import Any

_ALLOWED_LOG_FIELDS = frozenset({
    "ts", "level", "event", "code", "wf_ref", "run_ref", "trace_id", "span_id",
    "activity", "seq", "epoch", "state", "reason", "duration_ms", "outcome",
})
_SECRETISH = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|bearer)\s*[=:]\s*\S+")


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return _SECRETISH.sub(lambda m: m.group(1) + "=[REDACTED]", value)[:512]
    return value


class Metrics:
    def __init__(self) -> None:
        self._c: dict[tuple[str, tuple], float] = {}
        self._g: dict[tuple[str, tuple], float] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _k(name: str, labels: dict[str, str] | None) -> tuple[str, tuple]:
        return name, tuple(sorted((labels or {}).items()))

    def inc(self, name: str, labels: dict[str, str] | None = None, by: float = 1) -> None:
        with self._lock:
            k = self._k(name, labels)
            self._c[k] = self._c.get(k, 0) + by

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            self._g[self._k(name, labels)] = value

    def value(self, name: str, labels: dict[str, str] | None = None) -> float:
        k = self._k(name, labels)
        return self._c.get(k, self._g.get(k, 0))

    def exposition(self) -> str:
        lines = []
        with self._lock:
            for kind, store in (("counter", self._c), ("gauge", self._g)):
                for name in sorted({k[0] for k in store}):
                    lines.append(f"# TYPE inv57_{name} {kind}")
                    for (n, labels), v in sorted(store.items()):
                        if n == name:
                            lab = ",".join(f'{a}="{b}"' for a, b in labels)
                            lines.append(f"inv57_{n}{{{lab}}} {v}" if lab else f"inv57_{n} {v}")
        return "\n".join(lines) + "\n"


class Logger:
    def __init__(self, sink=None) -> None:
        self.records: list[str] = []
        self._sink = sink

    def log(self, level: str, event: str, **fields: Any) -> dict[str, Any]:
        rec = {"ts": round(time.time(), 3), "level": level, "event": event}
        for k, v in fields.items():
            if k in _ALLOWED_LOG_FIELDS:
                rec[k] = redact(v)
        line = json.dumps(rec, sort_keys=True)
        self.records.append(line)
        if self._sink:
            self._sink(line)
        return rec


def new_trace() -> tuple[str, str]:
    """W3C trace-context compatible ids (32-hex trace, 16-hex span)."""
    return secrets.token_hex(16), secrets.token_hex(8)


def traceparent(trace_id: str, span_id: str) -> str:
    return f"00-{trace_id}-{span_id}-01"


class ObservedWorker:
    """Wraps Worker.run with metrics, logs, trace ids and error-code decision reasons."""

    def __init__(self, worker, metrics: Metrics, logger: Logger, wf_ref: str = "") -> None:
        self.worker, self.metrics, self.logger, self.wf_ref = worker, metrics, logger, wf_ref

    def run(self, workflow):
        from .errors import spec_for
        trace_id, span_id = new_trace()
        before = len(self.worker.executed)
        t0 = time.perf_counter()
        self.metrics.inc("replays_total")
        try:
            result = self.worker.run(workflow)
            outcome, code = "completed", None
            return result
        except Exception as exc:
            outcome, code = "error", spec_for(exc).code
            if code == "INV57-E001":
                self.metrics.inc("nondeterminism_total")
            self.metrics.inc("run_errors_total", {"code": code})
            raise
        finally:
            ran = len(self.worker.executed) - before
            self.metrics.inc("activities_executed_total", by=ran)
            self.logger.log("info" if code is None else "warn", "workflow.run",
                            wf_ref=self.wf_ref, trace_id=trace_id, span_id=span_id,
                            outcome=outcome, code=code,
                            duration_ms=round((time.perf_counter() - t0) * 1000, 3))
