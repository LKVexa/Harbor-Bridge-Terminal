"""MC-019 - Metrics exporter (Prometheus text exposition 0.0.4, stdlib).

Versioned catalog with type/unit/labels/cardinality budget/owner.  Label sets
beyond budget collapse into ``__overflow__`` and increment a drop counter;
tenant/node/workload IDs are not permitted as labels.  Recording never
blocks: updates are O(1) under a short lock; export is a read.
"""
from __future__ import annotations

import threading

CATALOG_VERSION = "gap03-metrics/1"
BUCKETS_MS = (0.5, 1, 2, 5, 10, 20, 50, 100, 250, 500, 1000, 5000)
FORBIDDEN_LABELS = {"tenant", "node", "workload", "txn", "request_id", "dataset"}
CATALOG = {
    "gap03_score_latency_ms": ("histogram", "ms", ("result",), 8, "scoring", "scoring request latency"),
    "gap03_commit_latency_ms": ("histogram", "ms", ("result",), 8, "txn", "placement commit latency"),
    "gap03_requests_total": ("counter", "1", ("op", "code"), 64, "scheduler", "requests by outcome code"),
    "gap03_candidate_set_size": ("histogram", "candidates", (), 1, "scoring", "candidate set size"),
    "gap03_feasible_candidates": ("histogram", "candidates", (), 1, "scoring", "feasible candidate count"),
    "gap03_chosen_locality_cost": ("histogram", "cost_units", ("tenant_class",), 8, "scoring", "chosen-candidate locality cost"),
    "gap03_fairness_denials_total": ("counter", "1", ("reason",), 8, "fairshare", "fair-share denials"),
    "gap03_starved_tenants": ("gauge", "tenants", (), 1, "fairshare", "tenants below reservation"),
    "gap03_reservation_utilization_ratio": ("gauge", "ratio", (), 1, "fairshare", "used/capacity"),
    "gap03_spread_failures_total": ("counter", "1", (), 1, "scoring", "unsatisfiable anti-affinity"),
    "gap03_stale_rejections_total": ("counter", "1", ("kind",), 8, "state", "stale score/generation rejections"),
    "gap03_placement_txn_total": ("counter", "1", ("outcome",), 8, "txn", "transactions by terminal state"),
    "gap03_idempotent_replays_total": ("counter", "1", (), 1, "txn", "replayed requests"),
    "gap03_orphaned_reservations": ("gauge", "claims", (), 1, "ledger", "expired pending claims"),
    "gap03_dependency_up": ("gauge", "bool", ("dependency",), 16, "degraded", "dependency availability"),
    "gap03_breaker_state": ("gauge", "enum", ("dependency",), 16, "admission", "0 closed 1 half 2 open"),
    "gap03_coordination_is_leader": ("gauge", "bool", (), 1, "coordination", "lease held"),
    "gap03_coordination_term": ("gauge", "term", (), 1, "coordination", "current fencing term"),
    "gap03_cache_events_total": ("counter", "1", ("event",), 8, "cache", "cache hit/miss/evict/stale"),
    "gap03_admission_rejected_total": ("counter", "1", ("reason",), 32, "admission", "admission rejections"),
    "gap03_retry_attempts_total": ("counter", "1", ("dependency", "code"), 128, "retry", "retry attempts"),
    "gap03_retry_budget_exhausted_total": ("counter", "1", ("dependency",), 16, "retry", "retry budget exhaustion"),
    "gap03_topology_mutations_total": ("counter", "1", ("result",), 32, "topology", "topology mutation results"),
    "gap03_control_blocks_total": ("counter", "1", ("mode",), 8, "controls", "requests blocked by controls"),
    "gap03_telemetry_dropped_total": ("counter", "1", ("signal",), 4, "telemetry", "dropped telemetry"),
    "gap03_metric_label_overflow_total": ("counter", "1", ("metric",), 64, "telemetry", "label budget overflow"),
    "gap03_audit_write_failures_total": ("counter", "1", (), 1, "audit", "audit write failures"),
    "gap03_reconciliation_drift_total": ("counter", "1", ("kind",), 16, "reconcile", "drift events"),
    "gap03_store_write_latency_ms": ("histogram", "ms", ("store",), 16, "state", "durable write (append+fsync) latency"),
    "gap03_dependency_latency_ms": ("histogram", "ms", ("dependency",), 16, "degraded", "dependency call latency through breakers"),
    "gap03_admission_utilization_ratio": ("gauge", "ratio", (), 1, "admission", "max(scoring, commit, queue) utilisation"),
    "gap03_cache_build_ms": ("histogram", "ms", (), 1, "cache", "time to build a cache entry"),
    "gap03_cache_entries": ("gauge", "entries", (), 1, "cache", "cache size"),
    "gap03_generation_lag": ("gauge", "generations", ("source",), 8, "state", "adjacent-feed generation lag vs topology"),
    "gap03_active_controls": ("gauge", "controls", ("mode",), 8, "controls", "active freeze/quarantine controls"),
    "gap03_adapter_ingest_total": ("counter", "1", ("adapter", "result"), 64, "adapters", "adjacent-feed ingest outcomes"),
    "gap03_latency_samples_total": ("counter", "1", ("disposition",), 16, "latency", "latency sample dispositions"),
    "gap03_health_probe_total": ("counter", "1", ("probe", "status"), 16, "health", "health probe results"),
    "gap03_trust_verifications_total": ("counter", "1", ("result",), 16, "identity", "credential verification results"),
    "gap03_config_activations_total": ("counter", "1", ("kind",), 4, "config", "config activations/rollbacks"),
    "gap03_explain_queries_total": ("counter", "1", ("result",), 8, "explain", "explain queries"),
}


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.values: dict[tuple, float] = {}
        self.hist: dict[tuple, list] = {}
        self.label_sets: dict[str, set] = {}

    def _key(self, name, labels):
        if name not in CATALOG:
            raise KeyError(f"metric {name} not in catalog")
        typ, _, allowed, budget, _, _ = CATALOG[name]
        bad = set(labels) - set(allowed)
        if bad or set(labels) & FORBIDDEN_LABELS:
            raise ValueError(f"labels {sorted(bad or set(labels) & FORBIDDEN_LABELS)} not allowed on {name}")
        lk = tuple(sorted((k, str(v)[:64]) for k, v in labels.items()))
        seen = self.label_sets.setdefault(name, set())
        if lk not in seen:
            if len(seen) >= budget:
                ov = ("metric", name)
                self.values[("gap03_metric_label_overflow_total", (ov,))] = self.values.get(("gap03_metric_label_overflow_total", (ov,)), 0) + 1
                lk = (("__overflow__", "1"),)
            seen.add(lk)
        return (name, lk), typ

    def inc(self, name, v: float = 1.0, **labels):
        with self._lock:
            k, typ = self._key(name, labels)
            if typ != "counter":
                raise TypeError(name)
            self.values[k] = self.values.get(k, 0) + v

    def set(self, name, v: float, **labels):
        with self._lock:
            k, typ = self._key(name, labels)
            if typ != "gauge":
                raise TypeError(name)
            self.values[k] = v

    def observe(self, name, v: float, **labels):
        with self._lock:
            k, typ = self._key(name, labels)
            if typ != "histogram":
                raise TypeError(name)
            h = self.hist.setdefault(k, [0] * (len(BUCKETS_MS) + 1) + [0.0, 0])
            for i, b in enumerate(BUCKETS_MS):
                if v <= b:
                    h[i] += 1
            h[len(BUCKETS_MS)] += 1  # +Inf
            h[-2] += v
            h[-1] += 1

    def get(self, name, **labels) -> float:
        return self.values.get((name, tuple(sorted((k, str(v)) for k, v in labels.items()))), 0)

    def export(self) -> str:
        out = []
        with self._lock:
            for name in sorted(CATALOG):
                typ, unit, _, _, owner, help_ = CATALOG[name]
                out.append(f"# HELP {name} {help_} (unit={unit}, owner={owner}, catalog={CATALOG_VERSION})")
                out.append(f"# TYPE {name} {typ}")
                for (n, lk), v in sorted(self.values.items()):
                    if n == name:
                        out.append(f"{name}{_fmt(lk)} {v:g}")
                for (n, lk), h in sorted(self.hist.items()):
                    if n == name:
                        for i, b in enumerate(BUCKETS_MS):
                            out.append(f"{name}_bucket{_fmt(lk + (('le', f'{b:g}'),))} {h[i]}")
                        out.append(f"{name}_bucket{_fmt(lk + (('le', '+Inf'),))} {h[len(BUCKETS_MS)]}")
                        out.append(f"{name}_sum{_fmt(lk)} {h[-2]:g}")
                        out.append(f"{name}_count{_fmt(lk)} {h[-1]}")
        return "\n".join(out) + "\n"


def _fmt(lk) -> str:
    if not lk:
        return ""
    esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")  # noqa: E731
    return "{" + ",".join(f'{k}="{esc(v)}"' for k, v in lk) + "}"


RECORDING_RULES = [
    {"record": "gap03:commit_success_ratio:5m",
     "expr": 'sum(rate(gap03_placement_txn_total{outcome="COMMITTED"}[5m])) / sum(rate(gap03_placement_txn_total[5m]))'},
    {"record": "gap03:score_p99_ms:5m",
     "expr": "histogram_quantile(0.99, sum by (le) (rate(gap03_score_latency_ms_bucket[5m])))"},
    {"record": "gap03:overload_ratio:5m",
     "expr": 'sum(rate(gap03_requests_total{code="OVERLOADED"}[5m])) / sum(rate(gap03_requests_total[5m]))'},
    {"record": "gap03:fairness_violations:5m", "expr": 'sum(rate(gap03_requests_total{code="INTEGRITY_FAILURE"}[5m]))'},
]
