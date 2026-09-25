"""Metrics, structured logs, trace propagation, decision audit ledger (MC-058..MC-062, MC-065).

* :class:`Metrics` - the four contract signals (``toolchains_registered``, ``selections``,
  ``selection_refusals``, ``stale_reviews``) plus latency, as counters/gauges/histograms with a hard
  per-metric series cap (MC-061): once a metric holds ``MAX_SERIES`` label sets, new label sets fold
  into ``{overflow="true"}`` and ``inv28_metric_series_dropped_total`` counts them.  Label *keys*
  are allow-listed per metric; tenant and workload ids are never metric labels.
  ``exposition()`` renders Prometheus text format.
* :class:`StructuredLogger` - one JSON object per line with ``ts``, ``level``, ``event``,
  ``operation_id``, ``trace_id``; tenant/workload ids are replaced by keyed pseudonyms
  (HMAC, so they correlate without being recoverable) and any key matching the secret pattern is
  redacted (MC-059, MC-065).
* :class:`TraceContext` - W3C ``traceparent`` parse/emit; malformed headers start a new trace
  rather than propagating garbage (MC-060).
* :class:`AuditLedger` - append-only, hash-chained decision ledger (MC-062) with ``verify()``;
  optional JSONL persistence.  Every selection and refusal is recorded with its full input
  digests so a decision can be replayed (explain.py, MC-063).
"""
from __future__ import annotations

import bisect
import datetime as dt
import hashlib
import hmac
import json
import re
import secrets
import threading
from dataclasses import dataclass
from pathlib import Path

from .model import canonical, sha256_hex

MAX_SERIES = 200
LATENCY_BUCKETS_MS = (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250)
METRIC_LABELS = {
    "inv28_toolchains_registered": ("maturity", "lifecycle"),
    "inv28_selections_total": ("toolchain", "environment"),
    "inv28_selection_refusals_total": ("code", "environment"),
    "inv28_candidate_eliminations_total": ("code",),
    "inv28_stale_reviews": (),
    "inv28_selection_latency_ms": ("environment",),
    "inv28_registry_revision": (),
    "inv28_registry_mutations_total": ("op",),
    "inv28_metric_series_dropped_total": ("metric",),
    "inv28_dependency_errors_total": ("dependency",),
}
SECRET_KEY = re.compile(r"(?i)(secret|token|password|passwd|key|mac|signature|credential)")
PSEUDONYMISE = ("tenant", "workload_id")


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict = {}
        self._gauges: dict = {}
        self._hist: dict = {}
        self._series: dict = {}      # metric name -> set of label tuples (O(1) cardinality check)

    def _labels(self, name, labels: dict) -> tuple:
        allowed = METRIC_LABELS.get(name)
        if allowed is None:
            raise KeyError(f"undeclared metric {name}")
        extra = set(labels) - set(allowed)
        if extra:
            raise KeyError(f"{name}: label(s) {sorted(extra)} not allowed")
        key = tuple((k, str(labels.get(k, ""))[:64]) for k in allowed)
        series = self._series.setdefault(name, set())
        if key not in series:
            if len(series) >= MAX_SERIES:
                dk = (("metric", name),)
                self._counters[("inv28_metric_series_dropped_total", dk)] = \
                    self._counters.get(("inv28_metric_series_dropped_total", dk), 0) + 1
                self._series.setdefault("inv28_metric_series_dropped_total", set()).add(dk)
                key = (("overflow", "true"),)
            series.add(key)
        return key

    def inc(self, name, value=1, **labels):
        with self._lock:
            k = (name, self._labels(name, labels))
            self._counters[k] = self._counters.get(k, 0) + value

    def inc_many(self, name, label_key: str, counts: dict):
        """One lock acquisition for a batch of increments (hot path: per-candidate elimination codes)."""
        with self._lock:
            for value, n in counts.items():
                k = (name, self._labels(name, {label_key: value}))
                self._counters[k] = self._counters.get(k, 0) + n

    def set(self, name, value, **labels):
        with self._lock:
            self._gauges[(name, self._labels(name, labels))] = value

    def observe(self, name, value_ms, **labels):
        with self._lock:
            k = (name, self._labels(name, labels))
            h = self._hist.setdefault(k, [[0] * (len(LATENCY_BUCKETS_MS) + 1), 0.0, 0])
            h[0][bisect.bisect_left(LATENCY_BUCKETS_MS, value_ms)] += 1
            h[1] += value_ms
            h[2] += 1

    def value(self, name, **labels):
        with self._lock:
            key = tuple((k, str(labels.get(k, ""))) for k in METRIC_LABELS[name])
            return self._counters.get((name, key), self._gauges.get((name, key), 0))

    def series_count(self, name) -> int:
        with self._lock:
            return len(self._series.get(name, ()))

    def exposition(self) -> str:
        def lab(s):
            return "{" + ",".join(f'{k}="{v}"' for k, v in s) + "}" if s else ""
        out = []
        with self._lock:
            for (n, s), v in sorted(self._counters.items()):
                out.append(f"{n}{lab(s)} {v}")
            for (n, s), v in sorted(self._gauges.items()):
                out.append(f"{n}{lab(s)} {v}")
            for (n, s), (b, total, cnt) in sorted(self._hist.items()):
                acc = 0
                for i, edge in enumerate(LATENCY_BUCKETS_MS):
                    acc += b[i]
                    out.append(f'{n}_bucket{lab(s + (("le", str(edge)),))} {acc}')
                out.append(f'{n}_bucket{lab(s + (("le", "+Inf"),))} {cnt}')
                out.append(f"{n}_sum{lab(s)} {round(total, 6)}")
                out.append(f"{n}_count{lab(s)} {cnt}")
        return "\n".join(out) + "\n"


