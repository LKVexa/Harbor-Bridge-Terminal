"""Performance gate (MC-045): absolute ceilings + relative regression vs a same-environment baseline.

    python tools/perf_gate.py release/bench.json [--baseline release/bench_baseline.json] [--out release/perf_gate.json]
Exit 0 PASS, 1 FAIL.  A missing scenario is FAIL (never skipped silently).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get(sc, path):
    name, key = path.split(".", 1)
    return (sc.get(name) or {}).get(key.replace("_min", "").replace("_max", ""))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bench")
    ap.add_argument("--baseline", default=str(ROOT / "release" / "bench_baseline.json"))
    ap.add_argument("--out", default=str(ROOT / "release" / "perf_gate.json"))
    a = ap.parse_args(argv)
    th = json.loads((ROOT / "release" / "perf_thresholds.json").read_text())
    bench = json.loads(Path(a.bench).read_text())
    sc = bench["scenarios"]
    checks = []
    for path, limit in th["absolute"].items():
        v = get(sc, path)
        if v is None:
            ok = "soak." in path and "soak" not in sc  # soak optional only when not requested
            checks.append({"check": path, "value": None, "limit": limit, "result": "NOT_RUN" if ok else "FAIL"})
            continue
        ok = v >= limit if path.endswith("_min") else v <= limit
        checks.append({"check": path, "value": v, "limit": limit, "result": "PASS" if ok else "FAIL"})
    base_p = Path(a.baseline)
    if base_p.exists():
        base = json.loads(base_p.read_text())
        same = base.get("environment", {}).get("machine") == bench["environment"]["machine"] and \
            base.get("environment", {}).get("cpus") == bench["environment"]["cpus"]
        for path in th["regression"]["applies_to"]:
            b, v = get(base["scenarios"], path), get(sc, path)
            if not same or b is None or v is None:
                checks.append({"check": f"regression:{path}", "result": "NOT_RUN", "why": "no same-environment baseline"})
                continue
            higher_is_better = path.endswith("admissions_per_s")
            delta = (b - v) / b if higher_is_better else (v - b) / b
            checks.append({"check": f"regression:{path}", "baseline": b, "value": v, "delta": round(delta, 4),
                           "limit": th["regression"]["relative_max_increase"],
                           "result": "PASS" if delta <= th["regression"]["relative_max_increase"] else "FAIL"})
    else:
        checks.append({"check": "regression", "result": "NOT_RUN", "why": "no baseline file"})
    verdict = "FAIL" if any(c["result"] == "FAIL" for c in checks) else "PASS"
    out = {"schema": "PK_ECP_PERF_GATE/1", "verdict": verdict, "thresholds_status": th["status"],
           "environment": bench["environment"], "checks": checks}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(verdict, sum(c["result"] == "PASS" for c in checks), "pass /", len(checks))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
