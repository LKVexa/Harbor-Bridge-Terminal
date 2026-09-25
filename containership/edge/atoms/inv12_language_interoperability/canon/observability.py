"""MC-037 metrics, MC-038 tracing, MC-039 audit events, MC-041 health, MC-042 capacity.

* :class:`Metrics` - counters/histograms for the contract signals with a *closed*
  label vocabulary: label values must come from registered enumerations
  (languages, type kinds, error codes, directions).  Anything else is folded to
  ``"other"``, so cardinality is bounded by construction.  ``exposition()``
  renders the Prometheus text format.
* :class:`Tracer` - spans correlating interface, component, language pair,
  error code and duration.  Span attributes pass the same allow-list; payload
  values are never attributes.  ``export()`` yields OTLP-shaped dicts.
* :class:`AuditLog` - append-only, hash-chained, HMAC-sealed security events.
  ``verify()`` detects any modification, deletion, insertion or reordering.
* :class:`Health` - HEALTHY / DEGRADED / BLOCKED readiness model.
* :class:`CapacityController` - per-tenant fair-share admission for concurrent
  calls, copied bytes, live resources and stream windows.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from contextlib import contextmanager

from .errors import ERROR_CODES, LimitError, redact
from .registry import KINDS, SUPPORTED_LANGUAGES

COUNTERS = ("boundary_calls", "mapping_refusals", "range_violations", "ownership_transfers",
            "canonicalization_refusals", "encoding_refusals")
_LABEL_VOCAB = {
    "language": set(SUPPORTED_LANGUAGES),
    "source_language": set(SUPPORTED_LANGUAGES),
    "target_language": set(SUPPORTED_LANGUAGES),
    "kind": set(KINDS),
    "code": set(ERROR_CODES),
    "direction": {"lower", "lift", "in", "out"},
    "outcome": {"ok", "error"},
}
BUCKETS_US = (0.5, 1, 2, 5, 10, 50, 100, 1000, 10000)


def _label(k, v):
    vocab = _LABEL_VOCAB.get(k)
    if vocab is None:
        raise KeyError(f"label {k!r} is not registered")
    return v if v in vocab else "other"


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict = {}
        self.hist: dict = {}

    def inc(self, name: str, n: int = 1, **labels):
        if name not in COUNTERS:
            raise KeyError(f"unknown counter {name}")
        key = (name, tuple(sorted((k, _label(k, v)) for k, v in labels.items())))
        with self._lock:
            self.counters[key] = self.counters.get(key, 0) + n

    def observe_us(self, name: str, us: float, **labels):
        key = (name, tuple(sorted((k, _label(k, v)) for k, v in labels.items())))
        with self._lock:
            h = self.hist.setdefault(key, [0] * (len(BUCKETS_US) + 1) + [0.0, 0])
            for i, b in enumerate(BUCKETS_US):
                if us <= b:
                    h[i] += 1
            h[len(BUCKETS_US)] += 1           # +Inf
            h[-2] += us
            h[-1] += 1

    def value(self, name, **labels):
        key = (name, tuple(sorted((k, _label(k, v)) for k, v in labels.items())))
        return self.counters.get(key, 0)

    def cardinality(self) -> int:
        return len(self.counters) + len(self.hist)

    def exposition(self) -> str:
        lines = []
        with self._lock:
            for (name, labels), v in sorted(self.counters.items()):
                ls = ",".join(f'{k}="{v2}"' for k, v2 in labels)
                lines.append(f"inv12_{name}_total{{{ls}}} {v}")
            for (name, labels), h in sorted(self.hist.items()):
                base = ",".join(f'{k}="{v2}"' for k, v2 in labels)
                for i, b in enumerate(BUCKETS_US):
                    lines.append(f'inv12_{name}_us_bucket{{{base}{"," if base else ""}le="{b}"}} {h[i]}')
                lines.append(f'inv12_{name}_us_bucket{{{base}{"," if base else ""}le="+Inf"}} {h[len(BUCKETS_US)]}')
                lines.append(f"inv12_{name}_us_sum{{{base}}} {h[-2]}")
                lines.append(f"inv12_{name}_us_count{{{base}}} {h[-1]}")
        return "\n".join(lines) + "\n"


class Tracer:
    ATTRS = {"interface", "component", "source_language", "target_language", "code",
             "kind", "direction", "outcome"}

    def __init__(self, max_spans: int = 10_000):
        self.spans = []
        self.max_spans = max_spans
        self.dropped = 0
        self._lock = threading.Lock()
        self._ids = 0

    @contextmanager
    def span(self, name: str, parent=None, **attrs):
        bad = set(attrs) - self.ATTRS
        if bad:
            raise KeyError(f"span attribute(s) not allowed: {sorted(bad)}")
        with self._lock:
            self._ids += 1
            sid = self._ids
        rec = {"name": redact(name)[:64], "span_id": sid, "parent": parent,
               "attributes": {k: redact(str(v))[:64] for k, v in attrs.items()},
               "start_ns": time.perf_counter_ns()}
        try:
            yield rec
            rec["attributes"].setdefault("outcome", "ok")
        except Exception as e:  # noqa: BLE001 - re-raised
            rec["attributes"]["outcome"] = "error"
            rec["attributes"]["code"] = getattr(e, "code", "unhandled")
            raise
        finally:
            rec["duration_ns"] = time.perf_counter_ns() - rec.pop("start_ns")
            with self._lock:
                if len(self.spans) < self.max_spans:
                    self.spans.append(rec)
                else:
                    self.dropped += 1

    def export(self):
        with self._lock:
            return [dict(s) for s in self.spans]


class AuditLog:
    """Tamper-evident hash chain; each record is HMAC-SHA256 sealed."""

    EVENTS = {"mapping_policy_change", "trust_check_failed", "ownership_violation",
              "config_activated", "config_rolled_back", "emergency_disable", "provenance_rejected"}

    def __init__(self, key: bytes):
        if type(key) is not bytes or len(key) < 32:
            raise ValueError("audit key must be >= 32 bytes")
        self._key = key
        self.records = []
        self._lock = threading.Lock()

    def emit(self, event: str, actor: str, **fields):
        if event not in self.EVENTS:
            raise KeyError(f"unknown audit event {event}")
        with self._lock:
            prev = self.records[-1]["hash"] if self.records else "0" * 64
            body = {"seq": len(self.records), "event": event, "actor": redact(actor)[:128],
                    "fields": {k: redact(str(v))[:128] for k, v in sorted(fields.items())},
                    "ts": time.time(), "prev": prev}
            blob = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            body["hash"] = hashlib.sha256(blob).hexdigest()
            body["mac"] = hmac.new(self._key, body["hash"].encode(), hashlib.sha256).hexdigest()
            self.records.append(body)
            return body

    def verify(self, records=None) -> bool:
        records = self.records if records is None else records
        prev = "0" * 64
        for i, r in enumerate(records):
            body = {k: r[k] for k in ("seq", "event", "actor", "fields", "ts", "prev")}
            if r["seq"] != i or r["prev"] != prev:
                return False
            h = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if h != r["hash"]:
                return False
            mac = hmac.new(self._key, h.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(mac, r["mac"]):
                return False
            prev = h
        return True


class Health:
    """Readiness model.  Any BLOCKED condition makes the component not ready."""

    BLOCKING = {"mapping_profile_missing", "schema_incompatible", "runtime_fault",
                "config_invalid", "trust_unavailable", "emergency_disabled"}
    DEGRADING = {"quota_exhausted", "dependency_slow", "audit_backlog"}

    def __init__(self):
        self._conds = {}
        self._lock = threading.Lock()

    def set(self, condition: str, active: bool, detail: str = ""):
        if condition not in self.BLOCKING | self.DEGRADING:
            raise KeyError(f"unknown health condition {condition}")
        with self._lock:
            if active:
                self._conds[condition] = redact(detail)
            else:
                self._conds.pop(condition, None)

    def status(self) -> dict:
        with self._lock:
            conds = dict(self._conds)
        state = ("BLOCKED" if set(conds) & self.BLOCKING else
                 "DEGRADED" if conds else "HEALTHY")
        return {"state": state, "ready": state != "BLOCKED", "conditions": conds}


class CapacityController:
    """Per-tenant admission control with a fair share of a global pool."""

    def __init__(self, *, max_calls: int, max_bytes: int, max_resources: int, tenants: int = 1):
        if min(max_calls, max_bytes, max_resources, tenants) <= 0:
            raise ValueError("capacity values must be positive")
        self.limits = {"calls": max_calls, "bytes": max_bytes, "resources": max_resources}
        self.tenants = tenants
        self.use: dict = {}
        self.total = {"calls": 0, "bytes": 0, "resources": 0}
        self.rejections = 0
        self._lock = threading.Lock()

    def _share(self, dim):
        return max(1, self.limits[dim] // self.tenants)

    @contextmanager
    def admit(self, tenant: str, *, calls: int = 1, bytes_: int = 0, resources: int = 0):
        want = {"calls": calls, "bytes": bytes_, "resources": resources}
        with self._lock:
            u = self.use.setdefault(tenant, {"calls": 0, "bytes": 0, "resources": 0})
            for dim, n in want.items():
                if u[dim] + n > self._share(dim) or self.total[dim] + n > self.limits[dim]:
                    self.rejections += 1
                    raise LimitError(f"tenant quota exceeded for {dim}", retryable=True)
            for dim, n in want.items():
                u[dim] += n
                self.total[dim] += n
        try:
            yield
        finally:
            with self._lock:
                for dim, n in want.items():
                    u[dim] -= n
                    self.total[dim] -= n
