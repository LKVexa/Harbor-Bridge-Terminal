"""Reproducible benchmark harness and performance regression gate
(MC-051 .. MC-060, MC-077).

    python inv62_edge_topology/tools/bench.py [--quick] [--out perf/results.json] [--gate]

Measures (deterministic seeded estates):
  * engine nearest-query latency p50/p95/p99/max at several graph sizes
  * full wire-path resolve latency (decode, authn, authz, admission, policy, encode)
  * serialization share of the wire path (MC-055)
  * apply throughput, startup, WAL recovery time
  * per-tenant memory and latency overhead (MC-054)
  * overload: shed ratio and served-request latency under 3x offered load (MC-053)
  * peak Python heap (tracemalloc)
Power/thermal (MC-058) cannot be measured from Python on an unknown host and
is reported as NOT_MEASURED, never as PASS.
"""
from __future__ import annotations

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

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
sys.path.insert(0, str(PKG / "tests"))

from inv62_edge_topology import Topology, TopologyLimits  # noqa: E402
from inv62_edge_topology.production import wire  # noqa: E402
import support  # noqa: E402


def estate(n_devices: int, seed: int = 0, sites_per_region: int = 20, devs_per_site: int = 50) -> Topology:
    rng = random.Random(seed)
    t = Topology(limits=TopologyLimits(max_nodes=2_000_000, max_links=5_000_000, max_degree=65_536))
    t.add("cloud", "cloud", caps=["control", "gpu"])
    made = 0
    r = 0
    while made < n_devices:
        region = f"r{r}"
        t.add(region, "region", parent="cloud")
        t.connect("cloud", region, rng.uniform(10, 40))
        for s in range(sites_per_region):
            if made >= n_devices:
                break
            site = f"s{r}-{s}"
            gw = f"{site}-gw"
            t.add(gw, "site", site, ["coordinator", "cache"], parent=region)
            t.connect(region, gw, rng.uniform(20, 80))
            for d in range(devs_per_site):
                if made >= n_devices:
                    break
                dev = f"{site}-d{d}"
                t.add(dev, "device", site, ["gpu"] if rng.random() < 0.05 else [], parent=gw)
                t.connect(gw, dev, rng.uniform(0.5, 5))
                made += 1
        r += 1
    return t


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    k = min(len(xs) - 1, max(0, round(p / 100 * (len(xs) - 1))))
    return xs[k]


def summary(xs: list[float]) -> dict[str, float]:
    return {"n": len(xs), "p50_ms": round(pct(xs, 50), 4), "p95_ms": round(pct(xs, 95), 4),
            "p99_ms": round(pct(xs, 99), 4), "max_ms": round(max(xs), 4), "mean_ms": round(statistics.fmean(xs), 4)}


def time_ms(fn) -> float:
    t0 = time.perf_counter()
    fn()
    return (time.perf_counter() - t0) * 1000


def bench_engine(sizes, queries) -> dict:
    out = {}
    for n in sizes:
        t = estate(n)
        devices = [x for x in t.nodes if "-d" in x]
        rng = random.Random(n)
        lat = []
        for _ in range(queries):
            o = rng.choice(devices)
            t0 = time.perf_counter()
            t.nearest(o, "gpu")
            lat.append((time.perf_counter() - t0) * 1000)
        out[str(n)] = {"nodes": len(t.nodes), "links": len(t.links), **summary(lat)}
    return out


def bench_wire(n: int, queries: int) -> dict:
    svc = support.make_service(limits={"max_nodes": 100_000, "max_links": 200_000, "max_degree": 65_536})
    t = estate(n)
    feed = support.client(svc, "topology-feed")
    snap = t.snapshot()
    order = {"cloud": 0, "region": 1, "site": 2, "device": 3}
    muts = [{"kind": "add_node", "node": k, "tier": v["tier"], **({"site": v["site"]} if v["site"] else {}),
             **({"parent": v["parent"]} if v["parent"] else {}), "caps": v["caps"]}
            for k, v in sorted(snap["nodes"].items(), key=lambda kv: (order[kv[1]["tier"]], kv[0]))]
    muts += [{"kind": "connect", "a": l["a"], "b": l["b"], "latency_ms": l["latency_ms"]} for l in snap["links"]]
    t0 = time.perf_counter()
    for i in range(0, len(muts), wire.MAX_MUTATIONS_PER_APPLY):
        feed.apply(muts[i:i + wire.MAX_MUTATIONS_PER_APPLY])
    apply_s = time.perf_counter() - t0
    cred = svc.authn.issue("bench", "scheduler", [support.TENANT], lifetime_s=900)
    devices = [x for x in t.nodes if "-d" in x]
    rng = random.Random(1)
    total, codec = [], []
    for i in range(queries):
        env = {"protocol": "PK_TOPO_NEAREST/1", "op": "resolve", "tenant": support.TENANT, "request_id": f"req-{i:08d}",
               "credential": cred, "body": {"origin": rng.choice(devices), "capability": "gpu"}}
        t1 = time.perf_counter()
        raw = wire.encode(env)
        resp = svc.handle(raw)
        t2 = time.perf_counter()
        wire.decode(raw)
        wire.encode(json.loads(resp))
        t3 = time.perf_counter()
        total.append((t2 - t1) * 1000)
        codec.append((t3 - t2) * 1000)
    return {"nodes": len(t.nodes), "resolve": summary(total), "codec_share": round(sum(codec) / sum(total), 4),
            "apply_mutations_per_s": round(len(muts) / apply_s, 1)}


