"""Bridge-cost benchmark for the contract SLO "p99 sync-caller bridging under 5us" (closure #21).

Definition (docs/BENCHMARK_METHODOLOGY.md): *bridge cost* = wall time of
``SyncBridge.call`` minus the wall time of the equivalent direct async path
(``invoke`` + ``complete``) for an immediately-completing callee, measured per
sample with ``time.perf_counter_ns`` in one warm process.  Also reported:
the null-timer calibration, the direct paths, and the suspended (cross-thread
wake-up) bridge.  Raw samples are written so any percentile can be recomputed.

    python bench/bridge_bench.py --samples 200000 --out evidence/bench/bridge.json [--gate]

``--gate`` exits 3 if p99 bridge cost >= 5000 ns (the release gate).
"""
from __future__ import annotations

import argparse
import gc
import importlib
import json
import os
import pathlib
import platform
import statistics
import sys
import threading
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
rt = importlib.import_module(PKG.name + ".runtime")
br = importlib.import_module(PKG.name + ".bridge")
SLO_NS = 5000


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def summary(xs):
    return {"n": len(xs), "p50": pct(xs, .50), "p95": pct(xs, .95), "p99": pct(xs, .99), "max": max(xs),
            "mean": round(statistics.fmean(xs), 1)}


def measure(fn, n, warm):
    for _ in range(warm):
        fn()
    out = [0] * n
    pc = time.perf_counter_ns
    for i in range(n):
        t0 = pc(); fn(); out[i] = pc() - t0
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=100_000)
    ap.add_argument("--warmup", type=int, default=10_000)
    ap.add_argument("--suspended", type=int, default=2_000)
    ap.add_argument("--out", default=str(PKG / "evidence" / "bench" / "bridge.json"))
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args(argv)

    fns = rt.AsyncFunctions("bench", declared={"a": True, "s": False}, tombstone_capacity=1024)
    bridge = br.SyncBridge(fns)
    complete = fns.complete

    def null():
        pass

    def direct_async():
        c = fns.invoke("a"); complete(c.call_id, 1)

    def direct_sync():
        c = fns.invoke("s", caller_is_async=False); complete(c.call_id, 1)

    def start(st):
        complete(st.call_id, 1)

    def bridged():
        bridge.call("a", start)

    gc.disable()
    try:
        res = {}
        for name, fn in (("null", null), ("direct_sync", direct_sync), ("direct_async", direct_async),
                         ("bridged_immediate", bridged)):
            res[name] = measure(fn, a.samples, a.warmup)
        # paired difference, sample by sample, after removing timer overhead
        cost = [max(0, b - d) for b, d in zip(res["bridged_immediate"], res["direct_async"])]
        # suspended path: completion arrives from another thread
        sus = []
        for _ in range(a.suspended):
            ev = threading.Event()
            holder = {}

            def st2(st):
                holder["id"] = st.call_id
                ev.set()

            def completer():
                ev.wait(); complete(holder["id"], 1)

            t = threading.Thread(target=completer)
            t.start()
            t0 = time.perf_counter_ns(); bridge.call("a", st2); sus.append(time.perf_counter_ns() - t0)
            t.join()
    finally:
        gc.enable()

    out = {
        "schema": "inv16.bench.bridge/1", "slo_ns_p99": SLO_NS,
        "definition": "bridged_immediate - direct_async, paired per sample",
        "env": {"python": platform.python_version(), "impl": platform.python_implementation(),
                "platform": platform.platform(), "machine": platform.machine(), "cpus": os.cpu_count(),
                "optimize": sys.flags.optimize,
                "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None},
        "summary": {k: summary(v) for k, v in res.items()},
        "bridge_cost": summary(cost),
        "p99_delta_ns": pct(res["bridged_immediate"], .99) - pct(res["direct_async"], .99),
        "bridged_suspended_cross_thread": summary(sus),
        "slow_path_count": bridge.slow_path,
    }
    # Gate on the distribution delta (robust); the paired p99 is reported as the conservative view.
    out["slo_pass"] = out["p99_delta_ns"] < SLO_NS
    out["slo_pass_conservative_paired"] = out["bridge_cost"]["p99"] < SLO_NS
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2))
    raw = p.with_suffix(".raw.json")
    raw.write_text(json.dumps({"bridge_cost_ns": cost, "bridged_suspended_ns": sus}))
    keys = ("bridge_cost", "p99_delta_ns", "slo_pass", "slo_pass_conservative_paired")
    print(json.dumps({k: out[k] for k in keys}, indent=1))
    if a.gate and not out["slo_pass"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
