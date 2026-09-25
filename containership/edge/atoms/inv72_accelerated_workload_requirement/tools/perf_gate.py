"""Performance release gate (C062, C070).

    python -m inv72_accelerated_workload_requirement.tools.perf_gate [--results evidence/PERF_RESULTS.json]
        [--baseline evidence/PERF_BASELINE.json]

PASS requires: non-quick results; every threshold in ops/PERF_THRESHOLDS.json met; no scenario regressed
more than ``regression_budget_pct`` against an approved baseline measured on the same host fingerprint.
Thresholds with status PROPOSED can produce at most ``PASS_UNDER_PROPOSED_THRESHOLDS``, which the release
gate does not accept as PASS.  Writes evidence/PERF_GATE.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def evaluate(results: dict, th: dict, baseline: dict | None = None) -> dict:
    fails, rows = [], []
    sc = results.get("scenarios", {})
    for name, rule in th["thresholds"].items():
        got = sc.get(name)
        if got is None:
            fails.append(f"{name}: scenario missing")
            continue
        for k, limit in rule.items():
            if k.startswith("min_"):
                key = k[4:]
                v = got.get(key)
                ok = v is not None and v >= limit
            elif k.startswith("max_"):
                key = k[4:]
                v = got.get(key)
                ok = v is not None and v <= limit
            else:
                v = got.get(k)
                ok = v is not None and v <= limit
            rows.append({"scenario": name, "metric": k, "value": v, "limit": limit, "pass": ok})
            if not ok:
                fails.append(f"{name}.{k}={v} vs {limit}")
    if baseline:
        if baseline.get("host") != results.get("host"):
            fails.append("baseline host fingerprint differs; regression comparison invalid")
        else:
            budget = 1 + th.get("regression_budget_pct", 20) / 100
            for name, b in baseline.get("scenarios", {}).items():
                v = sc.get(name, {}).get("p99_us")
                if v and b.get("p99_us") and v > b["p99_us"] * budget:
                    fails.append(f"{name}.p99_us regressed {v} > {b['p99_us']} x {budget}")
    if results.get("quick"):
        fails.append("results are quick-mode (indicative only)")
    verdict = "FAIL" if fails else ("PASS" if th.get("status") == "APPROVED" and th.get("approver")
                                    else "PASS_UNDER_PROPOSED_THRESHOLDS")
    return {"schema": "PK_ACCEL_PERF_GATE/1", "verdict": verdict, "failures": fails, "rows": rows,
            "thresholds_status": th.get("status"), "baseline_used": bool(baseline), "quick": results.get("quick")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "evidence" / "PERF_RESULTS.json"))
    ap.add_argument("--baseline")
    a = ap.parse_args(argv)
    res = json.loads(Path(a.results).read_text())
    th = json.loads((ROOT / "ops" / "PERF_THRESHOLDS.json").read_text())
    base = json.loads(Path(a.baseline).read_text()) if a.baseline else None
    out = evaluate(res, th, base)
    (ROOT / "evidence" / "PERF_GATE.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("PERF", out["verdict"])
    for f in out["failures"]:
        print("FAIL", f)
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
