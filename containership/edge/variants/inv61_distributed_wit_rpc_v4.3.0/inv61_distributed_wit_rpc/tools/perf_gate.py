"""Release performance gate (C062/C070): compare bench results to thresholds.
Exit 1 when any gate fails. Writes evidence/perf_gate.json."""
from __future__ import annotations

import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]


def get(d, path):
    for part in path.split("."):
        d = d[part]
    return d


def evaluate(results: dict, thresholds: dict) -> list[dict]:
    res = dict(results)
    s = res.get("soak", {})
    if s:
        s["rss_growth_mb"] = round(s["rss_end_mb"] - s["rss_start_mb"], 1)
    out = []
    for g in thresholds["gates"]:
        v = get(res, g["metric"])
        ok = (("max" not in g or v <= g["max"]) and ("min" not in g or v >= g["min"])
              and ("equals" not in g or v == g["equals"]))
        out.append({**g, "value": v, "pass": ok})
    return out


def main() -> int:
    r = json.loads((PKG / "evidence" / "bench_results.json").read_text())
    t = json.loads((PKG / "bench" / "thresholds.json").read_text())
    rows = evaluate(r, t)
    (PKG / "evidence" / "perf_gate.json").write_text(json.dumps({"gates": rows, "pass": all(x["pass"] for x in rows)}, indent=2) + "\n")
    for x in rows:
        print(f"{'PASS' if x['pass'] else 'FAIL'} {x['id']:<24} {x['metric']} = {x['value']}")
    return 0 if all(x["pass"] for x in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
