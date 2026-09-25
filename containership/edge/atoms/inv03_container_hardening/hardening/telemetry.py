"""Metrics, structured secret-safe logging, and W3C trace context.

Checklist items served: 39 (metrics exporter), 40 (structured logging with
redaction), 41 (trace propagation), 44 (retention/export policy as data),
45 (alert rule definitions, evaluated in-process; dashboards are BLOCKED on a
real monitoring backend).
"""
from __future__ import annotations

import json
import re
import secrets
import threading
from bisect import bisect_left

BUCKETS_MS = (0.1, 0.25, 0.5, 1, 2, 5, 10, 25, 50, 100)
_SECRET_KEYS = re.compile(r"(?i)(token|secret|password|passwd|key|credential|authorization|cookie)")
_SECRET_VALUES = re.compile(r"(?i)(bearer\s+[a-z0-9._\-]+|eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]+|"
                            r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")

RETENTION_POLICY = {
    "schema": "INV03_TELEMETRY_POLICY/1",
    "audit_ledger": {"retention_days": 400, "sampling": "none (every event)", "tenant_isolated": True},
    "decision_logs": {"retention_days": 90, "sampling": "all denials; admits 10%", "tenant_isolated": True},
    "metrics": {"retention_days": 395, "resolution": "15s raw 14d, 5m rollup thereafter"},
    "traces": {"retention_days": 14, "sampling": "parent-based, 5% root"},
    "privacy": "no spec values, env vars or secrets leave the evaluator; only control names and reason codes",
    "status": "PROPOSED - retention numbers need owner approval (item 44 acceptance)",
}

ALERT_RULES = [
    {"name": "Inv03AttackIndicator", "expr": "rate(inv03_denials_total{control=~'not-privileged|host-mounts|host-namespaces'}[5m]) > 1",
     "class": "attack_indicator", "severity": "page"},
    {"name": "Inv03DependencyFailure", "expr": "rate(inv03_decisions_total{reason='DEPENDENCY_FAILURE'}[5m]) > 0",
     "class": "dependency_failure", "severity": "page"},
    {"name": "Inv03InternalDefect", "expr": "increase(inv03_decisions_total{reason='INTERNAL_DEFECT'}[10m]) > 0",
     "class": "software_defect", "severity": "page"},
    {"name": "Inv03ExceptionExpiring", "expr": "inv03_exceptions_expiring_soon > 0",
     "class": "exception_expiry_risk", "severity": "ticket"},
    {"name": "Inv03LatencySLO", "expr": "histogram_quantile(0.99, inv03_eval_ms_bucket) > 5",
     "class": "slo", "severity": "ticket"},
    {"name": "Inv03EmergencyDenyAll", "expr": "inv03_emergency_deny_all == 1",
     "class": "operational", "severity": "page"},
]


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict[tuple, int] = {}
        self.gauges: dict[str, float] = {}
        self.hist = [0] * (len(BUCKETS_MS) + 1)
        self.hist_sum = 0.0

    def inc(self, name: str, **labels) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self.counters[key] = self.counters.get(key, 0) + 1

    def set(self, name: str, v: float) -> None:
        with self._lock:
            self.gauges[name] = v

    def observe_ms(self, v: float) -> None:
        with self._lock:
            self.hist[bisect_left(BUCKETS_MS, v)] += 1
            self.hist_sum += v

    def get(self, name: str, **labels) -> int:
        return self.counters.get((name, tuple(sorted(labels.items()))), 0)

    def prometheus(self) -> str:
        lines = []
        with self._lock:
            for (name, labels), v in sorted(self.counters.items()):
                lab = ",".join(f'{k}="{_esc(val)}"' for k, val in labels)
                lines.append(f"{name}{{{lab}}} {v}")
            for name, gv in sorted(self.gauges.items()):
                lines.append(f"{name} {gv}")
            cum = 0.0
            for b, c in zip(BUCKETS_MS + (float("inf"),), self.hist, strict=True):
                cum += c
                le = "+Inf" if b == float("inf") else repr(b)
                lines.append(f'inv03_eval_ms_bucket{{le="{le}"}} {cum}')
            lines.append(f"inv03_eval_ms_sum {self.hist_sum}")
            lines.append(f"inv03_eval_ms_count {cum}")
        return "\n".join(lines) + "\n"

    def quantile_ms(self, q: float) -> float:
        total = sum(self.hist)
        if not total:
            return 0.0
        need, cum = q * total, 0
        for b, c in zip(BUCKETS_MS + (float("inf"),), self.hist, strict=True):
            cum += c
            if cum >= need:
                return b
        return float("inf")


def _esc(v: object) -> str:
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def redact(obj: object, depth: int = 0) -> object:
    if depth > 8:
        return "<depth-limit>"
    if isinstance(obj, dict):
        return {k: ("<redacted>" if _SECRET_KEYS.search(str(k)) else redact(v, depth + 1)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v, depth + 1) for v in obj[:64]]
    if isinstance(obj, str):
        return _SECRET_VALUES.sub("<redacted>", obj[:1024])
    return obj


class StructuredLogger:
    def __init__(self, sink=None):
        self.sink = sink if sink is not None else []
        self._lock = threading.Lock()

    def log(self, level: str, event: str, **fields) -> dict:
        rec = {"level": level, "event": event, "component": "INV-03", **dict(redact(fields))}  # type: ignore[call-overload]
        line = json.dumps(rec, sort_keys=True, default=str)
        with self._lock:
            if hasattr(self.sink, "append"):
                self.sink.append(line)
            else:
                self.sink.write(line + "\n")
        return rec


def parse_traceparent(h: object) -> tuple[str, str] | None:
    if not isinstance(h, str):
        return None
    m = _TRACEPARENT.match(h.strip())
    if not m or set(m.group(1)) == {"0"} or set(m.group(2)) == {"0"}:
        return None
    return m.group(1), m.group(2)


def child_traceparent(incoming: object) -> tuple[str, str, str]:
    """Continue an incoming trace or start one; returns (trace_id, span_id, header)."""
    parsed = parse_traceparent(incoming)
    trace_id = parsed[0] if parsed else secrets.token_hex(16)
    span_id = secrets.token_hex(8)
    return trace_id, span_id, f"00-{trace_id}-{span_id}-01"
