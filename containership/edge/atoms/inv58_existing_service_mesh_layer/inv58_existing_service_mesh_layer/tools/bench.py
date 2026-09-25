"""Reproducible benchmark harness + performance-regression gate (MC-021, MC-022, MC-023).

    python -B tools/bench.py run   [--out perf/results.json] [--quick]
    python -B tools/bench.py gate  [--results perf/results.json] [--baseline perf/baseline.json]
    python -B tools/bench.py rebaseline   # writes perf/baseline.json (requires human approval to commit)

Profiles: steady (single-thread closed loop), burst (8 threads), per-tenant
overhead (1 vs 200 tenants), startup (empty -> ready), memory (tracemalloc peak
for N routes / N bypass flags).  Power/thermal are NOT measurable here and are
recorded as BLOCKED rather than estimated.
"""
from __future__ import annotations

import json
import os
import pathlib
import platform
import statistics
import sys
import threading
import time
import tracemalloc

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.dont_write_bytecode = True
import _support as S  # noqa: E402

FLOOR = {"_us": 50.0, "_ms": 25.0, "_kib": 1024.0, "ratio_200_vs_1": 0.25}  # noise floors
GATE = {
    # metric: (absolute ceiling, allowed regression vs baseline)
    "mesh.map_identity.p99_us": (100.0, 0.50),      # contract SLO "handoff cost"
    "mesh.reconcile.p99_us": (100.0, 0.50),
    "svc.reconcile.p99_us": (2000.0, 0.50),
    "svc.map_identity.p99_us": (2000.0, 0.50),
    "svc.report_flow.p99_us": (2000.0, 0.50),
    "svc.migrate_route.p99_us": (4000.0, 0.50),
    "startup.bootstrap_ms": (250.0, 0.50),
    "memory.routes_10k_kib": (20_000.0, 0.25),
    "tenant_overhead.ratio_200_vs_1": (2.0, 0.25),
}


def pct(samples, q):
    s = sorted(samples)
    return s[min(len(s) - 1, int(q * len(s)))]


def summarize(ns):
    us = [x / 1000 for x in ns]
    return {"p50_us": pct(us, .5), "p95_us": pct(us, .95), "p99_us": pct(us, .99), "max_us": max(us),
            "mean_us": statistics.fmean(us), "n": len(us), "ops_per_s": 1e6 / statistics.fmean(us)}


def timeit(fn, n):
    out = []
    for i in range(n):
        t = time.perf_counter_ns()
        fn(i)
        out.append(time.perf_counter_ns() - t)
    return out


