"""Signal pipelines: logs (28), metrics (29), traces (30), profiles (31).
Each pipeline is bounded, applies the tenant policy before storing, and
explains every drop."""
from __future__ import annotations

import bisect
import math
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Any

from .controls import DecisionLog
from .errors import Malformed, QuotaExceeded
from .policy import PolicyEngine, deterministic_keep, redact
from .signals import SEVERITIES, Record, Resource

MAX_LOG_BYTES = 16_384


# ------------------------------------------------------------------ logs (28)

class LogPipeline:
    def __init__(self, policy: PolicyEngine, *, capacity: int = 100_000) -> None:
        self.policy = policy
        self.capacity = capacity
        self.records: list[Record] = []
        self._partial: dict[tuple, list[str]] = {}

    def ingest_raw(self, raw: bytes, *, resource: Resource, at: int, severity: str = "INFO",
                   stream: str = "stdout", continuation: bool = False) -> Record | None:
        """Decode (UTF-8 with replacement -- never crash on bad encodings),
        join multiline continuations, redact, sample, bound."""
        if severity not in SEVERITIES:
            raise Malformed("unknown severity")
        text = raw[:MAX_LOG_BYTES].decode("utf-8", errors="replace")
        truncated = len(raw) > MAX_LOG_BYTES
        key = (resource, stream)
        if continuation:
            self._partial.setdefault(key, []).append(text)
            if sum(map(len, self._partial[key])) > MAX_LOG_BYTES:
                text = "\n".join(self._partial.pop(key))[:MAX_LOG_BYTES]
                truncated = True
            else:
                return None
        elif key in self._partial:
            text = "\n".join(self._partial.pop(key) + [text])
        pol = self.policy.for_tenant(resource.tenant)
        text, hits = redact(text, pol.redact_kinds)
        if hits:
            self.policy.decisions.record(decision="redact", reason="secret/PII pattern", rule="LOG-REDACT",
                                         subject={"tenant": resource.tenant}, at=at, kinds=hits)
        if SEVERITIES.index(severity) <= SEVERITIES.index("INFO") and not deterministic_keep(
                f"{resource.tenant}|{at}|{text[:64]}", pol.log_sample_rate):
            self.policy.decisions.record(decision="sample_drop", reason="log sample rate", rule="LOG-SAMPLE",
                                         subject={"tenant": resource.tenant}, at=at)
            return None
        if len(self.records) >= self.capacity:
            raise QuotaExceeded("log pipeline full")
        rec = Record("log", "log." + stream, resource, at, {"severity": severity, "text": text, "truncated": truncated})
        self.records.append(rec)
        return rec

    def flush_partial(self, at: int) -> list[Record]:
        out = []
        for (res, stream), parts in list(self._partial.items()):
            out.append(Record("log", "log." + stream, res, at, {"severity": "INFO", "text": "\n".join(parts), "truncated": False}))
            del self._partial[(res, stream)]
        self.records.extend(out)
        return out


# ------------------------------------------------------------------ metrics (29)

@dataclass
class _Series:
    kind: str
    temporality: str
    last_raw: float | None = None
    cumulative: float = 0.0
    resets: int = 0
    points: list = field(default_factory=list)  # (at, value)
    buckets: tuple = ()
    counts: list = field(default_factory=list)
    hsum: float = 0.0
    hcount: int = 0