def bench_startup_recovery(n: int) -> dict:
    with tempfile.TemporaryDirectory() as d:
        t0 = time.perf_counter()
        svc = support.make_service(state_dir=d, limits={"max_nodes": 100_000, "max_links": 200_000, "max_degree": 65_536})
        start_ms = (time.perf_counter() - t0) * 1000
        feed = support.client(svc, "topology-feed")
        feed.apply(support.ESTATE)
        for i in range(n):
            feed.apply([{"kind": "add_node", "node": f"s1-x{i}", "tier": "device", "site": "s1", "parent": "s1-gw"}])
        t0 = time.perf_counter()
        support.make_service(state_dir=d, clock=svc.clock)
        rec_ms = (time.perf_counter() - t0) * 1000
    return {"cold_start_ms": round(start_ms, 3), "wal_records": n + 1, "recovery_ms": round(rec_ms, 3)}


def bench_tenants(k: int) -> dict:
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    svc = support.make_service()
    after_svc = tracemalloc.get_traced_memory()[0]
    lat1 = []
    for i in range(k):
        tenant = f"t{i:04d}"
        support.client(svc, "topology-feed", tenant=tenant).apply(support.ESTATE)
    after = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    s0 = support.client(svc, "scheduler", tenant="t0000")
    for _ in range(200):
        lat1.append(time_ms(lambda: s0.resolve("s1-d1", "gpu")))
    return {"tenants": k, "bytes_per_tenant": int((after - after_svc) / k), "service_base_bytes": int(after_svc - base),
            "resolve_with_k_tenants": summary(lat1)}


def bench_overload() -> dict:
    clk = support.FakeClock(0)
    svc = support.make_service(clock=clk, admission={"rate_per_s": 100.0, "burst": 100, "max_in_flight": 64})
    support.client(svc, "topology-feed").apply(support.ESTATE)
    cred = svc.authn.issue("b", "scheduler", [support.TENANT], lifetime_s=900)
    served, shed, lat = 0, 0, []
    # 3x offered load for 10 simulated seconds
    for i in range(3000):
        clk.t = i / 300.0
        env = {"protocol": "PK_TOPO_NEAREST/1", "op": "resolve", "tenant": support.TENANT, "request_id": f"req-{i:08d}",
               "credential": cred, "body": {"origin": "s1-d1", "capability": "gpu"}}
        t0 = time.perf_counter()
        r = json.loads(svc.handle(wire.encode(env)))
        if "error" in r:
            shed += 1
        else:
            served += 1
            lat.append((time.perf_counter() - t0) * 1000)
    return {"offered": 3000, "served": served, "shed": shed, "shed_ratio": round(shed / 3000, 4),
            "served_latency": summary(lat)}


def run(quick: bool) -> dict:
    tracemalloc.start()
    sizes = [100, 1000] if quick else [100, 1000, 10000]
    res = {
        "schema": "INV62_BENCH/1",
        "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                        "machine": platform.machine(), "system": platform.system(), "cpu_count": os.cpu_count(),
                        "quick": quick},
        "engine_nearest": bench_engine(sizes, 200 if quick else 500),
        "wire_resolve": bench_wire(1000, 300 if quick else 1000),
        "startup_recovery": bench_startup_recovery(200 if quick else 1000),
        "overload": bench_overload(),
        "power_thermal": "NOT_MEASURED",
    }
    res["peak_heap_bytes_engine_and_wire"] = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    res["tenants"] = bench_tenants(20 if quick else 100)
    return res


def gate(results: dict, thresholds: dict) -> dict:
    checks = []

    def check(name, value, limit, op="<="):
        ok = value <= limit if op == "<=" else value >= limit
        checks.append({"check": name, "value": value, "limit": limit, "op": op, "status": "PASS" if ok else "FAIL"})

    for size, lim in thresholds["engine_nearest_p99_ms"].items():
        if size in results["engine_nearest"]:
            check(f"engine_nearest[{size}].p99_ms", results["engine_nearest"][size]["p99_ms"], lim)
    w = results["wire_resolve"]
    check("wire_resolve[1000].p99_ms", w["resolve"]["p99_ms"], thresholds["wire_resolve_1000_p99_ms"])
    check("apply_mutations_per_s", w["apply_mutations_per_s"], thresholds["apply_mutations_per_s_min"], ">=")
    check("recovery_ms", results["startup_recovery"]["recovery_ms"], thresholds["recovery_ms"])
    check("cold_start_ms", results["startup_recovery"]["cold_start_ms"], thresholds["cold_start_ms"])
    check("bytes_per_tenant", results["tenants"]["bytes_per_tenant"], thresholds["bytes_per_tenant"])
    o = results["overload"]
    check("overload.served_ratio", round(o["served"] / o["offered"], 4), thresholds["overload_served_ratio_min"], ">=")
    check("overload.served_p99_ms", o["served_latency"]["p99_ms"], thresholds["overload_served_p99_ms"])
    checks.append({"check": "power_thermal", "status": "NOT_MEASURED"})
    failing = [c for c in checks if c["status"] == "FAIL"]
    return {"schema": "INV62_PERF_GATE/1", "status": "FAIL" if failing else "PASS", "checks": checks,
            "note": "power/thermal is NOT_MEASURED (MC-058 open_external)"}


def main(argv: list[str]) -> int:
    quick = "--quick" in argv
    out = pathlib.Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    res = run(quick)
    text = json.dumps(res, indent=2, sort_keys=True)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n")
    print(text)
    if "--gate" in argv:
        g = gate(res, json.loads((PKG / "perf" / "thresholds.json").read_text()))
        if out:
            (out.parent / "perf_gate.json").write_text(json.dumps(g, indent=2) + "\n")
        print(json.dumps(g, indent=2))
        return 0 if g["status"] == "PASS" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
