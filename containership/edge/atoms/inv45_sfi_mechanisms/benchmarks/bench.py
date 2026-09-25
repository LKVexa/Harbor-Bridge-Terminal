"""Reproducible benchmark / soak / burst harness (C061-C064, C067, C069, C088).

    python benchmarks/bench.py --out benchmarks/results/<name>.json [--quick] [--soak-seconds N]

Records raw samples plus p50/p95/p99/max for:

* verification latency (verifier startup cost) at three module sizes;
* rewrite latency; verification throughput (single worker);
* peak Python heap during verification of the large module (tracemalloc);
* runtime masking overhead measured in V8 (masked vs unmasked module, same workload);
* burst / overload through the admission controller (shed ratio, latency);
* per-tenant attribution of submit latency;
* soak: repeated submit/load cycles checking heap growth and audit-chain integrity.

Every number is tagged with the host fingerprint.  Numbers from a shared CI container
are *baselines for regression detection*, not capacity claims for production hardware.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from inv45_sfi_mechanisms.production import builder, engine, sfi  # noqa: E402
from inv45_sfi_mechanisms.production.builder import I32, Func, ModuleBuilder  # noqa: E402
from inv45_sfi_mechanisms.production.errors import SfiError  # noqa: E402
from inv45_sfi_mechanisms.tests.support import Harness  # noqa: E402

P = sfi.Profile(65536, 16)
PI = sfi.Profile(65536, 16, require_imported_memory=True)


def pct(xs: list[float]) -> dict[str, float]:
    s = sorted(xs)
    if not s:
        return {}

    def q(p: float) -> float:
        return s[min(len(s) - 1, int(round(p * (len(s) - 1))))]
    return {"n": len(s), "p50": q(0.5), "p95": q(0.95), "p99": q(0.99), "max": s[-1], "mean": statistics.fmean(s)}


def module_of(nfuncs: int) -> bytes:
    b = ModuleBuilder(memory=(4, None))
    for i in range(nfuncs):
        b.add(Func((I32, I32), (I32,), [(0x20, 0), (0x20, 1), (0x36, (2, i % 64)), (0x20, 0), (0x28, (2, 4)),
                                        (0x20, 1), (0x6A, None), (0x0B, None)]))
    return b.build()


def timed(fn, reps: int) -> list[float]:
    out = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t0) * 1000)
    return out


def bench_verify(quick: bool) -> dict:
    res = {}
    for name, n in (("small", 8), ("medium", 1000), ("large", 10000 if not quick else 3000)):
        raw = module_of(n)
        rw = sfi.rewrite(raw, P).artifact
        reps = 30 if n <= 1000 else 5
        res[name] = {"functions": n, "bytes_in": len(raw), "bytes_out": len(rw),
                     "size_overhead_pct": round(100 * (len(rw) - len(raw)) / len(raw), 2),
                     "rewrite_ms": pct(timed(lambda: sfi.rewrite(raw, P), reps)),
                     "verify_ms": pct(timed(lambda: sfi.verify(rw, P), reps))}
        if name == "large":
            tracemalloc.start()
            sfi.verify(rw, P)
            res[name]["verify_peak_heap_mb"] = round(tracemalloc.get_traced_memory()[1] / 2**20, 2)
            tracemalloc.stop()
            ms = res[name]["verify_ms"]["p50"]
            res[name]["instructions_per_ms"] = round(n * 7 / ms, 1)
    small = sfi.rewrite(module_of(8), P).artifact
    t_end = time.perf_counter() + (0.5 if quick else 2.0)
    count = 0
    while time.perf_counter() < t_end:
        sfi.verify(small, P)
        count += 1
    res["throughput_small_verifications_per_s"] = round(count / (0.5 if quick else 2.0), 1)
    return res


def mixed_module() -> bytes:
    """Compute-dominated loop: ~12 arithmetic ops per memory load (closer to typical guest code)."""
    b = ModuleBuilder(memory=(4, None), import_memory=("env", "memory"))
    body = [(0x02, ()), (0x03, ())]
    # s = s*31 + load((i*4) & 0x3ffc) ; s ^= s >>> 7 ; s += i*i ; i++
    body += [(0x20, 2), (0x41, 31), (0x6C, None),
             (0x20, 1), (0x41, 2), (0x74, None), (0x41, 0x3FFC), (0x71, None), (0x28, (2, 0)), (0x6A, None),
             (0x22, 2), (0x20, 2), (0x41, 7), (0x76, None), (0x73, None),
             (0x20, 1), (0x20, 1), (0x6C, None), (0x6A, None), (0x21, 2),
             (0x20, 1), (0x41, 1), (0x6A, None), (0x22, 1), (0x20, 0), (0x48, None), (0x0D, 0),
             (0x0B, None), (0x0B, None), (0x20, 2), (0x0B, None)]
    b.add(Func((I32,), (I32,), body, locals=[(2, I32)], export="mix"))
    return b.build()


def load_bound_module() -> bytes:
    """Worst case: tight loop, one load + add per iteration; outer loop repeats 256x per call."""
    b = ModuleBuilder(memory=(4, None), import_memory=("env", "memory"))
    # params: n ; locals: i(1) s(2) k(3)
    body = [(0x41, 256), (0x21, 3),
            (0x02, ()), (0x03, ()),                       # outer
            (0x41, 0), (0x21, 1),
            (0x02, ()), (0x03, ()),                       # inner
            (0x20, 2), (0x20, 1), (0x41, 2), (0x74, None), (0x28, (2, 0)), (0x6A, None), (0x21, 2),
            (0x20, 1), (0x41, 1), (0x6A, None), (0x22, 1), (0x20, 0), (0x48, None), (0x0D, 0),
            (0x0B, None), (0x0B, None),
            (0x20, 3), (0x41, 1), (0x6B, None), (0x22, 3), (0x0D, 0),
            (0x0B, None), (0x0B, None), (0x20, 2), (0x0B, None)]
    b.add(Func((I32,), (I32,), body, locals=[(3, I32)], export="sumk"))
    return b.build()


def bench_runtime_overhead(quick: bool) -> dict:
    if not engine.preflight(None)["ok"]:
        return {"status": "NOT RUN", "reason": "node-v8 engine unavailable"}
    eng = engine.NodeV8Engine(timeout=180, expected_major=None)
    reps = 15 if quick else 60
    warm = 1 + reps // 5
    out: dict = {}
    workloads = {
        "load_bound_sum": (load_bound_module(), "sumk", 16384, False),
        "compute_mixed": (mixed_module(), "mix", 200000, False),
    }
    for wname, (raw, export, n, needs_fill) in workloads.items():
        masked = sfi.rewrite(raw, PI).artifact
        sfi.verify(masked, PI)
        calls = [{"module": "m", "export": "fill", "args": [{"t": "i32", "v": n}]}] if needs_fill else []
        calls += [{"module": "m", "export": export, "args": [{"t": "i32", "v": n}]} for _ in range(reps)]
        res = {}
        results = {}
        for label, blob in (("unmasked", raw), ("masked", masked)):
            r = eng.run({"modules": [{"name": "m", "bytes": blob}], "memory_pages": 4, "calls": calls})
            body = r["calls"][1:] if needs_fill else r["calls"]
            results[label] = [c["result"] for c in body]
            res[label] = pct([c["ns"] / 1e6 for c in body[warm:]])
        res["same_results"] = results["masked"] == results["unmasked"]
        res["overhead_pct_p50"] = round(100 * (res["masked"]["p50"] / res["unmasked"]["p50"] - 1), 2)
        res["calls_measured"] = reps - warm
        out[wname] = res
    out["note"] = ("V8 still performs its own bounds checks, so SFI masking here is pure added work; "
                   "load_bound_sum is the worst case (one masked load per 7 instructions, 4.2M loads per call)")
    return out


def bench_burst_overload(quick: bool) -> dict:
    h = Harness()
    try:
        art = builder.rw_module()
        toks = {f"t{i}": h.tenant_token(f"t{i}") for i in range(8)}
        sts = {1: h.sign(art, "wl", 1)}
        lat: dict[str, list[float]] = {t: [] for t in toks}
        shed = ok = 0
        lock = threading.Lock()

        def one(i: int) -> None:
            nonlocal shed, ok
            t = f"t{i % 8}"
            t0 = time.perf_counter()
            try:
                h.svc.submit(toks[t], art, tenant=t, workload="wl", version=1, signed_statement=sts[1])
                with lock:
                    ok += 1
                    lat[t].append((time.perf_counter() - t0) * 1000)
            except SfiError as e:
                if e.code != "SFI_OVERLOADED":
                    raise
                with lock:
                    shed += 1
        total = 200 if quick else 1000
        t0 = time.perf_counter()
        with ThreadPoolExecutor(32) as ex:
            list(ex.map(one, range(total)))
        wall = time.perf_counter() - t0
        return {"requests": total, "concurrency": 32, "admitted": ok, "shed": shed,
                "shed_ratio": round(shed / total, 4), "admitted_per_s": round(ok / wall, 1),
                "admission": h.svc.admission.snapshot(),
                "per_tenant_submit_ms": {t: pct(v) for t, v in lat.items()},
                "all_submit_ms": pct([x for v in lat.values() for x in v])}
    finally:
        h.close()


def bench_soak(seconds: float) -> dict:
    h = Harness()
    try:
        art = builder.rw_module()
        tok = h.tenant_token("t1")
        tracemalloc.start()
        cycles = 0
        samples = []
        end = time.perf_counter() + seconds
        version = 0
        while time.perf_counter() < end:
            version += 1
            r = h.svc.submit(tok, art, tenant="t1", workload="wl", version=version,
                             signed_statement=h.sign(art, "wl", version))
            handle = h.svc.load(tok, r["artifact"], r["descriptor"])
            h.svc.stop(tok, handle)
            cycles += 1
            if cycles % 50 == 0:
                samples.append(tracemalloc.get_traced_memory()[0] / 2**20)
        tracemalloc.stop()
        from inv45_sfi_mechanisms.production.audit import verify_chain
        chain = verify_chain(h.root / "audit" / "audit.jsonl")
        growth = (samples[-1] - samples[len(samples) // 2]) if len(samples) > 2 else 0.0
        return {"seconds": seconds, "cycles": cycles, "heap_mb_samples": [round(s, 3) for s in samples[-10:]],
                "heap_growth_second_half_mb": round(growth, 3), "instances_left": len(h.svc.instances),
                "audit_events": chain["events"], "audit_chain": chain["result"],
                "replay_cache_entries": len(h.svc.replay)}
    finally:
        h.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--soak-seconds", type=float, default=10.0)
    ns = ap.parse_args()
    res = {"schema": "PK_SFI_BENCH/1", "component_version": (ROOT / "VERSION").read_text().strip(),
           "host": {"python": platform.python_version(), "platform": platform.platform(),
                    "machine": platform.machine(), "cpus": os.cpu_count(),
                    "node": engine.preflight(None).get("version")},
           "quick": ns.quick,
           "verification": bench_verify(ns.quick),
           "runtime_overhead_v8": bench_runtime_overhead(ns.quick),
           "burst_overload": bench_burst_overload(ns.quick),
           "soak": bench_soak(ns.soak_seconds),
           "not_measured": {"power_thermal": "no power/thermal sensors in the CI container; edge-node measurement "
                                             "is an open external item (C068)",
                            "fleet_scale": "single host only; fleet-scale certification is an open external item"}}
    Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ns.out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verify_large_p50_ms": res["verification"]["large"]["verify_ms"]["p50"],
                      "overhead_worst_case_pct": res["runtime_overhead_v8"].get("load_bound_sum", {}).get("overhead_pct_p50"),
                      "overhead_mixed_pct": res["runtime_overhead_v8"].get("compute_mixed", {}).get("overhead_pct_p50"),
                      "shed_ratio": res["burst_overload"]["shed_ratio"], "soak_cycles": res["soak"]["cycles"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
