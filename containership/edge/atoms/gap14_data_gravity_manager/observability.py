"""Metrics, structured logging, trace context (G14-P1-18, P1-19; D01-D05 everywhere).

* Metrics are declared up-front with an allowlist of label *names* and a closed
  set of label *values* (or a max distinct count).  Raw tenant, workload,
  dataset, request or decision IDs are never labels.  Exceeding the cardinality
  budget folds values into ``__overflow__`` rather than growing without bound.
* Logs are single-line JSON.  Fields named in ``REDACT`` are replaced by a keyed
  hash (stable for correlation, not reversible); fields in ``DROP`` (secrets,
  tokens, MACs) are removed.
* Trace context follows W3C ``traceparent`` (version 00).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sys
import threading
from bisect import bisect_left
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, TextIO

OVERFLOW = "__overflow__"
LATENCY_BUCKETS = (0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
COST_BUCKETS = (0, 1, 5, 10, 25, 50, 100, 250, 1000, 10000)


class _Metric:
    def __init__(self, name: str, help_: str, labels: tuple[str, ...], max_series: int):
        self.name, self.help, self.labels, self.max_series = name, help_, labels, max_series
        self._lock = threading.Lock()

    def _key(self, labels: Mapping[str, str], existing: Mapping[tuple, Any]) -> tuple:
        if set(labels) != set(self.labels):
            raise ValueError(f"{self.name}: labels must be exactly {self.labels}")
        key = tuple(str(labels[n])[:64] for n in self.labels)
        if key not in existing and len(existing) >= self.max_series:
            key = tuple(OVERFLOW for _ in self.labels)
        return key


class Counter(_Metric):
    kind = "counter"

    def __init__(self, *a: Any, **k: Any):
        super().__init__(*a, **k)
        self.values: dict[tuple, float] = {}

    def inc(self, n: float = 1.0, **labels: str) -> None:
        with self._lock:
            key = self._key(labels, self.values)
            self.values[key] = self.values.get(key, 0.0) + n


class Histogram(_Metric):
    kind = "histogram"

    def __init__(self, *a: Any, buckets: tuple[float, ...] = LATENCY_BUCKETS, **k: Any):
        super().__init__(*a, **k)
        self.buckets = buckets
        self.values: dict[tuple, list[float]] = {}   # [bucket counts..., +Inf, sum, count]

    def observe(self, v: float, **labels: str) -> None:
        with self._lock:
            key = self._key(labels, self.values)
            row = self.values.setdefault(key, [0.0] * (len(self.buckets) + 3))
            row[bisect_left(self.buckets, v)] += 1
            row[-2] += v
            row[-1] += 1

    def quantile(self, q: float, **labels: str) -> float:
        row = self.values.get(tuple(labels[n] for n in self.labels))
        if not row or not row[-1]:
            return 0.0
        target, acc = q * row[-1], 0.0
        for i, b in enumerate(self.buckets):
            acc += row[i]
            if acc >= target:
                return b
        return float("inf")


class Registry:
    def __init__(self) -> None:
        self.metrics: dict[str, _Metric] = {}

    def counter(self, name: str, help_: str, labels: Iterable[str] = (), max_series: int = 64) -> Counter:
        return self.metrics.setdefault(name, Counter(name, help_, tuple(labels), max_series))  # type: ignore[return-value]

    def histogram(self, name: str, help_: str, labels: Iterable[str] = (), max_series: int = 32,
                  buckets: tuple[float, ...] = LATENCY_BUCKETS) -> Histogram:
        return self.metrics.setdefault(name, Histogram(name, help_, tuple(labels), max_series, buckets=buckets))  # type: ignore[return-value]

    def series_count(self) -> int:
        return sum(len(m.values) for m in self.metrics.values())  # type: ignore[attr-defined]

    def exposition(self) -> str:
        """Prometheus text format 0.0.4."""
        out: list[str] = []
        for m in self.metrics.values():
            out.append(f"# HELP {m.name} {m.help}")
            out.append(f"# TYPE {m.name} {m.kind}")
            for key, val in sorted(m.values.items()):  # type: ignore[attr-defined]
                lbl = ",".join(f'{n}="{_esc(v)}"' for n, v in zip(m.labels, key))
                if isinstance(m, Counter):
                    out.append(f"{m.name}{{{lbl}}} {val}" if lbl else f"{m.name} {val}")
                else:
                    acc = 0.0
                    sep = "," if lbl else ""
                    for i, b in enumerate(m.buckets):
                        acc += val[i]
                        out.append(f'{m.name}_bucket{{{lbl}{sep}le="{b}"}} {acc}')
                    acc += val[len(m.buckets)]
                    out.append(f'{m.name}_bucket{{{lbl}{sep}le="+Inf"}} {acc}')
                    out.append(f"{m.name}_sum{{{lbl}}} {val[-2]}" if lbl else f"{m.name}_sum {val[-2]}")
                    out.append(f"{m.name}_count{{{lbl}}} {val[-1]}" if lbl else f"{m.name}_count {val[-1]}")
        return "\n".join(out) + "\n"


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def standard_metrics(reg: Registry) -> dict[str, _Metric]:
    """The GAP-14 signal set (contract.signals plus P1-18 additions)."""
    return {
        "recommendations": reg.counter("gap14_gravity_recommendations_total", "Recommendations by direction and outcome",
                                       ("direction", "outcome", "mode"), 48),
        "eliminated": reg.counter("gap14_illegal_options_eliminated_total", "Eliminated options by code",
                                  ("direction", "code"), 48),
        "no_legal": reg.counter("gap14_no_legal_option_total", "Pairs with no legal answer"),
        "refusals": reg.counter("gap14_refusals_total", "Refusals/errors by reason code and category",
                                ("code", "category"), 64),
        "cost": reg.histogram("gap14_move_cost_estimate", "Recommended-option cost", ("direction",), 8, COST_BUCKETS),
        "latency": reg.histogram("gap14_decision_latency_seconds", "End-to-end decision latency", ("mode",), 8),
        "dep_latency": reg.histogram("gap14_dependency_latency_seconds", "Dependency call latency",
                                     ("dependency", "outcome"), 48),
        "handshake": reg.histogram("gap14_pkcore_handshake_seconds", "pk_core compatibility handshake", ("result",), 16),
        "audit": reg.counter("gap14_audit_records_total", "Audit records written/failed", ("result",), 4),
        "config": reg.counter("gap14_config_activations_total", "Config activations", ("result",), 8),
        "admission": reg.counter("gap14_admission_rejected_total", "Admission rejections", ("code",), 8),
        "shadow_divergence": reg.counter("gap14_shadow_divergence_total", "Shadow vs primary direction divergence",
                                         ("model",), 16),
        "drift": reg.counter("gap14_calibration_drift_alarms_total", "Cost-model drift alarms", ("dimension",), 16),
        "build_info": reg.counter("gap14_build_info", "Engine version and active config revision (value 1)",
                                  ("version", "config_revision", "mode"), 16),
        "explain": reg.counter("gap14_explain_requests_total", "Explain requests by outcome", ("outcome",), 8),
        "simulations": reg.counter("gap14_simulations_total", "What-if simulations by outcome", ("outcome",), 8),
        "readiness": reg.counter("gap14_readiness_transitions_total", "Readiness transitions", ("to",), 8),
        "degraded": reg.counter("gap14_degraded_decisions_total", "Non-production decisions using grace-aged inputs",
                                ("source",), 8),
    }


# ------------------------------------------------------------------ logging
REDACT = frozenset({"tenant_id", "workload_id", "dataset", "subject", "principal"})
MAX_FIELD_CHARS = 512
MAX_RECORD_CHARS = 8192
DROP = frozenset({"token", "sig", "mac", "secret", "password", "authorization", "claims"})


class StructuredLogger:
    def __init__(self, stream: TextIO | None = None, *, redaction_key: bytes | None = None,
                 clock: Callable[[], float] | None = None, component: str = "GAP-14"):
        self.stream = stream or sys.stderr
        self._key = redaction_key or secrets.token_bytes(32)
        self._clock = clock
        self.component = component
        self._lock = threading.Lock()

    def redact(self, value: Any) -> str:
        return "h:" + hmac.new(self._key, str(value).encode(), hashlib.sha256).hexdigest()[:16]

    def _clean(self, obj: Any) -> Any:
        if isinstance(obj, Mapping):
            out = {}
            for k, v in obj.items():
                lk = str(k).lower()
                if lk in DROP:
                    continue
                out[k] = self.redact(v) if lk in REDACT else self._clean(v)
            return out
        if isinstance(obj, (list, tuple)):
            return [self._clean(v) for v in obj[:32]] + (["...truncated"] if len(obj) > 32 else [])
        if isinstance(obj, str) and len(obj) > MAX_FIELD_CHARS:
            return obj[:MAX_FIELD_CHARS] + "...truncated"
        return obj

    def log(self, level: str, event: str, *, trace: "TraceContext | None" = None, **fields: Any) -> dict[str, Any]:
        rec: dict[str, Any] = {"level": level, "event": event, "component": self.component}
        if self._clock:
            rec["ts"] = self._clock()
        if trace:
            rec["trace_id"], rec["span_id"] = trace.trace_id, trace.span_id
        rec.update(self._clean(fields))
        line = json.dumps(rec, sort_keys=True, default=str)
        if len(line) > MAX_RECORD_CHARS:  # keep event code + correlation, drop the payload
            keep = {k: rec[k] for k in ("level", "event", "component", "ts", "trace_id", "span_id") if k in rec}
            keep["truncated"] = True
            line = json.dumps(keep, sort_keys=True)
        try:
            with self._lock:
                self.stream.write(line + "\n")
        except Exception:  # telemetry failure must never change decision semantics
            pass
        return rec


# -------------------------------------------------------------------- tracing
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    parent_id: str | None = None
    flags: str = "01"

    @classmethod
    def from_traceparent(cls, header: str | None) -> "TraceContext":
        m = _TP.match(header or "")
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return cls(secrets.token_hex(16), secrets.token_hex(8))
        return cls(m.group(1), secrets.token_hex(8), m.group(2), m.group(3))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), self.span_id, self.flags)

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"
