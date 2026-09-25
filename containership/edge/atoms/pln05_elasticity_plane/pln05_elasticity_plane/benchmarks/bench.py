"""MC-21 reproducible benchmark suite.  Stdlib only; fixed seeds; repeated trials.

    python benchmarks/bench.py [--quick] [--out results.json]

Profiles: cold start, warm decision latency (p50/p95/p99/max), throughput, CPU per
decision, memory baseline/peak/growth, payload sizes, burst, overload + recovery,
cardinality scaling, observability on/off, persistence on/off, auth-path cost.
Measurements are of the library in-process (no network); power/thermal is not
measurable here and is reported as NOT_MEASURED rather than estimated."""
from __future__ import annotations

import argparse
import gc
import json
import os
import pathlib
import platform
import random
import statistics
import sys
import tempfile
import time
import tracemalloc

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "tests"))
from helpers import World  # noqa: E402

from pln05_elasticity_plane import __version__  # noqa: E402
from pln05_elasticity_plane.errors import PlaneError  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    k = min(len(xs) - 1, max(0, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


def env():
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "machine": platform.machine(), "system": platform.system(), "release": platform.release(),
            "cpu_count": os.cpu_count(), "package_version": __version__,
            "hashseed": os.environ.get("PYTHONHASHSEED", "random")}


def latency_run(n, *, persist=False, trace_ratio=None, scopes=1, seed=1):
    rng = random.Random(seed)
    tmp = tempfile.TemporaryDirectory() if persist else None
    w = World(tmp.name if tmp else None)
    if trace_ratio is not None:
        w.plane.tracer.ratio = trace_ratio
    for i in range(scopes):
        w.declare(workload=f"w{i}", ceiling=1000)
    toks = w.token(lifetime=3600)
    msgs = [w.demand(rng.random(), workload=f"w{i % scopes}") for i in range(n)]
    lat = []
    c0 = time.process_time()
    t0 = time.perf_counter()
    for raw in msgs:
        s = time.perf_counter()
        w.plane.submit_demand(raw, toks)
        lat.append((time.perf_counter() - s) * 1000)
    wall = time.perf_counter() - t0
    cpu = time.process_time() - c0
    if tmp:
        tmp.cleanup()
    return lat, wall, cpu, len(msgs[0])


def summary(lat):
    return {"n": len(lat), "p50_ms": pct(lat, 50), "p95_ms": pct(lat, 95), "p99_ms": pct(lat, 99),
            "max_ms": max(lat), "mean_ms": statistics.fmean(lat)}


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    n = 1000 if a.quick else 5000
    trials = 3 if a.quick else 5
    res = {"schema": "PLN05_BENCH/1", "env": env(), "params": {"n": n, "trials": trials, "seed": 1}}

    # cold start
    cold = []
    for t in range(trials * 3):
        gc.collect()
        s = time.perf_counter()
        w = World()
        w.declare()
        w.observe(0.9)
        cold.append((time.perf_counter() - s) * 1000)
    res["cold_start_ms"] = {"p50": pct(cold, 50), "max": max(cold)}

    # warm latency, repeated trials -> variance
    trial_p95, trial_p99, thr, cpu_per = [], [], [], []
    all_lat = []
    for t in range(trials):
        lat, wall, cpu, size = latency_run(n, seed=t + 1)
        all_lat += lat
        trial_p95.append(pct(lat, 95))
        trial_p99.append(pct(lat, 99))
        thr.append(n / wall)
        cpu_per.append(cpu / n * 1e6)
    res["decision_latency"] = summary(all_lat)
    res["decision_latency"]["p95_trials_ms"] = trial_p95
    res["decision_latency"]["p95_stdev_ms"] = statistics.pstdev(trial_p95)
    res["decision_latency"]["p99_trials_ms"] = trial_p99
    res["throughput_dps"] = {"median": statistics.median(thr), "min": min(thr), "trials": thr}
    res["cpu_us_per_decision"] = {"median": statistics.median(cpu_per), "trials": cpu_per}
    res["payload_bytes"] = {"demand_in": size}

    # memory: baseline, peak, growth across 2 halves
    tracemalloc.start()
    w = World()
    w.declare(ceiling=1000)
    tok = w.token(lifetime=3600)
    base = tracemalloc.get_traced_memory()[0]
    for i in range(n):
        w.plane.submit_demand(w.demand(0.5), tok)
    mid = tracemalloc.get_traced_memory()[0]
    for i in range(n):
        w.plane.submit_demand(w.demand(0.5), tok)
    end, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    res["memory_bytes"] = {"baseline": base, "after_n": mid, "after_2n": end, "peak": peak,
                           "growth_second_half": end - mid}

    # burst + overload + recovery
    w = World()
    w.declare(ceiling=1000)
    tok = w.token(lifetime=3600)
    rejected = 0
    s = time.perf_counter()
    for i in range(3000):
        try:
            w.plane.enqueue_demand(w.demand(0.5), tok)
        except PlaneError:
            rejected += 1
    depth = len(w.plane.admission)
    w.plane.process()
    burst_ms = (time.perf_counter() - s) * 1000
    lat, _, _, _ = latency_run(500, seed=99)
    res["burst_overload"] = {"offered": 3000, "queued_max": depth, "rejected": rejected,
                             "drain_total_ms": burst_ms, "recovery_p95_ms": pct(lat, 95)}

    # scaling, observability, persistence, auth path
    res["scaling_p95_ms"] = {str(k): pct(latency_run(n // 2, scopes=k)[0], 95) for k in (1, 100, 1000)}
    res["observability_p95_ms"] = {"trace_all": pct(latency_run(n // 2, trace_ratio=1.0)[0], 95),
                                   "trace_none": pct(latency_run(n // 2, trace_ratio=0.0)[0], 95)}
    res["persistence_p95_ms"] = {"state_on_disk": pct(latency_run(n // 5, persist=True)[0], 95),
                                 "in_memory": pct(latency_run(n // 5)[0], 95)}
    w = World()
    tok = w.token(lifetime=3600)
    s = time.perf_counter()
    for _ in range(n):
        w.plane.auth.authenticate(tok, w.clock())
    res["auth_verify_us"] = (time.perf_counter() - s) / n * 1e6
    res["power_thermal"] = "NOT_MEASURED: no power/thermal sensors in the reference environment"
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True))
    else:
        print(json.dumps(res, indent=1, sort_keys=True))
    return res


if __name__ == "__main__":
    main()
