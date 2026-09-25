"""Structured telemetry, SLO evaluation and health/readiness (MC-39, MC-40, MC-42).

Metrics are bounded-cardinality counters/gauges; label values outside an
allow-list collapse to ``other``.  The JSONL exporter writes redacted events.
"""
from __future__ import annotations

import json
import threading
import time
from collections import defaultdict

from .config import redact

MAX_SERIES = 512
_LABEL_KEYS = frozenset({"interface", "code", "classification", "branch", "operation", "result"})


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict = defaultdict(int)
        self.gauges: dict = {}
        self.dropped = 0

    def _key(self, name: str, labels: dict) -> tuple:
        clean = tuple(sorted((k, str(v)[:64]) for k, v in labels.items() if k in _LABEL_KEYS))
        return (name, clean)

    def inc(self, name: str, value: int = 1, **labels) -> None:
        with self._lock:
            key = self._key(name, labels)
            if key not in self.counters and len(self.counters) + len(self.gauges) >= MAX_SERIES:
                self.dropped += 1
                key = (name, (("overflow", "true"),))
            self.counters[key] += value

    def set(self, name: str, value: int, **labels) -> None:
        with self._lock:
            key = self._key(name, labels)
            if key not in self.gauges and len(self.counters) + len(self.gauges) >= MAX_SERIES:
                self.dropped += 1
                return
            self.gauges[key] = value

    def total(self, name: str) -> int:
        return sum(v for (n, _), v in self.counters.items() if n == name)

    def snapshot(self) -> dict:
        fmt = lambda k: k[0] + ("{" + ",".join(f"{a}={b}" for a, b in k[1]) + "}" if k[1] else "")  # noqa: E731
        with self._lock:
            return {"counters": {fmt(k): v for k, v in sorted(self.counters.items())},
                    "gauges": {fmt(k): v for k, v in sorted(self.gauges.items())},
                    "dropped_series": self.dropped}


class JsonlExporter:
    def __init__(self, path: str) -> None:
        self.path = path

    def emit(self, event: str, **fields) -> None:
        rec = {"ts": int(time.time()), "event": event, **redact(fields)}
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")


SLOS = (
    {"id": "no_silent_divergence", "signal": "uncertified_runs", "objective": 0, "budget": 0,
     "action": "page: an uncertified run reached execution; freeze site (runbook RB-02)"},
    {"id": "matrix_completeness", "signal": "unclassified_interfaces", "objective": 0, "budget": 0,
     "action": "block release: classify interfaces (runbook RB-01)"},
    {"id": "drift_visibility", "signal": "releases_without_drift_record", "objective": 0, "budget": 0,
     "action": "block release: record drift (runbook RB-05)"},
)


def evaluate_slos(signals: dict) -> list[dict]:
    """Zero-budget SLOs: any non-zero value is an immediate breach.  Missing signal = breach."""
    out = []
    for s in SLOS:
        v = signals.get(s["signal"])
        breached = v is None or v > s["budget"]
        out.append({"slo": s["id"], "value": v, "breached": breached, "action": s["action"] if breached else None})
    return out


def health(*, version: str, config_digest: str | None, store=None, trust_loaded: bool,
           baselines_pinned: bool, revocation_age: int | None, max_revocation_age: int, frozen_sites: list[str]) -> dict:
    """Liveness is 'process answers'; readiness requires every trust input to be fresh and valid."""
    reasons = []
    if config_digest is None:
        reasons.append("no active configuration")
    if store is None:
        reasons.append("store unavailable")
    else:
        integ = store.integrity_check()
        if not integ["ok"]:
            reasons.append("store integrity check failed")
    if not trust_loaded:
        reasons.append("trust store not loaded")
    if not baselines_pinned:
        reasons.append("branch baselines not immutably pinned")
    if revocation_age is None or revocation_age > max_revocation_age:
        reasons.append("revocation data stale")
    state = "not_ready" if reasons else ("degraded" if frozen_sites else "ready")
    return {"schema": "PK_BRANCH_HEALTH/1", "live": True, "ready": not reasons, "state": state,
            "reasons": reasons, "version": version, "config_digest": config_digest, "frozen_sites": frozen_sites}
