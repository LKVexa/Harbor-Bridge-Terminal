"""M27 audit stream, M34 metrics, M35 structured logs, M36 trace propagation,
M37 explain view.  Stdlib only; exporters (Prometheus/OTLP) attach at the edge.

Redaction rule (all sinks): never raw module bytes, never signatures/keys,
never attacker-controlled strings unsanitised; module identity is the digest.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import Counter
from typing import Any, Iterable

from .errors import Code, sanitize

# ---------------------------------------------------------------- M34 metrics
OUTCOMES = ("accept", "reject", "refuse", "error")
_ALLOWED_LABELS = {
    "outcome": set(OUTCOMES),
    "code": {c.value for c in Code} | {"OK"},
    "profile": None,  # bounded by the bundle's profile set, checked on emit
    "cache": {"hit", "miss"},
}
LATENCY_BUCKETS_MS = (1, 2, 5, 10, 20, 50, 100, 250, 1000, 5000)


class Metrics:
    def __init__(self, profiles: Iterable[str]):
        self._profiles = set(profiles)
        self._lock = threading.Lock()
        self.counters: Counter = Counter()
        self.latency: Counter = Counter()

    def _labels(self, labels: dict[str, str]) -> tuple:
        for k, v in labels.items():
            allowed = self._profiles if k == "profile" else _ALLOWED_LABELS.get(k, set())
            if v not in allowed:
                labels[k] = "other"  # bounded cardinality: never mint a new series from input
        return tuple(sorted(labels.items()))

    def inc(self, name: str, **labels: str) -> None:
        with self._lock:
            self.counters[(name, self._labels(labels))] += 1

    def observe_ms(self, ms: float, **labels: str) -> None:
        b = next((x for x in LATENCY_BUCKETS_MS if ms <= x), float("inf"))
        with self._lock:
            self.latency[(b, self._labels(labels))] += 1

    def exposition(self) -> str:
        """Prometheus text format."""
        lines = ["# TYPE inv09_validations_total counter"]
        for (name, labels), v in sorted(self.counters.items()):
            lab = ",".join(f'{k}="{val}"' for k, val in labels)
            lines.append(f"inv09_{name}{{{lab}}} {v}")
        lines.append("# TYPE inv09_validation_latency_ms histogram")
        cum: Counter = Counter()
        for (b, labels), v in sorted(self.latency.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            cum[labels] += v
            lab = ",".join(f'{k}="{val}"' for k, val in labels)
            le = "+Inf" if b == float("inf") else str(b)
            lines.append(f'inv09_validation_latency_ms_bucket{{{lab}{"," if lab else ""}le="{le}"}} {cum[labels]}')
        return "\n".join(lines) + "\n"


# ------------------------------------------------------------ M36 tracing
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_traceparent(value: str | None) -> tuple[str, str]:
    """Return (trace_id, parent_span_id); mint a fresh trace on bad/missing input."""
    m = _TP.match(value or "")
    if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
        return m.group(1), m.group(2)
    return os.urandom(16).hex(), ""


def new_span_id() -> str:
    return os.urandom(8).hex()


# ------------------------------------------------------------ M35 logging
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        doc = {"ts": round(record.created, 3), "level": record.levelname, "logger": record.name,
               "msg": sanitize(record.getMessage())}
        for k, v in getattr(record, "fields", {}).items():
            doc[k] = sanitize(v) if isinstance(v, str) else v
        return json.dumps(doc, sort_keys=True)


def get_logger() -> logging.Logger:
    log = logging.getLogger("inv09")
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(JsonFormatter())
        log.addHandler(h)
        log.setLevel(logging.WARNING)
        log.propagate = False
    return log


# ------------------------------------------------------------ M27 audit
class AuditStream:
    """Append-only, hash-chained audit events.  Each event carries the SHA-256
    of the previous event, so deletion/reordering/tampering is detectable by
    :func:`verify_chain`.  ``path=None`` keeps events in memory."""

    GENESIS = "0" * 64

    def __init__(self, path: str | None = None, max_memory_events: int = 10_000):
        self.path = path
        self.events: list[dict[str, Any]] = []   # in-memory window (durable copy is the file sink)
        self.max_memory_events = max_memory_events
        self.window_prev = self.GENESIS           # 'prev' of the first retained event
        self.total = 0
        self._head = self.GENESIS
        self._lock = threading.Lock()

    def emit(self, kind: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            ev = {"schema": "PK_AUDIT_EVENT/1", "seq": self.total, "ts": round(time.time(), 3),
                  "kind": kind, "prev": self._head,
                  **{k: (sanitize(v) if isinstance(v, str) else v) for k, v in fields.items()}}
            line = json.dumps(ev, sort_keys=True, separators=(",", ":"))
            self._head = hashlib.sha256(line.encode()).hexdigest()
            self.events.append(ev)
            self.total += 1
            if len(self.events) > self.max_memory_events:  # bounded memory (finding F-08)
                drop = len(self.events) - self.max_memory_events
                self.window_prev = hashlib.sha256(json.dumps(self.events[drop - 1], sort_keys=True,
                                                             separators=(",", ":")).encode()).hexdigest()
                del self.events[:drop]
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            return ev

    @property
    def head(self) -> str:
        return self._head


def verify_chain(events: list[dict[str, Any]], start_prev: str = AuditStream.GENESIS) -> bool:
    prev = start_prev
    first = events[0]["seq"] if events else 0
    for i, ev in enumerate(events, start=first):
        if ev.get("seq") != i or ev.get("prev") != prev:
            return False
        prev = hashlib.sha256(json.dumps(ev, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return True


# ------------------------------------------------------------ M37 explain
def explain(verdict: dict[str, Any]) -> str:
    """Operator-facing explanation of a verdict (no raw bytes, bounded)."""
    lines = [f"module {verdict.get('module_digest', '?')} -> {verdict.get('outcome', '?').upper()}"
             f" under profile {verdict.get('profile')!r}"]
    if verdict.get("failure"):
        f = verdict["failure"]
        lines.append(f"  reason: {f['code']} at byte {f.get('offset')} in {f.get('section')} section: {f['detail']}")
        lines.append("  remedy: " + REMEDIES.get(f["code"], "see runbook RB-01 (unexplained refusal)"))
    for name, off, why in verdict.get("feature_evidence", [])[:20]:
        lines.append(f"  feature {name}: byte {off} ({why})")
    if verdict.get("uses_float"):
        lines.append("  floating point used: engine must canonicalise NaNs for deterministic profiles")
    return "\n".join(lines)


REMEDIES = {
    "FEATURE_REFUSED": "recompile without the listed feature(s) or request a profile that permits them",
    "BINDING_MISMATCH": "the capability manifest does not match the bytes; regenerate it from this build",
    "UNSUPPORTED_PROPOSAL": "the validator does not certify this proposal; target wasm-core-2.0 features",
    "HOST_IMPORT_REFUSED": "remove the import or add it to the tenant host-import contract via change control",
    "ENGINE_UNSUPPORTED": "select an engine certified for the module's features (M21 matrix)",
    "LIMIT_EXCEEDED": "module exceeds a resource ceiling; split it or request a reviewed limit change",
    "DEADLINE_EXCEEDED": "validation timed out; retry is safe - the module was NOT admitted",
    "INTERNAL_ERROR": "validator fault - module refused; page the owner (RB-02)",
}
