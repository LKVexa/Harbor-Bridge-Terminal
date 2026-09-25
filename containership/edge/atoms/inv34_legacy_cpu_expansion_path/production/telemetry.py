"""Metrics, structured logs, trace propagation and redaction (MC-051..MC-054, MC-057).

SPDX-License-Identifier: NOASSERTION
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from typing import Any, TextIO

# --- W3C traceparent (MC-053) -------------------------------------------
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_traceparent(value: str | None) -> tuple[str, str] | None:
    if not value:
        return None
    m = _TP.match(value.strip())
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
        return None
    return m.group(1), m.group(2)


def child_traceparent(parent: str | None) -> tuple[str, str, str]:
    """Return (trace_id, span_id, header) continuing ``parent`` or starting a new trace."""
    p = parse_traceparent(parent)
    trace_id = p[0] if p else os.urandom(16).hex()
    span_id = os.urandom(8).hex()
    return trace_id, span_id, f"00-{trace_id}-{span_id}-01"


# --- redaction (MC-054, MC-031) -----------------------------------------
SENSITIVE_KEYS = re.compile(r"(secret|token|password|authorization|credential|key|signature|mac)$", re.I)
TOKEN_SHAPE = re.compile(r"\b[\w-]{1,128}\.\d{9,11}\.[0-9a-f]{16}\.[0-9a-f]{64}\b")


def redact(value: Any, _depth: int = 0) -> Any:
    if _depth > 8:
        return "<depth-limit>"
    if isinstance(value, dict):
        return {k: ("<redacted>" if SENSITIVE_KEYS.search(str(k)) else redact(v, _depth + 1)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v, _depth + 1) for v in value[:100]]
    if isinstance(value, str):
        return TOKEN_SHAPE.sub("<redacted-token>", value)[:2048]
    return value


# --- structured logs (MC-052) -------------------------------------------
STABLE_FIELDS = ("vm_id", "node", "tenant", "workload", "component", "operation", "request_id",
                 "generation", "trace_id", "config_digest", "release")


class StructuredLogger:
    def __init__(self, component: str, stream: TextIO | None = None, **static: Any) -> None:
        self.component, self.stream, self.static = component, stream or sys.stderr, static
        self._lock = threading.Lock()

    def log(self, level: str, msg: str, **fields: Any) -> dict:
        rec = {"ts": round(time.time(), 3), "level": level, "component": self.component, "msg": msg,
               **self.static, **fields}
        rec = redact(rec)
        with self._lock:
            self.stream.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        return rec


# --- metrics (MC-051) ---------------------------------------------------
class Metrics:
    """Prometheus text exposition, stdlib only.  Label values are restricted to a
    bounded vocabulary (error codes, outcome names) — never VM or tenant IDs —
    so the export cannot grow unbounded or leak tenant identity (MC-054)."""

    BUCKETS = (0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10, 30, 60, 120, 300)
    _LABEL = re.compile(r"^[A-Za-z0-9_]{1,64}$")

    def __init__(self) -> None:
        self.counters: dict[tuple[str, tuple], float] = {}
        self.gauges: dict[str, float] = {}
        self.hist: dict[str, list] = {}
        self._lock = threading.Lock()

    def inc(self, name: str, n: float = 1, **labels: str) -> None:
        for v in labels.values():
            if not self._LABEL.match(str(v)):
                raise ValueError("label value outside bounded vocabulary")
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self.counters[key] = self.counters.get(key, 0) + n

    def set(self, name: str, v: float) -> None:
        with self._lock:
            self.gauges[name] = v

    def observe(self, name: str, v: float) -> None:
        with self._lock:
            h = self.hist.setdefault(name, [[0] * len(self.BUCKETS), 0.0, 0])
            for i, b in enumerate(self.BUCKETS):
                if v <= b:
                    h[0][i] += 1
            h[1] += v
            h[2] += 1

    def render(self) -> str:
        out = []
        with self._lock:
            for (name, labels), v in sorted(self.counters.items()):
                lab = ",".join(f'{k}="{val}"' for k, val in labels)
                out.append(f"{name}{{{lab}}} {v}" if lab else f"{name} {v}")
            for name, v in sorted(self.gauges.items()):
                out.append(f"{name} {v}")
            for name, (b, s, c) in sorted(self.hist.items()):
                for le, n in zip(self.BUCKETS, b):
                    out.append(f'{name}_bucket{{le="{le}"}} {n}')
                out.append(f'{name}_bucket{{le="+Inf"}} {c}')
                out.append(f"{name}_sum {s}")
                out.append(f"{name}_count {c}")
        return "\n".join(out) + "\n"


TELEMETRY_POLICY = {
    "schema": "INV34_TELEMETRY_POLICY/1",
    "metrics": {"labels": "bounded vocabulary only (outcome, code); no vm/tenant ids", "retention_days": "PROPOSED:30"},
    "logs": {"redaction": "SENSITIVE_KEYS + TOKEN_SHAPE", "retention_days": "PROPOSED:14", "sampling": "none for audit-relevant events; 1:10 for debug"},
    "traces": {"propagation": "W3C traceparent", "sampling": "PROPOSED: parent-based, 10% head"},
    "audit": {"retention_days": "PROPOSED:400", "sampling": "never sampled"},
    "export": "no export destination bound in this package",
    "status": "PROPOSED — retention and export require owner approval (MC-057)",
}