class MetricsPipeline:
    """Counters (cumulative or delta, reset detection), gauges, explicit-
    bucket histograms, and step downsampling."""

    def __init__(self, *, max_series: int = 100_000, max_points: int = 10_000) -> None:
        self._s: dict[tuple, _Series] = {}
        self.max_series, self.max_points = max_series, max_points

    def _series(self, key, kind, temporality, buckets=()):
        s = self._s.get(key)
        if s is None:
            if len(self._s) >= self.max_series:
                raise QuotaExceeded("metric series bound")
            s = self._s[key] = _Series(kind, temporality, buckets=tuple(buckets), counts=[0] * (len(buckets) + 1))
        elif (s.kind, s.temporality) != (kind, temporality):
            raise Malformed("series kind/temporality changed")
        return s

    def counter(self, key: tuple, value: float, at: int, *, temporality: str = "cumulative") -> float:
        if temporality not in ("cumulative", "delta"):
            raise Malformed("temporality invalid")
        if not math.isfinite(value) or value < 0:
            raise Malformed("counter values must be finite and non-negative")
        s = self._series(key, "counter", temporality)
        if s.points and at <= s.points[-1][0]:
            raise Malformed("out-of-order counter point")
        if temporality == "delta":
            s.cumulative += value
        else:
            if s.last_raw is not None and value < s.last_raw:
                s.resets += 1              # reset: new raw value counts from zero
                s.cumulative += value
            elif s.last_raw is None:
                s.cumulative = 0.0         # first cumulative point establishes the baseline
            else:
                s.cumulative += value - s.last_raw
            s.last_raw = value
        self._append(s, at, s.cumulative)
        return s.cumulative

    def gauge(self, key: tuple, value: float, at: int) -> None:
        if not math.isfinite(value):
            raise Malformed("gauge value must be finite")
        s = self._series(key, "gauge", "instant")
        self._append(s, at, value)

    def histogram(self, key: tuple, value: float, at: int, *, buckets: tuple) -> None:
        if list(buckets) != sorted(set(buckets)) or not buckets:
            raise Malformed("bucket bounds must be strictly increasing")
        if not math.isfinite(value):
            raise Malformed("histogram value must be finite")
        s = self._series(key, "histogram", "cumulative", buckets)
        if s.buckets != tuple(buckets):
            raise Malformed("bucket layout changed for series")
        s.counts[bisect.bisect_left(s.buckets, value)] += 1
        s.hsum += value
        s.hcount += 1

    def _append(self, s: _Series, at: int, v: float) -> None:
        s.points.append((at, v))
        if len(s.points) > self.max_points:
            del s.points[: len(s.points) - self.max_points]

    def series(self, key: tuple) -> _Series:
        return self._s[key]

    @staticmethod
    def downsample(points: list, step: int, how: str = "last") -> list:
        if step <= 0:
            raise Malformed("step must be positive")
        buckets: "OrderedDict[int, list]" = OrderedDict()
        for at, v in points:
            buckets.setdefault(at - at % step, []).append(v)
        agg = {"last": lambda xs: xs[-1], "max": max, "min": min, "avg": lambda xs: sum(xs) / len(xs)}[how]
        return [(t, agg(xs)) for t, xs in buckets.items()]

    def quantile(self, key: tuple, q: float) -> float | None:
        s = self._s[key]
        if s.hcount == 0:
            return None
        target, run = q * s.hcount, 0
        for i, c in enumerate(s.counts):
            run += c
            if run >= target:
                return s.buckets[i] if i < len(s.buckets) else math.inf
        return math.inf


# ------------------------------------------------------------------ traces (30)

