"""Components 20, 21, 22 - tamper-evident audit sink, metrics exporter,
structured logging and trace propagation."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from bisect import bisect_left
from dataclasses import dataclass, field

from .keys import canonical

# --------------------------------------------------------------------- metrics
DEFAULT_BUCKETS = (0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
_LABEL_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class Metrics:
    """Minimal thread-safe Prometheus-compatible registry (text format 0.0.4)."""

    MAX_SERIES = 100_000  # hard cardinality cap

    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict[tuple, float] = {}
        self.gauges: dict[tuple, float] = {}
        self.hists: dict[tuple, list] = {}
        self.help: dict[str, tuple[str, str]] = {}
        self.dropped_series = 0

    @staticmethod
    def _key(name, labels):
        return (name, tuple(sorted((labels or {}).items())))

    def _room(self, store, key) -> bool:
        if key in store:
            return True
        total = len(self.counters) + len(self.gauges) + len(self.hists)
        if total >= self.MAX_SERIES:
            self.dropped_series += 1
            return False
        return True

    def describe(self, name, kind, text):
        self.help[name] = (kind, text)

    def inc(self, name, labels=None, value=1.0):
        k = self._key(name, labels)
        with self._lock:
            if self._room(self.counters, k):
                self.counters[k] = self.counters.get(k, 0.0) + value

    def set(self, name, value, labels=None):
        k = self._key(name, labels)
        with self._lock:
            if self._room(self.gauges, k):
                self.gauges[k] = float(value)

    def observe(self, name, value, labels=None, buckets=DEFAULT_BUCKETS):
        k = self._key(name, labels)
        with self._lock:
            if not self._room(self.hists, k):
                return
            h = self.hists.setdefault(k, [list(buckets), [0] * (len(buckets) + 1), 0.0, 0])
            h[1][bisect_left(h[0], value)] += 1
            h[2] += value
            h[3] += 1

    def get(self, name, labels=None):
        k = self._key(name, labels)
        return self.counters.get(k, self.gauges.get(k))

    @staticmethod
    def _fmt(labels, extra=()):
        items = list(labels) + list(extra)
        if not items:
            return ""
        esc = lambda v: str(v).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
        return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in items) + "}"

    def render(self) -> str:
        out = []
        with self._lock:
            names = sorted({k[0] for k in (*self.counters, *self.gauges, *self.hists)})
            for n in names:
                kind, text = self.help.get(n, ("untyped", n))
                out.append(f"# HELP {n} {text}")
                out.append(f"# TYPE {n} {kind}")
                for (name, labels), v in sorted(self.counters.items()):
                    if name == n:
                        out.append(f"{n}{self._fmt(labels)} {v}")
                for (name, labels), v in sorted(self.gauges.items()):
                    if name == n:
                        out.append(f"{n}{self._fmt(labels)} {v}")
                for (name, labels), (bk, counts, s, c) in sorted(self.hists.items()):
                    if name != n:
                        continue
                    cum = 0
                    for b, cnt in zip(bk + ["+Inf"], counts):
                        cum += cnt
                        out.append(f"{n}_bucket{self._fmt(labels, [('le', b)])} {cum}")
                    out.append(f"{n}_sum{self._fmt(labels)} {s}")
                    out.append(f"{n}_count{self._fmt(labels)} {c}")
        return "\n".join(out) + "\n"


METRIC_CATALOG = {
    "gap10_node_temperature_celsius": ("gauge", "Aggregated node temperature used for the decision"),
    "gap10_power_ratio": ("gauge", "Power draw divided by power budget"),
    "gap10_power_ceiling_slots": ("gauge", "Derived capacity ceiling per node"),
    "gap10_ceiling_fraction": ("gauge", "Derived ceiling fraction per node"),
    "gap10_thermal_exclusions_total": ("counter", "Transitions into exclusion, by reason"),
    "gap10_telemetry_age_seconds": ("gauge", "Age of the last trusted sample"),
    "gap10_telemetry_samples_total": ("counter", "Telemetry samples by outcome"),
    "gap10_hysteresis_holds_total": ("counter", "Decisions held by recovery hysteresis"),
    "gap10_decision_latency_seconds": ("histogram", "Decision evaluation latency"),
    "gap10_dependency_failures_total": ("counter", "Dependency failures by dependency and code"),
    "gap10_enforcement_divergence": ("gauge", "1 when downstream applied ceiling differs from desired"),
    "gap10_battery_runtime_seconds": ("gauge", "Estimated remaining runtime above reserve"),
    "gap10_sensor_absent": ("gauge", "1 when a node has no usable thermal evidence"),
    "gap10_controls_active": ("gauge", "Active quarantine/freeze/disable controls"),
    "gap10_safe_to_enforce": ("gauge", "1 when the component reports safe-to-enforce"),
}


def new_metrics() -> Metrics:
    m = Metrics()
    for name, (kind, text) in METRIC_CATALOG.items():
        m.describe(name, kind, text)
    return m


# --------------------------------------------------------------------- logging
def new_trace_id() -> str:
    return uuid.uuid4().hex


def new_span_id() -> str:
    return uuid.uuid4().hex[:16]


def traceparent(trace_id: str, span_id: str) -> str:
    return f"00-{trace_id}-{span_id}-01"


def parse_traceparent(value: str | None) -> tuple[str, str] | None:
    m = re.fullmatch(r"00-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}", value or "")
    return (m.group(1), m.group(2)) if m else None


_SENSITIVE = ("secret", "signature", "key", "token", "password")


def pseudonymize(value: str, salt: str = "gap10") -> str:
    return "h:" + hashlib.sha256((salt + value).encode()).hexdigest()[:12]


class StructuredLogger:
    """JSON-lines logger with stable ids, trace context and redaction."""

    def __init__(self, sink=None, component="GAP-10", max_field_len=512):
        self.records: list[dict] = []
        self.sink = sink
        self.component = component
        self.max_field_len = max_field_len

    def log(self, level: str, event: str, *, trace_id=None, span_id=None, **fields) -> dict:
        rec = {"level": level, "component": self.component, "event": event,
               "trace_id": trace_id or new_trace_id(), "span_id": span_id or new_span_id()}
        for k, v in fields.items():
            if any(s in k.lower() for s in _SENSITIVE):
                v = "[REDACTED]"
            elif k == "workload" and isinstance(v, str):
                v = pseudonymize(v)
            elif isinstance(v, str) and len(v) > self.max_field_len:
                v = v[: self.max_field_len] + "...[truncated]"
            rec[k] = v
        self.records.append(rec)
        if self.sink:
            self.sink.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        return rec


# --------------------------------------------------------------------- audit
GENESIS = "0" * 64


class AuditSink:
    """Append-only, hash-chained audit log. ``verify`` detects any edit,
    deletion, reordering or truncation (truncation via the anchored head)."""

    EVENT_TYPES = frozenset({
        "policy.proposed", "policy.activated", "policy.rolled_back", "policy.rejected",
        "node.excluded", "node.readmitted", "node.band_changed", "control.applied", "control.released", "control.rejected",
        "ownership.acquired", "ownership.lost", "ownership.rejected", "security.failure",
        "enforcement.divergence", "state.restored", "rollout.promoted", "rollout.rolled_back",
    })

    def __init__(self, path: str | None = None, max_in_memory: int = 10_000):
        """With a ``path`` the file is authoritative and only the most recent
        ``max_in_memory`` entries are kept in RAM (bounded memory under soak);
        use ``read_all(path)`` for full verification."""
        self.path = path
        self.max_in_memory = max_in_memory
        self.entries: list[dict] = []
        self.count = 0
        self.head = GENESIS
        self._lock = threading.Lock()
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        self.entries.append(json.loads(line))
            if self.entries:
                self.head = self.entries[-1]["hash"]
                self.count = len(self.entries)
                self.entries = self.entries[-max_in_memory:]

    def append(self, event_type: str, actor: str, at: float, **detail) -> dict:
        if event_type not in self.EVENT_TYPES:
            raise ValueError(f"unknown audit event type {event_type}")
        with self._lock:
            body = {"seq": self.count, "type": event_type, "actor": actor, "at": at,
                    "detail": detail, "prev": self.head}
            body["hash"] = hashlib.sha256(canonical(body)).hexdigest()
            self.entries.append(body)
            self.count += 1
            if self.path and len(self.entries) > self.max_in_memory:
                del self.entries[: len(self.entries) - self.max_in_memory]
            self.head = body["hash"]
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(body, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            return body

    @staticmethod
    def read_all(path: str) -> list[dict]:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    @staticmethod
    def verify(entries: list[dict], anchored_head: str | None = None) -> tuple[bool, str]:
        prev = GENESIS
        for i, e in enumerate(entries):
            if e.get("seq") != i or e.get("prev") != prev:
                return False, f"chain broken at seq {i}"
            body = {k: v for k, v in e.items() if k != "hash"}
            if hashlib.sha256(canonical(body)).hexdigest() != e.get("hash"):
                return False, f"hash mismatch at seq {i}"
            prev = e["hash"]
        if anchored_head is not None and prev != anchored_head:
            return False, "head does not match external anchor (truncation or fork)"
        return True, "ok"
