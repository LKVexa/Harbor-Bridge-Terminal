"""P1-23: performance, burst and soak benchmark for the decision path.

Measures wall-clock latency of DecisionService.decide against in-process signed
fixtures (no network), so it bounds GAP-14's *own* cost.  The estate SLO (p99 <
50 ms end-to-end) additionally includes real dependency latency and must be
re-measured against the live estate; this tool is the harness for both.

    python gap14_data_gravity_manager/tools/bench.py --n 5000 --threads 8 --soak-s 0 --out bench.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import platform
import statistics
import sys
import threading
import time
import tracemalloc

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "tests"))
sys.path.insert(0, str(HERE.parents[2]))

from fixtures.estate import Estate  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]


def run(n: int, threads: int, soak_s: float) -> dict:
    e = Estate()
    tok = e.token(ttl=3600)
    reqs = [e.request(name=f"d{i % 97}", size=float((i * 37) % 900), cls="pii" if i % 5 == 0 else "public",
                      compute="ams" if i % 2 else "fra") for i in range(n)]
    for r in [e.request(name=f"warm{i}", size=float(i)) for i in range(200)]:  # warm-up, not measured
        e.service.decide(r, tok)
    engine = __import__("gap14_data_gravity_manager.engine", fromlist=["x"])
    g = engine.GravityManager(residency={"dub": {"public"}, "ams": {"public"}}, distance={("dub", "ams"): 1.0, ("ams", "dub"): 1.0},
                              compute_sites={"dub", "ams"})
    eng = []
    for i in range(n):
        s0 = time.perf_counter()
        g.recommend(engine.Dataset("d", "dub", float(i % 900), "public"), "ams")
        eng.append(time.perf_counter() - s0)
    lat: list[float] = []
    lock = threading.Lock()
    errors: dict[str, int] = {}

    def worker(chunk):
        local = []
        for r in chunk:
            t0 = time.perf_counter()
            try:
                e.service.decide(r, tok)
            except Exception as exc:  # noqa: BLE001
                code = getattr(exc, "code", type(exc).__name__)
                with lock:
                    errors[code] = errors.get(code, 0) + 1
            local.append(time.perf_counter() - t0)
        with lock:
            lat.extend(local)

    t0 = time.perf_counter()
    chunks = [reqs[i::threads] for i in range(threads)]
    ts = [threading.Thread(target=worker, args=(c,)) for c in chunks]
    [t.start() for t in ts]
    [t.join() for t in ts]
    burst_s = time.perf_counter() - t0
    soak = None
    if soak_s > 0:
        tracemalloc.start()
        mem_start = tracemalloc.get_traced_memory()[0]
        end, k, samples = time.perf_counter() + soak_s, 0, []
        while time.perf_counter() < end:
            r = e.request(name=f"s{k % 50}", size=float(k % 700))
            s = time.perf_counter()
            e.service.decide(r, tok)
            samples.append(time.perf_counter() - s)
            k += 1
            if k % 500 == 0:  # fixture-only buffers (production uses FileAuditSink / log shipping)
                e.audit.records.clear()
                e.logs.seek(0)
                e.logs.truncate()
                if k == 5000:
                    mem_start = tracemalloc.get_traced_memory()[0]  # measure growth after caches warm
        soak = {"decisions": k, "p99_ms": round(pct(samples, 99) * 1000, 3),
                "mem_growth_bytes": tracemalloc.get_traced_memory()[0] - mem_start,
                "note": "tracemalloc active during soak (slower); fixture audit/log buffers cleared every 500; growth measured after decision 5000 (explain cache warm)"}
        tracemalloc.stop()
    return {"schema": "PK_GAP14_BENCH/1", "python": platform.python_version(), "machine": platform.machine(),
            "n": n, "threads": threads, "throughput_per_s": round(n / burst_s, 1),
            "p50_ms": round(statistics.median(lat) * 1000, 3), "p95_ms": round(pct(lat, 95) * 1000, 3),
            "p99_ms": round(pct(lat, 99) * 1000, 3), "max_ms": round(max(lat) * 1000, 3),
            "errors": errors, "engine_only": {"p50_ms": round(statistics.median(eng) * 1000, 4),
                                              "p99_ms": round(pct(eng, 99) * 1000, 4)}, "slo_p99_ms": 50.0, "slo_met_in_process": pct(lat, 99) * 1000 < 50.0, "soak": soak,
            "scope": "in-process signed fixtures (fixture signing cost included); excludes live network latency"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--soak-s", type=float, default=0.0)
    ap.add_argument("--out")
    a = ap.parse_args()
    res = run(a.n, a.threads, a.soak_s)
    txt = json.dumps(res, indent=2)
    print(txt)
    if a.out:
        pathlib.Path(a.out).write_text(txt + "\n")
    sys.exit(0 if res["slo_met_in_process"] else 1)
