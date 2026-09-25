"""Health, metrics export, structured logging, tracing, explainability, lineage.

Package-local references for MC-043 – MC-048.  Everything is stdlib-only and
emits standard wire formats (Prometheus text exposition 0.0.4, W3C
``traceparent``, JSON log lines) so that estate collectors (OpenTelemetry,
Prometheus, Loki/ELK) can ingest without an adapter.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
import threading
import time
from collections.abc import Mapping
from typing import Any, IO

from .security import redact

LOG_SCHEMA = "PK_IAC_LOG/1"
HEALTH_SCHEMA = "PK_IAC_HEALTH/1"
EXPLAIN_SCHEMA = "PK_IAC_EXPLAIN/1"
LINEAGE_SCHEMA = "PK_IAC_LINEAGE/1"


# --------------------------------------------------------------------- health
def health_status(*, version: str, config_digest: str | None, dependencies: Mapping[str, bool], critical: set[str],
                  backend_ok: bool, lock_holder: str | None, frozen: Mapping[str, Any], watchdog: Mapping[str, Any]) -> dict[str, Any]:
    reasons = []
    if not backend_ok:
        reasons.append("state backend unavailable or corrupt")
    for d, ok in sorted(dependencies.items()):
        if not ok and d in critical:
            reasons.append(f"critical dependency down: {d}")
    if frozen:
        reasons.append("mutation frozen: " + ",".join(sorted(frozen)))
    if watchdog.get("stalled"):
        reasons.append("stalled operations: " + ",".join(watchdog["stalled"]))
    return {
        "schema": HEALTH_SCHEMA,
        "version": version,
        "config_digest": config_digest,
        "live": True,
        "ready": not reasons,
        "readiness_reasons": reasons,
        "dependencies": dict(sorted(dependencies.items())),
        "lock_holder": lock_holder,
        "capabilities": ["plan", "apply", "drift", "protect", "rollback", "backup"],
        "watchdog": dict(watchdog),
    }


# -------------------------------------------------------------------- metrics
_METRIC_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
_LABEL_OK = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
ALLOWED_LABELS = {"tenant", "operation", "outcome", "dependency", "code"}
DEFAULT_BUCKETS = (0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 30)


class MetricsRegistry:
    """Counters, gauges and histograms with bounded label cardinality."""

    def __init__(self, max_series: int = 5000) -> None:
        self._c: dict[tuple[str, tuple], float] = {}
        self._g: dict[tuple[str, tuple], float] = {}
        self._h: dict[tuple[str, tuple], list[float]] = {}
        self._help: dict[str, tuple[str, str]] = {}
        self._lock = threading.Lock()
        self.max_series = max_series
        self.dropped = 0

    def _key(self, name: str, labels: Mapping[str, str] | None) -> tuple[str, tuple]:
        if not _METRIC_NAME.match(name):
            raise ValueError(f"bad metric name {name}")
        lab = tuple(sorted((labels or {}).items()))
        for k, v in lab:
            if k not in ALLOWED_LABELS or not _LABEL_OK.match(k):
                raise ValueError(f"label {k} not permitted (cardinality/privacy guard)")
            if redact({"v": v})["v"] != v:
                raise ValueError("secret-like label value refused")
        return name, lab

    def _room(self, store: dict, key: tuple) -> bool:
        if key in store:
            return True
        if len(self._c) + len(self._g) + len(self._h) >= self.max_series:
            self.dropped += 1
            return False
        return True

    def inc(self, name: str, value: float = 1, labels: Mapping[str, str] | None = None, help: str = "") -> None:
        k = self._key(name, labels)
        with self._lock:
            self._help.setdefault(name, ("counter", help))
            if self._room(self._c, k):
                self._c[k] = self._c.get(k, 0) + value

    def set(self, name: str, value: float, labels: Mapping[str, str] | None = None, help: str = "") -> None:
        k = self._key(name, labels)
        with self._lock:
            self._help.setdefault(name, ("gauge", help))
            if self._room(self._g, k):
                self._g[k] = value

    def observe(self, name: str, seconds: float, labels: Mapping[str, str] | None = None, help: str = "") -> None:
        k = self._key(name, labels)
        with self._lock:
            self._help.setdefault(name, ("histogram", help))
            if self._room(self._h, k):
                self._h.setdefault(k, []).append(seconds)

    def time(self, name: str, labels: Mapping[str, str] | None = None) -> "_Timer":
        return _Timer(self, name, labels)

    def ingest_state_metrics(self, state_metrics: Mapping[str, int], tenant: str = "default") -> None:
        for k, v in state_metrics.items():
            self.set(f"pk_iac_state_{k}", v, {"tenant": tenant})

    @staticmethod
    def _fmt(lab: tuple, extra: tuple = ()) -> str:
        items = list(lab) + list(extra)
        if not items:
            return ""
        esc = lambda s: str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")  # noqa: E731
        return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in items) + "}"

    def exposition(self) -> str:
        lines: list[str] = []
        with self._lock:
            for name in sorted(self._help):
                kind, help_ = self._help[name]
                lines.append(f"# HELP {name} {help_ or name}")
                lines.append(f"# TYPE {name} {kind}")
                if kind == "counter":
                    for (n, lab), v in sorted(self._c.items()):
                        if n == name:
                            lines.append(f"{name}{self._fmt(lab)} {v}")
                elif kind == "gauge":
                    for (n, lab), v in sorted(self._g.items()):
                        if n == name:
                            lines.append(f"{name}{self._fmt(lab)} {v}")
                else:
                    for (n, lab), obs in sorted(self._h.items()):
                        if n != name:
                            continue
                        for b in DEFAULT_BUCKETS:
                            lines.append(f"{name}_bucket{self._fmt(lab, (('le', str(b)),))} {sum(1 for o in obs if o <= b)}")
                        lines.append(f"{name}_bucket{self._fmt(lab, (('le', '+Inf'),))} {len(obs)}")
                        lines.append(f"{name}_sum{self._fmt(lab)} {sum(obs)}")
                        lines.append(f"{name}_count{self._fmt(lab)} {len(obs)}")
        return "\n".join(lines) + "\n"


class _Timer:
    def __init__(self, reg: MetricsRegistry, name: str, labels: Mapping[str, str] | None) -> None:
        self.reg, self.name, self.labels = reg, name, dict(labels or {})

    def __enter__(self) -> "_Timer":
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, et: Any, ev: Any, tb: Any) -> None:
        outcome = "error" if et else "ok"
        self.reg.observe(self.name, time.perf_counter() - self.t0, {**self.labels, "outcome": outcome})


# -------------------------------------------------------------------- tracing
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


class TraceContext:
    def __init__(self, trace_id: str, span_id: str, flags: str = "01", parent: str | None = None) -> None:
        self.trace_id, self.span_id, self.flags, self.parent = trace_id, span_id, flags, parent

    @classmethod
    def new(cls) -> "TraceContext":
        return cls(secrets.token_hex(16), secrets.token_hex(8))

    @classmethod
    def from_traceparent(cls, header: str | None) -> "TraceContext":
        m = _TP.match((header or "").strip().lower())
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return cls.new()  # invalid/untrusted header: start a fresh trace, never propagate garbage
        return cls(m.group(1), secrets.token_hex(8), m.group(3), parent=m.group(2))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), self.flags, parent=self.span_id)

    @property
    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"


# -------------------------------------------------------------------- logging
SEVERITIES = ("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL")


class StructuredLogger:
    def __init__(self, component: str = "INV-06", *, node: str | None = None, stream: IO[str] | None = None, min_severity: str = "INFO") -> None:
        self.component = component
        self.node = node or (os.uname().nodename if hasattr(os, "uname") else os.environ.get("COMPUTERNAME", "unknown"))
        self.stream = stream or sys.stderr
        self.min = SEVERITIES.index(min_severity)
        self._lock = threading.Lock()

    def log(self, severity: str, event: str, *, tenant: str | None = None, workload: str | None = None,
            operation: str | None = None, trace: TraceContext | None = None, **fields: Any) -> dict[str, Any]:
        if severity not in SEVERITIES:
            raise ValueError("unknown severity")
        rec = {
            "schema": LOG_SCHEMA,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{time.time_ns() % 1_000_000_000:09d}Z",
            "severity": severity,
            "component": self.component,
            "node": self.node,
            "tenant": tenant,
            "workload": workload,
            "operation": operation,
            "event": event,
            "trace_id": trace.trace_id if trace else None,
            "span_id": trace.span_id if trace else None,
            "fields": redact(fields),
        }
        if SEVERITIES.index(severity) >= self.min:
            with self._lock:
                self.stream.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        return rec


# -------------------------------------------------------------- explainability
def explain_plan(plan: Mapping[str, Any], *, current: Mapping[str, Any], desired: Mapping[str, Any],
                 policy_decision: Mapping[str, Any] | None = None, order: Mapping[str, list[str]] | None = None,
                 constraints: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Reason chain per resource: why it is in the plan, from which inputs, under which policy."""
    def diff_keys(a: Any, b: Any) -> list[str]:
        if isinstance(a, Mapping) and isinstance(b, Mapping):
            return sorted(k for k in set(a) | set(b) if a.get(k, object()) != b.get(k, object()))
        return ["<value>"]

    items = []
    for rid in sorted(plan["create"]):
        items.append({"resource": rid, "action": "create", "because": "declared in desired configuration, absent from state"})
    for rid in sorted(plan["update"]):
        items.append({"resource": rid, "action": "update", "because": "desired differs from state", "changed_fields": diff_keys(current.get(rid), desired.get(rid))})
    for rid in sorted(plan["delete"]):
        items.append({"resource": rid, "action": "delete", "because": "present in state, absent from desired configuration"})
    return redact({
        "schema": EXPLAIN_SCHEMA,
        "plan_digest": plan["integrity"]["digest"],
        "state_serial": plan["serial"],
        "policy": {"version": policy_decision.get("policy_version"), "allow": policy_decision.get("allow")} if policy_decision else None,
        "execution_order": dict(order) if order else None,
        "constraints": dict(constraints) if constraints else None,
        "items": items,
    })


