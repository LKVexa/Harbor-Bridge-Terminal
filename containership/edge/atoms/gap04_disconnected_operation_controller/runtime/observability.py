"""Metrics (C26), structured logging (C27), trace propagation (C28).

Dependency-free. Metrics render in Prometheus text exposition format 0.0.4 with
bounded label cardinality: every label value must come from a declared,
finite allow-list or it is folded into ``other``. Logging emits one JSON object
per line with stable identifiers and redacts secret-bearing fields. Traces use
W3C Trace Context (``traceparent``) so spans join across control-plane,
supervisor, replication, and reconciliation boundaries.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import secrets
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, TextIO

# ------------------------------------------------------------------ metrics
LABEL_VALUES = {
    "kind": {"restart", "rebalance", "admit-known", "admit-new", "scale"},
    "tier": {"full", "sustain", "freeze", "expired"},
    "code": None,  # filled from error registry at import time below
    "outcome": {"accepted", "conflict", "rejected", "retried", "compensated", "quarantined"},
    "state": {"up", "down", "degraded", "flapping"},
    "dependency": {"GAP-01", "GAP-05", "GAP-12", "GAP-13", "PLN-07", "pk_core"},
    "version": None, "config": None,
    "reason": {"journal_full", "journal_high_watermark", "clock", "quarantine", "override"},
}
DEFAULT_BUCKETS = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)


def _init_codes():
    from .errors import REGISTRY
    LABEL_VALUES["code"] = set(REGISTRY)


_init_codes()


class Metrics:
    def __init__(self, namespace: str = "gap04"):
        self.ns = namespace
        self._lock = threading.Lock()
        self._defs: dict[str, tuple[str, str, tuple[str, ...]]] = {}
        self._vals: dict[tuple[str, tuple], Any] = {}

    def _labels(self, name: str, labels: dict[str, str]) -> tuple:
        _, _, names = self._defs[name]
        out = []
        for n in names:
            v = str(labels.get(n, ""))
            allowed = LABEL_VALUES.get(n)
            out.append(v if allowed is None or v in allowed else "other")
        return tuple(out)

    def define(self, name: str, mtype: str, help_: str, labels: Iterable[str] = ()) -> None:
        self._defs[name] = (mtype, help_, tuple(labels))

    def inc(self, name: str, n: float = 1, **labels) -> None:
        with self._lock:
            k = (name, self._labels(name, labels))
            self._vals[k] = self._vals.get(k, 0) + n

    def set(self, name: str, v: float, **labels) -> None:
        with self._lock:
            self._vals[(name, self._labels(name, labels))] = v

    def observe(self, name: str, v: float, **labels) -> None:
        with self._lock:
            k = (name, self._labels(name, labels))
            h = self._vals.setdefault(k, {"buckets": [0] * len(DEFAULT_BUCKETS), "sum": 0.0, "count": 0})
            for i, b in enumerate(DEFAULT_BUCKETS):
                if v <= b:
                    h["buckets"][i] += 1
            h["sum"] += v
            h["count"] += 1

    def get(self, name: str, **labels):
        return self._vals.get((name, self._labels(name, labels)))

    def render(self) -> str:
        lines = []
        with self._lock:
            for name, (mtype, help_, lnames) in sorted(self._defs.items()):
                full = f"{self.ns}_{name}"
                lines.append(f"# HELP {full} {help_}")
                lines.append(f"# TYPE {full} {mtype}")
                for (n, lv), val in sorted(self._vals.items(), key=lambda kv: (kv[0][0], kv[0][1])):
                    if n != name:
                        continue
                    lab = ",".join(f'{k}="{v}"' for k, v in zip(lnames, lv))
                    if mtype == "histogram":
                        cum = 0
                        for b, c in zip(DEFAULT_BUCKETS, val["buckets"]):
                            cum = c
                            sep = "," if lab else ""
                            lines.append(f'{full}_bucket{{{lab}{sep}le="{b}"}} {cum}')
                        sep = "," if lab else ""
                        lines.append(f'{full}_bucket{{{lab}{sep}le="+Inf"}} {val["count"]}')
                        lines.append(f"{full}_sum{{{lab}}} {val['sum']}")
                        lines.append(f"{full}_count{{{lab}}} {val['count']}")
                    else:
                        lines.append(f"{full}{{{lab}}} {val}" if lab else f"{full} {val}")
        return "\n".join(lines) + "\n"


def standard_metrics() -> Metrics:
    m = Metrics()
    m.define("decisions_total", "counter", "Accepted offline decisions by kind and tier", ["kind", "tier"])
    m.define("denials_total", "counter", "Refused decisions by stable error code", ["code"])
    m.define("tier_transitions_total", "counter", "Degradation tier transitions", ["tier"])
    m.define("tier", "gauge", "Current tier (0=full,1=sustain,2=freeze,3=expired)")
    m.define("lease_remaining_seconds", "gauge", "Seconds until the autonomy lease expires")
    m.define("policy_staleness_seconds", "gauge", "Age of the cached verified policy")
    m.define("journal_utilization_ratio", "gauge", "Durable journal bytes / max_bytes")
    m.define("journal_bytes", "gauge", "Durable journal size in bytes")
    m.define("reconcile_outcomes_total", "counter", "Reconciliation outcomes", ["outcome"])
    m.define("reconcile_conflicts_total", "counter", "Conflicts surfaced on reconnect")
    m.define("retries_total", "counter", "Retries against adjacent dependencies", ["dependency"])
    m.define("decision_latency_seconds", "histogram", "End-to-end decide() latency")
    m.define("reachability_state", "gauge", "Control-plane reachability (1 up, 0 otherwise)", ["state"])
    m.define("storage_alarms_total", "counter", "Storage pressure / fail-safe events", ["reason"])
    m.define("quarantined", "gauge", "1 when the controller is quarantined")
    m.define("admission_rejections_total", "counter", "Load-shed requests")
    m.define("replays_total", "counter", "Idempotent replays of an already-committed request id")
    m.define("build_info", "gauge", "Build/config identity (value always 1)", ["version", "config"])
    m.define("verification_failures_total", "counter", "Lease/policy/time verification failures by code", ["code"])
    return m


# ------------------------------------------------------------------ logging
REDACT_KEYS = re.compile(r"(^|_)(sig|signature|secret|token|password|private|seed|nonce|authorization|ct|passphrase)(_|$)|key_material|private_key|audit_key", re.I)
HASH_KEYS = {"subject", "principal", "tenant_payload"}
LOG_SCHEMA = "PK_GAP04_LOG/1"


def _redact(obj: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "<depth>"
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if REDACT_KEYS.search(str(k)):
                out[k] = "<redacted>"
            elif k in HASH_KEYS and isinstance(v, str):
                out[k] = "h:" + hashlib.sha256(v.encode()).hexdigest()[:16]
            else:
                out[k] = _redact(v, depth + 1)
        return out
    if isinstance(obj, (list, tuple)):
        return [_redact(v, depth + 1) for v in obj[:100]]
    if isinstance(obj, str) and len(obj) > 2048:
        return obj[:2048] + "<truncated>"
    return obj


class StructuredLogger:
    LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40, "critical": 50}

    def __init__(self, site: str, node: str, stream: TextIO | None = None, level: str = "info",
                 debug_sample_rate: float = 0.01, clock: Callable[[], float] = time.time):
        self.site, self.node = site, node
        self.stream = stream or sys.stderr
        self.level = self.LEVELS[level]
        self.sample = debug_sample_rate
        self.clock = clock
        self._lock = threading.Lock()
        self.sink: list[dict] | None = None  # tests / in-process export

    def log(self, level: str, event: str, *, op: str | None = None, workload: str | None = None,
            trace: "TraceContext | None" = None, **fields) -> dict | None:
        lv = self.LEVELS[level]
        if lv < self.level and not (level == "debug" and random.random() < self.sample):
            return None
        rec = {"schema": LOG_SCHEMA, "ts": round(self.clock(), 3), "level": level, "event": event,
               "site": self.site, "node": self.node, "op": op, "workload": workload,
               "trace_id": trace.trace_id if trace else None, "span_id": trace.span_id if trace else None,
               "fields": _redact(fields)}
        line = json.dumps(rec, sort_keys=True, default=str)
        with self._lock:
            self.stream.write(line + "\n")
            if self.sink is not None:
                self.sink.append(rec)
        return rec

    def info(self, event, **kw): return self.log("info", event, **kw)
    def warning(self, event, **kw): return self.log("warning", event, **kw)
    def error(self, event, **kw): return self.log("error", event, **kw)


# ------------------------------------------------------------------ tracing
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    flags: str = "01"

    @classmethod
    def new(cls) -> "TraceContext":
        return cls(secrets.token_hex(16), secrets.token_hex(8))

    @classmethod
    def parse(cls, header: str | None) -> "TraceContext":
        """Parse a traceparent header; malformed/all-zero input starts a new trace (never trusted blindly)."""
        m = _TP.match(header or "")
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return cls.new()
        return cls(m.group(1), m.group(2), m.group(3))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), self.flags)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"
