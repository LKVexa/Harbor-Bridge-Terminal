"""MC-066..MC-070/072/074 — reproducible benchmark harness + regression gate.

Measures, on this node: baseline fork+exec latency, sandboxed launch latency
(all controls + kernel read-back), per-launch overhead, CPU time and peak RSS
of the host, burst behaviour (N concurrent), and scale (sequential run of M).
Writes evidence/bench-<host>.json.  ``--gate`` compares against docs/NFR.json;
thresholds there are PROPOSED (no owner approval exists), so a met threshold is
reported as ``met_under_proposed_target`` and never as certified.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import resource
import statistics
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
from importlib import import_module  # noqa: E402

L = import_module(HERE.name + ".linux.launcher")
profiles = import_module(HERE.name + ".profiles")


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def summarize(xs):
    return {"n": len(xs), "p50_ms": round(pct(xs, 50) * 1e3, 3), "p95_ms": round(pct(xs, 95) * 1e3, 3),
            "p99_ms": round(pct(xs, 99) * 1e3, 3), "max_ms": round(max(xs) * 1e3, 3),
            "mean_ms": round(statistics.fmean(xs) * 1e3, 3)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--burst", type=int, default=16)
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--out", default=str(HERE / "evidence"))
    a = ap.parse_args(argv)
    prof = profiles.load_profile("posix-minimal")
    spec = L.LaunchSpec(argv=("/bin/true",), syscalls=prof.syscalls)
    for _ in range(10):  # warm-up
        L.launch(spec)
    base = []
    for _ in range(a.n):
        t = time.perf_counter(); subprocess.run(["/bin/true"]); base.append(time.perf_counter() - t)
    r0 = resource.getrusage(resource.RUSAGE_SELF)
    sb = []
    for _ in range(a.n):
        t = time.perf_counter(); L.launch(spec); sb.append(time.perf_counter() - t)
    r1 = resource.getrusage(resource.RUSAGE_SELF)
    burst, errs = [], []

    def one():
        t = time.perf_counter()
        try:
            L.launch(spec); burst.append(time.perf_counter() - t)
        except Exception as e:  # noqa: BLE001
            errs.append(repr(e))
    ts = [threading.Thread(target=one) for _ in range(a.burst)]
    tb = time.perf_counter(); [t.start() for t in ts]; [t.join() for t in ts]; tb = time.perf_counter() - tb
    res = {
        "schema": "INV39_BENCH/1", "host": platform.node(), "kernel": platform.release(), "arch": platform.machine(),
        "python": platform.python_version(), "cpus": os.cpu_count(), "ts": int(time.time()),
        "baseline_fork_exec": summarize(base), "sandboxed_launch": summarize(sb),
        "overhead_p50_ms": round((pct(sb, 50) - pct(base, 50)) * 1e3, 3),
        "host_cpu_s_per_launch": round(((r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime)) / a.n, 6),
        "host_peak_rss_kb": r1.ru_maxrss,
        "burst": {"concurrency": a.burst, "ok": len(burst), "errors": errs[:5], "wall_s": round(tb, 3),
                  **(summarize(burst) if burst else {})},
        "launches_per_s_sequential": round(a.n / sum(sb), 1),
        "not_measured": ["power/thermal (MC-073: needs edge hardware + meter)",
                         "fleet-scale density (MC-091: needs a fleet)", "soak > 1h (MC-091)"],
    }
    out = pathlib.Path(a.out); out.mkdir(exist_ok=True)
    (out / f"bench-{platform.node() or 'host'}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    if a.gate:
        nfr = json.loads((HERE / "docs" / "NFR.json").read_text())
        fails = []
        for key, lim in nfr["release_thresholds"].items():
            metric, stat = key.split(".")
            val = res[metric][stat]
            if val > lim:
                fails.append(f"{key}={val} > {lim}")
        verdict = "REGRESSION" if fails else "met_under_proposed_target"
        print(json.dumps({"gate": verdict, "failures": fails, "threshold_status": nfr["status"]}))
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
