"""Observability for INV-44 (missing component 15; C071-C080).

* ``Metrics`` — the five contract signals plus latency histograms, labelled,
  exported in Prometheus text exposition format (no client library needed).
* ``StructuredLogger`` — one JSON object per line, fixed field set, secrets
  redacted, control characters escaped by JSON encoding, trace/span ids.
* ``explain`` — a decision-explanation record for every admit/refuse.

Dashboards and alert routing are data files under ``ops/`` (alerts.yaml);
wiring them to a real Prometheus/Alertmanager is an environment step that is
BLOCKED until an observability backend is provisioned.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
from collections import defaultdict
from typing import Mapping, TextIO

from .audit_log import _redact

CONTRACT_SIGNALS = {
    "instances": "gauge",
    "hardening_refusals": "counter",
    "verification_failures": "counter",
    "fuel_exhaustions": "counter",
    "memory_growth_refusals": "counter",
}
EXTRA_SIGNALS = {
    "admissions": "counter",
    "authz_denials": "counter",
    "tenant_violations": "counter",
    "load_shed": "counter",
    "instantiate_seconds": "histogram",
}
BUCKETS = (0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
_MAX_SERIES = 10_000  # cardinality guard (C077)


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[tuple[str, tuple], float] = defaultdict(float)
        self._hist: dict[tuple[str, tuple], list] = {}

    @staticmethod
    def _key(name: str, labels: Mapping[str, str]) -> tuple[str, tuple]:
        if name not in CONTRACT_SIGNALS and name not in EXTRA_SIGNALS:
            raise KeyError(f"undeclared metric {name!r}")
        return name, tuple(sorted((str(k), str(v)) for k, v in labels.items()))

    def _guard(self, key) -> None:
        if key not in self._values and key not in self._hist and \
                len(self._values) + len(self._hist) >= _MAX_SERIES:
            raise OverflowError("metric cardinality limit reached")

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._guard(key)
            self._values[key] += value

    def set(self, name: str, value: float, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._guard(key)
            self._values[key] = value

    def observe(self, name: str, seconds: float, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._guard(key)
            h = self._hist.setdefault(key, [[0] * len(BUCKETS), 0, 0.0])
            for i, b in enumerate(BUCKETS):
                if seconds <= b:
                    h[0][i] += 1
            h[1] += 1
            h[2] += seconds

    def value(self, name: str, **labels: str) -> float:
        return self._values.get(self._key(name, labels), 0.0)

    def exposition(self) -> str:
        def fmt(labels: tuple, extra: tuple = ()) -> str:
            pairs = list(labels) + list(extra)
            if not pairs:
                return ""
            esc = lambda s: s.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
            return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in pairs) + "}"

        out: list[str] = []
        with self._lock:
            kinds = {**CONTRACT_SIGNALS, **EXTRA_SIGNALS}
            for name in sorted(kinds):
                out.append(f"# TYPE inv44_{name} {kinds[name]}")
                for (n, labels), v in sorted(self._values.items()):
                    if n == name:
                        out.append(f"inv44_{name}{fmt(labels)} {v:g}")
                for (n, labels), (counts, total, s) in sorted(self._hist.items()):
                    if n == name:
                        for b, c in zip(BUCKETS, counts):
                            out.append(f"inv44_{name}_bucket{fmt(labels, (('le', f'{b:g}'),))} {c}")
                        out.append(f"inv44_{name}_bucket{fmt(labels, (('le', '+Inf'),))} {total}")
                        out.append(f"inv44_{name}_count{fmt(labels)} {total}")
                        out.append(f"inv44_{name}_sum{fmt(labels)} {s:.9f}")
        return "\n".join(out) + "\n"


class StructuredLogger:
    FIELDS = ("ts", "level", "event", "tenant", "module", "trace_id", "span_id", "code", "detail")

    def __init__(self, stream: TextIO, *, clock=time.time) -> None:
        self._stream = stream
        self._clock = clock
        self._lock = threading.Lock()

    def log(self, level: str, event: str, *, tenant: str | None = None, module: str | None = None,
            trace_id: str | None = None, code: str | None = None, **detail: object) -> dict:
        rec = {
            "ts": round(float(self._clock()), 6),
            "level": level,
            "event": event,
            "tenant": tenant,
            "module": module,
            "trace_id": trace_id or secrets.token_hex(16),
            "span_id": secrets.token_hex(8),
            "code": code,
            "detail": _redact(detail),
        }
        with self._lock:
            self._stream.write(json.dumps(rec, sort_keys=True) + "\n")
        return rec


def explain(decision: str, *, reason_code: str | None, checks: Mapping[str, bool]) -> dict:
    """Decision explanation (C080): every check evaluated and its outcome."""
    return {
        "decision": decision,
        "reason_code": reason_code,
        "checks": [{"check": k, "passed": bool(v)} for k, v in checks.items()],
    }
