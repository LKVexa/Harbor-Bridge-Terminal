"""M22/M27 - reproducible performance baseline, regression gate, burst/overload/soak/scale runs.

    python tools/perf.py --mode quick  [--out evidence/perf.json] [--gate]
    python tools/perf.py --mode soak --seconds 600

Uses the in-memory reference providers, so numbers measure PLN-04's own
admission overhead (policy, validation, state, audit, telemetry), not a real
hypervisor.  Thresholds live in ops/PERF_THRESHOLDS.json and are PROPOSED
until an owner approves them; the gate compares against them and fails
closed on regression.
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
sys.path.insert(0, str(ROOT.parent))

from pln04_execution_plane import errors, policy, providers, runtime  # noqa: E402
from pln04_execution_plane import plane as plane_mod  # noqa: E402


def make_plane(audit=None, **limits):
    reg = providers.ProviderRegistry(allow_reference=True)
    for t in runtime.TIERS:
        reg.register(providers.ReferenceProvider(t))
    lim = {"max_instances": 200000, "per_tenant_limit": 200000, "cpu_milli": 10**9, "memory_mib": 10**9, **limits}
    pl = plane_mod.ExecutionPlane(policy.PlaneConfig.load({"limits": lim}), reg, audit=audit)
    for t in runtime.TIERS:
        pl.attest_tier(t)
    return pl


def req(i: int, tenant: str = "t0", tc: str = "first-party") -> dict:
    return {"schema": "PK_ADMISSION/1", "kind": "request", "request_id": f"r{i}", "workload": f"w{i}",
            "tenant": tenant, "trust_class": tc, "resources": {"cpu_milli": 10, "memory_mib": 1}}


def baseline(n: int) -> dict:
    pl = make_plane()
    lat = []
    t0 = time.perf_counter()
    for i in range(n):
        s = time.perf_counter()
        pl.admit(req(i, tenant=f"t{i % 16}"))
        lat.append((time.perf_counter() - s) * 1e6)
    elapsed = time.perf_counter() - t0
    td = []
    for i in range(n):
        s = time.perf_counter()
        pl.teardown(f"w{i}", f"t{i % 16}")
        td.append((time.perf_counter() - s) * 1e6)
    lat.sort()
    td.sort()
    return {"admissions": n, "admit_ops_per_s": round(n / elapsed, 1),
            "admit_p50_us": round(lat[n // 2], 1), "admit_p99_us": round(lat[int(n * 0.99)], 1),
            "teardown_p50_us": round(td[n // 2], 1), "teardown_p99_us": round(td[int(n * 0.99)], 1)}


def burst(threads: int, per_thread: int) -> dict:
    pl = make_plane(max_inflight=8, max_queue=32, per_tenant_queue=8)
    outcomes: dict[str, int] = {}
    lock = threading.Lock()

    def worker(k: int) -> None:
        for j in range(per_thread):
            try:
                pl.admit({**req(k * per_thread + j, tenant=f"t{k % 4}"), "deadline_ms": 2000})
                key = "admitted"
            except errors.PlaneError as exc:
                key = exc.code
            with lock:
                outcomes[key] = outcomes.get(key, 0) + 1

    ts = [threading.Thread(target=worker, args=(k,)) for k in range(threads)]
    s = time.perf_counter()
    [t.start() for t in ts]
    [t.join() for t in ts]
    unexpected = {k: v for k, v in outcomes.items() if k not in ("admitted", "PLN04-CAP-002", "PLN04-TIME-001")}
    return {"threads": threads, "requests": threads * per_thread, "seconds": round(time.perf_counter() - s, 3),
            "outcomes": outcomes, "unexpected": unexpected, "queue_depth_after": pl.gate.depth()}


def overload() -> dict:
    """Capacity exhaustion must be refused with CAP-001, never crash or overcommit."""
    pl = make_plane(max_instances=100, per_tenant_limit=100)
    codes: dict[str, int] = {}
    for i in range(150):
        try:
            pl.admit(req(i))
            codes["admitted"] = codes.get("admitted", 0) + 1
        except errors.PlaneError as exc:
            codes[exc.code] = codes.get(exc.code, 0) + 1
    return {"attempted": 150, "outcomes": codes, "resident": len(pl.node.instances)}


def soak(seconds: float) -> dict:
    """Churn admit/teardown; heap is sampled only after every bounded ring (audit, logs) is full,
    so remaining growth is a leak rather than a ring filling up."""
    pl = make_plane(audit=plane_mod._MemoryAudit(capacity=1000))
    pl.node._audit_limit = 1000
    for w in range(600):
        pl.admit(req(-w - 1))
        pl.teardown(f"w{-w - 1}", "t0")
    tracemalloc.start()
    end = time.monotonic() + seconds
    i = cycles = 0
    samples = []
    while time.monotonic() < end:
        for _ in range(200):
            pl.admit(req(i))
            pl.teardown(f"w{i}", "t0")
            i += 1
        cycles += 200
        samples.append(tracemalloc.get_traced_memory()[0])
    tracemalloc.stop()
    samples = samples[1:] or samples
    third = max(1, len(samples) // 3)
    early, late = statistics.mean(samples[:third]), statistics.mean(samples[-third:])
    return {"seconds": seconds, "cycles": cycles, "heap_early_bytes": int(early), "heap_late_bytes": int(late),
            "heap_growth_ratio": round(late / early, 3) if early else None,
            "resident_after": len(pl.node.instances), "store_records_after": len(list(pl.store.items("inst/")))}


def scale(n: int) -> dict:
    pl = make_plane()
    s = time.perf_counter()
    for i in range(n):
        pl.admit(req(i, tenant=f"t{i % 256}"))
    fill = time.perf_counter() - s
    s = time.perf_counter()
    for k in range(200):
        pl.admit(req(n + k, tenant="t-probe"))
    probe = (time.perf_counter() - s) / 200 * 1e6
    return {"resident": n, "fill_seconds": round(fill, 2), "admit_us_at_scale": round(probe, 1)}


def gate(result: dict, thresholds: dict) -> tuple[bool, list[str]]:
    b, t = result["baseline"], thresholds["thresholds"]
    fails = []
    if b["admit_p99_us"] > t["admit_p99_us_max"]:
        fails.append(f"admit_p99_us {b['admit_p99_us']} > {t['admit_p99_us_max']}")
    if b["admit_ops_per_s"] < t["admit_ops_per_s_min"]:
        fails.append(f"admit_ops_per_s {b['admit_ops_per_s']} < {t['admit_ops_per_s_min']}")
    if result["burst"]["unexpected"]:
        fails.append(f"burst produced unexpected outcomes {result['burst']['unexpected']}")
    if result["overload"]["resident"] > 100:
        fails.append("overload overcommitted the node")
    if result.get("soak", {}).get("heap_growth_ratio") and result["soak"]["heap_growth_ratio"] > t["soak_heap_growth_ratio_max"]:
        fails.append(f"soak heap growth {result['soak']['heap_growth_ratio']}")
    return not fails, fails


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["quick", "full", "soak"], default="quick")
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--out")
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    n = 2000 if a.mode == "quick" else 20000
    result = {"schema": "PK_PLN04_PERF/1", "mode": a.mode, "python": platform.python_version(),
              "machine": platform.machine(), "cpu_count": os.cpu_count(), "note": "reference providers; indicative only",
              "baseline": baseline(n), "burst": burst(16, 50 if a.mode == "quick" else 500), "overload": overload()}
    if a.mode in ("soak", "full"):
        result["soak"] = soak(a.seconds)
        result["scale"] = scale(10000 if a.mode == "soak" else 100000)
    else:
        result["soak"] = soak(min(a.seconds, 3.0))
    thresholds = json.loads((ROOT / "ops" / "PERF_THRESHOLDS.json").read_text())
    ok, fails = gate(result, thresholds)
    result["gate"] = {"status": "PASS" if ok else "FAIL", "failures": fails, "thresholds_status": thresholds["status"]}
    text = json.dumps(result, indent=2)
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(text)
    print(text)
    return 0 if (ok or not a.gate) else 1


if __name__ == "__main__":
    sys.exit(main())
