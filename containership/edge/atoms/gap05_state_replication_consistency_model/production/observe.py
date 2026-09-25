"""MC26 observability package, MC27 structured logs/tracing, MC28 health/readiness,
MC29 admission control/backpressure, MC31 time-independent expiry semantics,
MC44 conflict analytics.

* Metrics are an in-process registry with Prometheus text exposition (no client
  library dependency).  Label cardinality is bounded (``max_series``); overflow series
  collapse into ``{overflow="true"}`` and are counted, never dropped silently.
* Logs are one JSON object per line with stable fields (ts, level, event, code,
  tenant, environment, site, op_id, trace_id, span_id).  Values and any field named in
  ``REDACT`` are replaced by a salted digest; sampling is deterministic on trace_id.
* Admission uses *logical* token buckets refilled by an injected tick source, so tests
  and replay are deterministic.
* Expiry is expressed in membership epochs / logical ticks, never wall clock, and only
  ever decides *retention*, never causal ordering.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import Counter, defaultdict

from .errors import CapacityError

REDACT = frozenset({"value", "secret", "token", "sig", "key_material", "ct"})


class Metrics:
    def __init__(self, *, max_series: int = 10_000):
        self.max_series = max_series
        self._lock = threading.Lock()
        self.counters: dict[tuple, float] = defaultdict(float)
        self.gauges: dict[tuple, float] = {}
        self.hist: dict[tuple, list] = defaultdict(list)
        self.overflow = 0

    def _key(self, name, labels):
        key = (name, tuple(sorted((labels or {}).items())))
        total = len(self.counters) + len(self.gauges) + len(self.hist)
        if key not in self.counters and key not in self.gauges and key not in self.hist and total >= self.max_series:
            self.overflow += 1
            return (name, (("overflow", "true"),))
        return key

    def inc(self, name, value=1.0, **labels):
        with self._lock:
            self.counters[self._key(name, labels)] += value

    def set(self, name, value, **labels):
        with self._lock:
            self.gauges[self._key(name, labels)] = value

    def observe(self, name, value, **labels):
        with self._lock:
            h = self.hist[self._key(name, labels)]
            h.append(value)
            if len(h) > 4096:  # bounded reservoir: keep every other sample
                del h[::2]

    def quantile(self, name, q, **labels):
        vals = sorted(self.hist.get((name, tuple(sorted(labels.items()))), []))
        if not vals:
            return None
        return vals[min(len(vals) - 1, int(q * len(vals)))]

    def get(self, name, **labels):
        key = (name, tuple(sorted(labels.items())))
        return self.counters.get(key, self.gauges.get(key, 0.0))

    def exposition(self) -> str:
        lines = []
        def fmt(k):
            name, labels = k
            lab = ",".join(f'{a}="{b}"' for a, b in labels)
            return f"gap05_{name}{{{lab}}}" if lab else f"gap05_{name}"
        with self._lock:
            for k, v in sorted(self.counters.items()):
                lines.append(f"{fmt(k)} {v}")
            for k, v in sorted(self.gauges.items()):
                lines.append(f"{fmt(k)} {v}")
            for k, vals in sorted(self.hist.items()):
                s = sorted(vals)
                for q in (0.5, 0.95, 0.99):
                    name, labels = k
                    lines.append(f"{fmt((name, labels + (('quantile', str(q)),)))} "
                                 f"{s[min(len(s) - 1, int(q * len(s)))] if s else 0}")
            lines.append(f"gap05_metric_series_overflow_total {self.overflow}")
        return "\n".join(lines) + "\n"


class StructuredLog:
    def __init__(self, sink=None, *, salt: bytes | None = None, sample_rate: float = 1.0, max_lines: int = 100_000):
        self.sink = sink
        self.lines: list[str] = []
        self.salt = salt or os.urandom(16)
        self.sample_rate = sample_rate
        self.max_lines = max_lines
        self.dropped_by_sampling = 0

    def _redact(self, value) -> str:
        return "sha256:" + hashlib.sha256(self.salt + str(value).encode("utf-8", "surrogatepass")).hexdigest()[:16]

    def _sampled(self, trace_id: str | None, level: str) -> bool:
        if level in ("error", "warn") or self.sample_rate >= 1.0 or not trace_id:
            return True
        return int(hashlib.sha256(trace_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < self.sample_rate

    def emit(self, level: str, event: str, **fields) -> dict | None:
        if not self._sampled(fields.get("trace_id"), level):
            self.dropped_by_sampling += 1
            return None
        rec = {"ts": round(time.time(), 6), "level": level, "event": event}
        for k, v in fields.items():
            rec[k] = self._redact(v) if k in REDACT else v
        line = json.dumps(rec, sort_keys=True, default=str)
        if self.sink is not None:
            self.sink(line)
        self.lines.append(line)
        if len(self.lines) > self.max_lines:
            del self.lines[: len(self.lines) // 2]
        return rec


def new_trace_id() -> str:
    return os.urandom(16).hex()


def new_span_id() -> str:
    return os.urandom(8).hex()


class TokenBucket:
    def __init__(self, capacity: int, refill_per_tick: int):
        self.capacity = capacity
        self.refill = refill_per_tick
        self.tokens = capacity
        self.tick = 0

    def advance(self, ticks: int = 1):
        self.tick += ticks
        self.tokens = min(self.capacity, self.tokens + ticks * self.refill)

    def take(self, n: int = 1) -> bool:
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


class Admission:
    """Per-tenant, per-key and replay-storm admission control with explicit reasons."""

    def __init__(self, *, tenant_capacity=10_000, tenant_refill=1_000, key_capacity=500, key_refill=50,
                 max_tracked_keys=100_000, recovery_capacity=5_000):
        self.tenant = defaultdict(lambda: TokenBucket(tenant_capacity, tenant_refill))
        self.keys: dict = {}
        self.key_capacity, self.key_refill = key_capacity, key_refill
        self.max_tracked_keys = max_tracked_keys
        self.recovery = TokenBucket(recovery_capacity, recovery_capacity // 10 or 1)
        self.rejections = Counter()

    def advance(self, ticks=1):
        for b in self.tenant.values():
            b.advance(ticks)
        for b in self.keys.values():
            b.advance(ticks)
        self.recovery.advance(ticks)

    def admit(self, tenant: str, key: str, *, recovery: bool = False) -> None:
        if recovery and not self.recovery.take():
            self.rejections["recovery_burst"] += 1
            raise CapacityError("recovery replay rate exceeded", code="CAP_RECOVERY_BURST")
        if not self.tenant[tenant].take():
            self.rejections["tenant_rate"] += 1
            raise CapacityError(f"tenant {tenant} over write rate", code="CAP_TENANT_RATE")
        kb = self.keys.get((tenant, key))
        if kb is None:
            if len(self.keys) >= self.max_tracked_keys:
                self.keys.pop(next(iter(self.keys)))
            kb = self.keys[(tenant, key)] = TokenBucket(self.key_capacity, self.key_refill)
        if not kb.take():
            self.rejections["hot_key"] += 1
            raise CapacityError(f"hot key {key} over write rate", code="CAP_HOT_KEY")


class EpochExpiry:
    """Retention/TTL in logical epochs.  Returns only *retention* verdicts."""

    def __init__(self, ttl_epochs: int):
        if ttl_epochs < 1:
            raise ValueError("ttl_epochs must be >= 1")
        self.ttl = ttl_epochs

    def expired(self, recorded_epoch: int, current_epoch: int) -> bool:
        return current_epoch - recorded_epoch >= self.ttl


class ConflictAnalytics:
    def __init__(self, *, top_n: int = 20):
        self.by_key = Counter()
        self.by_pair = Counter()
        self.outcomes = Counter()
        self.recurrence = Counter()
        self._resolved_once: set = set()
        self.top_n = top_n

    def record(self, tenant, key, outcome, sites=()):
        self.outcomes[outcome] += 1
        if outcome in ("conflict", "quarantined"):
            self.by_key[(tenant, key)] += 1
            s = sorted(set(sites))
            for i in range(len(s)):
                for j in range(i + 1, len(s)):
                    self.by_pair[(s[i], s[j])] += 1
            if (tenant, key) in self._resolved_once:
                self.recurrence[(tenant, key)] += 1

    def record_resolution(self, tenant, key, policy_version):
        self._resolved_once.add((tenant, key))
        self.outcomes[f"resolved:{policy_version}"] += 1

    def report(self) -> dict:
        total = sum(v for k, v in self.outcomes.items() if not k.startswith("resolved:"))
        conflicts = self.outcomes["conflict"] + self.outcomes["quarantined"]
        return {"writes": total, "conflict_rate": (conflicts / total) if total else 0.0,
                "hot_keys": [{"tenant": t, "key": k, "conflicts": n} for (t, k), n in self.by_key.most_common(self.top_n)],
                "site_pairs": [{"pair": list(p), "conflicts": n} for p, n in self.by_pair.most_common(self.top_n)],
                "recurring": [{"tenant": t, "key": k, "recurrences": n}
                              for (t, k), n in self.recurrence.most_common(self.top_n)],
                "outcomes": dict(self.outcomes)}