def run(quick=False):
    n = 2_000 if quick else 20_000
    res = {"environment": {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
                           "machine": platform.machine(), "system": platform.system(), "cpu_count": os.cpu_count(),
                           "quick": quick, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
           "metrics": {}, "profiles": {}}
    M = res["metrics"]
    for name, fn in {
        "mesh.map_identity": lambda i: S.mesh.map_identity("spiffe://estate.local/ns/shop/sa/orders", "estate.local"),
        "mesh.reconcile": lambda i: S.mesh.reconcile("orders->payments", 3, 3, 3),
    }.items():
        timeit(fn, 200)
        s = summarize(timeit(fn, n))
        res["profiles"][name] = s
        M[f"{name}.p99_us"] = s["p99_us"]

    t = time.perf_counter()
    svc, clock, kms = S.make_service(cfg=S.base_config(admission={"rate_per_s": 1e6, "burst": 10**6}))
    M["startup.bootstrap_ms"] = (time.perf_counter() - t) * 1000
    fence = [0]

    def mig(i):
        fence[0] += 1
        svc.migrate_route(S.CTRL_A, "alpha", f"r{i % 500}", 3, 1, fence=fence[0], idempotency_key=f"bench-{fence[0]:09d}")
    ops = {
        "svc.reconcile": lambda i: svc.reconcile(S.CTRL_A, "alpha", "orders->payments", 3, 3),
        "svc.map_identity": lambda i: svc.map_identity(S.NODE, "alpha", "spiffe://estate.local/ns/alpha/sa/orders"),
        "svc.report_flow": lambda i: svc.report_flow(S.NODE, "alpha", "cron", "payments", i % 2 == 0),
        "svc.migrate_route": mig,
    }
    for name, fn in ops.items():
        timeit(fn, 100)
        s = summarize(timeit(fn, n // 4))
        res["profiles"][name] = s
        M[f"{name}.p99_us"] = s["p99_us"]

    # burst: 8 threads closed loop
    lat, lock = [], threading.Lock()

    def worker():
        local = timeit(ops["svc.reconcile"], n // 16)
        with lock:
            lat.extend(local)
    ts = [threading.Thread(target=worker) for _ in range(8)]
    t0 = time.perf_counter()
    for th in ts:
        th.start()
    for th in ts:
        th.join()
    b = summarize(lat)
    b["wall_ops_per_s"] = len(lat) / (time.perf_counter() - t0)
    res["profiles"]["burst.svc.reconcile.8threads"] = b

    # per-tenant overhead
    tenants = [f"t{i:03d}" for i in range(200)]
    cfg = S.base_config(tenants=tenants, admission={"rate_per_s": 1e6, "burst": 10**6},
                        spiffe_bindings={"runtime:ns/t000/sa/controller": {"actor_type": "controller", "roles": ["mesh-controller"]}})
    big, _, _ = S.make_service(cfg=cfg)
    cred = {"san": "spiffe://estate.local/ns/t000/sa/controller"}
    one = summarize(timeit(lambda i: svc.reconcile(S.CTRL_A, "alpha", "r", 3, 3), n // 4))
    many = summarize(timeit(lambda i: big.reconcile(cred, "t000", "r", 3, 3), n // 4))
    M["tenant_overhead.ratio_200_vs_1"] = many["p50_us"] / one["p50_us"]
    res["profiles"]["tenant_overhead"] = {"tenants_1_p50_us": one["p50_us"], "tenants_200_p50_us": many["p50_us"]}

    # memory
    tracemalloc.start()
    reg = S.mesh.RoutePolicyRegistry(max_routes=20_000)
    base = tracemalloc.take_snapshot()
    for i in range(10_000):
        reg.migrate_route(f"route-{i:06d}", 3, 1)
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    M["memory.routes_10k_kib"] = peak / 1024
    res["profiles"]["memory"] = {"routes_10k_peak_kib": peak / 1024,
                                 "note": "copy-on-write registry: each migrate copies the dict (O(n) per write) - see docs/PERFORMANCE.md OPT-1"}
    res["blocked"] = {"power_thermal": "BLOCKED: no edge hardware / power telemetry in this environment (C068)",
                      "network_overhead": "BLOCKED: no live mesh data plane; INV-58 adds no network hop in-process (C061)"}
    return res


def run_best(quick=True, repeats=3):
    """Best-of-N per metric: scheduler noise only ever makes a sample slower."""
    runs = [run(quick=quick) for _ in range(repeats)]
    best = runs[0]
    for r in runs[1:]:
        for k, v in r["metrics"].items():
            best["metrics"][k] = min(best["metrics"][k], v)
    best["environment"]["repeats"] = repeats
    return best


def gate(results, baseline):
    failures, rows = [], []
    for metric, (ceiling, allowed) in GATE.items():
        cur = results["metrics"].get(metric)
        base = baseline["metrics"].get(metric) if baseline else None
        if cur is None:
            failures.append(f"{metric}: missing from results")
            continue
        floor = next(v for k, v in FLOOR.items() if metric.endswith(k))
        limit = ceiling if base is None else min(ceiling, max(base * (1 + allowed), base + floor))
        ok = cur <= limit
        rows.append({"metric": metric, "current": round(cur, 3), "baseline": base and round(base, 3), "limit": round(limit, 3), "pass": ok})
        if not ok:
            failures.append(f"{metric}: {cur:.2f} > {limit:.2f}")
    return {"pass": not failures, "failures": failures, "rows": rows}


def main(argv):
    cmd = argv[0] if argv else "run"
    if cmd in ("run", "rebaseline"):
        res = run_best(quick=True) if "--quick" in argv else run_best(quick=False, repeats=2)
        out = ROOT / ("perf/baseline.json" if cmd == "rebaseline" else "perf/results.json")
        if "--out" in argv:
            out = pathlib.Path(argv[argv.index("--out") + 1])
        out.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
        print(json.dumps(res["metrics"], indent=2))
        return 0
    if cmd == "gate":
        r = json.loads((ROOT / "perf/results.json").read_text())
        b = json.loads((ROOT / "perf/baseline.json").read_text()) if (ROOT / "perf/baseline.json").exists() else None
        g = gate(r, b)
        print(json.dumps(g, indent=2))
        return 0 if g["pass"] else 4
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
