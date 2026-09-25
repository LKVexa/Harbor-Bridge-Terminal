"""SLO report computed from runtime telemetry (C091)."""
from __future__ import annotations

import json
import pathlib

from .runtime import Runtime

PKG = pathlib.Path(__file__).resolve().parent


def report(rt: Runtime) -> dict:
    th = json.loads((PKG / "conformance" / "PERFORMANCE_THRESHOLDS.json").read_text())
    limit_s = th["slo"]["resolution_latency_s"]
    m = rt.metrics
    samples = [v for (n, _), d in m.hist.items() if n == "inv18_resolution_latency_seconds" for v in d]
    good = sum(1 for v in samples if v <= limit_s)
    created = m.counter("inv18_futures_created_total")
    violations = m.counter("inv18_invariant_violations_total")
    sli_lat = good / len(samples) if samples else 1.0
    budget = 1 - th["slo"]["resolution_latency_objective"]
    burn = ((1 - sli_lat) / budget) if budget else 0.0
    return {
        "schema": "INV18_SLO_REPORT/1", "status_of_objectives": th["status"],
        "at_most_once": {"violations": violations, "denominator_futures": created, "met": violations == 0},
        "no_orphans": {"abandonments": m.counter("inv18_abandonments_total"), "violations": violations, "met": violations == 0},
        "resolution_latency": {"threshold_s": limit_s, "good": good, "total": len(samples), "sli": sli_lat,
                               "objective": th["slo"]["resolution_latency_objective"], "burn_rate": burn,
                               "page": burn >= 14.4, "ticket": burn >= 6.0},
    }
