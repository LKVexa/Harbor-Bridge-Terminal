"""Benchmark suite (MC-049): selection latency (p50/p99) at 16 and 1024 entries, cache hit path, registry
build, snapshot/verify cost, memory high-water (tracemalloc).  Compares to ops/PERF_THRESHOLDS.json
(PROPOSED) and writes evidence/BENCH_RESULTS.json.  ``--quick`` shrinks iterations; quick results are
marked and never valid for gating.
"""
from __future__ import annotations

import argparse
import platform
import statistics
import sys
import time
import tracemalloc
import warnings

from ._common import EVIDENCE, ROOT, ensure_path, read_json, write_json


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def run(quick=False) -> dict:
    ensure_path()
    warnings.simplefilter("ignore", DeprecationWarning)
    from inv28_unikernel_implementations import fixtures as F
    from inv28_unikernel_implementations.registry import verify_snapshot
    n_iter = 50 if quick else 400
    out: dict = {}
    for size in (16, 1024):
        recs = [F.record(f"t{i:04d}", languages=("c",) if i % 5 == 0 else ("ocaml",)) for i in range(size)]
        t = time.perf_counter()
        w = F.world(records=recs)
        out[f"build_{size}_s"] = round(time.perf_counter() - t, 4)
        lat = []
        for i in range(n_iter):
            w["selector"].invalidate()
            t = time.perf_counter()
            w["selector"].select(F.request(workload_id=f"w{i}"), now=F.NOW)
            lat.append((time.perf_counter() - t) * 1000)
        out[f"select_{size}"] = {"p50_ms": round(statistics.median(lat), 4), "p99_ms": round(pct(lat, 99), 4),
                                 "max_ms": round(max(lat), 4), "n": n_iter}
        hits = []
        for _ in range(n_iter):
            t = time.perf_counter()
            w["selector"].select(F.request(workload_id="hot"), now=F.NOW)
            hits.append((time.perf_counter() - t) * 1000)
        out[f"cached_select_{size}"] = {"p50_ms": round(statistics.median(hits), 4), "p99_ms": round(pct(hits, 99), 4)}
        t = time.perf_counter()
        snap = w["registry"].snapshot()
        out[f"snapshot_{size}_ms"] = round((time.perf_counter() - t) * 1000, 3)
        t = time.perf_counter()
        verify_snapshot(w["ring"], snap)
        out[f"verify_snapshot_{size}_ms"] = round((time.perf_counter() - t) * 1000, 3)
    tracemalloc.start()
    w = F.world(records=[F.record(f"m{i:04d}") for i in range(1024)], with_certs=False)
    for i in range(200):
        w["selector"].select(F.request(workload_id=f"x{i}", environment="dev"), now=F.NOW)
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    out["memory_1024_peak_mib"] = round(peak / 2 ** 20, 2)
    return out


def compare(res: dict, thr: dict) -> list[str]:
    t = thr["thresholds"]
    checks = [("select_p99_ms_16_entries", res["select_16"]["p99_ms"]),
              ("select_p99_ms_1024_entries", res["select_1024"]["p99_ms"]),
              ("register_1024_total_s", res["build_1024_s"]),
              ("snapshot_1024_ms", res["snapshot_1024_ms"]),
              ("verify_snapshot_1024_ms", res["verify_snapshot_1024_ms"])]
    return [f"{k}: {v} > {t[k]}" for k, v in checks if v > t[k]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    res = run(a.quick)
    thr = read_json(ROOT / "ops" / "PERF_THRESHOLDS.json")
    fails = compare(res, thr)
    doc = {"schema": "PK_BENCH/1", "quick": a.quick, "python": platform.python_version(),
           "machine": platform.machine(), "platform": platform.platform(terse=True), "results": res,
           "thresholds_status": thr["status"], "failures": fails,
           "verdict": "PASS" if not fails and not a.quick else ("QUICK" if not fails else "FAIL"),
           "note": "measured on the build host, not reference hardware (waiver W-003)"}
    write_json(EVIDENCE / "BENCH_RESULTS.json", doc)
    print("BENCH", doc["verdict"], res["select_16"], res["select_1024"], f"build_1024={res['build_1024_s']}s")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
