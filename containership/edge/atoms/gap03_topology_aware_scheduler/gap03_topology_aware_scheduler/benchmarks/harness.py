"""MC-031 - Benchmark harness and regression gate (separate from unit tests).

python -m gap03_topology_aware_scheduler.benchmarks.harness [--gate] [--out FILE]

* fixed seeds + generated immutable workloads; matrix over candidate counts,
  topology sizes, tenant counts, cache state, spread and concurrency;
* records hardware/OS/Python metadata with every run;
* warm-up, repeated samples, p50/p90/p95/p99/max, stdev, throughput, peak
  memory (tracemalloc), result checksum (dead-code guard), timer resolution;
* compares against ``thresholds/<platform-key>.json``; a regression beyond
  budget fails the gate unless a matching active waiver exists;
* appends to ``trend.jsonl`` keyed by version.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import statistics
import sys
import time
import gc
import threading
import tracemalloc

HERE = os.path.dirname(os.path.abspath(__file__))
MATRIX = [
    {"id": "score-100", "candidates": 100, "topology": 1_000, "tenants": 4, "spread": 0, "cache": "cold"},
    {"id": "score-1000", "candidates": 1_000, "topology": 5_000, "tenants": 16, "spread": 3, "cache": "cold"},
    {"id": "score-1000-warm", "candidates": 1_000, "topology": 5_000, "tenants": 16, "spread": 3, "cache": "warm"},
    {"id": "score-5000", "candidates": 5_000, "topology": 20_000, "tenants": 64, "spread": 8, "cache": "cold"},
    {"id": "ledger-prepare", "kind": "ledger", "ops": 200},
    {"id": "compose-1000-3obj", "kind": "compose", "candidates": 1_000, "topology": 5_000, "tenants": 16, "objectives": 3},
    {"id": "score-1000-4threads", "candidates": 1_000, "topology": 5_000, "tenants": 16, "spread": 3, "cache": "cold", "threads": 4},
]


def env_meta() -> dict:
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(), "platform": platform.platform(),
            "machine": platform.machine(), "cpu_count": os.cpu_count(), "timer_resolution_s": time.get_clock_info("perf_counter").resolution,
            "optimized": sys.flags.optimize}


def platform_key() -> str:
    return f"{platform.system().lower()}-{platform.machine().lower()}-py{sys.version_info.major}{sys.version_info.minor}"


def _pct(xs, p):
    xs = sorted(xs)
    k = min(len(xs) - 1, max(0, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


def run_case(case: dict, *, seed: int = 1234, samples: int = 30, warmup: int = 5) -> dict:
    from gap03_topology_aware_scheduler import Topology
    from gap03_topology_aware_scheduler.controlplane.cache import ScoreCache
    from gap03_topology_aware_scheduler.scheduler import _score_snapshot
    rng = random.Random(seed)
    if case.get("kind") == "ledger":
        import tempfile
        from gap03_topology_aware_scheduler.controlplane.ledger_store import LedgerStore
        d = tempfile.mkdtemp(prefix="gap03-bench-")
        led = LedgerStore(d)
        led.submit({"type": "set_capacity", "capacity": 10**6})
        led.submit({"type": "set_reservations", "reserved": {}, "entitlement_generation": 1})
        times = []
        for i in range(case["ops"]):
            t = time.perf_counter()
            led.submit({"type": "prepare", "claim_id": f"c{i}", "tenant": "t", "slots": 1, "owner": "o", "expires_at": 10**12,
                        "require_entitlement": False})
            times.append((time.perf_counter() - t) * 1000)
        tracemalloc.start()
        led.submit({"type": "prepare", "claim_id": "mem", "tenant": "t", "slots": 1, "owner": "o", "expires_at": 10**12,
                    "require_entitlement": False})
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        import shutil
        shutil.rmtree(d, ignore_errors=True)
        return _summ(case, times, peak, hashlib.sha256(str(led.seq).encode()).hexdigest()[:12])
    topo = Topology()
    for i in range(case["topology"]):
        topo.place(f"n{i}", f"r{i % 8}", f"s{i % 64}", f"k{i % 512}")
    snap = topo.snapshot()
    cands = rng.sample([f"n{i}" for i in range(case["topology"])], case["candidates"])
    spread = cands[: case.get("spread", 0)]
    if case.get("kind") == "compose":
        from gap03_topology_aware_scheduler.controlplane import objectives
        grav = {c: rng.randrange(1000) for c in cands}
        dem = {c: rng.randrange(1000) for c in cands}

        def fn():
            return objectives.compose(cands, weights={"locality": 1000, "gravity": 500, "demand": 200},
                                      locality=lambda n: snap.cost("n0", n) * 1000 // 101, gravity=grav.get, demand=dem.get)
        return _timed(case, fn, samples, warmup, lambda r: r[0].node)
    cache = ScoreCache()
    key = ScoreCache.key(topology_generation=snap.generation, config_generation=1, schema_version="1.1", scoring_version="b",
                         anchor="n0", candidates=cands, spread_from=spread)
    fn = (lambda: cache.get_or_compute(key, lambda: _score_snapshot(snap, "n0", cands, spread_from=spread))) \
        if case["cache"] == "warm" else (lambda: _score_snapshot(snap, "n0", cands, spread_from=spread))
    if case.get("threads", 1) > 1:
        def multi():
            out = [None] * case["threads"]

            def w(i):
                out[i] = fn()
            ts = [threading.Thread(target=w, args=(i,)) for i in range(case["threads"])]
            [t.start() for t in ts]
            [t.join() for t in ts]
            return out[0]
        return _timed(case, multi, samples, warmup, lambda r: r[0].node)
    return _timed(case, fn, samples, warmup, lambda r: r[0].node)


def _timed(case, fn, samples, warmup, key):
    """warm-up, then a timing pass (tracemalloc OFF - it inflates timings several-fold) recording wall and CPU time
    and GC collections, a determinism check on every sample, then a separate memory pass."""
    chk = None
    for _ in range(warmup):
        chk = fn()
    times, cpu = [], []
    gc0 = sum(s["collections"] for s in gc.get_stats())
    for _ in range(samples):
        t, c = time.perf_counter(), time.process_time()
        res = fn()
        times.append((time.perf_counter() - t) * 1000)
        cpu.append((time.process_time() - c) * 1000)
        if key(res) != key(chk):
            raise AssertionError("non-deterministic benchmark result")
    gcs = sum(s["collections"] for s in gc.get_stats()) - gc0
    tracemalloc.start()
    fn()
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    out = _summ(case, times, peak, hashlib.sha256(repr(key(chk)).encode()).hexdigest()[:12])
    out.update({"cpu_p50_ms": round(_pct(cpu, 50), 4), "gc_collections": gcs})
    return out


def _summ(case, times, peak, checksum):
    return {"id": case["id"], "samples": len(times), "p50_ms": round(_pct(times, 50), 4), "p90_ms": round(_pct(times, 90), 4),
            "p95_ms": round(_pct(times, 95), 4), "p99_ms": round(_pct(times, 99), 4), "max_ms": round(max(times), 4),
            "stdev_ms": round(statistics.pstdev(times), 4), "throughput_per_s": round(1000 / max(statistics.mean(times), 1e-9), 1),
            "peak_mem_kib": peak // 1024, "result_checksum": checksum}


def gate(results: list[dict], thresholds: dict, waivers: list[dict] | None = None) -> dict:
    fails = []
    for r in results:
        t = thresholds.get("cases", {}).get(r["id"])
        if not t:
            fails.append({"id": r["id"], "why": "no accepted threshold"})
            continue
        budget = 1 + t.get("regression_budget", 0.2)
        if r["p99_ms"] > t["p99_ms"] * budget:
            fails.append({"id": r["id"], "why": f"p99 {r['p99_ms']} > {t['p99_ms']}x{budget}"})
        if r["peak_mem_kib"] > t.get("peak_mem_kib", 10**9) * budget:
            fails.append({"id": r["id"], "why": "memory regression"})
    waived = [f for f in fails if any(f["id"] in w.get("benchmarks", []) for w in (waivers or []))]
    blocking = [f for f in fails if f not in waived]
    return {"pass": not blocking, "failures": blocking, "waived": waived, "threshold_status": thresholds.get("status", "UNKNOWN")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--samples", type=int, default=30)
    ap.add_argument("--trend", default=os.path.join(HERE, "trend.jsonl"))
    a = ap.parse_args(argv)
    res = [run_case(c, samples=a.samples, warmup=min(5, a.samples)) for c in MATRIX]
    from gap03_topology_aware_scheduler import __version__
    doc = {"version": __version__, "env": env_meta(), "platform_key": platform_key(), "results": res, "ts": int(time.time())}
    tpath = os.path.join(HERE, "thresholds", f"{platform_key()}.json")
    if os.path.exists(tpath):
        with open(tpath, encoding="utf-8") as fh:
            doc["gate"] = gate(res, json.load(fh))
    else:
        doc["gate"] = {"pass": False, "failures": [{"why": f"no accepted threshold file for {platform_key()}"}]}
    with open(a.trend, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"version": __version__, "platform_key": platform_key(),
                             "p99": {r["id"]: r["p99_ms"] for r in res}, "ts": doc["ts"]}) + "\n")
    text = json.dumps(doc, indent=1, sort_keys=True)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)
    return 0 if (doc["gate"]["pass"] or not a.gate) else 1


if __name__ == "__main__":
    raise SystemExit(main())