class TracePipeline:
    """Span assembly tolerant of late/out-of-order arrival.

    Spans are buffered per trace until the trace is ``complete`` (root present
    and every parent reference resolved) or ``max_wait`` elapses, at which
    point the trace is emitted with ``incomplete=True`` and orphan span ids --
    it is never silently dropped.  Head sampling is consistent on trace_id.
    Baggage is size-bounded and dropped (with a decision) when oversized.
    """

    MAX_BAGGAGE = 8192

    def __init__(self, policy: PolicyEngine, *, max_wait: int = 30, max_traces: int = 10_000, max_spans: int = 1_000) -> None:
        self.policy, self.max_wait, self.max_traces, self.max_spans = policy, max_wait, max_traces, max_spans
        self._open: dict[str, dict] = {}
        self.emitted: list[dict] = []

    def add_span(self, *, trace_id: str, span_id: str, parent_id: str | None, name: str, resource: Resource,
                 start: int, end: int, arrived: int, links: tuple = (), baggage: str = "") -> bool:
        if end < start:
            raise Malformed("span ends before it starts")
        pol = self.policy.for_tenant(resource.tenant)
        if not deterministic_keep(trace_id, pol.trace_sample_rate):
            return False
        if len(baggage.encode()) > self.MAX_BAGGAGE:
            self.policy.decisions.record(decision="drop_baggage", reason="baggage over budget", rule="TR-BAGGAGE",
                                         subject={"trace_id": trace_id}, at=arrived)
            baggage = ""
        t = self._open.get(trace_id)
        if t is None:
            if len(self._open) >= self.max_traces:
                raise QuotaExceeded("open trace bound")
            t = self._open[trace_id] = {"tenant": resource.tenant, "first_arrival": arrived, "spans": {}}
        if t["tenant"] != resource.tenant:
            raise Malformed("trace id reused across tenants")
        if len(t["spans"]) >= self.max_spans:
            raise QuotaExceeded("spans per trace bound")
        t["spans"][span_id] = {"span_id": span_id, "parent_id": parent_id, "name": name, "start": start,
                               "end": end, "links": list(links), "baggage": baggage, "boundary": resource.boundary}
        return True

    def _complete(self, t) -> bool:
        spans = t["spans"]
        roots = [s for s in spans.values() if s["parent_id"] is None]
        return len(roots) == 1 and all(s["parent_id"] in spans for s in spans.values() if s["parent_id"])

    def sweep(self, now: int) -> list[dict]:
        out = []
        for tid, t in list(self._open.items()):
            done = self._complete(t)
            if done or now - t["first_arrival"] >= self.max_wait:
                spans = t["spans"]
                orphans = sorted(s["span_id"] for s in spans.values() if s["parent_id"] and s["parent_id"] not in spans)
                out.append({"trace_id": tid, "tenant": t["tenant"], "incomplete": not done, "orphans": orphans,
                            "spans": sorted(spans.values(), key=lambda s: (s["start"], s["span_id"]))})
                del self._open[tid]
        self.emitted.extend(out)
        return out


# ------------------------------------------------------------------ profiles (31)

class ProfilePipeline:
    """Folded-stack profiles with a symbolization hook, per-tenant byte
    budget and frame privacy (paths reduced to basenames; frames matching
    secret patterns are dropped)."""

    TYPES = frozenset({"cpu", "alloc", "heap", "lock", "wall"})

    def __init__(self, *, tenant_budget_bytes: int = 8 << 20, symbolizer=None, decisions: DecisionLog | None = None) -> None:
        self.budget = tenant_budget_bytes
        self.used: dict[str, int] = defaultdict(int)
        self.symbolizer = symbolizer or (lambda frame: frame)
        self.decisions = decisions or DecisionLog()
        self.profiles: list[Record] = []

    def ingest(self, *, resource: Resource, at: int, ptype: str, folded: dict[str, int]) -> Record:
        if ptype not in self.TYPES:
            raise Malformed("unknown profile type")
        clean: dict[str, int] = {}
        for stack, count in folded.items():
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise Malformed("sample counts must be non-negative integers")
            frames = []
            for fr in stack.split(";"):
                fr = self.symbolizer(fr)
                fr = fr.replace("\\", "/").rsplit("/", 1)[-1]
                if redact(fr)[1]:
                    self.decisions.record(decision="drop_frame", reason="secret-like frame", rule="PROF-PRIV",
                                          subject={"tenant": resource.tenant}, at=at)
                    fr = "<redacted>"
                frames.append(fr)
            key = ";".join(frames)
            clean[key] = clean.get(key, 0) + count
        size = sum(len(k) + 8 for k in clean)
        if self.used[resource.tenant] + size > self.budget:
            raise QuotaExceeded("tenant profile budget exhausted", tenant=resource.tenant)
        self.used[resource.tenant] += size
        rec = Record("profile", "profile." + ptype, resource, at, {"folded": clean})
        self.profiles.append(rec)
        return rec
