"""MC-075..MC-084 — status, metrics, logs, trace context, diagnostics, reasons, explain.

All sinks are bounded; label cardinality is capped; diagnostics are redacted
and sampled.  Signals match the contract: sandbox_starts, syscall_denials,
residual_syscalls, profile_failures, retained_capabilities, plus
RED/USE metrics for the launcher.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import threading
import time
from collections import deque
from typing import Any

from .config import redact

MAX_SERIES = 2048
BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
_LABEL_RE = re.compile(r"^[a-zA-Z0-9_.:-]{0,64}$")


class Metrics:
    def __init__(self):
        self.counters: dict[tuple, float] = {}
        self.gauges: dict[tuple, float] = {}
        self.hist: dict[tuple, list[float]] = {}
        self.dropped_series = 0
        self._lock = threading.Lock()

    def _key(self, name, labels):
        lab = tuple(sorted((k, v if _LABEL_RE.match(str(v)) else "invalid") for k, v in (labels or {}).items()))
        return (name, lab)

    def _room(self, store, key) -> bool:
        if key in store or len(self.counters) + len(self.gauges) + len(self.hist) < MAX_SERIES:
            return True
        self.dropped_series += 1
        return False

    def inc(self, name, labels=None, v=1.0):
        with self._lock:
            k = self._key(name, labels)
            if self._room(self.counters, k):
                self.counters[k] = self.counters.get(k, 0) + v

    def set(self, name, labels=None, v=0.0):
        with self._lock:
            k = self._key(name, labels)
            if self._room(self.gauges, k):
                self.gauges[k] = v

    def observe(self, name, v, labels=None):
        with self._lock:
            k = self._key(name, labels)
            if self._room(self.hist, k):
                h = self.hist.setdefault(k, [0.0] * (len(BUCKETS) + 2))
                for i, b in enumerate(BUCKETS):
                    if v <= b:
                        h[i] += 1
                h[-2] += v
                h[-1] += 1

    def exposition(self) -> str:
        def fmt(name, lab, extra=()):
            lab = list(lab) + list(extra)
            return name + ("{" + ",".join(f'{k}="{v}"' for k, v in lab) + "}" if lab else "")
        out = []
        with self._lock:
            for (n, lab), v in sorted(self.counters.items()):
                out.append(f"{fmt('inv39_' + n + '_total', lab)} {v}")
            for (n, lab), v in sorted(self.gauges.items()):
                out.append(f"{fmt('inv39_' + n, lab)} {v}")
            for (n, lab), h in sorted(self.hist.items()):
                for i, b in enumerate(BUCKETS):
                    out.append(f"{fmt('inv39_' + n + '_bucket', lab, [('le', b)])} {h[i]}")
                out.append(f"{fmt('inv39_' + n + '_bucket', lab, [('le', '+Inf')])} {h[-1]}")
                out.append(f"{fmt('inv39_' + n + '_sum', lab)} {h[-2]}")
                out.append(f"{fmt('inv39_' + n + '_count', lab)} {h[-1]}")
            out.append(f"inv39_dropped_series_total {self.dropped_series}")
        return "\n".join(out) + "\n"


def new_traceparent(parent: str | None = None) -> str:
    """W3C trace-context: keep trace-id from a valid parent, new span id (MC-078)."""
    m = re.fullmatch(r"00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})", parent or "")
    trace = m.group(1) if m and m.group(1) != "0" * 32 else os.urandom(16).hex()
    return f"00-{trace}-{os.urandom(8).hex()}-01"


def trace_id(tp: str) -> str:
    return tp.split("-")[1]


class Logger:
    """Structured JSON lines with stable identifiers (MC-077)."""

    REQUIRED = ("node", "tenant", "workload", "component", "operation")

    def __init__(self, stream=None, *, node: str, component: str = "inv39", max_line: int = 8192):
        self.stream = stream or sys.stderr
        self.node, self.component, self.max_line = node, component, max_line
        self.lines = deque(maxlen=1000)

    def log(self, level: str, msg: str, *, tenant="-", workload="-", operation="-", trace=None, **fields):
        rec = {"ts": round(time.time(), 6), "level": level, "msg": msg, "node": self.node,
               "tenant": tenant, "workload": workload, "component": self.component,
               "operation": operation, "trace_id": trace_id(trace) if trace else None}
        rec.update(redact(fields))
        line = json.dumps(rec, sort_keys=True, default=str)[: self.max_line]
        self.lines.append(line)
        self.stream.write(line + "\n")


class Diagnostics:
    """High-cardinality channel: sampled, redacted, bounded ring (MC-079/083)."""

    def __init__(self, sample_rate: float = 1.0, capacity: int = 5000, rng=random.random):
        self.sample_rate, self.rng = sample_rate, rng
        self.ring = deque(maxlen=capacity)

    def record(self, kind: str, data: dict[str, Any]) -> bool:
        if self.rng() >= self.sample_rate:
            return False
        self.ring.append({"ts": time.time(), "kind": kind, "data": redact(data)})
        return True


REASON_KINDS = ("admission", "rejection", "rollback", "termination", "quarantine", "launch")


class Reasons:
    """Persistent reason record for every automated decision (MC-080) via the audit chain."""

    def __init__(self, audit):
        self.audit = audit

    def record(self, kind: str, decision: str, *, subject: str, code: str | None, because: list[str],
               profile_digest: str | None = None, config_digest: str | None = None, evidence: str | None = None):
        if kind not in REASON_KINDS:
            raise ValueError(kind)
        return self.audit.append("reason", {"kind": kind, "decision": decision, "subject": subject,
                                            "code": code, "because": because[:16],
                                            "profile_digest": profile_digest, "config_digest": config_digest,
                                            "evidence": evidence})

    def explain(self, subject: str) -> list[dict[str, Any]]:
        """Operator explain view (MC-081): every decision about ``subject``, oldest first."""
        entries = getattr(self.audit, "entries", [])
        if not entries and self.audit.path:
            with open(self.audit.path) as f:
                entries = [json.loads(l) for l in f if l.strip()]
        return [e for e in entries if e["kind"] == "reason" and e["data"]["subject"] == subject]


# MC-084: alert classes that must stay distinguishable on dashboards
ALERT_RULES = {
    "load": "inv39_admission_rejections_total{code=\"E_OVERLOADED\"} rate > 1/s for 5m",
    "degradation": "inv39_launch_seconds p99 > NFR startup p99 for 10m",
    "policy_rejection": "inv39_profile_failures_total{code=\"E_PROFILE_INVALID\"} rate > 0",
    "dependency_failure": "inv39_errors_total{code=\"E_DEPENDENCY_UNAVAILABLE\"} > 0",
    "attack": "inv39_errors_total{code=~\"E_ATTESTATION_FAILED|E_UNAUTHENTICATED\"} > 0 or "
              "inv39_syscall_denials_total rate spike > 10x baseline",
    "software_defect": "inv39_errors_total{code=\"E_INTERNAL\"} > 0",
}
