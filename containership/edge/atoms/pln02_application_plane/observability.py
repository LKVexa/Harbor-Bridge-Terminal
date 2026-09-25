"""MC-23 / MC-30 - Health, readiness, stall detection, metrics, logs, traces, explain.

Stdlib only. Exporters (Prometheus text, JSON logs) are provided; shipping to a
backend is a deployment concern (docs/operations/TELEMETRY_GOVERNANCE.md).
"""
from __future__ import annotations

from collections import deque
import json
import re
import secrets
import threading
import time
from typing import Any, Callable, Mapping

from .secret_refs import redact

MAX_SERIES_PER_METRIC = 2000
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")
_LABEL_VALUE = re.compile(r"^[A-Za-z0-9._:/\-]{1,64}$")
DEFAULT_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)


class Metrics:
    """Counters/gauges/histograms with a hard per-metric series cap (cardinality guard)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._c: dict[str, dict[tuple, float]] = {}
        self._g: dict[str, dict[tuple, float]] = {}
        self._h: dict[str, dict[tuple, list]] = {}
        self.dropped_series = 0

    @staticmethod
    def _key(labels: Mapping[str, str] | None) -> tuple:
        if not labels:
            return ()
        return tuple(sorted((k, v if _LABEL_VALUE.fullmatch(str(v)) else "_invalid") for k, v in labels.items()))

    def _slot(self, table: dict, name: str, key: tuple, init: Any) -> Any:
        series = table.setdefault(name, {})
        if key not in series:
            if len(series) >= MAX_SERIES_PER_METRIC:
                self.dropped_series += 1
                key = (("overflow", "true"),)
                if key in series:
                    return key
            series[key] = init() if callable(init) else init
        return key

    def inc(self, name: str, labels: Mapping[str, str] | None = None, value: float = 1.0) -> None:
        with self._lock:
            k = self._slot(self._c, name, self._key(labels), 0.0)
            self._c[name][k] += value

    def set(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        with self._lock:
            k = self._slot(self._g, name, self._key(labels), 0.0)
            self._g[name][k] = value

    def observe(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        with self._lock:
            k = self._slot(self._h, name, self._key(labels), lambda: [0] * (len(DEFAULT_BUCKETS) + 1) + [0.0])
            h = self._h[name][k]
            for i, b in enumerate(DEFAULT_BUCKETS):
                if value <= b:
                    h[i] += 1
            h[len(DEFAULT_BUCKETS)] += 1
            h[-1] += value

    def value(self, name: str, labels: Mapping[str, str] | None = None) -> float:
        k = self._key(labels)
        for t in (self._c, self._g):
            if name in t and k in t[name]:
                return t[name][k]
        return 0.0

    def prometheus(self) -> str:
        def lbl(k: tuple, extra: str = "") -> str:
            parts = [f'{a}="{b}"' for a, b in k] + ([extra] if extra else [])
            return "{" + ",".join(parts) + "}" if parts else ""
        out = []
        with self._lock:
            for n, s in sorted(self._c.items()):
                out.append(f"# TYPE {n} counter")
                out += [f"{n}{lbl(k)} {v}" for k, v in sorted(s.items())]
            for n, s in sorted(self._g.items()):
                out.append(f"# TYPE {n} gauge")
                out += [f"{n}{lbl(k)} {v}" for k, v in sorted(s.items())]
            for n, s in sorted(self._h.items()):
                out.append(f"# TYPE {n} histogram")
                for k, h in sorted(s.items()):
                    for i, b in enumerate(DEFAULT_BUCKETS):
                        le = 'le="%s"' % b
                        out.append("%s_bucket%s %s" % (n, lbl(k, le), h[i]))
                    out.append("%s_bucket%s %s" % (n, lbl(k, 'le="+Inf"'), h[len(DEFAULT_BUCKETS)]))
                    out.append(f"{n}_count{lbl(k)} {h[len(DEFAULT_BUCKETS)]}")
                    out.append(f"{n}_sum{lbl(k)} {h[-1]}")
        return "\n".join(out) + "\n"


class TraceContext:
    """W3C Trace Context (``traceparent``) parse/propagate."""

    def __init__(self, trace_id: str, parent_id: str, flags: str = "01") -> None:
        self.trace_id, self.parent_id, self.flags = trace_id, parent_id, flags

    @classmethod
    def from_header(cls, header: str | None) -> "TraceContext":
        m = _TRACEPARENT.fullmatch(header or "")
        if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
            return cls(m.group(1), m.group(2), m.group(3))
        return cls(secrets.token_hex(16), secrets.token_hex(8))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), self.flags)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.parent_id}-{self.flags}"


class StructuredLogger:
    """JSON-lines logs; payloads are redacted and size-bounded."""

    def __init__(self, sink: Callable[[str], None] | None = None, *, max_bytes: int = 8192, keep: int = 1000) -> None:
        self.records: deque[dict] = deque(maxlen=keep)
        self._sink = sink
        self.max_bytes = max_bytes

    def log(self, level: str, event: str, **fields: Any) -> dict:
        rec = {"ts": round(time.time(), 3), "level": level, "event": event, **redact(fields)}
        line = json.dumps(rec, sort_keys=True, default=str)
        if len(line) > self.max_bytes:
            rec = {"ts": rec["ts"], "level": level, "event": event, "truncated": True}
            line = json.dumps(rec, sort_keys=True)
        self.records.append(rec)
        if self._sink:
            self._sink(line)
        return rec


class Watchdog:
    """Stall detection: an operation still in flight past ``stall_after`` is stalled."""

    def __init__(self, stall_after: float = 2.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.stall_after, self._clock = stall_after, clock
        self._inflight: dict[int, tuple[str, float]] = {}
        self._lock = threading.Lock()
        self._n = 0

    def start(self, op: str) -> int:
        with self._lock:
            self._n += 1
            self._inflight[self._n] = (op, self._clock())
            return self._n

    def finish(self, token: int) -> None:
        with self._lock:
            self._inflight.pop(token, None)

    def stalled(self) -> list[dict]:
        now = self._clock()
        with self._lock:
            return [{"op": op, "age_seconds": round(now - t, 3)} for op, t in self._inflight.values()
                    if now - t > self.stall_after]


class Health:
    """Liveness (process can serve) vs readiness (dependencies usable) vs degraded."""

    def __init__(self, version: str, watchdog: Watchdog) -> None:
        self.version = version
        self.watchdog = watchdog
        self._checks: dict[str, Callable[[], tuple[str, str]]] = {}

    def register(self, name: str, check: Callable[[], tuple[str, str]]) -> None:
        """``check`` returns (status, detail) where status in ok|degraded|fail."""
        self._checks[name] = check

    def report(self, *, config_digest: str | None = None) -> dict:
        deps = {}
        for name, check in sorted(self._checks.items()):
            try:
                status, detail = check()
            except Exception as exc:  # a failing probe is a failing dependency
                status, detail = "fail", type(exc).__name__
            deps[name] = {"status": status, "detail": str(detail)[:200]}
        stalled = self.watchdog.stalled()
        statuses = {d["status"] for d in deps.values()}
        overall = "fail" if "fail" in statuses or stalled else ("degraded" if "degraded" in statuses else "ok")
        return {"live": True, "ready": overall != "fail", "status": overall, "version": self.version,
                "config_digest": config_digest, "dependencies": deps, "stalled": stalled}
