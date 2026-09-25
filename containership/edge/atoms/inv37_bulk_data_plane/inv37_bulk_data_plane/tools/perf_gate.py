"""Performance regression gate (C062, C070).  Exit 0 = PASS, 1 = REGRESSION,
2 = BLOCKED (missing inputs).  Never reports PASS when a metric is absent."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def get(d, path):
    for p in path.split("."):
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d


def evaluate(current: dict, baseline: dict | None, thresholds: dict) -> dict:
    findings = []
    for path, rule in thresholds["absolute"].items():
        v = get(current, path)
        if v is None:
            findings.append({"metric": path, "status": "BLOCKED", "reason": "missing"})
        elif ("max" in rule and v > rule["max"]) or ("eq" in rule and v != rule["eq"]):
            findings.append({"metric": path, "status": "REGRESSION", "value": v, "rule": rule})
        else:
            findings.append({"metric": path, "status": "PASS", "value": v})
    for path, rule in thresholds["relative_to_baseline"].items():
        v, b = get(current, path), get(baseline or {}, path)
        if v is None or b in (None, 0):
            findings.append({"metric": path, "status": "BLOCKED", "reason": "missing current or baseline"})
            continue
        ratio = v / b
        bad = ("min_ratio" in rule and ratio < rule["min_ratio"]) or ("max_ratio" in rule and ratio > rule["max_ratio"])
        findings.append({"metric": path, "status": "REGRESSION" if bad else "PASS", "ratio": round(ratio, 3), "rule": rule})
    st = {f["status"] for f in findings}
    status = "BLOCKED" if "BLOCKED" in st else ("REGRESSION" if "REGRESSION" in st else "PASS")
    return {"schema": "INV37_PERF_GATE/1", "status": status, "findings": findings}


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    cur = json.loads(Path(argv[0]).read_text())
    base_p = Path(argv[1]) if len(argv) > 1 else HERE / "artifacts" / "benchmarks" / "baseline.json"
    base = json.loads(base_p.read_text()) if base_p.exists() else None
    rep = evaluate(cur, base, json.loads((HERE / "PERF_THRESHOLDS.json").read_text()))
    print(json.dumps(rep, indent=1))
    return {"PASS": 0, "REGRESSION": 1, "BLOCKED": 2}[rep["status"]]


if __name__ == "__main__":
    sys.exit(main())
