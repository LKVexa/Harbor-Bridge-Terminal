"""INV-38-C070 — Performance regression gate (compares candidate to baseline)."""
from __future__ import annotations
from dataclasses import dataclass

# Higher-is-better for throughput; lower-is-better for latency/startup/memory.
LOWER_IS_BETTER = {"p95_us", "p99_us", "p999_us", "max_us", "startup_s", "pinned_mem_mb"}
HIGHER_IS_BETTER = {"throughput_mps"}

@dataclass
class GateResult:
    metric: str
    baseline: float
    candidate: float
    delta_pct: float
    threshold_pct: float
    passed: bool
    reason: str

def compare(metric: str, baseline: float, candidate: float, threshold_pct: float) -> GateResult:
    if baseline == 0:
        raise ValueError("baseline must be non-zero")
    delta = (candidate - baseline) / baseline * 100.0
    if metric in LOWER_IS_BETTER:
        passed = delta <= threshold_pct
    elif metric in HIGHER_IS_BETTER:
        passed = -delta <= threshold_pct
    else:
        raise ValueError(f"unknown metric direction for {metric!r}")
    return GateResult(metric, baseline, candidate, round(delta, 3), threshold_pct, passed,
                      "PK_BYPASS_PERF_OK" if passed else "PK_BYPASS_PERF_REGRESSION")

def gate(baseline: dict, candidate: dict, thresholds: dict) -> tuple[bool, list[GateResult]]:
    results = []
    for metric, base in baseline.items():
        if metric not in candidate:
            results.append(GateResult(metric, base, float("nan"), float("nan"),
                                      thresholds.get(metric, 0), False, "PK_BYPASS_PERF_EVIDENCE_MISSING"))
            continue
        results.append(compare(metric, base, candidate[metric], thresholds.get(metric, 5.0)))
    return all(r.passed for r in results), results
