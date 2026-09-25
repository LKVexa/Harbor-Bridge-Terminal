"""Observability exporter (component 22).

* bounded-cardinality metrics (labels are allow-listed; node ids are never
  metric labels — they go to logs/traces) with Prometheus text exposition;
* structured JSON logs, redacted through ``secrets_boundary.redact``, each
  carrying ``rollout_id``/``wave``/``trace_id`` for GAP-09 correlation;
* alert rules evaluated in-process for tests and exported as data for the
  production alert manager.
"""
from __future__ import annotations

import json
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

from .common import Clock, SystemClock, new_id
from .secrets_boundary import redact

ALLOWED_LABELS = frozenset({"outcome", "trigger", "state", "op", "reason_code", "gate_class", "complete", "version",
                            "dependency", "site"})
MAX_SERIES_PER_METRIC = 200

METRICS = {
    "gap08_rollouts_active": ("gauge", "Active rollouts by lifecycle state"),
    "gap08_gate_verdicts_total": ("counter", "Gate verdicts by outcome"),
    "gap08_rollbacks_total": ("counter", "Rollbacks by trigger and completeness"),
    "gap08_rollback_failed_nodes_total": ("counter", "Nodes that failed rollback"),
    "gap08_nodes_on_version": ("gauge", "Nodes recorded on a version"),
    "gap08_deferred_nodes": ("gauge", "Deferred nodes"),
    "gap08_deferred_oldest_age_seconds": ("gauge", "Age of the oldest deferred node"),
    "gap08_quarantined_nodes": ("gauge", "Quarantined nodes"),
    "gap08_commands_total": ("counter", "Node commands by op and outcome"),
    "gap08_state_restore_failures_total": ("counter", "Snapshot/audit integrity rejections"),
    "gap08_dependency_unavailable_total": ("counter", "Fail-closed events by dependency"),
    "gap08_errors_total": ("counter", "Errors by reason_code"),
    "gap08_drift_nodes": ("gauge", "Nodes whose observed version drifts from recorded state"),
    "gap08_step_seconds": ("histogram", "Controller step latency"),
}
_BUCKETS = (0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 30, 120)


@dataclass
class Telemetry:
    clock: Clock = field(default_factory=SystemClock)
    sink: Callable[[str], None] | None = None
    _series: dict[str, dict[tuple, float]] = field(default_factory=lambda: defaultdict(dict))
    _hist: dict[str, dict[tuple, list[float]]] = field(default_factory=lambda: defaultdict(dict))
    logs: list[dict[str, Any]] = field(default_factory=list)
    dropped_series: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _key(self, name: str, labels: dict[str, str]) -> tuple | None:
        if name not in METRICS:
            raise KeyError(name)
        bad = set(labels) - ALLOWED_LABELS
        if bad:
            raise ValueError(f"label(s) {bad} not allowed (cardinality control)")
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        s = self._series[name] if METRICS[name][0] != "histogram" else self._hist[name]
        if key not in s and len(s) >= MAX_SERIES_PER_METRIC:
            self.dropped_series += 1
            return None
        return key

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            if k is not None:
                self._series[name][k] = self._series[name].get(k, 0.0) + value

    def set(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            if k is not None:
                self._series[name][k] = value

    def observe(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            k = self._key(name, labels)
            if k is not None:
                self._hist[name].setdefault(k, []).append(value)

    def get(self, name: str, **labels: str) -> float:
        return self._series[name].get(tuple(sorted((k, str(v)) for k, v in labels.items())), 0.0)

    def log(self, event: str, *, level: str = "info", trace_id: str | None = None, **fields: Any) -> dict[str, Any]:
        rec = redact({"ts": self.clock.now(), "level": level, "event": event,
                      "trace_id": trace_id or new_id("tr"), **fields})
        with self._lock:
            self.logs.append(rec)
            if len(self.logs) > 10_000:
                del self.logs[: len(self.logs) - 10_000]
        if self.sink:
            self.sink(json.dumps(rec, sort_keys=True))
        return rec

    def prometheus(self) -> str:
        lines = []
        with self._lock:
            for name, (kind, help_) in sorted(METRICS.items()):
                lines.append(f"# HELP {name} {help_}")
                lines.append(f"# TYPE {name} {kind}")
                if kind == "histogram":
                    for key, vals in sorted(self._hist[name].items()):
                        lab = ",".join(f'{k}="{v}"' for k, v in key)
                        for b in _BUCKETS:
                            le = f'le="{b}"'
                            lines.append(f"{name}_bucket{{{lab + ',' if lab else ''}{le}}} {sum(1 for v in vals if v <= b)}")
                        lines.append(f"{name}_count{{{lab}}} {len(vals)}")
                        lines.append(f"{name}_sum{{{lab}}} {sum(vals)}")
                    continue
                for key, v in sorted(self._series[name].items()):
                    lab = ",".join(f'{k}="{v2}"' for k, v2 in key)
                    lines.append(f"{name}{{{lab}}} {v}" if lab else f"{name} {v}")
        return "\n".join(lines) + "\n"


ALERT_RULES = [
    {"alert": "Gap08RollbackIncomplete", "expr": "increase(gap08_rollback_failed_nodes_total[10m]) > 0",
     "severity": "page", "runbook": "docs/RUNBOOKS.md#rollback-incomplete"},
    {"alert": "Gap08QuarantineNonZero", "expr": "gap08_quarantined_nodes > 0", "severity": "ticket",
     "runbook": "docs/RUNBOOKS.md#quarantine-recovery"},
    {"alert": "Gap08DeferredAging", "expr": "gap08_deferred_oldest_age_seconds > 86400", "severity": "ticket",
     "runbook": "docs/RUNBOOKS.md#deferred-nodes"},
    {"alert": "Gap08DependencyFailClosed", "expr": "increase(gap08_dependency_unavailable_total[5m]) > 0",
     "severity": "page", "runbook": "docs/RUNBOOKS.md#degraded-dependencies"},
    {"alert": "Gap08StateIntegrity", "expr": "increase(gap08_state_restore_failures_total[5m]) > 0",
     "severity": "page", "runbook": "docs/RUNBOOKS.md#integrity-failure"},
    {"alert": "Gap08Drift", "expr": "gap08_drift_nodes > 0", "severity": "ticket",
     "runbook": "docs/RUNBOOKS.md#reconciliation"},
]
