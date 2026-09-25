"""Metrics / structured logs / trace context / health (v6), dependency-free.

* ``Metrics`` - counters and fixed-bucket histograms with *bounded* label
  values (unknown values collapse to ``other``), Prometheus text exposition.
  Refusal reasons are labelled by stable error code only.
* ``StructuredLogger`` - JSON lines with a redaction pass: keys that look like
  secrets and values that look like key material/tokens are replaced; full
  artifact payloads are never logged (only digests).
* ``TraceContext`` - W3C ``traceparent`` parse/propagate so admission spans can
  join an OpenTelemetry trace (the OTel SDK exporter is optional; the IDs and
  attributes emitted are OTel-compatible).
* ``Health`` - liveness vs readiness aggregation of named dependency checks.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, TextIO

from .errors import ERROR_CODES

_BUCKETS = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, float("inf"))
ALLOWED_LABELS = {
    "code": set(ERROR_CODES) | {"ALLOW", "ok"},
    "kind": {"code", "policy", "grant", "label", "attestation", "bundle", "oci-image", "oci-index", "wasm-module",
             "wasm-component", "microvm-image", "provider-bundle", "trust-config", "sbom"},
    "outcome": {"allow", "deny", "defer", "error"},
    "dependency": {"trust", "policy", "time", "tlog", "kms", "registry", "audit"},
    "environment": None,  # validated by format + cardinality cap
}
MAX_SERIES = 5000


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._hist: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}
        self._env_seen: set[str] = set()

    def _labels(self, labels: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
        out = []
        for k, v in sorted(labels.items()):
            allowed = ALLOWED_LABELS.get(k, set())
            v = str(v)
            if k == "environment":
                if re.fullmatch(r"[a-z0-9-]{1,32}", v) is None or (v not in self._env_seen and len(self._env_seen) >= 32):
                    v = "other"
                else:
                    self._env_seen.add(v)
            elif allowed is not None and v not in allowed:
                v = "other"
            out.append((k, v))
        return tuple(out)

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            key = (name, self._labels(labels))
            if key not in self._counters and len(self._counters) >= MAX_SERIES:
                return
            self._counters[key] = self._counters.get(key, 0.0) + value

    def observe(self, name: str, seconds: float, **labels: str) -> None:
        with self._lock:
            key = (name, self._labels(labels))
            h = self._hist.get(key)
            if h is None:
                if len(self._hist) >= MAX_SERIES:
                    return
                h = self._hist[key] = [0.0] * (len(_BUCKETS) + 2)
            for i, b in enumerate(_BUCKETS):
                if seconds <= b:
                    h[i] += 1
            h[-2] += seconds
            h[-1] += 1

    def get(self, name: str, **labels: str) -> float:
        return self._counters.get((name, self._labels(labels)), 0.0)

    def exposition(self) -> str:
        lines = []
        with self._lock:
            for (name, labels), v in sorted(self._counters.items()):
                lines.append(f"{name}{_fmt(labels)} {v:g}")
            for (name, labels), h in sorted(self._hist.items()):
                for i, b in enumerate(_BUCKETS):
                    le = "+Inf" if b == float("inf") else f"{b:g}"
                    lines.append(f"{name}_bucket{_fmt(labels + (('le', le),))} {h[i]:g}")
                lines.append(f"{name}_sum{_fmt(labels)} {h[-2]:g}")
                lines.append(f"{name}_count{_fmt(labels)} {h[-1]:g}")
        return "\n".join(lines) + "\n"


def _fmt(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}"


_SECRET_KEY = re.compile(r"(secret|password|passwd|token|private|credential|pin|api[_-]?key|authorization)", re.I)
_SECRET_VAL = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|AKIA[0-9A-Z]{16}|hvs\.[A-Za-z0-9]{20,})")


def redact(obj: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "[depth]"
    if isinstance(obj, Mapping):
        return {k: ("[redacted]" if _SECRET_KEY.search(str(k)) else redact(v, depth + 1)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v, depth + 1) for v in obj[:100]]
    if isinstance(obj, (bytes, bytearray)):
        return f"[bytes:{len(obj)}]"
    if isinstance(obj, str):
        return "[redacted]" if _SECRET_VAL.search(obj) else obj[:2048]
    return obj


class StructuredLogger:
    def __init__(self, stream: TextIO | None = None, component: str = "gap07"):
        self._s = stream or sys.stderr
        self._c = component
        self._lock = threading.Lock()

    def log(self, level: str, event: str, trace: "TraceContext | None" = None, **fields: Any) -> dict[str, Any]:
        rec = {"ts": round(time.time(), 3), "level": level, "component": self._c, "event": event, **redact(fields)}
        if trace is not None:
            rec["trace_id"], rec["span_id"] = trace.trace_id, trace.span_id
        with self._lock:
            self._s.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        return rec


_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    flags: str = "01"

    @classmethod
    def from_traceparent(cls, header: str | None) -> "TraceContext":
        m = _TP.fullmatch(header or "")
        if m is None or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return cls(secrets.token_hex(16), secrets.token_hex(8))
        return cls(m.group(1), secrets.token_hex(8), m.group(3))

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{self.flags}"


class Health:
    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], tuple[bool, str]]] = {}

    def register(self, name: str, fn: Callable[[], tuple[bool, str]]) -> None:
        self._checks[name] = fn

    def liveness(self) -> dict[str, Any]:
        return {"live": True, "pid": os.getpid()}

    def readiness(self) -> dict[str, Any]:
        results = {}
        for name, fn in sorted(self._checks.items()):
            try:
                ok, why = fn()
            except Exception as exc:  # noqa: BLE001 - a crashing check means not ready
                ok, why = False, getattr(exc, "code", "INTERNAL_ERROR")
            results[name] = {"ok": ok, "reason": why}
        return {"ready": all(r["ok"] for r in results.values()) and bool(results), "checks": results}
