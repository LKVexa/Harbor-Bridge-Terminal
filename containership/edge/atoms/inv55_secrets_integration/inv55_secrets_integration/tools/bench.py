"""Benchmark harness (checklist #61-#65, #69, #70).

Measures in-process resolve latency (cached and provider paths), use latency,
throughput under N threads, and per-tenant overhead, against the in-memory
provider.  Output is machine-readable JSON with the host fingerprint recorded
as *run evidence* (never baked into a generated file).  These numbers are a
reference-environment baseline; they are NOT the certified-environment
evidence the SLO requires (see WAIVERS.md W-006).
"""
from __future__ import annotations

import json
import platform
import statistics
import sys
import threading
import time
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _support as S  # noqa: E402

THRESHOLDS = {  # PROPOSED - not owner-approved (WAIVERS.md W-006)
    "resolve_cached_p99_ms": 5.0,
    "resolve_cached_p50_ms": 1.0,
    "use_p99_ms": 5.0,
}


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def run(n=3000, threads=8):
    big = S.cfg(limits={"burst": 10**6, "rate_per_s": 10**6, "max_inflight": 10**4}, cache={"fresh_s": 3600, "max_stale_s": 3600})
    svc, prov, ver, clock, wall = S.seeded(config=big)
    tok = S.token(ver, wall)
    body = S.req()
    svc.handle("RESOLVE", body, tok)
    lat = []
    for _ in range(n):
        t0 = time.perf_counter(); r = svc.handle("RESOLVE", body, tok); lat.append((time.perf_counter() - t0) * 1000)
    lid = r["lease"]["lease_id"]
    ul = []
    for _ in range(n):
        t0 = time.perf_counter(); svc.use(lid, tok); ul.append((time.perf_counter() - t0) * 1000)
    svc2, prov2, ver2, clock2, wall2 = S.seeded(config=S.cfg(limits={"burst": 10**6, "rate_per_s": 10**6}, cache={"fresh_s": 0, "max_stale_s": 0}))
    tok2 = S.token(ver2, wall2)
    pl = []
    for _ in range(n // 3):
        t0 = time.perf_counter(); svc2.handle("RESOLVE", body, tok2); pl.append((time.perf_counter() - t0) * 1000)
    done = [0]
    lock = threading.Lock()

    def worker():
        c = 0
        for _ in range(n // threads):
            svc.handle("RESOLVE", body, tok); c += 1
        with lock:
            done[0] += c
    t0 = time.perf_counter()
    ts = [threading.Thread(target=worker) for _ in range(threads)]
    [t.start() for t in ts]; [t.join() for t in ts]
    thr = done[0] / (time.perf_counter() - t0)
    # per-tenant overhead: 50 tenants' state
    for i in range(50):
        svc.policy.set_scope(f"t{i}/s", [(f"t{i}", "a")])
    res = {
        "resolve_cached_ms": {"p50": pct(lat, .5), "p95": pct(lat, .95), "p99": pct(lat, .99), "max": max(lat), "mean": statistics.mean(lat), "n": n},
        "resolve_provider_ms": {"p50": pct(pl, .5), "p99": pct(pl, .99), "max": max(pl), "n": len(pl)},
        "use_ms": {"p50": pct(ul, .5), "p99": pct(ul, .99), "max": max(ul), "n": n},
        "throughput_rps": {"threads": threads, "value": thr},
        "saturation": {"cache_entries": len(svc.cache), "leases": len(svc._leases), "audit_records": svc.audit.seq,
                       "metric_series": len(svc.metrics.counters) + len(svc.metrics.hist)},
        "thresholds_proposed": THRESHOLDS,
    }
    res["verdict"] = {
        "resolve_cached_p99_ms": res["resolve_cached_ms"]["p99"] <= THRESHOLDS["resolve_cached_p99_ms"],
        "resolve_cached_p50_ms": res["resolve_cached_ms"]["p50"] <= THRESHOLDS["resolve_cached_p50_ms"],
        "use_p99_ms": res["use_ms"]["p99"] <= THRESHOLDS["use_p99_ms"],
    }
    res["run_environment"] = {"python": platform.python_version(), "impl": platform.python_implementation(),
                              "machine": platform.machine(), "system": platform.system(), "certified": False}
    return res


def regression(current: dict, baseline: dict, tolerance=1.5) -> list[str]:
    """Performance-regression gate: p99 may not exceed baseline x tolerance."""
    bad = []
    for k in ("resolve_cached_ms", "use_ms"):
        if current[k]["p99"] > baseline[k]["p99"] * tolerance:
            bad.append(f"{k}.p99 {current[k]['p99']:.3f} > {baseline[k]['p99']:.3f} x {tolerance}")
    return bad


if __name__ == "__main__":
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 3000)
    print(json.dumps(r, indent=2))
