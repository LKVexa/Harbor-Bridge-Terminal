"""Observability: GAP11-P1-24 tamper-evident audit ledger, P1-25 metrics exporter,
P1-26 structured logs + trace propagation, P1-27 health/readiness/explain,
P1-28 alert rules.
"""
from __future__ import annotations

import bisect
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
from typing import Any

from .common import REASON_CODES, ControlError, Telemetry, canonical, utc_iso
from .security import Keyring, redact

# ------------------------------------------------------------------ audit ledger (P1-24)
class AuditLedger:
    """Append-only JSONL; each entry chains ``prev`` hash and carries an HMAC.

    Chains detect edit/reorder/deletion *inside* the file. Tail truncation is not
    detectable from the file alone, so ``head()`` is exported to an external
    witness (metrics / release bundle) and ``verify(expected_head=...)`` checks it.
    """

    GENESIS = "0" * 64

    def __init__(self, path: str, keyring: Keyring, *, clock: Any) -> None:
        self.path, self.keyring, self.clock = path, keyring, clock
        self._lock = threading.Lock()
        self._head = self.GENESIS
        self._n = 0
        if os.path.exists(path):
            rep = self.verify()
            if not rep["ok"]:
                raise ControlError("STORE_CORRUPT", "audit ledger failed verification", at=rep["bad_index"])
            self._head, self._n = rep["head"], rep["entries"]

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            body = {"i": self._n, "ts": utc_iso(self.clock.wall()), "prev": self._head, "event": redact(event)}
            h = hashlib.sha256(canonical(body)).hexdigest()
            kid = self.keyring.active
            if kid is None:
                raise ControlError("DEPENDENCY_UNAVAILABLE", "audit signing key unavailable")
            mac = hmac.new(self.keyring.get(kid), h.encode(), hashlib.sha256).hexdigest()
            rec = {**body, "hash": h, "kid": kid, "mac": mac}
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            self._head, self._n = h, self._n + 1
            return rec

    def head(self) -> dict[str, Any]:
        return {"entries": self._n, "head": self._head}

    def verify(self, expected_head: dict[str, Any] | None = None) -> dict[str, Any]:
        prev, n = self.GENESIS, 0
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as fh:
                for idx, line in enumerate(fh):
                    try:
                        rec = json.loads(line)
                        body = {k: rec[k] for k in ("i", "ts", "prev", "event")}
                        h = hashlib.sha256(canonical(body)).hexdigest()
                        mac_ok = hmac.compare_digest(hmac.new(self.keyring.get(rec["kid"]), h.encode(), hashlib.sha256).hexdigest(), rec["mac"])
                        ok = rec["i"] == idx and rec["prev"] == prev and rec["hash"] == h and mac_ok
                    except Exception:
                        ok = False
                    if not ok:
                        return {"ok": False, "bad_index": idx, "entries": n, "head": prev}
                    prev, n = h, n + 1
        if expected_head is not None and (expected_head["entries"] != n or expected_head["head"] != prev):
            return {"ok": False, "bad_index": n, "entries": n, "head": prev, "truncated_or_diverged": True}
        return {"ok": True, "entries": n, "head": prev}


# ------------------------------------------------------------------ metrics (P1-25)
BUCKETS = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
METRIC_LABEL_BUDGET = {"operation": {"allocate", "release", "scrub", "heartbeat", "reconcile", "inventory"},
                       "code": set(REASON_CODES) | {"OK"}}


