"""Metrics export, structured event log and latency histograms (closure items #23-#25).

* ``METRICS`` is the versioned metric catalogue (name, type, unit, description).
* ``prometheus_text`` renders a runtime snapshot in Prometheus exposition format
  with bounded labels (instance, function) - never call ids or user input.
* ``EventLog`` is a bounded, non-blocking JSON-lines sink with sampling that
  never samples critical integrity events and hashes tenant identifiers.
* ``Histogram`` is a fixed exponential-bucket latency histogram.

No third-party telemetry SDK is required; an OpenTelemetry bridge only needs to
map ``snapshot()`` + ``METRICS`` onto its instruments.
"""
from __future__ import annotations

import hashlib
from bisect import bisect_left
import json
import random
import threading
from collections import deque
from typing import Callable, Iterable

METRICS_SCHEMA_VERSION = "inv16.metrics/1"

# name -> (type, unit, description)
METRICS: dict[str, tuple[str, str, str]] = {
    "inv16_calls_in_flight": ("gauge", "calls", "Live calls per instance/function"),
    "inv16_calls_queued": ("gauge", "calls", "Calls waiting in a re-entrancy queue"),
    "inv16_tombstones": ("gauge", "records", "Retained terminal records"),
    "inv16_call_ids_remaining": ("gauge", "ids", "Unallocated call ids in this generation"),
    "inv16_reentrancy_refusals_total": ("counter", "calls", "Re-entrant calls refused"),
    "inv16_concurrency_refusals_total": ("counter", "calls", "Calls refused at the in-flight limit"),
    "inv16_queue_refusals_total": ("counter", "calls", "Calls refused because the re-entrancy queue was full"),
    "inv16_queued_calls_total": ("counter", "calls", "Calls that were queued for admission"),
    "inv16_bridge_calls_total": ("counter", "calls", "Sync-caller/async-callee pairs"),
    "inv16_double_delivery_attempts_total": ("counter", "events", "Second completion attempts; must stay 0"),
    "inv16_completed_calls_total": ("counter", "calls", "Calls completed"),
    "inv16_cancelled_calls_total": ("counter", "calls", "Calls cancelled"),
    "inv16_trapped_calls_total": ("counter", "calls", "Calls ended by callee trap"),
    "inv16_tombstone_evictions_total": ("counter", "records", "Terminal records reclaimed"),
    "inv16_expired_late_events_total": ("counter", "events", "Late events after history expiry"),
    "inv16_stale_generation_events_total": ("counter", "events", "Events for a previous generation"),
    "inv16_sink_failures_total": ("counter", "events", "Telemetry sink failures (isolated)"),
    "inv16_listener_failures_total": ("counter", "events", "Terminal-listener failures (isolated)"),
    "inv16_trace_context_rejected_total": ("counter", "events", "Malformed inbound traceparent"),
    "inv16_bridge_latency_ns": ("histogram", "ns", "Sync bridge end-to-end latency"),
}

_COUNTER_FIELDS = {
    "inv16_reentrancy_refusals_total": "reentrancy_refusals",
    "inv16_concurrency_refusals_total": "concurrency_refusals",
    "inv16_queue_refusals_total": "queue_refusals",
    "inv16_queued_calls_total": "queued_calls",
    "inv16_bridge_calls_total": "bridge_calls",
    "inv16_double_delivery_attempts_total": "double_delivery_attempts",
    "inv16_completed_calls_total": "completed_calls",
    "inv16_cancelled_calls_total": "cancelled_calls",
    "inv16_trapped_calls_total": "trapped_calls",
    "inv16_tombstone_evictions_total": "tombstone_evictions",
    "inv16_expired_late_events_total": "expired_late_events",
    "inv16_stale_generation_events_total": "stale_generation_events",
    "inv16_sink_failures_total": "sink_failures",
    "inv16_listener_failures_total": "listener_failures",
    "inv16_trace_context_rejected_total": "trace_context_rejected",
}

_LABEL_OK = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.:/#@")


def _label(v: str) -> str:
    s = "".join(c if c in _LABEL_OK else "_" for c in str(v))[:128]
    return s.replace("\\", "\\\\").replace('"', '\\"')


class Histogram:
    """Exponential buckets (powers of two, ns).  Thread-safe, O(1) record."""

    def __init__(self, lo_exp: int = 7, hi_exp: int = 30):
        self.bounds = [1 << e for e in range(lo_exp, hi_exp + 1)]
        self.counts = [0] * (len(self.bounds) + 1)
        self.total = 0
        self.sum = 0
        self._lock = threading.Lock()

    def record(self, v: int) -> None:
        idx = bisect_left(self.bounds, v)  # first bucket with bound >= v
        with self._lock:
            self.counts[idx] += 1
            self.total += 1
            self.sum += v

    def quantile(self, q: float) -> int | None:
        """Upper bound of the bucket holding quantile q (conservative)."""
        with self._lock:
            if not self.total:
                return None
            target = q * self.total
            run = 0
            for i, c in enumerate(self.counts):
                run += c
                if run >= target:
                    return self.bounds[i] if i < len(self.bounds) else -1
        return -1


