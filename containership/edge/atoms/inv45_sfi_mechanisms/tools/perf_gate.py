"""Machine-enforced performance release gate (C070).

    python tools/perf_gate.py RESULT.json [--thresholds benchmarks/thresholds.json]

Verdict per threshold: PASS / FAIL / NOT_RUN.  Overall:

* ``FAIL``      any threshold failed (exit 1);
* ``INCOMPLETE`` a required metric was not measured (exit 3) - never PASS;
* ``PASS_UNDER_PROPOSED_THRESHOLDS`` everything passed but the threshold file is not
  approved (exit 0 for CI, but release certification treats it as NOT approved);
* ``PASS`` only when every threshold passed AND thresholds.status == "APPROVED".
Regression: each listed metric must stay <= baseline * tolerance_ratio.
"""
from __future__ import annotations

import json
import operator
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = {"<=": operator.le, ">=": operator.ge, "==": operator.eq, "<": operator.lt}


def get(d, path):
    for part in path.split("."):
        if not isinstance(d, dict) or part not in d:
            return None
        d = d[part]
    return d


def evaluate(result: dict, th: dict, baseline: dict | None) -> dict:
    rows = []
    for t in th["absolute"]:
        v = get(result, t["metric"])
        verdict = "NOT_RUN" if v is None else ("PASS" if OPS[t["op"]](v, t["value"]) else "FAIL")
        rows.append({**t, "observed": v, "verdict": verdict})
    if baseline is not None:
        tol = th["regression"]["tolerance_ratio"]
        for m in th["regression"]["metrics"]:
            v, b = get(result, m), get(baseline, m)
            verdict = "NOT_RUN" if v is None or b is None else ("PASS" if v <= b * tol else "FAIL")
            rows.append({"id": f"REG:{m}", "metric": m, "op": "<=", "value": None if b is None else b * tol,
                         "observed": v, "verdict": verdict, "kind": "regression"})
    verdicts = {r["verdict"] for r in rows}
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "NOT_RUN" in verdicts:
        overall = "INCOMPLETE"
    elif th.get("status") != "APPROVED":
        overall = "PASS_UNDER_PROPOSED_THRESHOLDS"
    else:
        overall = "PASS"
    return {"schema": "PK_SFI_PERF_GATE/1", "overall": overall, "thresholds_status": th.get("status"), "rows": rows}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    th_path = ROOT / "benchmarks" / "thresholds.json"
    if "--thresholds" in sys.argv:
        th_path = Path(sys.argv[sys.argv.index("--thresholds") + 1])
        args = [a for a in args if a != str(th_path)]
    result = json.loads(Path(args[0]).read_text())
    th = json.loads(th_path.read_text())
    bpath = ROOT / th["regression"]["baseline"]
    baseline = json.loads(bpath.read_text()) if bpath.exists() else None
    rep = evaluate(result, th, baseline)
    print(json.dumps(rep, indent=1))
    return {"FAIL": 1, "INCOMPLETE": 3}.get(rep["overall"], 0)


if __name__ == "__main__":
    sys.exit(main())