def render_explanation(exp: Mapping[str, Any]) -> str:
    lines = [f"Plan {exp['plan_digest'][:12]} against state serial {exp['state_serial']}"]
    if exp.get("policy"):
        lines.append(f"  policy {exp['policy']['version']}: {'ALLOW' if exp['policy']['allow'] else 'DENY'}")
    for it in exp["items"]:
        extra = f" (fields: {', '.join(it['changed_fields'])})" if it.get("changed_fields") else ""
        lines.append(f"  {it['action'].upper():7} {it['resource']} — {it['because']}{extra}")
    return "\n".join(lines)


# ------------------------------------------------------------------- lineage
def lineage_record(*, plan: Mapping[str, Any], applied_serial: int, release_id: str, artifact_versions: Mapping[str, str],
                   config_digest: str, trace: TraceContext | None = None) -> dict[str, Any]:
    if not release_id:
        raise ValueError("release_id required for lineage")
    return {
        "schema": LINEAGE_SCHEMA,
        "release_id": release_id,
        "plan_digest": plan["integrity"]["digest"],
        "from_serial": plan["serial"],
        "to_serial": applied_serial,
        "config_digest": config_digest,
        "artifact_versions": dict(sorted(artifact_versions.items())),
        "resources": sorted(set(plan["create"]) | set(plan["update"]) | set(plan["delete"])),
        "trace_id": trace.trace_id if trace else None,
    }
