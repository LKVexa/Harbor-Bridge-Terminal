"""Reproducible performance baseline for INV-72 (C061-C066, C088).

    python -B <pkg>/bench/perf_suite.py [--quick] [--out <pkg>/evidence/PERF_RESULTS.json]

Scenarios (fixed seeds, fixed fleets, warm-up excluded):
  pure_match_{16,256,4096}   matcher.decide on fleets of increasing size         -> scale curve (C063)
  service_steady             full governed pipeline, authenticated, 1 thread      -> per-request overhead (C064)
  service_burst              8 threads x burst, admission on                      -> burst + shed behaviour (C063)
  service_overload           offered > admission rate                             -> shed ratio, p99 of admitted
  recovery_after_overload    steady latency after overload stops                  -> recovery (C063)
  soak                       N minutes (quick: 3 s) steady; RSS + audit growth    -> memory bound (C067, C088)
  per_tenant_overhead        same load split over 1 vs 50 tenants                 -> per-tenant cost (C064)
Each result records p50/p95/p99/max in microseconds, ops/s, host facts and the quick flag.  Quick results
are indicative only; the perf gate refuses them for release (C070).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import platform
import random
import resource
import statistics
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve()
PKG = HERE.parents[1]
sys.path.insert(0, str(PKG.parent))
sys.path.insert(0, str(PKG / "tests"))
sys.dont_write_bytecode = True

from harness import M, Tokens, build, pkg  # noqa: E402


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def summarise(lat_us, seconds, extra=None):
    return {"n": len(lat_us), "p50_us": round(pct(lat_us, .50), 1), "p95_us": round(pct(lat_us, .95), 1),
            "p99_us": round(pct(lat_us, .99), 1), "max_us": round(max(lat_us), 1),
            "mean_us": round(statistics.fmean(lat_us), 1), "ops_per_s": round(len(lat_us) / seconds, 1), **(extra or {})}


def fleet(n, seed=1):
    rng = random.Random(seed)
    return [pkg.Device(f"d{i:05d}", rng.choice(["gpu-large", "gpu-small"]), rng.choice([40, 80]), f"n{i // 8}",
                       f"l{(i // 4) % 2}", f"g{i}" if rng.random() < 0.2 else "") for i in range(n)]


def fleet_dicts(n, seed=1):
    return [{"dev_id": d.dev_id, "cls": d.cls, "mem_gb": d.mem_gb, "node": d.node, "link_group": d.link_group,
             "partition_of": d.partition_of} for d in fleet(n, seed)]


def pure(n, iters):
    f = fleet(n)
    r = {"class": "gpu-large", "mem_gb": 80, "count": 2, "interconnect": True, "tenant": "t1"}
    for _ in range(50):
        pkg.decide(r, f)
    lat = []
    t0 = time.perf_counter()
    for _ in range(iters):
        a = time.perf_counter()
        pkg.decide(r, f)
        lat.append((time.perf_counter() - a) * 1e6)
    return summarise(lat, time.perf_counter() - t0, {"inventory": n})


def service(n_dev=256, rate=100000, burst=100000):
    svc, _, _ = build(devices=fleet_dicts(n_dev))
    cfg = M["config"].compose("cloud", {"admission": {"rate_per_s": rate, "burst": burst, "max_inflight": 10_000},
                                        "quotas": {"default_devices_per_tenant": 4096}})
    svc.config.activate(cfg, author="bench", reason="bench")
    svc.logger.stream = io.StringIO()
    svc.logger.level = "warn"
    return svc


def steady(svc, iters, tenants=1):
    tok = Tokens()
    r = lambda i: {"class": "gpu-large", "mem_gb": 40, "tenant": f"t{i % tenants}"}
    toks = [tok.caller(tenants=tuple(f"t{j}" for j in range(tenants)), caps=["accel.match"]) for _ in range(iters + 20)]
    for i in range(20):
        svc.request(r(i), token=toks[i], reserve=False)
    lat, t0 = [], time.perf_counter()
    for i in range(iters):
        a = time.perf_counter()
        svc.request(r(i), token=toks[20 + i], reserve=False)
        lat.append((time.perf_counter() - a) * 1e6)
    if len(svc.audit.events) > 50_000:
        svc.audit.export()
    return summarise(lat, time.perf_counter() - t0, {"tenants": tenants})


def burst(svc, threads, per_thread):
    tok = Tokens()
    toks = [[tok.caller(caps=["accel.match"]) for _ in range(per_thread)] for _ in range(threads)]
    lat, shed, lock = [], [0], threading.Lock()
    barrier = threading.Barrier(threads)

    def w(k):
        barrier.wait()
        for i in range(per_thread):
            a = time.perf_counter()
            try:
                svc.request({"class": "gpu-large", "mem_gb": 40, "tenant": "t1"}, token=toks[k][i], reserve=False)
                with lock:
                    lat.append((time.perf_counter() - a) * 1e6)
            except M["errors"].AccelError as e:
                if e.code != "ACCEL_OVERLOADED":
                    raise
                with lock:
                    shed[0] += 1
    t0 = time.perf_counter()
    ts = [threading.Thread(target=w, args=(k,)) for k in range(threads)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    dt = time.perf_counter() - t0
    return summarise(lat or [0.0], dt, {"threads": threads, "offered": threads * per_thread, "shed": shed[0],
                                        "shed_ratio": round(shed[0] / (threads * per_thread), 4)})


def soak(seconds):
    svc = service()
    tok = Tokens()
    rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    end, n, lat = time.time() + seconds, 0, []
    while time.time() < end:
        a = time.perf_counter()
        svc.request({"class": "gpu-large", "mem_gb": 40, "tenant": "t1"}, token=tok.caller(caps=["accel.match"]),
                    reserve=False)
        lat.append((time.perf_counter() - a) * 1e6)
        n += 1
        if len(svc.audit.events) >= 20_000:
            svc.audit.export()
    rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return summarise(lat, seconds, {"seconds": seconds, "rss_growth_kb": rss1 - rss0,
                                    "decisions_retained": len(svc._decisions),
                                    "audit_buffered": len(svc.audit.events),
                                    "nonce_cache": len(svc.auth._seen)})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(PKG / "evidence" / "PERF_RESULTS.json"))
    a = ap.parse_args(argv)
    q = a.quick
    it = 300 if q else 3000
    res = {"schema": "PK_ACCEL_PERF_RESULTS/1", "quick": q, "generated_at": time.time(),
           "host": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                    "machine": platform.machine(), "system": platform.system(), "cpus": os.cpu_count()},
           "scenarios": {}}
    S = res["scenarios"]
    for n in (16, 256, 4096):
        S[f"pure_match_{n}"] = pure(n, it if n < 4096 else max(50, it // 10))
    S["service_steady"] = steady(service(), it)
    S["service_burst"] = burst(service(), 8, it // 8)
    S["service_overload"] = burst(service(rate=200, burst=50), 8, it // 8)
    S["recovery_after_overload"] = steady(service(), it // 2)
    S["per_tenant_overhead_1"] = steady(service(), it, tenants=1)
    S["per_tenant_overhead_50"] = steady(service(), it, tenants=50)
    S["soak"] = soak(3 if q else 60)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in S.items():
        print(f"{k:28s} p50={v['p50_us']:>8}us p99={v['p99_us']:>9}us ops/s={v['ops_per_s']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
