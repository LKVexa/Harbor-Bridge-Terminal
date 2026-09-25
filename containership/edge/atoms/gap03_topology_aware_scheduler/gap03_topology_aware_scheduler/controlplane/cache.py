"""MC-028 - Topology/cost cache with generation invalidation (GAP03-CACHE/1).

Keys include EVERY dimension that can change a ranking: topology generation,
config generation, schema version, scoring version, anchor, candidate-set
digest, spread-set digest.  Values are immutable tuples.  Bounded LRU with
TTL and per-entry size cap; single-flight fill; process-local only - correctness
never depends on it: fairness verdicts/claims are NEVER cached and are always
revalidated at commit.
"""
from __future__ import annotations

from collections import OrderedDict
import threading
import time

from . import canonical

MAX_ENTRIES = 4096
MAX_ENTRY_CANDIDATES = 20_000
TTL_S = 300


class ScoreCache:
    def __init__(self, *, max_entries=MAX_ENTRIES, ttl_s=TTL_S, clock=time.monotonic, metrics=None, enabled=True):
        self.max_entries, self.ttl, self.clock, self.metrics, self.enabled = max_entries, ttl_s, clock, metrics, enabled
        self._d: "OrderedDict[tuple, tuple]" = OrderedDict()
        self._lock = threading.Lock()
        self._inflight: dict[tuple, threading.Event] = {}
        self.stats = {"hit": 0, "miss": 0, "evict": 0, "stale": 0, "fill": 0}
        self.namespace = None

    def _ev(self, e):
        self.stats[e] += 1
        if self.metrics:
            self.metrics.inc("gap03_cache_events_total", event=e)

    @staticmethod
    def key(*, topology_generation, config_generation, schema_version, scoring_version, anchor, candidates, spread_from) -> tuple:
        return (topology_generation, config_generation, schema_version, scoring_version, anchor,
                canonical.digest(list(candidates)), canonical.digest(sorted(spread_from)))

    def set_namespace(self, topology_generation, config_generation):
        with self._lock:
            ns = (topology_generation, config_generation)
            if ns != self.namespace:
                self._d.clear()  # invalidate on generation change, not just TTL
                self.namespace = ns

    def get_or_compute(self, key: tuple, compute):
        if not self.enabled:
            return compute()
        while True:
            with self._lock:
                item = self._d.get(key)
                if item is not None:
                    ts, val = item
                    if self.clock() - ts <= self.ttl and key[:2] == (self.namespace or key[:2]):
                        self._d.move_to_end(key)
                        self._ev("hit")
                        return val
                    del self._d[key]
                    self._ev("stale")
                ev = self._inflight.get(key)
                if ev is None:
                    ev = self._inflight[key] = threading.Event()
                    leader = True
                    self._ev("miss")
                else:
                    leader = False
            if leader:
                try:
                    import time as _t
                    t0 = _t.perf_counter()
                    val = tuple(compute())
                    if self.metrics:
                        self.metrics.observe("gap03_cache_build_ms", (_t.perf_counter() - t0) * 1000)
                    if len(val) <= MAX_ENTRY_CANDIDATES:
                        with self._lock:
                            self._d[key] = (self.clock(), val)
                            self._ev("fill")
                            while len(self._d) > self.max_entries:
                                self._d.popitem(last=False)
                                self._ev("evict")
                            if self.metrics:
                                self.metrics.set("gap03_cache_entries", len(self._d))
                    return val
                finally:
                    with self._lock:
                        self._inflight.pop(key, None)
                    ev.set()
            ev.wait(5.0)

    def warm(self, items, *, budget_s: float = 0.5) -> dict:
        """Precompute (key, compute) pairs within a hard time budget; never blocks readiness past it."""
        start, done, skipped = self.clock(), 0, 0
        for key, compute in items:
            if self.clock() - start >= budget_s:
                skipped += 1
                continue
            self.get_or_compute(key, compute)
            done += 1
        return {"warmed": done, "skipped_for_budget": skipped}

    def size(self) -> int:
        return len(self._d)