class Metrics:
    """Prometheus text exposition. Labels restricted to a fixed budget — never tenant, lease or device ids."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict[tuple[str, tuple], float] = {}
        self.gauges: dict[str, float] = {}
        self.hist: dict[tuple[str, tuple], list[float]] = {}

    def _labels(self, labels: dict[str, str]) -> tuple:
        for k, v in labels.items():
            if k not in METRIC_LABEL_BUDGET or v not in METRIC_LABEL_BUDGET[k]:
                raise ValueError(f"label {k}={v!r} outside cardinality budget")
        return tuple(sorted(labels.items()))

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        key = (name, self._labels(labels))
        with self._lock:
            self.counters[key] = self.counters.get(key, 0.0) + value

    def set(self, name: str, value: float) -> None:
        with self._lock:
            self.gauges[name] = value

    def observe(self, name: str, seconds: float, **labels: str) -> None:
        key = (name, self._labels(labels))
        with self._lock:
            self.hist.setdefault(key, []).append(seconds)

    def quantile(self, name: str, q: float, **labels: str) -> float | None:
        vals = sorted(self.hist.get((name, self._labels(labels)), []))
        if not vals:
            return None
        return vals[min(len(vals) - 1, int(q * len(vals)))]

    def expose(self) -> str:
        def lab(t: tuple, extra: str = "") -> str:
            parts = [f'{k}="{v}"' for k, v in t] + ([extra] if extra else [])
            return "{" + ",".join(parts) + "}" if parts else ""
        out = []
        with self._lock:
            for (n, t), v in sorted(self.counters.items()):
                out.append(f"gap11_{n}_total{lab(t)} {v}")
            for n, v in sorted(self.gauges.items()):
                out.append(f"gap11_{n} {v}")
            for (n, t), vals in sorted(self.hist.items()):
                s = sorted(vals)
                for b in BUCKETS:
                    le = 'le="%s"' % b
                    out.append(f"gap11_{n}_seconds_bucket{lab(t, le)} {bisect.bisect_right(s, b)}")
                inf = 'le="+Inf"'
                out.append(f"gap11_{n}_seconds_bucket{lab(t, inf)} {len(s)}")
                out.append(f"gap11_{n}_seconds_sum{lab(t)} {sum(s)}")
                out.append(f"gap11_{n}_seconds_count{lab(t)} {len(s)}")
        return "\n".join(out) + "\n"


def refusal_class(code: str) -> str:
    """P1-27/P1-28: separate capacity, policy, hardware, scrub, dependency, attack, defect."""
    classes = {
        "capacity": {"CAPACITY_EXHAUSTED", "QUOTA_EXCEEDED", "OVERLOADED", "THERMAL_UNAVAILABLE"},
        "policy": {"POLICY_DENIED", "CONSTRAINT_UNSATISFIED", "MAINTENANCE_MODE"},
        "hardware": {"HARDWARE_FAULT", "DEVICE_MISSING", "DEVICE_QUARANTINED"},
        "scrub": {"SCRUB_FAILED", "SCRUB_TIMEOUT"},
        "dependency": {"DEPENDENCY_UNAVAILABLE", "STORE_UNAVAILABLE", "NOT_LEADER", "DEADLINE_EXCEEDED"},
        "attack_indicator": {"UNAUTHENTICATED", "REPLAY_DETECTED", "ATTESTATION_INVALID", "IDEMPOTENCY_CONFLICT", "STALE_FENCE"},
        "client_error": {"SCHEMA_INVALID", "MESSAGE_TOO_LARGE", "LEASE_NOT_FOUND", "LEASE_EXPIRED", "DUPLICATE_REQUEST"},
        "software_defect": {"ILLEGAL_TRANSITION", "STORE_CORRUPT", "STALE_REVISION", "AMBIGUOUS_EVIDENCE", "CONFIG_INVALID"},
    }
    for name, codes in classes.items():
        if code in codes:
            return name
    return "software_defect"


# ------------------------------------------------------------------ logs + traces (P1-26)
TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-0[01]$")


def child_trace(traceparent: str | None) -> dict[str, str]:
    """Continue a W3C trace (new span) or start one. Invalid input starts a new trace."""
    m = TRACEPARENT.match(traceparent or "")
    trace_id = m.group(1) if m and m.group(1) != "0" * 32 else secrets.token_hex(16)
    span = secrets.token_hex(8)
    return {"trace_id": trace_id, "span_id": span, "traceparent": f"00-{trace_id}-{span}-01",
            "parent_span_id": m.group(2) if m else None}


class StructuredLogger:
    LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")

    def __init__(self, sink: list[str] | None = None, *, clock: Any, min_level: str = "INFO", sample_debug: int = 100) -> None:
        self.sink = sink if sink is not None else []
        self.clock = clock
        self.min = self.LEVELS.index(min_level)
        self.sample_debug = sample_debug
        self._n = 0

    def log(self, level: str, msg: str, **fields: Any) -> str | None:
        if self.LEVELS.index(level) < self.min:
            return None
        if level == "DEBUG":
            self._n += 1
            if self._n % self.sample_debug:
                return None
        line = json.dumps({"ts": utc_iso(self.clock.wall()), "level": level, "msg": msg, **redact(fields)}, sort_keys=True)
        self.sink.append(line)
        return line


# ------------------------------------------------------------------ health / readiness / explain (P1-27)
def health_report(*, version: str, config_digest: str, elector: Any, store: Any, dependencies: dict[str, bool],
                  reconcile_lag_s: float, max_lag_s: float = 60.0) -> dict[str, Any]:
    live = True
    deps_ok = all(dependencies.values())
    ready = bool(deps_ok and elector.is_leader() and not store.read_only and reconcile_lag_s <= max_lag_s)
    return {"schema": "PK_HEALTH/1", "version": version, "config_digest": config_digest, "live": live, "ready": ready,
            "role": "leader" if elector.is_leader() else "follower", "controller_epoch": elector.epoch,
            "store_revision": store.revision, "dependencies": dict(sorted(dependencies.items())),
            "reconcile_lag_s": reconcile_lag_s}


def explain(decision: Any, *, include_sensitive: bool = False) -> dict[str, Any]:
    out = {"selected": decision.device, "reasons": decision.reasons}
    return out if include_sensitive else redact(out)


# ------------------------------------------------------------------ alerts (P1-28)
ALERT_RULES = [
    {"id": "GAP11-ALERT-001", "severity": "page", "class": "scrub", "expr": "rate(scrub_failures) > 0 for 5m",
     "action": "RUNBOOK-06 failed scrub", "dedupe": "device"},
    {"id": "GAP11-ALERT-002", "severity": "page", "class": "software_defect", "expr": "illegal_transition > 0",
     "action": "RUNBOOK-09 incident containment", "dedupe": "code"},
    {"id": "GAP11-ALERT-003", "severity": "page", "class": "attack_indicator", "expr": "stale_fence|replay > 3 in 10m",
     "action": "RUNBOOK-09 incident containment; check split-brain", "dedupe": "controller_epoch"},
    {"id": "GAP11-ALERT-004", "severity": "ticket", "class": "capacity", "expr": "capacity_refusal_ratio > 0.2 for 30m",
     "action": "capacity review", "dedupe": "kind"},
    {"id": "GAP11-ALERT-005", "severity": "page", "class": "dependency", "expr": "not ready for 2m",
     "action": "RUNBOOK-05 store recovery / RUNBOOK-03 emergency disable", "dedupe": "dependency"},
    {"id": "GAP11-ALERT-006", "severity": "ticket", "class": "hardware", "expr": "quarantined_devices > 0 for 1h",
     "action": "RUNBOOK-08 device replacement", "dedupe": "device"},
    {"id": "GAP11-ALERT-007", "severity": "page", "class": "software_defect", "expr": "audit_verify_failed",
     "action": "freeze mutations; preserve evidence", "dedupe": "ledger"},
]


def evaluate_alerts(counts: dict[str, int]) -> list[dict[str, Any]]:
    """Minimal evaluator over pre-aggregated counts per refusal class."""
    fired = []
    for r in ALERT_RULES:
        if counts.get(r["class"], 0) > 0:
            fired.append({"id": r["id"], "severity": r["severity"], "action": r["action"]})
    return fired


def telemetry_bridge(tel: Telemetry, metrics: Metrics) -> None:
    def on(ev: dict[str, Any]) -> None:
        metrics.inc("events", operation=ev["event"] if ev["event"] in METRIC_LABEL_BUDGET["operation"] else "inventory",
                    code=ev["code"] if ev["code"] in METRIC_LABEL_BUDGET["code"] else "OK")
    tel.subscribers.append(on)
