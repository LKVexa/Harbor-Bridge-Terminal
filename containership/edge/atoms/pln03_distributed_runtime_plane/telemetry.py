"""Metrics, structured logs, trace propagation, health/readiness and stall
detection (MC-036, MC-045).  Dependency-free; exposition is Prometheus text.
Log records pass through ``config.redact`` so payloads and secrets never leak.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict
from typing import Callable

from .config import redact

BUCKETS = (0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 1.0, float("inf"))
MAX_SERIES = 5000


def new_trace_id() -> str:
    return os.urandom(16).hex()


def parse_traceparent(header: str | None) -> str:
    """W3C traceparent ``00-<32hex>-<16hex>-<2hex>``; invalid input starts a new trace."""
    try:
        v, tid, sid, fl = (header or "").split("-")
        if v == "00" and len(tid) == 32 and len(sid) == 16 and int(tid, 16) and len(fl) == 2:
            return tid
    except ValueError:
        pass
    return new_trace_id()


class Metrics:
    def __init__(self) -> None:
        self._c: dict[tuple, float] = defaultdict(float)
        self._h: dict[tuple, list[int]] = {}
        self._hsum: dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
        self.dropped_series = 0

    def _ok(self, key: tuple) -> bool:
        if key in self._c or key in self._h:
            return True
        if len(self._c) + len(self._h) >= MAX_SERIES:
            self.dropped_series += 1
            return False
        return True

    def inc(self, name: str, n: float = 1, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            if self._ok(key):
                self._c[key] += n

    def observe(self, name: str, value: float, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            if not self._ok(key):
                return
            h = self._h.setdefault(key, [0] * len(BUCKETS))
            for i, b in enumerate(BUCKETS):
                if value <= b:
                    h[i] += 1
            self._hsum[key] += value

    def get(self, name: str, **labels: str) -> float:
        return self._c.get((name, tuple(sorted(labels.items()))), 0.0)

    def exposition(self) -> str:
        out = []
        with self._lock:
            for (n, lab), v in sorted(self._c.items()):
                ls = ",".join(f'{k}="{val}"' for k, val in lab)
                out.append(f"pk_pln03_{n}{{{ls}}} {v}")
            for (n, lab), h in sorted(self._h.items()):
                base = ",".join(f'{k}="{val}"' for k, val in lab)
                for b, c in zip(BUCKETS, h):
                    le = "+Inf" if b == float("inf") else repr(b)
                    out.append(f'pk_pln03_{n}_bucket{{{base}{"," if base else ""}le="{le}"}} {c}')
                out.append(f"pk_pln03_{n}_sum{{{base}}} {self._hsum[(n, lab)]}")
                out.append(f"pk_pln03_{n}_count{{{base}}} {h[-1]}")
        return "\n".join(out) + "\n"


class StructuredLog:
    def __init__(self, sink: Callable[[str], None] | None = None, max_records: int = 10_000):
        self.records: list[dict] = []
        self.sink, self.max_records = sink, max_records

    def log(self, level: str, event: str, **fields: object) -> dict:
        rec = redact({"ts": round(time.time(), 6), "level": level, "event": event, **fields})
        if len(self.records) >= self.max_records:
            self.records.pop(0)
        self.records.append(rec)
        if self.sink:
            self.sink(json.dumps(rec, sort_keys=True, default=str))
        return rec


class Watchdog:
    """Stall detector: an operation in flight longer than ``stall_s`` is reported (MC-036)."""

    def __init__(self, stall_s: float, clock: Callable[[], float] = time.monotonic):
        self.stall_s, self.clock = stall_s, clock
        self._inflight: dict[int, tuple[str, float]] = {}
        self._n = 0
        self._lock = threading.Lock()

    def start(self, op: str) -> int:
        with self._lock:
            self._n += 1
            self._inflight[self._n] = (op, self.clock())
            return self._n

    def stop(self, token: int) -> None:
        with self._lock:
            self._inflight.pop(token, None)

    def stalled(self) -> list[tuple[str, float]]:
        now = self.clock()
        with self._lock:
            return [(op, now - t) for op, t in self._inflight.values() if now - t > self.stall_s]


def health_report(*, lifecycle_state: str, adapters: dict[str, bool], breakers: dict[str, str],
                  stalled: list, config_digest: str | None, owner: str | None) -> dict:
    """Liveness = process can answer; readiness = serving writes with every dependency reachable."""
    ready = lifecycle_state in {"ready"} and all(adapters.values()) and not stalled \
        and all(s != "open" for s in breakers.values())
    return {"schema": "pk.health/1", "live": lifecycle_state not in {"stopped", "failed"},
            "ready": ready, "state": lifecycle_state, "adapters": adapters, "breakers": breakers,
            "stalled_ops": [op for op, _ in stalled], "config_digest": config_digest,
            "accountable_owner": owner}
