"""Performance-regression release gate (MC-033).

Usage: python tools/perf_gate.py [results.json]   (runs the benchmark if omitted)
Exit 0 = PASS, 1 = FAIL.  Writes conformance/perf_gate_result.json.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]


def _get(d, dotted):
    for part in dotted.split("."):
        d = d[part]
    return d


def evaluate(results: dict, baseline: dict) -> dict:
    checks = []
    for key, rule in baseline["slo_thresholds"].items():
        v = _get(results, key)
        checks.append({"metric": key, "value": v, "rule": rule, "pass": v <= rule["max"], "kind": "slo"})
    for key, rule in baseline["regression_thresholds"].items():
        v = _get(results, key)
        if "min_ratio" in rule:
            ok = v >= rule["baseline"] * rule["min_ratio"]
        else:
            ok = v <= rule["baseline"] * (1 + rule["max_regression_pct"] / 100)
        checks.append({"metric": key, "value": v, "rule": rule, "pass": ok, "kind": "regression"})
    return {"schema": "PLN01_PERF_GATE/1", "baseline_approved": baseline["approved"],
            "status": "PASS" if all(c["pass"] for c in checks) else "FAIL", "checks": checks,
            "environment": results.get("environment")}


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        results = json.loads(pathlib.Path(argv[1]).read_text())
    else:
        out = subprocess.run([sys.executable, str(PKG / "benchmarks" / "benchmark_graph.py")],
                             check=True, capture_output=True, text=True).stdout
        results = json.loads(out)
    baseline = json.loads((PKG / "conformance" / "perf_baseline.json").read_text())
    verdict = evaluate(results, baseline)
    (PKG / "conformance" / "perf_gate_result.json").write_text(json.dumps(verdict, indent=2))
    print(f"perf gate: {verdict['status']} (baseline approved: {verdict['baseline_approved']})")
    return 0 if verdict["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