class StructuredLogger:
    def __init__(self, sink=None, *, pseudonym_key: bytes | None = None, clock=None):
        self._sink = sink if sink is not None else []
        self._key = pseudonym_key or secrets.token_bytes(32)
        self._clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self._lock = threading.Lock()

    def pseudonym(self, value: str) -> str:
        return "p:" + hmac.new(self._key, str(value).encode(), hashlib.sha256).hexdigest()[:16]

    def _clean(self, obj, depth=0):
        if depth > 6:
            return "<truncated>"
        if isinstance(obj, dict):
            out = {}
            for k, v in list(obj.items())[:64]:
                if SECRET_KEY.search(str(k)):
                    out[k] = "<redacted>"
                elif k in PSEUDONYMISE and v:
                    out[k] = self.pseudonym(v)
                else:
                    out[k] = self._clean(v, depth + 1)
            return out
        if isinstance(obj, (list, tuple)):
            return [self._clean(v, depth + 1) for v in list(obj)[:64]]
        if isinstance(obj, str):
            return obj[:512]
        return obj

    def log(self, level: str, event: str, *, operation_id: str = "", trace=None, **fields):
        rec = {"ts": self._clock().strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "level": level, "event": event,
               "component": "INV-28", "operation_id": operation_id,
               "trace_id": trace.trace_id if trace else "", "span_id": trace.span_id if trace else "",
               **self._clean(fields)}
        line = json.dumps(rec, sort_keys=True)
        with self._lock:
            if hasattr(self._sink, "write"):
                self._sink.write(line + "\n")
            else:
                self._sink.append(line)
        return rec

    @property
    def lines(self):
        return list(self._sink) if isinstance(self._sink, list) else []


_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str = ""
    sampled: bool = True

    @classmethod
    def new(cls, sampled=True):
        return cls(secrets.token_hex(16), secrets.token_hex(8), "", sampled)

    @classmethod
    def from_traceparent(cls, header):
        m = _TP.match(header.strip().lower()) if isinstance(header, str) else None
        if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
            return cls.new()
        return cls(m.group(1), secrets.token_hex(8), m.group(2), bool(int(m.group(3), 16) & 1))

    def child(self):
        return TraceContext(self.trace_id, secrets.token_hex(8), self.span_id, self.sampled)

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


class AuditLedger:
    """Hash-chained append-only ledger.  ``entry_hash = sha256(prev_hash || canonical(body))``."""

    GENESIS = "0" * 64

    def __init__(self, path=None, *, clock=None, max_in_memory: int = 100_000):
        self._path = Path(path) if path else None
        self._clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self._entries: list[dict] = []
        self._max = max_in_memory
        self._lock = threading.Lock()
        if self._path and self._path.exists():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._entries.append(json.loads(line))

    @property
    def head(self) -> str:
        return self._entries[-1]["entry_hash"] if self._entries else self.GENESIS

    def append(self, kind: str, payload: dict) -> dict:
        with self._lock:
            body = {"seq": len(self._entries) + 1, "kind": kind,
                    "at": self._clock().strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "payload": payload}
            prev = self.head
            h = hashlib.sha256(prev.encode() + canonical(body)).hexdigest()
            entry = {**body, "prev_hash": prev, "entry_hash": h}
            if len(self._entries) >= self._max:
                raise OverflowError("audit ledger in-memory bound reached; rotate to persistent storage")
            self._entries.append(entry)
            if self._path:
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, sort_keys=True) + "\n")
            return entry

    def entries(self, kind: str | None = None) -> list[dict]:
        return [dict(e) for e in self._entries if kind is None or e["kind"] == kind]

    def find(self, **match) -> list[dict]:
        return [e for e in self._entries if all(e["payload"].get(k) == v for k, v in match.items())]

    def verify(self) -> list[str]:
        problems, prev = [], self.GENESIS
        for i, e in enumerate(self._entries, 1):
            body = {k: e[k] for k in ("seq", "kind", "at", "payload")}
            if e["seq"] != i:
                problems.append(f"entry {i}: sequence gap")
            if e["prev_hash"] != prev:
                problems.append(f"entry {i}: broken chain")
            if hashlib.sha256(prev.encode() + canonical(body)).hexdigest() != e["entry_hash"]:
                problems.append(f"entry {i}: hash mismatch")
            prev = e["entry_hash"]
        return problems


@dataclass(frozen=True)
class TelemetryPolicy:
    """MC-065: machine-readable mirror of ops/TELEMETRY_POLICY.json (a test pins them together)."""

    log_retention_days: int = 30
    audit_retention_days: int = 400
    metric_retention_days: int = 90
    trace_sample_rate: float = 0.1
    refusal_trace_sample_rate: float = 1.0
    export_allowed: tuple = ("prometheus", "otlp", "jsonl")
    pseudonymised_fields: tuple = PSEUDONYMISE

    def to_dict(self):
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in self.__dict__.items()}


def digest_of(obj) -> str:
    return sha256_hex(obj)
