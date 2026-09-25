#!/usr/bin/env python3
"""MC-030 / MC-033 - benchmark, burst, soak, overload harness with regression gate.

    python tools/bench.py                 # quick profile, compare to PERF_THRESHOLDS.json
    python tools/bench.py --soak 60       # add a 60 s soak (open/resolve/close churn)
    python tools/bench.py --tables 256    # fleet-scale: many tables in one process

Exit 3 when any measured percentile exceeds its threshold (release-blocking).
Results -> evidence/bench.json.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import platform
import statistics
import sys
import time
import tracemalloc

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import descriptors as d  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def measure(fn, n):
    lat = []
    for _ in range(n):
        t0 = time.perf_counter_ns()
        fn()
        lat.append(time.perf_counter_ns() - t0)
    return {"n": n, "p50_us": pct(lat, 50) / 1e3, "p95_us": pct(lat, 95) / 1e3, "p99_us": pct(lat, 99) / 1e3,
            "max_us": max(lat) / 1e3, "mean_us": statistics.fmean(lat) / 1e3}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--soak", type=float, default=0.0)
    ap.add_argument("--tables", type=int, default=64)
    args = ap.parse_args()
    res = {"python": platform.python_version(), "machine": platform.machine(), "platform": platform.platform()}
    t = d.DescriptorTable("bench")
    fds = []

    def op_open():
        if len(t._entries) >= d.TABLE_LIMIT - 1:
            for fd in fds:
                t.close(fd)
            fds.clear()
        fds.append(t.open("stream", 0))
    res["open"] = measure(op_open, args.n)
    fd = t.open("stream", 0)
    res["resolve"] = measure(lambda: t.resolve(fd, expect="stream"), args.n)
    wire = fd.to_wire()
    res["import"] = measure(lambda: t.from_wire(wire), args.n)
    res["reject_forged"] = measure(lambda: _swallow(t.from_wire, {**wire, "auth": "0" * 64}), args.n)

    def churn():
        t.close(t.open("stream", 0))
    res["open_close"] = measure(churn, args.n)
    # burst: fill to limit, overload (rejections must stay cheap), drain
    b = d.DescriptorTable("burst")
    t0 = time.perf_counter()
    burst = [b.open("s", 0) for _ in range(d.TABLE_LIMIT)]
    res["burst_fill_ms"] = (time.perf_counter() - t0) * 1e3
    res["overload_reject"] = measure(lambda: _swallow(b.open, "s", 0), 5000)
    for x in burst:
        b.close(x)
    # fleet scale
    tracemalloc.start()
    fleet = [d.DescriptorTable(f"w{i}") for i in range(args.tables)]
    for tb in fleet:
        for _ in range(64):
            tb.open("s", 0)
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    res["fleet"] = {"tables": args.tables, "descriptors": args.tables * 64, "peak_kib": peak / 1024}
    if args.soak:
        end, ops = time.time() + args.soak, 0
        s = d.DescriptorTable("soak")
        while time.time() < end:
            s.close(s.open("s", 0))
            ops += 1
        res["soak"] = {"seconds": args.soak, "ops": ops, "ops_per_s": ops / args.soak, "live_end": s.status()["live"]}
    th = json.loads((PKG / "PERF_THRESHOLDS.json").read_text())
    violations = []
    for op, lim in th["latency_us"].items():
        for k, v in lim.items():
            if res[op][k] > v:
                violations.append(f"{op}.{k}={res[op][k]:.2f}us > {v}us")
    if res["fleet"]["peak_kib"] > th["fleet_peak_kib_per_1k_descriptors"] * res["fleet"]["descriptors"] / 1000:
        violations.append("fleet memory above threshold")
    res["violations"] = violations
    res["passed"] = not violations
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "bench.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({k: res[k] for k in ("open", "resolve", "import", "violations")}, indent=1))
    return 0 if not violations else 3


def _swallow(fn, *a):
    try:
        fn(*a)
    except d.DescriptorError:
        pass


if __name__ == "__main__":
    sys.exit(main())
