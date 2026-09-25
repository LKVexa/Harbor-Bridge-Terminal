"""Spans, metrics, telemetry policy, lineage/topology correlation (C074, C078, C079, C072-support).

Sampling applies to *traces only*.  Audit/transcript/run-event and explain
records are classed ``mandatory_unsampled`` and bypass the sampler entirely.
Every exported record passes a per-type field allowlist and redaction; buffers
are bounded and count overflow instead of growing.  Records carrying a tenant
residency label are routed only to exporters whose zone matches.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
import bisect
import hashlib
import json
import random
import threading
import time

from .context import TraceContext
from .redaction import redact

TELEMETRY_POLICY: Mapping[str, Any] = {
    "schema": "PK_AGENT_TELEMETRY_POLICY/1",
    "version": "PK_AGENT_TELEMETRY_POLICY/1.0.0",
    "types": {
        "metric": {"sensitivity": "low", "retention_days": 395, "sampling": "none (aggregated)", "access": "operator",
                   "allowed_fields": ["name", "labels", "value", "kind", "at"]},
        "trace": {"sensitivity": "medium", "retention_days": 14, "sampling": "head-based, config telemetry.trace_sample_rate",
                  "access": "operator", "allowed_fields": ["trace_id", "span_id", "parent_span_id", "links", "name",
                                                           "start", "end", "attributes", "status"]},
        "log": {"sensitivity": "medium", "retention_days": 30, "sampling": "none; rate-limited", "access": "operator",
                "allowed_fields": ["level", "code", "message", "correlation_id", "at", "lineage"]},
        "audit": {"sensitivity": "high", "retention_days": 2555, "sampling": "mandatory_unsampled",
                  "access": "security+auditor", "allowed_fields": None},  # full record; already secret-free by design
        "explain": {"sensitivity": "high", "retention_days": 400, "sampling": "mandatory_unsampled",
                    "access": "tenant-operator", "allowed_fields": None},
    },
    "encryption": "in transit TLS1.3 / at rest AES-256 (delegated to exporter backend; INV-47 external)",
    "residency": "records labelled with residency.zone are exported only to exporters in the same zone",
    "deletion": "local buffers are memory-only and cleared on flush/rotation; retention hold is enforced by the backend",
    "span_attribute_allowlist": ["run_id", "tool", "tool_class", "code", "policy_version", "sandbox", "dependency",
                                 "attempt", "tenant", "config_digest", "release_id", "site", "outcome", "profile"],
}
MANDATORY_UNSAMPLED = frozenset(t for t, s in TELEMETRY_POLICY["types"].items() if s["sampling"] == "mandatory_unsampled")
UNKNOWN = "unknown"


@dataclass(frozen=True)
class Lineage:
    """Release lineage + infrastructure-graph identifiers (C078). Missing values are 'unknown', never dropped."""
    app_version: str = UNKNOWN
    release_id: str = UNKNOWN
    artifact_digest: str = UNKNOWN
    config_generation: str = UNKNOWN
    node: str = UNKNOWN
    site: str = UNKNOWN
    cluster: str = UNKNOWN
    provider: str = UNKNOWN
    topology_snapshot: str = UNKNOWN
    topology_snapshot_at: float | None = None

    def as_labels(self) -> dict[str, Any]:
        return dict(self.__dict__)


class TopologyAdapter:
    """Versioned snapshot adapter over the authoritative infrastructure graph (read-only).

    The adapter never invents topology: a missing/stale snapshot yields 'unknown'
    with the staleness recorded."""

    def __init__(self, snapshot: Mapping[str, Any] | None = None, *, max_age_s: float = 3600, clock=time.time):
        self._snap, self.max_age_s, self._clock = snapshot, max_age_s, clock

    def update(self, snapshot: Mapping[str, Any]) -> None:
        for k in ("version", "taken_at", "nodes"):
            if k not in snapshot:
                raise ValueError(f"topology snapshot missing {k}")
        self._snap = snapshot

    def lineage(self, node: str, *, release: Mapping[str, str] | None = None) -> Lineage:
        release = release or {}
        base = dict(app_version=release.get("app_version", UNKNOWN), release_id=release.get("release_id", UNKNOWN),
                    artifact_digest=release.get("artifact_digest", UNKNOWN),
                    config_generation=str(release.get("config_generation", UNKNOWN)), node=node or UNKNOWN)
        s = self._snap
        if not s or self._clock() - float(s["taken_at"]) > self.max_age_s:
            return Lineage(**base, topology_snapshot=(f"stale:{s['version']}" if s else UNKNOWN),
                           topology_snapshot_at=(float(s["taken_at"]) if s else None))
        n = s["nodes"].get(node, {})
        return Lineage(**base, site=n.get("site", UNKNOWN), cluster=n.get("cluster", UNKNOWN),
                       provider=n.get("provider", UNKNOWN), topology_snapshot=str(s["version"]),
                       topology_snapshot_at=float(s["taken_at"]))


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start: float
    links: tuple[str, ...] = ()
    attributes: dict[str, Any] = field(default_factory=dict)
    end: float | None = None
    status: str = "unset"


class Histogram:
    def __init__(self, bounds=(0.00005, 0.0001, 0.00025, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5)):
        self.bounds = list(bounds)
        self.counts = [0] * (len(bounds) + 1)
        self.n = 0
        self.total = 0.0

    def observe(self, v: float) -> None:
        self.counts[bisect.bisect_left(self.bounds, v)] += 1
        self.n += 1
        self.total += v


class Telemetry:
    def __init__(self, *, sample_rate: float = 0.1, buffer_limit: int = 10_000, zone: str = "unassigned",
                 rng: random.Random | None = None, clock=time.time):
        self.sample_rate = sample_rate
        self.buffer_limit = buffer_limit
        self.zone = zone
        self._rng = rng or random.Random()
        self._clock = clock
        self._lock = threading.Lock()
        self.buffers: dict[str, list[dict]] = {t: [] for t in TELEMETRY_POLICY["types"]}
        self.overflow: dict[str, int] = {t: 0 for t in TELEMETRY_POLICY["types"]}
        self.counters: dict[tuple[str, tuple], int] = {}
        self.histograms: dict[tuple[str, tuple], Histogram] = {}
        self.exporters: list[tuple[str, Callable[[str, dict], None]]] = []

    # ---- metrics
    def inc(self, name: str, n: int = 1, **labels) -> None:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        with self._lock:
            self.counters[key] = self.counters.get(key, 0) + n

    def observe(self, name: str, value: float, **labels) -> None:
        key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
        with self._lock:
            self.histograms.setdefault(key, Histogram()).observe(value)

    def counter(self, name: str, **labels) -> int:
        if labels:
            return self.counters.get((name, tuple(sorted((k, str(v)) for k, v in labels.items()))), 0)
        return sum(v for (n, _), v in self.counters.items() if n == name)

    # ---- traces
    def sampled(self, trace: TraceContext) -> bool:
        # deterministic per-trace decision so all spans of one trace agree
        h = int(hashlib.sha256(trace.trace_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        return trace.sampled and h < self.sample_rate

    def start_span(self, name: str, trace: TraceContext, parent: str | None = None, **attrs) -> Span:
        allowed = set(TELEMETRY_POLICY["span_attribute_allowlist"])
        clean = {k: v for k, v in attrs.items() if k in allowed}
        return Span(trace.trace_id, trace.span_id, parent, name, self._clock(), trace.links, redact(clean))

    def end_span(self, span: Span, status: str = "ok") -> None:
        span.end, span.status = self._clock(), status
        if self.sampled(TraceContext(span.trace_id, span.span_id)):
            self.record("trace", span.__dict__)

    # ---- records
    def record(self, rtype: str, rec: Mapping[str, Any], *, zone: str | None = None) -> None:
        spec = TELEMETRY_POLICY["types"][rtype]
        allowed = spec["allowed_fields"]
        out = redact({k: v for k, v in rec.items() if allowed is None or k in allowed})
        out["_zone"] = zone or self.zone
        with self._lock:
            buf = self.buffers[rtype]
            if len(buf) >= self.buffer_limit:
                if rtype in MANDATORY_UNSAMPLED:
                    # never drop audit silently: signal back-pressure to the caller
                    self.overflow[rtype] += 1
                    raise OverflowError(f"{rtype} buffer full; mandatory records cannot be dropped")
                self.overflow[rtype] += 1
                buf.pop(0)
            buf.append(out)

    def buffer_full(self, rtype: str) -> bool:
        with self._lock:
            return len(self.buffers[rtype]) >= self.buffer_limit

    def drop_exported(self, rtype: str, predicate) -> int:
        """Remove records already persisted by an authoritative sink (e.g. GovernedRuntime.archive)."""
        with self._lock:
            before = len(self.buffers[rtype])
            self.buffers[rtype] = [r for r in self.buffers[rtype] if not predicate(r)]
            return before - len(self.buffers[rtype])

    def add_exporter(self, zone: str, fn: Callable[[str, dict], None]) -> None:
        self.exporters.append((zone, fn))

    def flush(self) -> dict[str, int]:
        sent = {t: 0 for t in self.buffers}
        with self._lock:
            pending = {t: list(b) for t, b in self.buffers.items()}
        for rtype, recs in pending.items():
            delivered = []
            for r in recs:
                targets = [fn for z, fn in self.exporters if z == r["_zone"]]
                if not targets:
                    continue  # residency: no same-zone exporter => stays local
                for fn in targets:
                    fn(rtype, r)
                delivered.append(r)
                sent[rtype] += 1
            with self._lock:
                self.buffers[rtype] = [r for r in self.buffers[rtype] if r not in delivered]
        return sent

    def policy_ids(self) -> dict[str, Any]:
        return {"telemetry_policy": TELEMETRY_POLICY["version"], "trace_sample_rate": self.sample_rate,
                "mandatory_unsampled": sorted(MANDATORY_UNSAMPLED)}

    def metrics_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"counters": [{"name": n, "labels": dict(l), "value": v} for (n, l), v in sorted(self.counters.items())],
                    "histograms": [{"name": n, "labels": dict(l), "n": h.n, "sum": h.total, "bounds": h.bounds,
                                    "counts": h.counts} for (n, l), h in sorted(self.histograms.items())],
                    "overflow": dict(self.overflow)}

    def export_json(self) -> str:
        return json.dumps(self.metrics_snapshot(), sort_keys=True)
