"""C070: performance regression gate. Compares benchmarks/results/latest.json with
benchmarks/baseline.json; fails when p99 handoff, throughput, startup or bytes/element
regress beyond tolerance (default 25%, env INV17_PERF_TOLERANCE). A baseline recorded on a
different machine/interpreter is reported as NOT_COMPARABLE rather than pass/fail."""
import json, os, sys
from _tools_pkg import ROOT

TOL = float(os.environ.get("INV17_PERF_TOLERANCE", "0.25"))


def main(argv):
    latest = json.loads((ROOT / "benchmarks" / "results" / "latest.json").read_text())
    base_p = ROOT / "benchmarks" / "baseline.json"
    if "--record-baseline" in argv:
        base_p.write_text(json.dumps(latest, indent=2) + "\n"); print("baseline recorded"); return 0
    base = json.loads(base_p.read_text())
    envkeys = ("python", "implementation", "machine", "system")
    if any(base["environment"][k] != latest["environment"][k] for k in envkeys):
        out = {"verdict": "NOT_COMPARABLE", "reason": "baseline from a different environment"}
    else:
        checks = {
            "handoff_p99": (latest["handoff_ns"]["p99"], base["handoff_ns"]["p99"], "lower"),
            "throughput": (latest["throughput_eps"]["median"], base["throughput_eps"]["median"], "higher"),
            "startup_us": (latest["startup_us"], base["startup_us"], "lower"),
            "bytes_per_element": (latest["memory"]["bytes_per_element"], base["memory"]["bytes_per_element"], "lower"),
        }
        res = {}
        for k, (cur, ref, better) in checks.items():
            ratio = cur / ref if ref else 1.0
            bad = ratio > 1 + TOL if better == "lower" else ratio < 1 - TOL
            res[k] = {"current": cur, "baseline": ref, "ratio": round(ratio, 3), "regressed": bad}
        out = {"verdict": "FAIL" if any(v["regressed"] for v in res.values()) else "PASS", "tolerance": TOL, "checks": res}
    (ROOT / "benchmarks" / "results" / "perf-gate.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=1))
    return 1 if out["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
