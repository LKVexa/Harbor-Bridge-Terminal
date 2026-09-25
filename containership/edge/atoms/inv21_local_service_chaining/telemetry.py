"""Bounded, privacy-safe telemetry: metrics, decision ledger, explain view.

GAP-019 (export surface), GAP-020 (privacy/retention/sampling/explain),
GAP-023 (saturation signals).

Privacy policy (docs/TELEMETRY_PRIVACY.md):
* request payloads, credentials and handler exception text are NEVER recorded;
* principal subjects are pseudonymised with a keyed hash (``redact``);
* tenant and callee labels are kept (needed for isolation SLOs) but label
  cardinality is capped; overflow collapses into ``__other__``;
* the decision ledger is a bounded ring with a max age; refusals are always
  kept, successful routes are sampled at ``sample_rate``.
"""
from __future__ import annotations

import hashlib
import hmac
import random
import secrets
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Optional

OVERFLOW = "__other__"


@dataclass(frozen=True)
class DecisionEvent:
    callee: str
    tenant: str
    trace_id: str
    route: str
    reason: str
    depth: int
    duration_ns: int
    code: Optional[str] = None
    subject: Optional[str] = None
    ts: float = 0.0
    config_revision: Optional[int] = None
    policy_revision: Optional[int] = None


class Metrics:
    def __init__(self, *, max_series: int = 2048, max_label_values: int = 256) -> None:
        self._lock = threading.Lock()
        self._counters: dict = {}
        self._gauges: dict = {}
        self._hist: dict = {}
        self.max_series = max_series
        self.max_label_values = max_label_values
        self._label_values: dict = {}
        self._keycache: dict = {}
        self.dropped_series = 0

    def _label(self, key: str, value: str) -> str:
        seen = self._label_values.setdefault(key, set())
        if value in seen:
            return value
        if len(seen) >= self.max_label_values:
            return OVERFLOW
        seen.add(value)
        return value

    def _series(self, store: dict, name: str, labels: dict):
        ck = (id(store), name, tuple(labels.items()))
        hit = self._keycache.get(ck)
        if hit is not None and hit in store:
            return hit
        key = self._series_slow(store, name, labels)
        if len(self._keycache) < 4 * self.max_series:
            self._keycache[ck] = key
        return key

    def _series_slow(self, store: dict, name: str, labels: dict):
        key = (name, tuple(sorted((k, self._label(k, str(v))) for k, v in labels.items())))
        if key not in store and sum(map(len, (self._counters, self._gauges, self._hist))) >= self.max_series:
            self.dropped_series += 1
            key = (name, (("overflow", OVERFLOW),))
        return key

    def inc(self, name: str, n: int = 1, **labels) -> None:
        with self._lock:
            k = self._series(self._counters, name, labels)
            self._counters[k] = self._counters.get(k, 0) + n

    def set(self, name: str, value: float, **labels) -> None:
        with self._lock:
            self._gauges[self._series(self._gauges, name, labels)] = value

    BUCKETS_US = (1, 2, 5, 10, 20, 50, 100, 1000, 10000, 100000)

    def observe_us(self, name: str, us: float, **labels) -> None:
        with self._lock:
            k = self._series(self._hist, name, labels)
            h = self._hist.setdefault(k, [0] * (len(self.BUCKETS_US) + 1) + [0.0])
            for i, b in enumerate(self.BUCKETS_US):
                if us <= b:
                    h[i] += 1
                    break
            else:
                h[len(self.BUCKETS_US)] += 1
            h[-1] += us

    def counter(self, name: str, **labels) -> int:
        with self._lock:
            return sum(v for (n, ls), v in self._counters.items()
                       if n == name and all((k, str(val)) in ls for k, val in labels.items()))

    def prometheus(self) -> str:
        """Prometheus text exposition (0.0.4)."""
        def fmt(ls):
            return "{" + ",".join(f'{k}="{_esc(v)}"' for k, v in ls) + "}" if ls else ""
        out = []
        with self._lock:
            for (n, ls), v in sorted(self._counters.items()):
                out.append(f"inv21_{n}_total{fmt(ls)} {v}")
            for (n, ls), v in sorted(self._gauges.items()):
                out.append(f"inv21_{n}{fmt(ls)} {v}")
            for (n, ls), h in sorted(self._hist.items()):
                cum = 0
                for i, b in enumerate(self.BUCKETS_US):
                    cum += h[i]
                    out.append(f"inv21_{n}_bucket{fmt(ls + (('le', str(b)),))} {cum}")
                cum += h[len(self.BUCKETS_US)]
                out.append(f"inv21_{n}_bucket{fmt(ls + (('le', '+Inf'),))} {cum}")
                out.append(f"inv21_{n}_count{fmt(ls)} {cum}")
                out.append(f"inv21_{n}_sum{fmt(ls)} {h[-1]}")
        return "\n".join(out) + "\n"


def _esc(v: str) -> str:
    return str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class DecisionLedger:
    def __init__(self, *, max_events: int = 1024, max_age_s: float = 3600.0,
                 sample_rate: float = 1.0, redact_key: Optional[bytes] = None) -> None:
        if not isinstance(max_events, int) or isinstance(max_events, bool) or max_events < 1:
            raise ValueError("max_telemetry_events must be an integer >= 1")
        if not 0 <= sample_rate <= 1:
            raise ValueError("sample_rate must be within [0,1]")
        self._events: deque = deque(maxlen=max_events)
        self._lock = threading.Lock()
        self.max_age_s = max_age_s
        self.sample_rate = sample_rate
        self._redact_key = redact_key or secrets.token_bytes(32)  # per-process unless configured
        self.sampled_out = 0
        self._pseudo: dict = {}

    def redact(self, subject: Optional[str]) -> Optional[str]:
        if subject is None:
            return None
        p = self._pseudo.get(subject)
        if p is None:
            p = "p-" + hmac.new(self._redact_key, subject.encode(), hashlib.sha256).hexdigest()[:16]
            if len(self._pseudo) >= 4096:
                self._pseudo.clear()
            self._pseudo[subject] = p
        return p

    def record(self, ev: DecisionEvent) -> None:
        keep = ev.route == "refused" or self.sample_rate >= 1 or random.random() < self.sample_rate
        with self._lock:
            if not keep:
                self.sampled_out += 1
                return
            self._events.append(ev)

    def events(self) -> list:
        cutoff = time.time() - self.max_age_s
        with self._lock:
            if any(e.ts and e.ts < cutoff for e in self._events):
                kept = [e for e in self._events if not (e.ts and e.ts < cutoff)]
                self._events.clear(); self._events.extend(kept)
            return list(self._events)

    def explain(self, trace_id: str) -> list:
        """Operator explain view: every recorded routing decision for one trace."""
        return [asdict(e) for e in self.events() if e.trace_id == trace_id]
