"""Component 54 - telemetry governance (``PK_DYN_TELEMETRY_GOV/1``).

* Retention classes: every telemetry kind maps to exactly one class; unknown kinds
  are rejected (default deny).  Durations are PROPOSED, owner UNASSIGNED.
* Sampling: errors/warnings always kept; other events kept iff
  ``int(sha256(trace_id)[:8],16)/2**32 < rate`` - deterministic, so every service
  keeps the same traces.  Aggregation: fixed-window mean/max/count rollups.
* Minimization: per-kind field allow-list; tenant ids pseudonymised with a keyed
  HMAC (salt supplied by caller), all remaining strings pass ``core.redact``.
* Egress/residency: destination rules state region + allowed classes; export
  outside the data's residency region or of a non-allowed class is refused.
* Cardinality: per-metric/label distinct counts vs thresholds, with a series-cost estimate.
"""
from __future__ import annotations

import hashlib
import hmac
from collections import defaultdict

from .core import Inv08Error, redact

SCHEMA = "PK_DYN_TELEMETRY_GOV/1"
RETENTION_CLASSES = {  # days; PROPOSED, owner UNASSIGNED
    "debug": 3, "operational": 30, "metrics_raw": 15, "metrics_rollup": 395,
    "trace": 7, "decision": 90, "security_audit": 400,
}
KIND_CLASS = {
    "log.debug": "debug", "log.info": "operational", "log.warning": "operational",
    "log.error": "operational", "log.critical": "security_audit", "metric": "metrics_raw",
    "metric.rollup": "metrics_rollup", "span": "trace", "decision": "decision", "audit": "security_audit",
}
FIELD_ALLOWLIST = {
    "log": {"schema", "seq", "ts", "level", "event", "msg", "service", "corr", "trace", "prev", "hash"},
    "decision": {"schema", "id", "seq", "ts", "inputs", "policy", "result", "error", "graph"},
    "span": {"trace_id", "span_id", "parent_span_id", "name", "start", "end", "status"},
}
DEFAULT_THRESHOLDS = {"per_label_values": 100, "per_metric_series": 1000}
BYTES_PER_SERIES = 3 * 1024  # PROPOSED cost model input


def _err(name: str, msg: str) -> Inv08Error:
    return Inv08Error(f"INV08.TELEMETRY.{name}", msg)


def retention_class(kind: str) -> tuple[str, int]:
    if kind not in KIND_CLASS:
        raise _err("UNCLASSIFIED", f"telemetry kind {kind!r} has no retention class")
    c = KIND_CLASS[kind]
    return c, RETENTION_CLASSES[c]


def expired(kind: str, age_days: float, legal_hold: bool = False) -> bool:
    return not legal_hold and age_days > retention_class(kind)[1]


def keep_sample(trace_id: str, level: str, rate: float) -> bool:
    if not 0.0 <= rate <= 1.0:
        raise _err("BAD_RATE", str(rate))
    if level in ("warning", "error", "critical"):
        return True
    h = int(hashlib.sha256(trace_id.encode()).hexdigest()[:8], 16)
    return h / 2 ** 32 < rate


def rollup(points: list[tuple[float, float]], window: float) -> list[dict]:
    if window <= 0:
        raise _err("BAD_WINDOW", str(window))
    buckets: dict[int, list[float]] = defaultdict(list)
    for t, v in points:
        buckets[int(t // window)].append(v)
    return [{"start": k * window, "count": len(v), "mean": sum(v) / len(v), "max": max(v)}
            for k, v in sorted(buckets.items())]


def pseudonymise(value: str, salt: bytes) -> str:
    if len(salt) < 16:
        raise _err("WEAK_SALT", "pseudonymisation salt must be >= 16 bytes")
    return "p-" + hmac.new(salt, value.encode(), hashlib.sha256).hexdigest()[:20]


def minimize(kind: str, record: dict, salt: bytes) -> dict:
    allow = FIELD_ALLOWLIST.get(kind)
    if allow is None:
        raise _err("UNCLASSIFIED", kind)
    out = {k: v for k, v in record.items() if k in allow}
    corr = out.get("corr")
    if isinstance(corr, dict) and corr.get("tenant"):
        out["corr"] = dict(corr, tenant=pseudonymise(str(corr["tenant"]), salt))
    return redact(out)


EGRESS_RULES = {  # destination -> rule; regions are placeholders pending residency decision (UNASSIGNED)
    "local-store": {"region": "any", "classes": set(RETENTION_CLASSES), "minimized": False},
    "central-observability": {"region": "same", "classes": {"operational", "metrics_raw", "metrics_rollup", "trace"},
                              "minimized": True},
    "vendor-support": {"region": "same", "classes": {"metrics_rollup"}, "minimized": True},
}


def check_egress(dest: str, klass: str, data_region: str, dest_region: str, minimized: bool) -> None:
    rule = EGRESS_RULES.get(dest)
    if rule is None:
        raise _err("EGRESS_DENIED", f"unknown destination {dest!r}")
    if klass not in rule["classes"]:
        raise _err("EGRESS_DENIED", f"class {klass} may not go to {dest}")
    if rule["region"] == "same" and data_region != dest_region:
        raise _err("RESIDENCY", f"{data_region} data may not leave to {dest_region}")
    if rule["minimized"] and not minimized:
        raise _err("EGRESS_DENIED", f"{dest} requires minimized data")


def detect_high_cardinality(series: list[tuple[str, dict]], thresholds: dict | None = None) -> list[dict]:
    th = dict(DEFAULT_THRESHOLDS, **(thresholds or {}))
    per_metric: dict[str, set] = defaultdict(set)
    per_label: dict[tuple, set] = defaultdict(set)
    for name, labels in series:
        per_metric[name].add(tuple(sorted(labels.items())))
        for k, v in labels.items():
            per_label[(name, k)].add(v)
    findings = []
    for (name, k), vals in sorted(per_label.items()):
        if len(vals) > th["per_label_values"]:
            findings.append({"metric": name, "label": k, "distinct": len(vals), "action": "drop_or_bucket_label"})
    for name, s in sorted(per_metric.items()):
        if len(s) > th["per_metric_series"]:
            findings.append({"metric": name, "label": None, "distinct": len(s), "action": "cap_series",
                             "est_bytes": len(s) * BYTES_PER_SERIES})
    return findings
