"""Metrics, structured logs, W3C trace context, decision records and explain
view (INV-37-C071..C079).  Stdlib only; export is pull (``snapshot``) or JSONL.

Privacy policy (C075, C079): logs and metrics never contain payload bytes,
tokens or key material.  Tenant ids in high-cardinality diagnostics are
replaced by a keyed pseudonym (``pseudonym``) unless the caller holds the
``inspect`` capability; see OBSERVABILITY.md.
"""
from __future__ import annotations

import bisect
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import IO, Any, Mapping

_FORBIDDEN_FIELDS = re.compile(r"(payload|token|secret|key|password|data_bytes)", re.I)
TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


class Histogram:
    """Bounded reservoir (most recent N) for percentile estimation."""

    def __init__(self, cap: int = 4096) -> None:
        self._vals: deque[float] = deque(maxlen=cap)
        self.count = 0
        self.total = 0.0
        self.max = 0.0

    def observe(self, v: float) -> None:
        self._vals.append(v)
        self.count += 1
        self.total += v
        self.max = max(self.max, v)

    def percentiles(self) -> dict[str, float]:
        s = sorted(self._vals)
        if not s:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0, "count": 0}

        def q(p: float) -> float:
            return s[min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))]

        return {"p50": q(0.50), "p95": q(0.95), "p99": q(0.99), "max": self.max, "count": self.count}


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict[tuple[str, tuple], float] = {}
        self.gauges: dict[tuple[str, tuple], float] = {}
        self.hist: dict[tuple[str, tuple], Histogram] = {}

    @staticmethod
    def _k(name: str, labels: Mapping[str, str] | None) -> tuple[str, tuple]:
        return name, tuple(sorted((labels or {}).items()))

    def inc(self, name: str, v: float = 1, **labels: str) -> None:
        with self._lock:
            k = self._k(name, labels)
            self.counters[k] = self.counters.get(k, 0) + v

    def set(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            self.gauges[self._k(name, labels)] = v

    def observe(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            self.hist.setdefault(self._k(name, labels), Histogram()).observe(v)

    def get(self, name: str, **labels: str) -> float:
        with self._lock:
            k = self._k(name, labels)
            return self.counters.get(k, self.gauges.get(k, 0))

    def snapshot(self) -> dict[str, Any]:
        def fmt(k):
            n, lab = k
            return n + ("{" + ",".join(f'{a}="{b}"' for a, b in lab) + "}" if lab else "")

        with self._lock:
            return {
                "counters": {fmt(k): v for k, v in sorted(self.counters.items())},
                "gauges": {fmt(k): v for k, v in sorted(self.gauges.items())},
                "histograms": {fmt(k): h.percentiles() for k, h in sorted(self.hist.items())},
            }

    def prometheus(self) -> str:
        snap = self.snapshot()
        lines = [f"inv37_{k} {v}" for k, v in {**snap["counters"], **snap["gauges"]}.items()]
        for k, p in snap["histograms"].items():
            for q in ("p50", "p95", "p99", "max"):
                lines.append(f"inv37_{k}_{q} {p[q]}")
        return "\n".join(lines) + "\n"


@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    sampled: bool = True

    @classmethod
    def new(cls, sample_ratio: float = 1.0) -> "TraceContext":
        return cls(secrets.token_hex(16), secrets.token_hex(8), secrets.randbelow(10_000) < sample_ratio * 10_000)

    @classmethod
    def parse(cls, header: str | None, sample_ratio: float = 1.0) -> "TraceContext":
        """Parse W3C ``traceparent``; malformed or all-zero ids start a new trace."""
        if isinstance(header, str):
            m = TRACEPARENT.match(header.strip())
            if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
                return cls(m.group(1), m.group(2), bool(int(m.group(3), 16) & 1))
        return cls.new(sample_ratio)

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, secrets.token_hex(8), self.sampled)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


_LEVELS = {"debug": 10, "info": 20, "warning": 30, "error": 40}


class StructuredLogger:
    def __init__(self, *, node: str, component: str = "inv37", level: str = "info",
                 stream: IO[str] | None = None, path: str | None = None, keep: int = 2000) -> None:
        self.node = node
        self.component = component
        self.level = _LEVELS[level]
        self.stream = stream
        self.path = path
        self.records: deque[dict[str, Any]] = deque(maxlen=keep)
        self._lock = threading.Lock()
        self.export_errors = 0

    def log(self, level: str, op: str, msg: str, *, tenant: str | None = None, workload: str | None = None,
            transfer_id: str | None = None, trace: TraceContext | None = None, **fields: Any) -> dict[str, Any] | None:
        if _LEVELS[level] < self.level:
            return None
        clean = {k: ("<redacted>" if _FORBIDDEN_FIELDS.search(k) else v) for k, v in fields.items()}
        rec = {"ts": round(time.time(), 6), "level": level, "node": self.node, "component": self.component,
               "op": op, "msg": msg, "tenant": tenant, "workload": workload, "transfer_id": transfer_id,
               "trace_id": trace.trace_id if trace else None, "span_id": trace.span_id if trace else None, **clean}
        with self._lock:
            self.records.append(rec)
            line = json.dumps(rec, sort_keys=True, default=str)
            # Export is a non-critical dependency (C056): failures degrade, never block.
            try:
                if self.stream is not None:
                    self.stream.write(line + "\n")
                if self.path:
                    with open(self.path, "a", encoding="utf-8") as fh:
                        fh.write(line + "\n")
            except (OSError, ValueError):
                self.export_errors += 1
        return rec


def pseudonym(key: bytes, value: str) -> str:
    return "t_" + hmac.new(key, value.encode(), hashlib.sha256).hexdigest()[:16]


@dataclass
class Decision:
    """Record of an automated decision (C076) with inputs, policy and outcome."""

    decision: str                    # e.g. admission, transport_select, quarantine
    outcome: str                     # admit | reject | select:<x> | ...
    reason_code: str
    inputs: dict[str, Any]
    policy: dict[str, Any]
    constraints: dict[str, Any]
    transfer_id: str | None = None
    trace_id: str | None = None
    config_digest: str | None = None
    artifact: str | None = None
    ts: float = field(default_factory=time.time)


class DecisionLog:
    def __init__(self, keep: int = 5000) -> None:
        self._d: deque[Decision] = deque(maxlen=keep)
        self._lock = threading.Lock()

    def record(self, d: Decision) -> Decision:
        with self._lock:
            self._d.append(d)
        return d

    def for_transfer(self, tid: str) -> list[Decision]:
        with self._lock:
            return [d for d in self._d if d.transfer_id == tid]

    def all(self) -> list[Decision]:
        with self._lock:
            return list(self._d)


def explain(decisions: list[Decision]) -> str:
    """Operator-readable explain view (C077)."""
    if not decisions:
        return "no automated decisions recorded"
    out = []
    for d in decisions:
        out.append(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(d.ts))}] {d.decision} -> {d.outcome} "
                   f"(reason={d.reason_code})")
        out.append(f"    inputs:      {json.dumps(d.inputs, sort_keys=True, default=str)}")
        out.append(f"    policy:      {json.dumps(d.policy, sort_keys=True, default=str)}")
        out.append(f"    constraints: {json.dumps(d.constraints, sort_keys=True, default=str)}")
        out.append(f"    lineage:     artifact={d.artifact} config={d.config_digest} trace={d.trace_id}")
    return "\n".join(out)


def release_lineage() -> dict[str, Any]:
    """Artifact identity for correlation with release lineage (C078).  The
    package digest is computed over the installed source files."""
    from pathlib import Path

    root = Path(__file__).resolve().parent
    h = hashlib.sha256()
    for p in sorted(root.glob("*.py")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    ver = (root / "VERSION").read_text(encoding="utf-8").strip()
    return {"package": "inv37-bulk-data-plane", "version": ver, "source_digest": "sha256:" + h.hexdigest(),
            "python": sys.version.split()[0], "platform": sys.platform,
            "build_commit": os.environ.get("INV37_BUILD_COMMIT"),
            "infrastructure_node": os.environ.get("INV37_NODE_ID")}
