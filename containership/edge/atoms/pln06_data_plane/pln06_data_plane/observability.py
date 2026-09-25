"""#34-#41 observability: structured logs, metrics+exporter, tracing, safe diagnostics, lineage, governance."""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import sys
import threading
import time
from bisect import bisect_left
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from typing import IO

# ---------------------------------------------------------------- #40 governance
TELEMETRY_POLICY = {
    "schema": "PK_TELEMETRY_POLICY/1",
    "retention_days": {"logs": 30, "metrics": 395, "traces": 7, "audit": 2555},
    "sampling": {"traces_default": 0.1, "errors": 1.0, "security_events": 1.0},
    "privacy": {"payload_bytes": "never", "secrets": "never", "tenant_ids": "hashed in metrics labels",
                "destinations": "plain (operator data)"},
    "access": {"logs": "sre, security", "audit": "security (read), nobody (write)", "diagnostics": "diagnostics.read capability"},
    "export": ["prometheus-text", "jsonl"],
    "deletion": "tenant offboarding purges tenant-keyed logs/traces within 30 days; audit retained per legal hold",
    "cardinality": {"max_series_per_metric": 1000, "overflow_label": "__other__"},
}

REDACT_KEYS = re.compile(r"(secret|token|password|mac|key|credential|authorization|payload|data)$", re.I)


def redact(obj: object) -> object:
    if isinstance(obj, Mapping):
        return {k: ("[REDACTED]" if REDACT_KEYS.search(str(k)) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in obj]
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return f"[{len(obj)} bytes]"
    return obj


def hash_label(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


# ---------------------------------------------------------------- #36 structured logging
LOG_SCHEMA = "PK_LOG/1"
LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "SECURITY": 50}


class StructuredLogger:
    """JSON-lines logger with stable fields, redaction and a bounded in-memory ring."""

    def __init__(self, *, node: str, component: str = "PLN-06", release: str = "unknown",
                 level: str = "INFO", sink: IO[str] | None = None, ring: int = 10_000,
                 clock: Callable[[], float] = time.time):
        self._base = {"schema": LOG_SCHEMA, "node": node, "component": component, "release": release}
        self._level = LEVELS[level]
        self._sink = sink
        self.ring: deque[dict[str, object]] = deque(maxlen=ring)
        self.dropped = 0
        self._clock = clock
        self._lock = threading.Lock()

    def log(self, level: str, event: str, *, operation: str, tenant: str | None = None,
            workload: str | None = None, trace: Mapping[str, str] | None = None, **fields: object) -> dict[str, object] | None:
        if LEVELS[level] < self._level:
            return None
        rec = {**self._base, "ts": self._clock(), "level": level, "event": event, "operation": operation,
               "tenant": tenant, "workload": workload,
               "trace_id": (trace or {}).get("trace_id"), "span_id": (trace or {}).get("span_id"),
               "fields": redact(fields)}
        with self._lock:
            if len(self.ring) == self.ring.maxlen:
                self.dropped += 1
            self.ring.append(rec)
            if self._sink is not None:
                try:
                    self._sink.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
                except (OSError, ValueError):
                    self.dropped += 1  # telemetry sink down: never block admission
        return rec


# ---------------------------------------------------------------- #35 metrics + exporter
DEFAULT_BUCKETS = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)


class Histogram:
    def __init__(self, buckets: Iterable[float] = DEFAULT_BUCKETS):
        self.buckets = tuple(sorted(buckets))
        self.counts = [0] * (len(self.buckets) + 1)
        self.sum = 0.0
        self.count = 0
        self._samples: deque[float] = deque(maxlen=4096)

    def observe(self, v: float) -> None:
        self.counts[bisect_left(self.buckets, v)] += 1
        self.sum += v
        self.count += 1
        self._samples.append(v)

    def quantile(self, q: float) -> float:
        if not self._samples:
            return 0.0
        s = sorted(self._samples)
        return s[min(len(s) - 1, int(q * len(s)))]


