"""Reproducible in-process benchmark for INV-31 (C061, C063, C064, C088).

Deterministic workload (seeded); reports wall-clock latency percentiles, which
naturally vary by host.  --check compares against evidence/bench_thresholds.json
(PROPOSED thresholds) and exits 1 on regression.
"""
from __future__ import annotations

import argparse, json, pathlib, platform, random, sys, time, tracemalloc

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
PKG = HERE.name
import importlib
rt = importlib.import_module(f"{PKG}.runtime")
bd = importlib.import_module(f"{PKG}.boundary")

KEY = b"b" * 32


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def summary(xs):
    return {"n": len(xs), "p50_ns": pct(xs, .5), "p95_ns": pct(xs, .95), "p99_ns": pct(xs, .99),
            "max_ns": max(xs)}


def scenario_pool(n, tenants, versions, seed, max_instances=1024):
    rng, pool, lat = random.Random(seed), rt.FunctionPool(max_instances=max_instances), []
    for t in range(n):
        s = time.perf_counter_ns()
        try:
            pool.invoke(tenant=f"t{rng.randrange(tenants)}", version=f"v{rng.randrange(versions)}", now=t // 10)
        except rt.PoolCapacityExceeded:
            pass
        lat.append(time.perf_counter_ns() - s)
    st = pool.pool_snapshot(n // 10)["stats"]
    return {**summary(lat), "warm_rate": st["warm_rate"], "capacity_rejections": st["capacity_rejections"],
            "instances": len(pool.instances)}


def scenario_gateway(n, tenants, seed):
    rng = random.Random(seed)
    gw = bd.Gateway(pool=rt.FunctionPool(), authenticator=bd.HmacAuthenticator({"k": KEY}),
                    max_tenant_share=1.0)
    lat, sign_ns = [], []
    for t in range(n):
        ten = f"t{rng.randrange(tenants)}"
        s0 = time.perf_counter_ns()
        a = bd.HmacAuthenticator.sign(KEY, {"key_id": "k", "subject": "bench", "tenant": ten,
             "capabilities": [f"invoke:{ten}"], "kind": "service", "issued_at": 0,
             "expires_at": 500, "nonce": f"n{t}"})
        s = time.perf_counter_ns()
        sign_ns.append(s - s0)
        r = gw.invoke(a, {"schema": bd.REQUEST_SCHEMA, "tenant": ten, "version": "v1"}, now=t % 400)
        lat.append(time.perf_counter_ns() - s)
        assert r["ok"], r
    return {**summary(lat), "client_sign": summary(sign_ns)}


def run(quick=False):
    n = 5_000 if quick else 50_000
    out = {
        "schema": "PK_INV31_BENCH/1",
        "interpreter": f"{platform.python_implementation()} {platform.python_version()}",
        "machine": platform.machine(),
        "workloads": {
            "steady_pool_4t_2v": scenario_pool(n, 4, 2, 1),
            "burst_many_tenants_64t": scenario_pool(n, 64, 4, 2),
            "overload_small_pool": scenario_pool(n // 5, 200, 4, 3, max_instances=16),
            "gateway_authenticated_8t": scenario_gateway(n // 5, 8, 4),
        },
    }
    # Memory is measured in a separate pass: tracemalloc distorts latency heavily.
    tracemalloc.start()
    scenario_pool(n // 5, 64, 4, 2)
    out["tracemalloc_peak_bytes_64t"] = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    raw = out["workloads"]["steady_pool_4t_2v"]["p50_ns"]
    gw = out["workloads"]["gateway_authenticated_8t"]["p50_ns"]
    out["gateway_overhead_p50_ns"] = gw - raw  # C064 per-invocation overhead of the boundary
    return out


def check(result, thresholds):
    fails = []
    for wl, lim in thresholds["workloads"].items():
        for k, v in lim.items():
            got = result["workloads"][wl][k]
            if (k.startswith("warm") and got < v) or (not k.startswith("warm") and got > v):
                fails.append(f"{wl}.{k}={got} vs {v}")
    return fails


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    res = run(a.quick)
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    if a.check:
        f = check(res, json.loads((HERE / "evidence/bench_thresholds.json").read_text()))
        print("BENCH", "REGRESSION " + "; ".join(f) if f else "WITHIN_PROPOSED_THRESHOLDS")
        sys.exit(1 if f else 0)
