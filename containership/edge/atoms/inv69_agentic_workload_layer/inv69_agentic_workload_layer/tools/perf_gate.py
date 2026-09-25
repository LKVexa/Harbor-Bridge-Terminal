"""Performance release gate (C062, C070).

    python -m inv69_agentic_workload_layer.tools.perf_gate --results evidence/PERF_RESULTS.json
        [--baseline evidence/PERF_BASELINE.json] [--approve-baseline --approver NAME]

Fails when an absolute PROPOSED threshold is exceeded or a metric regresses beyond tolerance vs the approved
baseline.  A failing candidate can never overwrite the baseline; --approve-baseline requires a passing
candidate and a named human approver.  Writes evidence/PERF_GATE.json (report for reviewers).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = re.compile(r"(?i)\b(bot|ci|service|automation|pipeline|claude)\b")


def get(d, path):
    for k in path.split("."):
        d = d[k]
    return d


def evaluate(results: dict, thresholds: dict, baseline: dict | None) -> dict:
    fails, rows = [], []
    for metric, rule in thresholds["absolute"].items():
        try:
            v = get(results, metric)
        except (KeyError, TypeError):
            fails.append(f"{metric}: missing from results")
            continue
        ok = True
        if "max" in rule:
            ok = v <= rule["max"]
        if "min" in rule:
            ok = ok and v >= rule["min"]
        if "eq" in rule:
            ok = ok and v == rule["eq"]
        if "startswith" in rule:
            ok = ok and str(v).startswith(rule["startswith"])
        rows.append({"metric": metric, "value": v, "rule": rule, "pass": ok})
        if not ok:
            fails.append(f"{metric}={v} violates {rule}")
    if baseline:
        if baseline["fingerprint"]["machine"] != results["fingerprint"]["machine"] or \
           baseline["fingerprint"]["python"] != results["fingerprint"]["python"]:
            fails.append("baseline environment fingerprint differs; comparison invalid")
        reg = thresholds["regression"]
        for metric in reg["metrics"]:
            b, v = get(baseline, metric), get(results, metric)
            hib = reg["direction"].get(metric) == "higher_is_better"
            ratio = (b / v if v else float("inf")) if hib else (v / b if b else float("inf"))
            ok = ratio <= reg["tolerance_ratio"]
            rows.append({"metric": metric, "baseline": b, "value": v, "regression_ratio": round(ratio, 3), "pass": ok})
            if not ok:
                fails.append(f"{metric} regressed x{ratio:.2f} vs baseline (tolerance {reg['tolerance_ratio']})")
    if results["fingerprint"].get("optimized_mode") is None:
        fails.append("results lack environment fingerprint")
    return {"schema": "PK_PERF_GATE/1", "verdict": "PASS" if not fails else "FAIL", "failures": fails, "rows": rows,
            "thresholds_status": thresholds.get("status"), "baseline_used": bool(baseline), "at": time.time()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "evidence" / "PERF_RESULTS.json"))
    ap.add_argument("--baseline", default=str(ROOT / "evidence" / "PERF_BASELINE.json"))
    ap.add_argument("--approve-baseline", action="store_true")
    ap.add_argument("--approver")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "PERF_GATE.json"))
    a = ap.parse_args(argv)
    results = json.loads(Path(a.results).read_text())
    thresholds = json.loads((ROOT / "ops" / "PERF_THRESHOLDS.json").read_text())
    bpath = Path(a.baseline)
    baseline = json.loads(bpath.read_text()) if bpath.exists() else None
    rep = evaluate(results, thresholds, baseline)
    Path(a.out).write_text(json.dumps(rep, indent=2))
    for f in rep["failures"]:
        print("FAIL", f)
    print("PERF_GATE", rep["verdict"])
    if a.approve_baseline:
        if rep["verdict"] != "PASS":
            print("refusing: a failing candidate cannot become the baseline")
            return 2
        if not a.approver or SERVICE.search(a.approver):
            print("refusing: --approver must name a human")
            return 2
        bpath.write_text(json.dumps(dict(results, approved_by=a.approver, approved_at=time.time()), indent=2))
        print("baseline approved by", a.approver)
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
