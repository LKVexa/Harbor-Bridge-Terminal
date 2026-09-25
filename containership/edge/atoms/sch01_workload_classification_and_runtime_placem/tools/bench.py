"""MC-35 reproducible benchmark + MC-36 regression gate.

  python3 -B tools/bench.py --out evidence/bench.json          # measure
  python3 -B tools/bench.py --gate evidence/bench.json         # compare to thresholds

Measures engine.place over synthetic fleets (100/1,000/5,000 nodes) with a fixed seed.
Thresholds in THRESHOLDS are PROPOSED (no owner has approved them); a met gate reports
`met_under_proposed_thresholds`, never an approved pass.  Host facts are recorded as run
evidence only and never written into the repository's tracked documents.
"""
from __future__ import annotations

import json
import platform
import random
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
import sch01_workload_classification_and_runtime_placem as sch  # noqa: E402

THRESHOLDS = {"status": "PROPOSED", "p99_ms_1000_nodes": 100.0, "p50_ms_1000_nodes": 25.0,
              "max_regression_ratio": 1.25, "peak_kib_5000_nodes": 65536}


def fleet(n, seed):
    r = random.Random(seed)
    return [sch.NodeReport(f"n{i:05d}", r.choice(["eu", "us", "ap"]), frozenset(r.sample(sch.TIER_ORDER, r.randint(1, 5))),
                           capabilities=frozenset(r.sample(["gpu", "sgx", "nvme"], r.randint(0, 2))),
                           free_slots=r.randint(0, 8), reported_at=r.randint(40, 60)) for i in range(n)]


def measure(n, iters, seed=7):
    lat = []
    provs = ["internal", "first-party", "partner", "public", "quarantined"]
    for i in range(iters):
        nodes = fleet(n, seed + i)
        w = sch.Workload(f"w{i}", "t", provs[i % 5])
        t0 = time.perf_counter()
        try: sch.place(w, nodes, now=60)
        except sch.Unplaceable: pass
        lat.append((time.perf_counter() - t0) * 1000)
    lat.sort()
    q = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))]
    return {"nodes": n, "iters": iters, "p50_ms": q(.5), "p95_ms": q(.95), "p99_ms": q(.99), "max_ms": lat[-1],
            "mean_ms": statistics.fmean(lat), "throughput_per_s": 1000 / statistics.fmean(lat)}


def measure_service(n, iters):
    """The 4.3.0 governed path (authn, attestation cache, all filters, fenced journal fsync)."""
    import tempfile
    sys.path.insert(0, str(PKG / "tests"))
    from _fx import Rig  # per-run keys; nothing persisted outside a temp dir
    r = Rig(tmp=tempfile.mkdtemp(prefix="sch01-bench-"), default_quota=10**6)
    rng = random.Random(3)
    for i in range(n):
        r.node(f"n{i:05d}", tiers=rng.sample(sch.TIER_ORDER, rng.randint(1, 5)), slots=rng.randint(1, 8))
    lat = []
    for i in range(iters):
        req, tok, ctx = r.req(name=f"w{i}", prov="partner"), r.tok(), r.ctx()
        t0 = time.perf_counter()
        try: r.s.place(tok, req, ctx)
        except Exception: pass
        lat.append((time.perf_counter() - t0) * 1000)
    lat.sort(); q = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))]
    return {"path": "Scheduler.place", "nodes": n, "iters": iters, "p50_ms": q(.5), "p99_ms": q(.99), "max_ms": lat[-1]}


def main(argv):
    if "--gate" in argv:
        cur = json.loads(Path(argv[argv.index("--gate") + 1]).read_text())
        base_p = argv[argv.index("--baseline") + 1] if "--baseline" in argv else None
        res = {r["nodes"]: r for r in cur["results"]}
        fails = []
        if res[1000]["p99_ms"] > THRESHOLDS["p99_ms_1000_nodes"]: fails.append("p99@1000")
        if res[1000]["p50_ms"] > THRESHOLDS["p50_ms_1000_nodes"]: fails.append("p50@1000")
        svc = {r["nodes"]: r for r in cur.get("service_results", [])}
        if 1000 not in svc: fails.append("service@1000 not measured")
        elif svc[1000]["p99_ms"] > THRESHOLDS["p99_ms_1000_nodes"]: fails.append("service p99@1000")
        if cur["peak_kib_5000"] > THRESHOLDS["peak_kib_5000_nodes"]: fails.append("memory@5000")
        if base_p:
            base = {r["nodes"]: r for r in json.loads(Path(base_p).read_text())["results"]}
            for n in res:
                if n in base and res[n]["p99_ms"] > base[n]["p99_ms"] * THRESHOLDS["max_regression_ratio"]:
                    fails.append(f"regression@{n}")
        verdict = "FAIL" if fails else "met_under_proposed_thresholds"
        print(json.dumps({"verdict": verdict, "failures": fails, "thresholds": THRESHOLDS})); return 1 if fails else 0
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    results = [measure(100, 200), measure(1000, 100), measure(5000, 20)]
    tracemalloc.start(); sch.place(sch.Workload("m", "t", "public"), fleet(5000, 1), now=60)
    peak = tracemalloc.get_traced_memory()[1] // 1024; tracemalloc.stop()
    doc = {"schema": "PK_SCHEDULER_BENCH/1", "seed": 7, "results": results,
           "service_results": [measure_service(1000, 50)], "peak_kib_5000": peak,
           "host": {"python": platform.python_version(), "machine": platform.machine(), "system": platform.system()},
           "not_measured": ["power", "network overhead", "storage overhead", "startup under production config"]}
    text = json.dumps(doc, indent=2, sort_keys=True)
    if out: out.write_text(text + "\n")
    print(text); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