class MetricsRegistry:
    """Counters, gauges and histograms with a hard label-cardinality ceiling."""

    def __init__(self, max_series: int = 1000):
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._hist: dict[tuple[str, tuple[tuple[str, str], ...]], Histogram] = {}
        self._series: dict[str, int] = {}
        self._max = max_series
        self._lock = threading.Lock()
        self.overflowed = 0

    def _key(self, name: str, labels: Mapping[str, str]) -> tuple[str, tuple[tuple[str, str], ...]]:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        if key not in self._counters and key not in self._gauges and key not in self._hist:
            if self._series.get(name, 0) >= self._max:
                self.overflowed += 1
                return (name, (("overflow", "__other__"),))
            self._series[name] = self._series.get(name, 0) + 1
        return key

    def inc(self, name: str, value: float = 1, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            self._counters[k] = self._counters.get(k, 0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self._gauges[self._key(name, labels)] = value

    def observe(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            self._hist.setdefault(k, Histogram()).observe(value)

    def histogram(self, name: str, **labels: str) -> Histogram | None:
        return self._hist.get((name, tuple(sorted(labels.items()))))

    @staticmethod
    def _fmt(labels: tuple[tuple[str, str], ...], extra: tuple[tuple[str, str], ...] = ()) -> str:
        items = labels + extra
        if not items:
            return ""
        return "{" + ",".join(f'{k}="{v}"' for k, v in items) + "}"

    def prometheus(self) -> str:
        """Prometheus text exposition format 0.0.4."""
        out: list[str] = []
        with self._lock:
            for (n, lab), v in sorted(self._counters.items()):
                out.append(f"{n}_total{self._fmt(lab)} {v}")
            for (n, lab), v in sorted(self._gauges.items()):
                out.append(f"{n}{self._fmt(lab)} {v}")
            for (n, lab), h in sorted(self._hist.items(), key=lambda kv: kv[0]):
                cum = 0
                for b, c in zip(h.buckets, h.counts[:-1], strict=True):
                    cum += c
                    out.append(f"{n}_bucket{self._fmt(lab, (('le', repr(b)),))} {cum}")
                out.append(f"{n}_bucket{self._fmt(lab, (('le', '+Inf'),))} {h.count}")
                out.append(f"{n}_sum{self._fmt(lab)} {h.sum}")
                out.append(f"{n}_count{self._fmt(lab)} {h.count}")
        return "\n".join(out) + "\n"


def process_resources() -> dict[str, float]:
    """CPU/memory resource metrics from the stdlib (Unix)."""
    try:
        import resource
        ru = resource.getrusage(resource.RUSAGE_SELF)
        rss = ru.ru_maxrss * (1 if sys.platform == "darwin" else 1024)
        return {"cpu_user_s": ru.ru_utime, "cpu_sys_s": ru.ru_stime, "max_rss_bytes": float(rss)}
    except ImportError:  # pragma: no cover - windows
        return {"cpu_user_s": time.process_time(), "cpu_sys_s": 0.0, "max_rss_bytes": 0.0}


# ---------------------------------------------------------------- #37 tracing (W3C trace-context)
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_traceparent(header: str | None) -> dict[str, str] | None:
    if not header:
        return None
    m = _TP.match(header.strip())
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
        return None
    return {"trace_id": m.group(1), "parent_id": m.group(2), "flags": m.group(3)}


class Tracer:
    """Minimal span recorder with W3C ``traceparent`` ingress/egress and a bounded export buffer."""

    def __init__(self, sample_rate: float = 1.0, buffer: int = 10_000, clock: Callable[[], float] = time.time):
        self.sample_rate = sample_rate
        self.spans: deque[dict[str, object]] = deque(maxlen=buffer)
        self._clock = clock

    def start(self, name: str, traceparent: str | None = None, **attrs: object) -> dict[str, object]:
        parent = parse_traceparent(traceparent)
        trace_id = parent["trace_id"] if parent else secrets.token_hex(16)
        sampled = (parent["flags"] == "01") if parent else (secrets.randbelow(10_000) < self.sample_rate * 10_000)
        return {"name": name, "trace_id": trace_id, "span_id": secrets.token_hex(8),
                "parent_id": parent["parent_id"] if parent else None, "start": self._clock(),
                "sampled": sampled, "attrs": redact(attrs)}

    @staticmethod
    def traceparent(span: Mapping[str, object]) -> str:
        return f"00-{span['trace_id']}-{span['span_id']}-{'01' if span['sampled'] else '00'}"

    def end(self, span: dict[str, object], status: str = "ok", **attrs: object) -> None:
        span["end"] = self._clock()
        span["status"] = status
        span["attrs"] = {**span["attrs"], **redact(attrs)}  # type: ignore[dict-item]
        if span["sampled"] or status != "ok":
            self.spans.append(span)


# ---------------------------------------------------------------- #38 safe diagnostics / #39 lineage
def explain(decision: Mapping[str, object], *, policy_revision: str, precedence: Iterable[str],
            adapter_choice: Mapping[str, object] | None, lineage: Mapping[str, str]) -> dict[str, object]:
    """Operator explain view: why a decision was made, without tenant secrets or payload."""
    return {
        "schema": "PK_DATA_PLANE_EXPLAIN/1",
        "transfer": decision.get("transfer_id"),
        "tenant_hash": hash_label(str(decision.get("tenant", ""))),
        "workload_hash": hash_label(str(decision.get("workload", ""))),
        "tier": decision.get("tier"), "locality": decision.get("locality"),
        "destination": decision.get("destination"), "classification": decision.get("classification"),
        "size": decision.get("size"), "policy_revision": policy_revision,
        "constraints": list(precedence), "adapter": redact(dict(adapter_choice or {})),
        "lineage": dict(lineage),
    }


def lineage(release: str, build_sha256: str, node: str, infra_graph_ref: str = "unset") -> dict[str, str]:
    """Correlation block linking telemetry to release lineage and the infrastructure graph."""
    return {"release": release, "artifact_sha256": build_sha256, "node": node, "infra_graph_ref": infra_graph_ref}
