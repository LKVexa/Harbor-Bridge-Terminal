"""Release regression gate (52).

Exit codes: 0 PASS, 1 REGRESSION, 3 INCOMPLETE (baseline missing, host
mismatch, or a benchmark absent) -- INCOMPLETE is never PASS.
Thresholds are PROPOSED (waiver W-004) until an owner approves them.
"""
from __future__ import annotations

import json
import sys

PROPOSED_MAX_RATIO = {"p95_us": 1.5, "p99_us": 2.0}


def compare(baseline: dict, current: dict) -> tuple[int, list[str]]:
    msgs = []
    if baseline.get("host") != current.get("host"):
        return 3, ["host descriptor differs; cross-host comparison refused"]
    base = {r["name"]: r for r in baseline["results"]}
    cur = {r["name"]: r for r in current["results"]}
    missing = sorted(set(base) - set(cur))
    if missing:
        return 3, [f"benchmark missing from current run: {m}" for m in missing]
    rc = 0
    for name, b in sorted(base.items()):
        for metric, lim in PROPOSED_MAX_RATIO.items():
            ratio = cur[name][metric] / max(b[metric], 1e-9)
            flag = "REGRESSION" if ratio > lim else "ok"
            if ratio > lim:
                rc = 1
            msgs.append(f"{flag:10s} {name} {metric} x{ratio:.2f} (limit x{lim}, PROPOSED)")
    return rc, msgs


if __name__ == "__main__":
    with open(sys.argv[1]) as a, open(sys.argv[2]) as b:
        rc, msgs = compare(json.load(a), json.load(b))
    print("\n".join(msgs))
    sys.exit(rc)
