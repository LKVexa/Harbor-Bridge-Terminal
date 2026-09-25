"""MC-027 - Latency-refinement engine (GAP03-LAT/1).

Contract rule: "measured latency refines a cost but never invents an edge".
The refined cost therefore stays strictly inside the static locality class
band of the pair, so measurements can re-order candidates *within* a class but
never across classes.  Producers are authenticated node identities that must
own the measurement's source endpoint; samples are bounded, de-duplicated,
EWMA-smoothed with outlier + rate-of-change limits; stale / sparse evidence
falls back to the static cost.  Paths are directional.
"""
from __future__ import annotations

from collections import OrderedDict, deque
import math
import statistics

from ..scheduler import LEVEL_COST
from .errors import SchedulerError

MAX_US = 10_000_000
FUTURE_SKEW_S = 30
TTL_S = 120
MIN_SAMPLES = 5
ALPHA = 0.2
OUTLIER_X = 5.0
PERSIST_TO_ACCEPT = 3
MAX_STEP_X = 2.0
RAW_KEEP = 32
MAX_PAIRS = 100_000
# static class -> (floor, band width) ; refined = floor + frac*(width) with width < gap to next class
BANDS = {0: (0, 0), 1: (1, 0), 2: (2, 8), 11: (11, 89), 101: (101, 0)}
BAND_REF_US = {2: (50, 2_000), 11: (500, 50_000)}  # latency range mapped onto the band


class LatencyEngine:
    def __init__(self, *, clock, metrics=None):
        self.clock, self.metrics = clock, metrics
        self.pairs: "OrderedDict[tuple, dict]" = OrderedDict()
        self.seen: "OrderedDict[str, None]" = OrderedDict()
        self.generation = None

    def invalidate(self, topology_generation: int):
        if topology_generation != self.generation:
            self.pairs.clear()
            self.generation = topology_generation

    def ingest(self, producer: str, sample: dict) -> str:
        """producer: verified identity ``spiffe://td/node/<name>``. Returns disposition (also counted)."""
        try:
            d = self._ingest(producer, sample)
        except SchedulerError as exc:
            d = exc.code
            raise
        finally:
            if self.metrics:
                self.metrics.inc("gap03_latency_samples_total", disposition=d if isinstance(d, str) else "error")
        return d

    def _ingest(self, producer: str, sample: dict) -> str:
        src, dst = sample.get("src"), sample.get("dst")
        if producer.rsplit("/", 1)[-1] != src:
            raise SchedulerError("PERMISSION_DENIED", "producer does not own the source endpoint")
        sid = str(sample.get("sample_id", ""))
        if not sid or sid in self.seen:
            return "duplicate"
        v = sample.get("rtt_us")
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or v > MAX_US:
            raise SchedulerError("INVALID_ARGUMENT", "latency out of bounds")
        ts = float(sample.get("ts", 0))
        now = self.clock()
        if ts > now + FUTURE_SKEW_S:
            raise SchedulerError("INVALID_ARGUMENT", "sample from the future")
        if now - ts > TTL_S:
            return "stale"
        self.seen[sid] = None
        if len(self.seen) > 4 * MAX_PAIRS:
            self.seen.popitem(last=False)
        key = (src, dst)
        st = self.pairs.get(key)
        if st is None:
            st = self.pairs[key] = {"ewma": float(v), "n": 0, "raw": deque(maxlen=RAW_KEEP), "last": ts, "suspect": 0,
                                    "suspects": []}
            if len(self.pairs) > MAX_PAIRS:
                self.pairs.popitem(last=False)
        self.pairs.move_to_end(key)
        if st["n"] >= MIN_SAMPLES:
            med = statistics.median(x for _, x in st["raw"])
            if v > OUTLIER_X * med or v < med / OUTLIER_X:
                st["suspect"] += 1
                st["suspects"].append((ts, float(v)))
                recent = st["suspects"][-PERSIST_TO_ACCEPT:]
                if len(recent) < PERSIST_TO_ACCEPT:
                    return "outlier_held"
                rmed = statistics.median(x for _, x in recent)
                if any(x > OUTLIER_X * rmed or x < rmed / OUTLIER_X for _, x in recent):
                    return "outlier_held"  # deviations are not mutually consistent: noise/attack, not a route
                # persistent, self-consistent shift = genuine route change: new regime replaces the old window
                st["raw"] = deque(recent, maxlen=RAW_KEEP)
                st["ewma"] = rmed
                st["suspect"], st["suspects"], st["n"], st["last"] = 0, [], st["n"] + 1, ts
                return "route_change_accepted"
        st["raw"].append((ts, float(v)))
        st["suspect"], st["suspects"] = 0, []
        target = (1 - ALPHA) * st["ewma"] + ALPHA * v
        target = min(st["ewma"] * MAX_STEP_X, max(st["ewma"] / MAX_STEP_X, target))
        st["ewma"], st["n"], st["last"] = target, st["n"] + 1, max(st["last"], ts)
        return "accepted"

    def refined_cost(self, snapshot, a: str, b: str) -> dict:
        static = snapshot.cost(a, b)
        floor, width = BANDS[static]
        now = self.clock()
        st, direction = self.pairs.get((a, b)), "forward"
        if st is None and (b, a) in self.pairs:
            st, direction = self.pairs[(b, a)], "reverse_assumed"
        if width == 0 or st is None:
            return {"cost_milli": static * 1000, "static": static, "status": "static", "age_s": None, "confidence": 0.0}
        age = now - st["last"]
        conf = min(1.0, st["n"] / (2 * MIN_SAMPLES))
        if age > TTL_S or st["n"] < MIN_SAMPLES:
            return {"cost_milli": static * 1000, "static": static, "status": "stale" if age > TTL_S else "sparse",
                    "age_s": round(age, 1), "confidence": conf}
        lo, hi = BAND_REF_US[static]
        frac = min(1.0, max(0.0, (math.log(max(st["ewma"], 1)) - math.log(lo)) / (math.log(hi) - math.log(lo))))
        milli = floor * 1000 + int(frac * (width * 1000 - 1))  # strictly below next class
        return {"cost_milli": milli, "static": static, "status": "measured", "direction": direction,
                "age_s": round(age, 1), "confidence": round(conf, 2), "ewma_us": round(st["ewma"], 1)}
