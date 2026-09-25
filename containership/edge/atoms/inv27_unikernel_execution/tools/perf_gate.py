"""Performance regression gate (MC-061, MC-068).  PASS only on non-quick results within every threshold.

    python -B -m inv27_unikernel_execution.tools.perf_gate
"""
from __future__ import annotations

import json
import sys

from ._refs import ROOT, load


def evaluate(results: dict, thresholds: dict) -> dict:
    failures = []
    if results.get("quick"):
        failures.append("quick-mode results are not valid for gating")
    for name, t in thresholds["thresholds"].items():
        got = results["results"].get(name, {}).get("p99_ms")
        if got is None:
            failures.append(f"{name}: not measured")
        elif got > t["p99_ms"]:
            failures.append(f"{name}: p99 {got} ms > {t['p99_ms']} ms")
    if thresholds.get("reference_hardware") is None:
        failures.append("no reference hardware recorded; thresholds PROPOSED (W-PERF)")
    return {"verdict": "PASS" if not failures else "FAIL", "failures": failures, "quick": results.get("quick")}


def main(argv=None) -> int:
    r = evaluate(load("evidence/PERF_RESULTS.json"), load("ops/PERF_THRESHOLDS.json"))
    (ROOT / "evidence" / "PERF_GATE.json").write_text(json.dumps(r, indent=1))
    for f in r["failures"]:
        print("FAIL", f)
    print("PERF_GATE", r["verdict"])
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