def prometheus_text(snapshots: Iterable[dict], histograms: dict[str, Histogram] | None = None,
                    resource: dict | None = None) -> str:
    lines: list[str] = []
    snaps = list(snapshots)
    if resource:
        lines.append("# HELP inv16_build_info Runtime/ABI/config identity (resource attributes)")
        lines.append("# TYPE inv16_build_info gauge")
        attrs = ",".join(f'{k}="{_label(v)}"' for k, v in sorted(resource.items()))
        lines.append(f"inv16_build_info{{{attrs}}} 1")

    def head(name: str) -> None:
        typ, unit, desc = METRICS[name]
        lines.append(f"# HELP {name} {desc} ({unit})")
        lines.append(f"# TYPE {name} {typ}")

    head("inv16_calls_in_flight")
    for s in snaps:
        inst = _label(s["instance"])
        for fn, n in sorted(s["calls_in_flight_by_function"].items()):
            lines.append(f'inv16_calls_in_flight{{instance="{inst}",function="{_label(fn)}"}} {n}')
    for name, key in (("inv16_calls_queued", "calls_queued"), ("inv16_tombstones", "tombstones"),
                      ("inv16_call_ids_remaining", "call_ids_remaining")):
        head(name)
        for s in snaps:
            lines.append(f'{name}{{instance="{_label(s["instance"])}"}} {s[key]}')
    for name, key in _COUNTER_FIELDS.items():
        head(name)
        for s in snaps:
            lines.append(f'{name}{{instance="{_label(s["instance"])}"}} {s[key]}')
    for hname, h in (histograms or {}).items():
        head(hname)
        run = 0
        for b, c in zip(h.bounds, h.counts):
            run += c
            lines.append(f'{hname}_bucket{{le="{b}"}} {run}')
        lines.append(f'{hname}_bucket{{le="+Inf"}} {h.total}')
        lines.append(f"{hname}_sum {h.sum}")
        lines.append(f"{hname}_count {h.total}")
    return "\n".join(lines) + "\n"


CRITICAL_EVENTS = frozenset({"double_delivery", "callee_trapped", "late_event_history_expired",
                             "stale_generation", "call_id_near_exhaustion", "generation_renewed"})


class EventLog:
    """Bounded, non-blocking structured event sink (JSON lines).

    * ordinary events are sampled at ``sample_rate``; critical ones never are;
    * ``tenant``/``workload`` fields are replaced by a salted hash;
    * when the buffer is full the oldest *non-critical* event is dropped and
      counted - the lifecycle path never waits on the sink.
    """

    def __init__(self, capacity: int = 10_000, sample_rate: float = 1.0, salt: bytes = b"inv16",
                 writer: Callable[[str], None] | None = None, rng: random.Random | None = None):
        self.capacity = capacity
        self.sample_rate = sample_rate
        self.salt = salt
        self.writer = writer
        self.buffer: deque[tuple[bool, str]] = deque()
        self.dropped = 0
        self.sampled_out = 0
        self.write_failures = 0
        self._rng = rng or random.Random(0)
        self._lock = threading.Lock()

    def __call__(self, event: dict) -> None:
        critical = event.get("type") in CRITICAL_EVENTS or event.get("severity") == "critical"
        if not critical and self.sample_rate < 1.0 and self._rng.random() >= self.sample_rate:
            self.sampled_out += 1
            return
        ev = dict(event)
        for k in ("tenant", "workload"):
            if k in ev:
                ev[k] = "h:" + hashlib.sha256(self.salt + str(ev[k]).encode()).hexdigest()[:16]
        line = json.dumps(ev, sort_keys=True, separators=(",", ":"), default=str)
        with self._lock:
            if len(self.buffer) >= self.capacity:
                self._evict_one()
            self.buffer.append((critical, line))
        if self.writer is not None:
            try:
                self.writer(line)
            except Exception:  # noqa: BLE001 - writer failure must not propagate
                self.write_failures += 1

    def _evict_one(self) -> None:
        for i, (crit, _line) in enumerate(self.buffer):
            if not crit:
                del self.buffer[i]
                self.dropped += 1
                return
        self.buffer.popleft()
        self.dropped += 1

    def events(self) -> list[dict]:
        with self._lock:
            return [json.loads(x) for _c, x in self.buffer]
