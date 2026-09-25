"""Audit sink (M19), event export (M36), metrics/logs/traces/health/explain (M20),
telemetry policy (M21) and admission-latency SLO measurement (M44)."""
from __future__ import annotations

import bisect
import hashlib
import json
import os
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping, Protocol

from .errors import PlaneError
from .security import redact

GENESIS = "0" * 64


def _canon(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()


# --------------------------------------------------------------------------- audit sink (M19)

class AuditAnchor(Protocol):
    """External anchor (transparency log, WORM bucket, notary).  Must be append-only."""

    def anchor(self, sequence: int, head_hash: str) -> str: ...


class FileAnchor:
    """Append-only local anchor file (reference).  Production: external WORM/transparency log."""

    def __init__(self, path: str) -> None:
        self._path = path

    def anchor(self, sequence: int, head_hash: str) -> str:
        line = json.dumps({"sequence": sequence, "head": head_hash, "ts_ns": time.time_ns()}, sort_keys=True)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return f"file:{self._path}#{sequence}"

    def anchors(self) -> list[dict]:
        if not os.path.exists(self._path):
            return []
        with open(self._path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]


class DurableAuditSink:
    """Hash-chained JSONL audit log, fsync'd per record, resumable after restart.

    ``verify()`` re-derives the whole chain; ``anchor_every`` records the head
    in an external anchor so truncation of the tail is also detectable.
    Writes that cannot be made durable raise, and the plane refuses the
    security-relevant operation rather than proceeding unaudited.
    """

    def __init__(self, path: str, *, anchor: AuditAnchor | None = None, anchor_every: int = 64,
                 fsync: bool = True, max_bytes: int = 256 * 1024 * 1024) -> None:
        self._path = path
        self._anchor = anchor
        self._every = anchor_every
        self._fsync = fsync
        self._max_bytes = max_bytes
        self._lock = threading.Lock()
        self.sequence, self.head = self._resume()
        self._fh = open(path, "a", encoding="utf-8")

    def _resume(self) -> tuple[int, str]:
        if not os.path.exists(self._path):
            return 0, GENESIS
        ok, seq, head, _ = verify_audit_file(self._path)
        if not ok:
            raise PlaneError("PLN04-STATE-003", details={"reason": f"audit chain broken at record {seq + 1}"})
        return seq, head

    def append(self, kind: str, details: Mapping[str, object], timestamp_ns: int | None = None) -> dict:
        with self._lock:
            if self._fh.tell() > self._max_bytes:
                raise PlaneError("PLN04-DEP-001", details={"dependency": "audit-sink", "reason": "audit log full; rotate/export"})
            seq = self.sequence + 1
            body = {"sequence": seq, "timestamp_ns": timestamp_ns or time.time_ns(), "kind": kind,
                    "details": redact(dict(details)), "previous_hash": self.head}
            body["event_hash"] = hashlib.sha256(_canon({k: body[k] for k in ("sequence", "timestamp_ns", "kind", "details", "previous_hash")})).hexdigest()
            try:
                self._fh.write(json.dumps(body, sort_keys=True, separators=(",", ":"), default=str) + "\n")
                self._fh.flush()
                if self._fsync:
                    os.fsync(self._fh.fileno())
            except OSError as exc:
                raise PlaneError("PLN04-DEP-001", details={"dependency": "audit-sink"}, cause=exc) from None
            self.sequence, self.head = seq, body["event_hash"]
            if self._anchor is not None and seq % self._every == 0:
                self._anchor.anchor(seq, self.head)
            return body

    def anchor_now(self) -> str | None:
        with self._lock:
            return self._anchor.anchor(self.sequence, self.head) if self._anchor and self.sequence else None

    def close(self) -> None:
        with self._lock:
            self._fh.close()


def verify_audit_file(path: str, anchors: Iterable[Mapping[str, object]] = ()) -> tuple[bool, int, str, str]:
    """Return ``(ok, last_good_sequence, head, reason)``; checks anchors if supplied."""
    prev, seq = GENESIS, 0
    heads: dict[int, str] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                expected = hashlib.sha256(_canon({k: rec[k] for k in ("sequence", "timestamp_ns", "kind", "details", "previous_hash")})).hexdigest()
            except (ValueError, KeyError):
                return False, seq, prev, "unparseable record"
            if rec["sequence"] != seq + 1 or rec["previous_hash"] != prev or rec["event_hash"] != expected:
                return False, seq, prev, "hash chain mismatch"
            seq, prev = rec["sequence"], rec["event_hash"]
            heads[seq] = prev
    for a in anchors:
        s = int(a["sequence"])
        if s > seq:
            return False, seq, prev, f"anchored sequence {s} missing (truncation)"
        if heads.get(s) != a["head"]:
            return False, seq, prev, f"anchor mismatch at {s}"
    return True, seq, prev, "ok"


# --------------------------------------------------------------------------- event export (M36)

class EventSink(Protocol):
    def publish(self, batch: list[dict]) -> None: ...


class JsonlEventSink:
    def __init__(self, path: str) -> None:
        self._path = path

    def publish(self, batch: list[dict]) -> None:
        with open(self._path, "a", encoding="utf-8") as fh:
            for ev in batch:
                fh.write(json.dumps(ev, sort_keys=True, separators=(",", ":")) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


class EventExporter:
    """Transactional-outbox exporter: at-least-once delivery, stable ``event_id`` for consumer dedupe,
    bounded outbox (overflow => producer back-pressure, never silent drop)."""

    def __init__(self, sink: EventSink, *, max_outbox: int = 10000, batch: int = 100) -> None:
        self._sink = sink
        self._outbox: deque[dict] = deque()
        self._max = max_outbox
        self._batch = batch
        self._lock = threading.Lock()
        self.delivered = 0
        self.failures = 0

    def enqueue(self, event: dict) -> None:
        with self._lock:
            if len(self._outbox) >= self._max:
                raise PlaneError("PLN04-CAP-002", details={"queue_depth": len(self._outbox), "dependency": "event-export"}, retry_after_s=1.0)
            self._outbox.append({"event_id": event.get("event_hash") or uuid.uuid4().hex, **event})

    def flush(self) -> int:
        sent = 0
        while True:
            with self._lock:
                batch = list(self._outbox)[: self._batch]
            if not batch:
                return sent
            try:
                self._sink.publish(batch)
            except Exception:
                with self._lock:
                    self.failures += 1
                return sent  # keep in outbox for the next flush (at-least-once)
            with self._lock:
                for _ in batch:
                    self._outbox.popleft()
                self.delivered += len(batch)
            sent += len(batch)

    def pending(self) -> int:
        with self._lock:
            return len(self._outbox)


# --------------------------------------------------------------------------- telemetry policy (M21)

@dataclass(frozen=True)
class TelemetryPolicy:
    log_sample_rate: float = 1.0          # security/lifecycle events are never sampled
    trace_sample_rate: float = 0.1
    retention_days_logs: int = 30
    retention_days_audit: int = 400
    retention_days_metrics: int = 90
    tenant_identifier_mode: str = "hashed"  # "hashed" | "clear" | "omit"
    tenant_hash_salt: str = "pln04"

    def __post_init__(self) -> None:
        if not (0 <= self.log_sample_rate <= 1 and 0 <= self.trace_sample_rate <= 1):
            raise ValueError("sample rates must be within [0, 1]")
        if self.tenant_identifier_mode not in ("hashed", "clear", "omit"):
            raise ValueError("invalid tenant_identifier_mode")
        if self.retention_days_audit < self.retention_days_logs:
            raise ValueError("audit retention must be >= log retention")

    def tenant_label(self, tenant: str | None) -> str | None:
        if tenant is None or self.tenant_identifier_mode == "omit":
            return None
        if self.tenant_identifier_mode == "clear":
            return tenant
        return "t_" + hashlib.sha256((self.tenant_hash_salt + tenant).encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- metrics / logs / traces (M20, M44)

LATENCY_BUCKETS_MS = (0.5, 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)


class Histogram:
    def __init__(self, buckets: Iterable[float] = LATENCY_BUCKETS_MS, reservoir: int = 4096) -> None:
        self.buckets = tuple(buckets)
        self.counts = [0] * (len(self.buckets) + 1)
        self.sum = 0.0
        self.n = 0
        self._samples: deque[float] = deque(maxlen=reservoir)

    def observe(self, value: float) -> None:
        self.counts[bisect.bisect_left(self.buckets, value)] += 1
        self.sum += value
        self.n += 1
        self._samples.append(value)

    def quantile(self, q: float) -> float | None:
        if not self._samples:
            return None
        s = sorted(self._samples)
        return s[min(len(s) - 1, int(q * len(s)))]


class Telemetry:
    """In-process metrics registry + structured JSON logger + span helper.

    Exposition: ``prometheus()`` (text format 0.0.4) and ``snapshot()``.
    Labels are bounded (tier/outcome/error_code only) to prevent cardinality
    explosions; tenant ids never appear as metric labels.
    """

    def __init__(self, policy: TelemetryPolicy | None = None, *, log_stream=None, rng: random.Random | None = None) -> None:
        self.policy = policy or TelemetryPolicy()
        self._counters: dict[tuple[str, tuple], float] = {}
        self._gauges: dict[tuple[str, tuple], float] = {}
        self._hists: dict[tuple[str, tuple], Histogram] = {}
        self._lock = threading.Lock()
        self._stream = log_stream
        self._rng = rng or random.Random()
        self.logs: deque[dict] = deque(maxlen=2048)

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def gauge(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self._gauges[(name, tuple(sorted(labels.items())))] = value

    def observe(self, name: str, value: float, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._hists.setdefault(key, Histogram()).observe(value)

    def histogram(self, name: str, **labels: str) -> Histogram | None:
        with self._lock:
            return self._hists.get((name, tuple(sorted(labels.items()))))

    def log(self, level: str, event: str, *, security: bool = False, trace_id: str | None = None, **fields: object) -> None:
        if not security and level == "debug" and self._rng.random() >= self.policy.log_sample_rate:
            return
        if "tenant" in fields:
            fields["tenant"] = self.policy.tenant_label(fields["tenant"])  # type: ignore[arg-type]
        rec = {"ts_ns": time.time_ns(), "level": level, "event": event, "component": "PLN-04",
               "trace_id": trace_id, **redact(fields)}
        with self._lock:
            self.logs.append(rec)
        if self._stream is not None:
            self._stream.write(json.dumps(rec, sort_keys=True, default=str) + "\n")

    def new_trace(self, parent: str | None = None) -> tuple[str, bool]:
        """Return (trace_id, sampled); honours a W3C ``traceparent`` if supplied."""
        if parent:
            parts = parent.split("-")
            if len(parts) == 4 and len(parts[1]) == 32 and all(c in "0123456789abcdef" for c in parts[1]):
                return parts[1], parts[3] == "01"
        return uuid.uuid4().hex, self._rng.random() < self.policy.trace_sample_rate

    def prometheus(self) -> str:
        def fmt(labels: tuple) -> str:
            return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}" if labels else ""

        out: list[str] = []
        with self._lock:
            for (name, labels), v in sorted(self._counters.items()):
                out.append(f"{name}_total{fmt(labels)} {v}")
            for (name, labels), v in sorted(self._gauges.items()):
                out.append(f"{name}{fmt(labels)} {v}")
            for (name, labels), h in sorted(self._hists.items()):
                cum = 0
                for b, c in zip(h.buckets, h.counts):
                    cum += c
                    out.append(f"{name}_bucket{fmt(labels + (('le', str(b)),))} {cum}")
                out.append(f"{name}_bucket{fmt(labels + (('le', '+Inf'),))} {h.n}")
                out.append(f"{name}_sum{fmt(labels)} {h.sum}")
                out.append(f"{name}_count{fmt(labels)} {h.n}")
        return "\n".join(out) + "\n"

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "counters": {f"{n}{dict(l)}": v for (n, l), v in self._counters.items()},
                "gauges": {f"{n}{dict(l)}": v for (n, l), v in self._gauges.items()},
                "latency_ms": {f"{n}{dict(l)}": {"n": h.n, "p50": h.quantile(0.5), "p99": h.quantile(0.99)}
                               for (n, l), h in self._hists.items()},
            }


@dataclass(frozen=True)
class LatencySlo:
    """M44 - admission latency objective (values are PROPOSED until approved in ops/SLO.json)."""

    p50_ms: float = 5.0
    p99_ms: float = 50.0
    min_samples: int = 100

    def evaluate(self, hist: Histogram | None) -> dict:
        if hist is None or hist.n < self.min_samples:
            return {"status": "INSUFFICIENT_DATA", "samples": 0 if hist is None else hist.n}
        p50, p99 = hist.quantile(0.5), hist.quantile(0.99)
        ok = p50 is not None and p99 is not None and p50 <= self.p50_ms and p99 <= self.p99_ms
        return {"status": "MET" if ok else "BREACHED", "samples": hist.n, "p50_ms": p50, "p99_ms": p99,
                "objective": {"p50_ms": self.p50_ms, "p99_ms": self.p99_ms}}
