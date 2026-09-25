"""MC-23 performance regression gate.

    python ci/performance_gate.py RESULTS.json [--baseline benchmarks/baseline.json] [--tier presubmit|release]

Absolute SLO thresholds and relative regression thresholds are evaluated separately; p95/p99
not means; results carry every metric delta.  Release tier additionally refuses an
unapproved baseline and expired performance waivers.  Exit 0 = PASS."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def get(d, dotted):
    for p in dotted.split("."):
        d = d[p]
    return d


def evaluate(res: dict, base: dict, thr: dict, waivers: list, tier: str, today: dt.date) -> dict:
    checks, fails = [], []
    trials = len(res["decision_latency"].get("p95_trials_ms", []))
    if trials < thr["min_trials"]:
        fails.append(f"only {trials} trials (< {thr['min_trials']})")
    active_waivers = {w["metric"]: w for w in waivers
                      if w.get("kind") == "performance" and dt.date.fromisoformat(w["expires"]) >= today}
    for w in waivers:
        if w.get("kind") == "performance" and dt.date.fromisoformat(w["expires"]) < today:
            fails.append(f"expired performance waiver {w['id']}")
    for metric, rule in thr["absolute"].items():
        v = get(res, metric)
        ok = (v <= rule["max"]) if "max" in rule else (v >= rule["min"])
        checks.append({"kind": "absolute", "metric": metric, "value": v, "limit": rule, "ok": ok})
        if not ok and metric not in active_waivers:
            fails.append(f"absolute {metric}={v}")
    for metric, rule in thr["relative"].items():
        v, b = get(res, metric), get(base["results"], metric)
        if "max_ratio" in rule:
            limit = b * rule["max_ratio"] + rule.get("noise_floor", 0)
            ok = v <= limit
        else:
            limit = b * rule["min_ratio"]
            ok = v >= limit
        checks.append({"kind": "relative", "metric": metric, "value": v, "baseline": b,
                       "delta": v - b, "limit": limit, "ok": ok})
        if not ok and metric not in active_waivers:
            fails.append(f"regression {metric}={v} vs baseline {b}")
    if tier == "release" and base.get("status") != "APPROVED":
        fails.append(f"baseline status {base.get('status')} (release tier needs APPROVED)")
    return {"schema": "PLN05_PERF_GATE/1", "tier": tier, "result": "PASS" if not fails else "FAIL",
            "failures": fails, "checks": checks, "baseline_status": base.get("status"),
            "waivers_applied": sorted(active_waivers)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--baseline", default=str(ROOT / "benchmarks" / "baseline.json"))
    ap.add_argument("--tier", default="presubmit", choices=["presubmit", "release"])
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = json.loads(pathlib.Path(a.results).read_text())
    base = json.loads(pathlib.Path(a.baseline).read_text())
    thr = json.loads((ROOT / "benchmarks" / "thresholds.json").read_text())
    waivers = json.loads((ROOT / "governance" / "waivers.json").read_text())["waivers"]
    out = evaluate(res, base, thr, waivers, a.tier, dt.date.today())
    text = json.dumps(out, indent=1, sort_keys=True)
    if a.out:
        pathlib.Path(a.out).write_text(text)
    print(json.dumps({"result": out["result"], "failures": out["failures"]}))
    return 0 if out["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
