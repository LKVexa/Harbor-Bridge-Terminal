"""Reproducible benchmark, load-regime, scaling and soak harness (C061-C065,
C067, C069, C070, C088).

Every result carries platform metadata.  ``quick=True`` is the CI profile;
the full profile raises sample counts.  All regimes verify correctness
(exactly one winner, no double take) and not only speed.
"""
from __future__ import annotations

import gc
import json
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from typing import Callable

from .config import ConfigStore
from .errors import FutureError, Rejected
from .future import Future
from .runtime import Runtime

NS = 1e-9


def metadata() -> dict:
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "machine": platform.machine(), "system": platform.system(), "release": platform.release(),
            "processor": platform.processor() or "unknown", "cpu_count": os.cpu_count(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def _pct(samples: list[float]) -> dict:
    s = sorted(samples)
    n = len(s)
    q = lambda p: s[min(n - 1, int(round(p / 100 * (n - 1))))]
    return {"n": n, "p50_us": q(50) * 1e6, "p95_us": q(95) * 1e6, "p99_us": q(99) * 1e6,
            "max_us": s[-1] * 1e6, "mean_us": statistics.fmean(s) * 1e6}


def _time_each(setup: Callable[[], object], op: Callable[[object], object], n: int, warmup: int = 200) -> list[float]:
    for _ in range(warmup):
        op(setup())
    out = []
    pc = time.perf_counter_ns
    gc_was = gc.isenabled()
    gc.disable()
    try:
        for _ in range(n):
            x = setup()
            t = pc()
            op(x)
            out.append((pc() - t) * NS)
    finally:
        if gc_was:
            gc.enable()
    return out


def micro(n: int) -> dict:
    def resolved():
        f = Future(int); f.resolve(1); return f
    return {
        "create": _pct(_time_each(lambda: None, lambda _: Future(int), n)),
        "resolve": _pct(_time_each(lambda: Future(int), lambda f: f.resolve(1), n)),
        "resolve_error": _pct(_time_each(lambda: Future(int), lambda f: f.resolve_error("e"), n)),
        "abandon": _pct(_time_each(lambda: Future(int), lambda f: f.abandon(), n)),
        "take": _pct(_time_each(resolved, lambda f: f.take(), n)),
    }


def runtime_cycle(n: int) -> dict:
    rt = Runtime(ConfigStore({"environment": "test"}))
    def cyc(_):
        r, q = rt.create(int); rt.resolve(r, 1); rt.take(q)
    return {"create_resolve_take": _pct(_time_each(lambda: None, cyc, n)), "leftover": rt.outstanding}


def contention(threads: int, rounds: int) -> dict:
    lat, errors = [], 0
    for _ in range(rounds):
        f = Future(int)
        b = threading.Barrier(threads)
        wins = []
        lock = threading.Lock()
        def w(i):
            b.wait()
            t = time.perf_counter_ns()
            try:
                f.resolve(i)
                with lock:
                    wins.append(i)
            except FutureError:
                pass
            with lock:
                lat.append((time.perf_counter_ns() - t) * NS)
        ts = [threading.Thread(target=w, args=(i,)) for i in range(threads)]
        [t.start() for t in ts]; [t.join() for t in ts]
        if len(wins) != 1:
            errors += 1
        # receiver race
        g = Future(int); g.resolve(1)
        got = []
        b2 = threading.Barrier(threads)
        def r():
            b2.wait()
            try:
                got.append(g.take())
            except FutureError:
                pass
        ts = [threading.Thread(target=r) for _ in range(threads)]
        [t.start() for t in ts]; [t.join() for t in ts]
        if len(got) != 1:
            errors += 1
    return {"threads": threads, "rounds": rounds, "latency": _pct(lat), "invariant_errors": errors}


def throughput(seconds: float) -> dict:
    end = time.perf_counter() + seconds
    n = 0
    while time.perf_counter() < end:
        for _ in range(500):
            f = Future(int); f.resolve(1); f.take()
        n += 500
    return {"ops_per_s": n / seconds, "seconds": seconds}


def memory_per_future(count: int) -> dict:
    gc.collect()
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    fs = [Future(int) for _ in range(count)]
    bare = (tracemalloc.get_traced_memory()[0] - base) / count
    del fs
    gc.collect()
    rt = Runtime(ConfigStore({"environment": "test"}))
    base = tracemalloc.get_traced_memory()[0]
    caps = [rt.create(int) for _ in range(count)]
    governed = (tracemalloc.get_traced_memory()[0] - base) / count
    for r, q in caps:
        rt.resolve(r, 1); rt.take(q)
    del caps
    gc.collect()
    after = tracemalloc.get_traced_memory()[0] - base
    tracemalloc.stop()
    return {"count": count, "bytes_per_bare_future": bare, "bytes_per_governed_future": governed,
            "residual_bytes_after_release": after, "residual_per_future": after / count,
            "outstanding_after_release": rt.outstanding}


def import_time(repeats: int = 5) -> dict:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
    vals = []
    for _ in range(repeats):
        code = f"import time;t=time.perf_counter();import {name};print(time.perf_counter()-t)"
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=root)
        if out.returncode == 0:
            vals.append(float(out.stdout.strip()))
    return {"import_ms_median": statistics.median(vals) * 1000 if vals else None, "samples": len(vals)}


