"""Metrics, histograms, structured events, trace context, audit chain
(components 43, 47-51, 54).

Nothing in this module ever receives a handle token: callers pass the
redacted correlation id (handles.redact) only.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import json
import os
import random
import re
import threading

BUCKETS_NS = tuple(2 ** k for k in range(8, 36, 2))  # 256ns .. ~17s


class Histogram:
    def __init__(self, name: str, help_: str):
        self.name, self.help = name, help_
        self.counts = [0] * (len(BUCKETS_NS) + 1)
        self.n = 0
        self.total = 0
        self.max = 0
        self._samples: deque[int] = deque(maxlen=4096)  # bounded reservoir for exact quantiles

    def observe(self, v: int) -> None:
        v = max(0, int(v))
        i = 0
        while i < len(BUCKETS_NS) and v > BUCKETS_NS[i]:
            i += 1
        self.counts[i] += 1
        self.n += 1
        self.total += v
        self.max = max(self.max, v)
        self._samples.append(v)

    def quantile(self, q: float) -> int | None:
        if not self._samples:
            return None
        s = sorted(self._samples)
        return s[min(len(s) - 1, int(q * len(s)))]

    def summary(self) -> dict:
        return {"count": self.n, "p50": self.quantile(.5), "p95": self.quantile(.95),
                "p99": self.quantile(.99), "max": self.max if self.n else None,
                "window": len(self._samples)}


class Metrics:
    """Bounded metric registry. Label sets are restricted to instance, scope and
    reason-code names (bounded enums); free-form strings are refused."""

    MAX_SERIES = 4096
    _LABEL_OK = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")

    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict[tuple, int] = {}
        self.gauges: dict[tuple, int] = {}
        self.dropped_series = 0
        self.hist = {
            "cancel_ack_ns": Histogram("pk_async_cancel_ack_ns", "cancel request to acknowledgement"),
            "cancel_terminal_ns": Histogram("pk_async_cancel_terminal_ns", "cancel request to terminal state"),
            "ready_to_resume_ns": Histogram("pk_async_ready_to_resume_ns", "readiness publication to scheduler resume"),
            "ready_to_take_ns": Histogram("pk_async_ready_to_take_ns", "readiness publication to take"),
            "wait_size": Histogram("pk_async_wait_size", "wait set cardinality"),
            "publish_to_runnable_ns": Histogram("pk_async_publish_to_runnable_ns", "ready publication to runnable"),
        }

    def _key(self, name, labels):
        items = tuple(sorted((labels or {}).items()))
        for k, v in items:
            if not self._LABEL_OK.match(str(k)) or not self._LABEL_OK.match(str(v)):
                raise ValueError(f"unbounded or unsafe label {k}")
        return (name, items)

    def inc(self, name, labels=None, n=1):
        with self._lock:
            k = self._key(name, labels)
            if k not in self.counters and len(self.counters) >= self.MAX_SERIES:
                self.dropped_series += 1
                return
            self.counters[k] = self.counters.get(k, 0) + n

    def set(self, name, value, labels=None):
        with self._lock:
            k = self._key(name, labels)
            if k not in self.gauges and len(self.gauges) >= self.MAX_SERIES:
                self.dropped_series += 1
                return
            self.gauges[k] = value

    def get(self, name, labels=None):
        k = self._key(name, labels)
        return self.counters.get(k, self.gauges.get(k, 0))

    def render_prometheus(self) -> str:
        out = []
        with self._lock:
            for (name, labels), v in sorted(self.counters.items()):
                out.append(f"{name}{_fmt(labels)} {v}")
            for (name, labels), v in sorted(self.gauges.items()):
                out.append(f"{name}{_fmt(labels)} {v}")
            for h in self.hist.values():
                acc = 0
                for b, c in zip(BUCKETS_NS + ("+Inf",), h.counts):
                    acc += c
                    out.append(f'{h.name}_bucket{{le="{b}"}} {acc}')
                out.append(f"{h.name}_count {h.n}")
                out.append(f"{h.name}_sum {h.total}")
            out.append(f"pk_async_metric_series_dropped_total {self.dropped_series}")
        return "\n".join(out) + "\n"


def _fmt(labels):
    if not labels:
        return ""
    return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}"


@dataclass(frozen=True)
class TraceContext:
    """W3C traceparent subset: version 00, 16-byte trace id, 8-byte span id."""

    trace_id: str
    span_id: str
    sampled: bool = True

    _RX = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")

    @classmethod
    def parse(cls, header: str) -> "TraceContext | None":
        m = cls._RX.match(header or "")
        if not m or set(m.group(1)) == {"0"} or set(m.group(2)) == {"0"}:
            return None  # invalid context is dropped, never fatal
        return cls(m.group(1), m.group(2), bool(int(m.group(3), 16) & 1))

    def child(self) -> "TraceContext":
        return TraceContext(self.trace_id, os.urandom(8).hex(), self.sampled)

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"


EVENT_FIELDS = ("seq", "ts_ns", "op", "instance", "tenant", "workload", "corr",
                "from", "to", "code", "reason", "duration_ns", "trace_id", "span_id")
SECURITY_OPS = frozenset({"foreign_handle", "use_after_consume", "budget_refusal", "tenant_mismatch",
                          "replay", "cancel_storm", "duplicate_publication", "late_completion"})


class EventLog:
    """Structured event ring with fixed schema and sampling.

    Security events are never sampled out; other events are kept with
    probability ``sample_rate`` (deterministic seeded RNG for testability).
    """

    def __init__(self, capacity=10000, sample_rate=1.0, seed=0):
        self.events: deque[dict] = deque(maxlen=capacity)
        self.sample_rate = sample_rate
        self._rng = random.Random(seed)
        self._seq = 0
        self.sampled_out = 0
        self._lock = threading.Lock()

    def emit(self, **kw) -> None:
        unknown = set(kw) - set(EVENT_FIELDS)
        if unknown:
            raise ValueError(f"event fields outside schema: {sorted(unknown)}")
        with self._lock:
            if kw.get("op") not in SECURITY_OPS and self._rng.random() >= self.sample_rate:
                self.sampled_out += 1
                return
            self._seq += 1
            ev = {f: None for f in EVENT_FIELDS}
            ev.update(kw)
            ev["seq"] = self._seq
            self.events.append(ev)


class AuditChain:
    """Tamper-evident (hash-chained) security audit records."""

    def __init__(self, capacity=100000):
        self.records: list[dict] = []
        self.capacity = capacity
        self.head = "0" * 64
        self.dropped = 0
        self._lock = threading.Lock()

    def append(self, kind: str, **fields) -> None:
        with self._lock:
            if len(self.records) >= self.capacity:
                self.dropped += 1  # counted, and verify() reports it
                return
            body = {"i": len(self.records), "kind": kind, "prev": self.head, **fields}
            digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            body["hash"] = digest
            self.records.append(body)
            self.head = digest

    def verify(self) -> tuple[bool, str]:
        prev = "0" * 64
        for i, r in enumerate(self.records):
            body = {k: v for k, v in r.items() if k != "hash"}
            if r.get("i") != i or r.get("prev") != prev:
                return False, f"chain break at {i}"
            if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != r["hash"]:
                return False, f"hash mismatch at {i}"
            prev = r["hash"]
        if prev != self.head:
            return False, "head mismatch (tail truncation)"
        return True, f"{len(self.records)} records, dropped {self.dropped}"
