"""G13-MC-022 metrics, G13-MC-023 structured logging, G13-MC-024 tracing,
G13-MC-025 telemetry redaction/privacy and G13-MC-026 release-lineage
correlation.  Stdlib only; exporters are pluggable sinks.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

# ----------------------------------------------------------------------- redaction (MC-025)
#: field -> class.  "public" exported as-is; "pseudonymous" hashed with a per-deployment salt;
#: "sensitive" never exported; anything unlisted is dropped (allowlist, not denylist).
FIELD_CLASSES: dict[str, str] = {
    "event": "public", "component": "public", "operation": "public", "node": "public", "site": "public",
    "environment": "public", "effect": "public", "rule": "public", "version": "public",
    "generation": "public", "digest": "public", "bundle_id": "public", "code": "public",
    "reason": "public", "mode": "public", "state": "public", "latency_ms": "public", "tie_break": "public",
    "stale": "public", "trace_id": "public", "span_id": "public", "release": "public",
    "tenant": "pseudonymous", "workload": "pseudonymous", "subject": "pseudonymous",
    "request": "sensitive", "attributes": "sensitive", "token": "sensitive", "values": "sensitive",
}
RETENTION = {"logs_days": 30, "metrics_days": 395, "traces_days": 7, "audit_days": 2555}
SAMPLING = {"trace_ratio": 0.05, "always_sample_errors": True, "always_sample_denies": False}


class Redactor:
    def __init__(self, salt: bytes | None = None) -> None:
        self.salt = salt or secrets.token_bytes(16)

    def pseudonym(self, value: Any) -> str:
        return "p:" + hashlib.sha256(self.salt + str(value).encode()).hexdigest()[:16]

    def apply(self, fields: Mapping[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in fields.items():
            cls = FIELD_CLASSES.get(k)
            if cls == "public":
                out[k] = v
            elif cls == "pseudonymous":
                out[k] = self.pseudonym(v)
        return out


# ----------------------------------------------------------------------- metrics (MC-022)
LATENCY_BUCKETS_MS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 1000)
_LABEL_OK = re.compile(r"^[A-Za-z0-9_.:@/-]{0,128}$")


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict[tuple[str, tuple], float] = {}
        self.gauges: dict[tuple[str, tuple], float] = {}
        self.hist: dict[tuple[str, tuple], list] = {}
        self.max_series = 5000          # cardinality guard

    @staticmethod
    def _labels(labels: Mapping[str, Any]) -> tuple:
        return tuple(sorted((k, str(v) if _LABEL_OK.match(str(v)) else "invalid") for k, v in labels.items()))

    def inc(self, name: str, value: float = 1, **labels: Any) -> None:
        with self._lock:
            key = (name, self._labels(labels))
            if key not in self.counters and len(self.counters) >= self.max_series:
                key = (name, (("overflow", "true"),))
            self.counters[key] = self.counters.get(key, 0) + value

    def set(self, name: str, value: float, **labels: Any) -> None:
        with self._lock:
            self.gauges[(name, self._labels(labels))] = value

    def observe(self, name: str, value_ms: float, **labels: Any) -> None:
        with self._lock:
            key = (name, self._labels(labels))
            h = self.hist.setdefault(key, [[0] * (len(LATENCY_BUCKETS_MS) + 1), 0.0, 0, []])
            h[0][bisect.bisect_left(LATENCY_BUCKETS_MS, value_ms)] += 1
            h[1] += value_ms
            h[2] += 1
            if len(h[3]) < 10_000:
                h[3].append(value_ms)
            else:
                h[3][h[2] % 10_000] = value_ms

    def counter(self, name: str, **labels: Any) -> float:
        if labels:
            return self.counters.get((name, self._labels(labels)), 0)
        return sum(v for (n, _), v in self.counters.items() if n == name)

    def quantile(self, name: str, q: float) -> float | None:
        samples = sorted(s for (n, _), h in self.hist.items() if n == name for s in h[3])
        if not samples:
            return None
        return samples[min(len(samples) - 1, int(q * len(samples)))]

    def prometheus(self) -> str:
        lines = []
        fmt = lambda lbl: "{" + ",".join(f'{k}="{v}"' for k, v in lbl) + "}" if lbl else ""
        with self._lock:
            for (n, l), v in sorted(self.counters.items()):
                lines.append(f"g13_{n}_total{fmt(l)} {v}")
            for (n, l), v in sorted(self.gauges.items()):
                lines.append(f"g13_{n}{fmt(l)} {v}")
            for (n, l), (b, s, c, _) in sorted(self.hist.items()):
                acc = 0
                for bound, cnt in zip(LATENCY_BUCKETS_MS + (float("inf"),), b):
                    acc += cnt
                    le = "+Inf" if bound == float("inf") else str(bound)
                    lines.append(f"g13_{n}_bucket{fmt(tuple(l) + (('le', le),))} {acc}")
                lines.append(f"g13_{n}_sum{fmt(l)} {s}")
                lines.append(f"g13_{n}_count{fmt(l)} {c}")
        return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------- tracing (MC-024)
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    start: float
    end: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-01"


class Tracer:
    def __init__(self, redactor: Redactor, sink: Callable[[Span], None] | None = None) -> None:
        self.redactor = redactor
        self.sink = sink
        self.finished: list[Span] = []

    @staticmethod
    def parse(traceparent: str | None) -> tuple[str | None, str | None]:
        if isinstance(traceparent, str):
            m = _TP.match(traceparent.strip())
            if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
                return m.group(1), m.group(2)
        return None, None

    def start(self, name: str, traceparent: str | None = None, **attrs: Any) -> Span:
        tid, parent = self.parse(traceparent)
        return Span(name, tid or secrets.token_hex(16), secrets.token_hex(8), parent, time.perf_counter(),
                    attributes=self.redactor.apply(attrs))

    def finish(self, span: Span, **attrs: Any) -> None:
        span.end = time.perf_counter()
        span.attributes.update(self.redactor.apply(attrs))
        if len(self.finished) < 10_000:
            self.finished.append(span)
        if self.sink:
            self.sink(span)


# ----------------------------------------------------------------------- logging (MC-023)
EVENT_IDS = {
    "G13-L001": "verdict", "G13-L002": "default_deny", "G13-L010": "bundle_activated",
    "G13-L011": "bundle_rejected", "G13-L012": "bundle_rollback", "G13-L020": "stale_warning",
    "G13-L021": "stale_hard", "G13-L022": "stale_recovered", "G13-L030": "control_changed",
    "G13-L040": "auth_denied", "G13-L050": "overload_shed", "G13-L060": "dependency_failure",
    "G13-L070": "config_changed",
}


class StructuredLogger:
    def __init__(self, redactor: Redactor, *, component: str = "GAP-13", node: str | None = None,
                 site: str = "default", environment: str = "prod", sink: Callable[[str], None] | None = None,
                 capacity: int = 10_000) -> None:
        self.redactor = redactor
        self.base = {"component": component, "node": node or os.environ.get("HOSTNAME", "local"),
                     "site": site, "environment": environment}
        self.sink = sink
        self.lines: list[dict[str, Any]] = []
        self.capacity = capacity

    def log(self, event_id: str, level: str = "info", **fields: Any) -> dict[str, Any]:
        if event_id not in EVENT_IDS:
            raise ValueError(f"unregistered event id {event_id}")
        rec = {"ts_ms": int(time.time() * 1000), "level": level, "event_id": event_id,
               "event": EVENT_IDS[event_id], **self.redactor.apply({**self.base, **fields})}
        rec["event_id"] = event_id
        rec["level"] = level
        if len(self.lines) >= self.capacity:
            self.lines.pop(0)
        self.lines.append(rec)
        if self.sink:
            self.sink(json.dumps(rec, sort_keys=True))
        return rec


# ----------------------------------------------------------------------- lineage (MC-026)
@dataclass(frozen=True)
class Lineage:
    """Binds every verdict to engine release, bundle provenance and topology snapshot."""
    engine_release: str
    engine_artifact_digest: str | None = None
    topology_source: str | None = None
    topology_snapshot: str | None = None

    def annotate(self, verdict: dict[str, Any]) -> dict[str, Any]:
        verdict["lineage"] = {"engine_release": self.engine_release,
                              "engine_artifact_digest": self.engine_artifact_digest,
                              "topology_snapshot": self.topology_snapshot}
        return verdict