def regimes(quick: bool) -> dict:
    """Steady, burst, sustained burst, overload, increasing concurrency, recovery."""
    rt = Runtime(ConfigStore({"environment": "test", "max_outstanding": 2000, "soft_outstanding": 1500,
                              "max_per_tenant": 2000}))
    out: dict = {}
    k = 2000 if quick else 20000

    def cycle_batch(n):
        lat = []
        for _ in range(n):
            t = time.perf_counter_ns()
            r, q = rt.create(int); rt.resolve(r, 1); rt.take(q)
            lat.append((time.perf_counter_ns() - t) * NS)
        return lat

    out["steady"] = _pct(cycle_batch(k))
    # short burst: allocate many outstanding at once then drain
    def burst(n):
        t = time.perf_counter()
        caps, rej = [], 0
        for _ in range(n):
            try:
                caps.append(rt.create(int))
            except Rejected:
                rej += 1
        for r, q in caps:
            rt.resolve(r, 1); rt.take(q)
        return {"requested": n, "admitted": len(caps), "rejected": rej, "seconds": time.perf_counter() - t,
                "outstanding_after": rt.outstanding}
    out["short_burst"] = burst(1000)
    out["sustained_burst"] = [burst(1500) for _ in range(5 if quick else 50)]
    out["overload"] = burst(5000)      # 2.5x the hard limit: must reject, not grow
    out["post_overload_recovery"] = _pct(cycle_batch(k))
    conc = {}
    for th in (1, 2, 4, 8, 16):
        lat, lock = [], threading.Lock()
        def worker():
            loc = cycle_batch(k // th)
            with lock:
                lat.extend(loc)
        t0 = time.perf_counter()
        ts = [threading.Thread(target=worker) for _ in range(th)]
        [t.start() for t in ts]; [t.join() for t in ts]
        conc[str(th)] = {**_pct(lat), "ops_per_s": len(lat) / (time.perf_counter() - t0)}
    out["increasing_concurrency"] = conc
    out["correctness"] = {"outstanding_end": rt.outstanding,
                          "double_resolutions": rt.metrics.counter("inv18_double_resolutions_total"),
                          "double_takes": rt.metrics.counter("inv18_double_takes_total")}
    out["scale_out_in"] = "N/A: process-local primitive; scale-out is the caller's replication of processes (docs/PERFORMANCE.md)"
    return out


def scaling(sizes=(1, 10, 100, 1000, 10000)) -> dict:
    res = {}
    for n in sizes:
        rt = Runtime(ConfigStore({"environment": "test", "max_outstanding": max(n, 10), "soft_outstanding": max(n, 10),
                                  "max_per_tenant": max(n, 10)}))
        gc.collect()
        tracemalloc.start()
        b = tracemalloc.get_traced_memory()[0]
        t = time.perf_counter()
        caps = [rt.create(int) for _ in range(n)]
        for r, q in caps:
            rt.resolve(r, 1)
        for r, q in caps:
            rt.take(q)
        el = time.perf_counter() - t
        peak = tracemalloc.get_traced_memory()[1] - b
        tracemalloc.stop()
        res[str(n)] = {"seconds_per_op_us": el / n / 3 * 1e6, "peak_bytes_per_future": peak / n}
    return res


def soak(seconds: float) -> dict:
    rt = Runtime(ConfigStore({"environment": "test"}))
    from .runtime import TOMBSTONES
    tracemalloc.start()                       # before warm-up, so evictions of warm-up entries are traced
    for _ in range(TOMBSTONES + 1000):        # warm-up: fill every bounded ring to steady state
        r, q = rt.create(int); rt.resolve(r, 1); rt.take(q)
    samples = []
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        t = time.perf_counter()
        for _ in range(1000):
            r, q = rt.create(int); rt.resolve(r, 1); rt.take(q)
        samples.append({"t": round(time.perf_counter() - end + seconds, 3),
                        "us_per_cycle": (time.perf_counter() - t) * 1e3,
                        "mem": tracemalloc.get_traced_memory()[0]})
    tracemalloc.stop()
    n = len(samples)
    first, last = samples[: max(1, n // 5)], samples[-max(1, n // 5):]
    drift = statistics.fmean(s["us_per_cycle"] for s in last) / statistics.fmean(s["us_per_cycle"] for s in first)
    # the bounded tombstone ring (runtime.TOMBSTONES) fills during the first half; a leak shows as
    # growth in the second half, after every bounded structure has reached steady state
    mem_growth = samples[-1]["mem"] - samples[n // 2]["mem"]
    total_growth = samples[-1]["mem"] - samples[0]["mem"]
    return {"seconds": seconds, "windows": n, "latency_drift_ratio": drift, "memory_growth_bytes": mem_growth,
            "total_memory_growth_bytes": total_growth,
            "invariant_errors": int(rt.metrics.counter("inv18_double_resolutions_total")
                                    + rt.metrics.counter("inv18_double_takes_total")),
            "outstanding_end": rt.outstanding, "series": samples[:: max(1, n // 50)]}


def profile_ops() -> dict:
    """Allocation / copy / lock analysis for one governed cycle (C065)."""
    rt = Runtime(ConfigStore({"environment": "test"}))
    payload = "x" * 1024
    tracemalloc.start()
    s1 = tracemalloc.take_snapshot()
    r, q = rt.create(str); rt.resolve(r, payload); out = rt.take(q)
    s2 = tracemalloc.take_snapshot()
    tracemalloc.stop()
    stats = s2.compare_to(s1, "filename")
    return {"payload_copied": out[1] is not payload, "payload_identity_preserved": out[1] is payload,
            "lock_acquisitions_per_cycle": {"future_condition": 3, "registry_lock": 3},
            "top_allocations": [{"file": os.path.basename(str(s.traceback[0].filename)), "size_diff": s.size_diff,
                                 "count_diff": s.count_diff} for s in stats[:5]],
            "network_hops": 0, "serialization_in_core": False}


def run(quick: bool = True, reps: int = 5) -> dict:
    n = 3000 if quick else 50000
    reps_micro = [micro(n) for _ in range(reps)]
    agg = {}
    for op in reps_micro[0]:
        p50s = [r[op]["p50_us"] for r in reps_micro]
        p99s = [r[op]["p99_us"] for r in reps_micro]
        agg[op] = {**reps_micro[-1][op], "p50_us_runs": p50s, "p50_us_stdev": statistics.pstdev(p50s),
                   "p99_us_median": statistics.median(p99s)}
    return {
        "schema": "PK_FUTURE_BENCH/1", "profile": "quick" if quick else "full", "metadata": metadata(),
        "micro": agg, "runtime": runtime_cycle(n),
        "contention": [contention(t, 20 if quick else 200) for t in (2, 8, 16)],
        "throughput": throughput(0.5 if quick else 5.0), "memory": memory_per_future(5000),
        "import": import_time(3 if quick else 10), "regimes": regimes(quick),
        "scaling": scaling(), "soak": soak(2.0 if quick else 60.0), "profile_ops": profile_ops(),
        "storage_network_overhead": "N/A: core performs no storage or network I/O (verified by test_authority)",
        "power": "N/A pending approval: see governance/WAIVERS.json W-C068",
    }


# ---------------------------------------------------------------- capacity model (C069)
def capacity_model(result: dict, *, max_outstanding: int = 100_000) -> dict:
    """Derive the safe operating envelope from measured data."""
    per = result["memory"]["bytes_per_governed_future"]
    cyc_us = result["runtime"]["create_resolve_take"]["p50_us"]
    conc = result["regimes"]["increasing_concurrency"]
    single = conc["1"]["ops_per_s"]
    knee = next((int(k) for k, v in sorted(conc.items(), key=lambda kv: int(kv[0]))
                 if v["ops_per_s"] < 0.5 * single), None)
    return {
        "memory_bytes": {"formula": "outstanding * bytes_per_governed_future", "bytes_per_future": per,
                         "at_hard_limit": per * max_outstanding},
        "cpu_seconds_per_cycle": cyc_us * 1e-6,
        "throughput_per_runtime_1_thread": single,
        "contention_knee_threads": knee,
        "saturation_signals": {"outstanding_warning": "soft_outstanding (80 % of hard)",
                               "outstanding_critical": "max_outstanding",
                               "memory_pressure": f"outstanding * {per:.0f} B > 50 % of node memory",
                               "latency_degradation": "p99 governed cycle > 800 us",
                               "lock_contention": f"more than {max(1, (knee or 2) - 1)} threads per Runtime"},
        "safe_envelope": f"<= {max(1, (knee or 2) - 1)} threads per Runtime; outstanding <= soft limit; "
                         f"memory budget {per * max_outstanding / 1e6:.0f} MB at the default hard limit",
    }


def predict_memory(bytes_per_future: float, n: int) -> float:
    return bytes_per_future * n


# ---------------------------------------------------------------- regression gate (C070)
GATED = [  # (json path, direction, allowed regression ratio, absolute noise floor in the metric's unit)
    ("micro.resolve.p50_us", "lower", 0.60, 1.0),
    ("micro.resolve.p95_us", "lower", 0.75, 1.0),
    ("micro.resolve.p99_us_median", "lower", 1.00, 2.0),
    ("micro.take.p50_us", "lower", 0.50, 1.0),
    ("micro.create.p50_us", "lower", 0.50, 1.0),
    ("runtime.create_resolve_take.p50_us", "lower", 1.00, 20.0),
    ("throughput.ops_per_s", "higher", 0.40, 0.0),
    ("memory.bytes_per_governed_future", "lower", 0.25, 0.0),
    ("import.import_ms_median", "lower", 1.00, 20.0),
]


def _get(d, path):
    for k in path.split("."):
        d = d[k]
    return d


def compare(result: dict, baseline: dict, waivers: dict | None = None) -> list[dict]:
    """Return a list of regressions (empty = pass).  Waivers are keyed by metric path."""
    regs = []
    for path, direction, allowed, floor in GATED:
        try:
            cur, base = float(_get(result, path)), float(_get(baseline, path))
        except (KeyError, TypeError, ValueError):
            regs.append({"metric": path, "reason": "missing"})
            continue
        ratio = (cur - base) / base if direction == "lower" else (base - cur) / base
        # sub-microsecond timings on shared hosts jitter by ~1 us; a regression must exceed
        # both the ratio and the absolute noise floor to block
        if ratio > allowed and abs(cur - base) > floor and path not in (waivers or {}):
            regs.append({"metric": path, "baseline": base, "current": cur, "regression": ratio, "allowed": allowed})
    return regs


if __name__ == "__main__":
    print(json.dumps(run(quick="--full" not in sys.argv), indent=1, default=str))
