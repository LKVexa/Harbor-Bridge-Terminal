"""Reproducible benchmark, efficiency and regression gate (INV-68 MC-22, MC-23, MC-24, MC-31, MC-33).

    python -m inv68_resource_packing.tools.bench [--out evidence/] [--quick] [--update-baseline]

Profiles (fixed seeds, fixed datasets -- ``DATASETS`` below):

=============  ==========================================================  ===========================
profile        workload                                                    purpose
=============  ==========================================================  ===========================
steady-1000    1000 mixed workloads, 16c/64G hosts                          declared SLO: p99 < 100 ms
burst-5000     5000 mixed workloads                                         burst batch
fleet-20000    20000 small workloads (fleet cardinality)                    scale
worst-5000     5000 workloads that each need a new host                    4.2.0 quadratic case
tiny-1         a single workload                                           startup/fixed overhead
service-1000   steady-1000 through PackingService (auth+audit+explain)      boundary overhead
=============  ==========================================================  ===========================

Method: ``warmup`` untimed runs, then ``runs`` timed runs with
``time.perf_counter``; p50/p95/p99/max reported; peak Python allocation per
call via ``tracemalloc``; machine metadata recorded.  **Efficiency**: 200
random batches (seed 68) compare hosts used with the volume lower bound; the
contract SLO says ``<= 1.10 * LB`` in at least 95% of batches.

Outputs ``PERF.json`` and, against the committed ``bench/PERF_BASELINE.json``,
``PERF_GATE.json``: a profile regresses when its p95 exceeds
``baseline * (1 + tolerance)`` *and* the absolute delta exceeds the noise floor
(0.5 ms) -- the noise floor stops sub-millisecond jitter from failing releases.
Hosts-used per profile must match the baseline exactly (density regression).
"""
from __future__ import annotations

import argparse
import math
import random
import tempfile
import time
import tracemalloc
from pathlib import Path

from .common import PKG, machine, pct, revision, write

from inv68_resource_packing.packing import lower_bound, pack_detailed  # noqa: E402

TOLERANCE = 0.50  # 50% p95 envelope: shared CI runners are noisy; tighten on dedicated hardware
NOISE_FLOOR_MS = 0.5


def _mixed(n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    return [{"name": f"w{i}", "cpu": rng.choice([0.25, 0.5, 1, 2, 4]), "mem": rng.choice([0.5, 1, 2, 4, 8, 16])}
            for i in range(n)]


DATASETS = {
    "tiny-1": lambda: [{"name": "w0", "cpu": 1, "mem": 1}],
    "steady-1000": lambda: _mixed(1000, 7),
    "burst-5000": lambda: _mixed(5000, 8),
    "fleet-20000": lambda: [{"name": f"w{i}", "cpu": 0.05, "mem": 0.1} for i in range(20000)],
    "worst-5000": lambda: [{"name": f"w{i}", "cpu": 12, "mem": 1} for i in range(5000)],
}


def _time(fn, warmup: int, runs: int) -> tuple[list[float], int]:
    for _ in range(warmup):
        fn()
    out = []
    for _ in range(runs):
        t = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t) * 1000.0)
    tracemalloc.start()
    fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return out, peak


def run_profiles(quick: bool) -> dict:
    runs = 10 if quick else 40
    profiles = {}
    for name, make in DATASETS.items():
        work = make()
        r = runs if len(work) <= 5000 else max(5, runs // 4)
        result = pack_detailed(work, 16, 64)
        times, peak = _time(lambda: pack_detailed(work, 16, 64), 3, r)
        profiles[name] = {"workloads": len(work), "runs": r, "hosts_used": len(result.hosts),
                          "lower_bound": lower_bound(work, 16, 64), "p50_ms": round(pct(times, .5), 3),
                          "p95_ms": round(pct(times, .95), 3), "p99_ms": round(pct(times, .99), 3),
                          "max_ms": round(max(times), 3), "peak_alloc_bytes": peak,
                          "throughput_workloads_per_s": round(len(work) / (pct(times, .5) / 1000.0), 1)}
    profiles["service-1000"] = _service_profile(runs)
    return profiles


def _service_profile(runs: int) -> dict:
    from inv68_resource_packing.audit import AuditLog
    from inv68_resource_packing.auth import Authorizer, mint
    from inv68_resource_packing.config import ConfigStore, defaults
    from inv68_resource_packing.service import PackingService
    key = {"k": b"b" * 32}
    with tempfile.TemporaryDirectory() as tmp:
        audit = AuditLog(Path(tmp) / "a.jsonl")
        store = ConfigStore(Path(tmp) / "c", audit=audit)
        store.activate(defaults(), actor="bench", epoch=1)
        svc = PackingService(store, Authorizer(key), audit)
        body = {"tenant": "bench", "host_capacity": {"cpu": 16, "mem": 64}, "workloads": _mixed(1000, 7)}
        tokens = [mint(key["k"], kid="k", sub="bench", kind="workload-scheduler", tenants=["bench"],
                       caps=["pack:submit"]) for _ in range(runs + 10)]
        it = iter(tokens)
        times, peak = _time(lambda: svc.pack(body, next(it)), 3, runs)
    return {"workloads": 1000, "runs": runs, "hosts_used": None, "p50_ms": round(pct(times, .5), 3),
            "p95_ms": round(pct(times, .95), 3), "p99_ms": round(pct(times, .99), 3), "max_ms": round(max(times), 3),
            "peak_alloc_bytes": peak, "note": "includes authentication, validation, audit fsync, explain view"}


def efficiency(batches: int = 200) -> dict:
    rng = random.Random(68)
    ratios = []
    for _ in range(batches):
        n = rng.randint(20, 400)
        work = [{"name": f"w{i}", "cpu": rng.choice([0.25, 0.5, 1, 2, 4, 6]),
                 "mem": rng.choice([0.5, 1, 2, 4, 8, 16, 24])} for i in range(n)]
        lb = lower_bound(work, 16, 64, placeable_only=True)
        ratios.append(len(pack_detailed(work, 16, 64).hosts) / lb)
    within = sum(1 for r in ratios if r <= 1.10 + 1e-12)
    return {"batches": batches, "within_10pct": within, "fraction_within": round(within / batches, 4),
            "worst_ratio": round(max(ratios), 4), "mean_ratio": round(sum(ratios) / batches, 4),
            "slo": "hosts used within 10% of the lower bound in >= 95% of batches",
            "result": "PASS" if within / batches >= 0.95 else "FAIL"}


def gate(profiles: dict, baseline: dict | None) -> dict:
    if not baseline:
        return {"result": "FAIL", "reason": "no committed baseline (bench/PERF_BASELINE.json)"}
    rows, bad = [], []
    for name, cur in profiles.items():
        base = baseline["profiles"].get(name)
        if not base:
            bad.append(f"{name}: no baseline")
            continue
        limit = base["p95_ms"] * (1 + TOLERANCE)
        delta = cur["p95_ms"] - base["p95_ms"]
        latency_regressed = cur["p95_ms"] > limit and delta > NOISE_FLOOR_MS
        density_regressed = base.get("hosts_used") is not None and cur["hosts_used"] != base["hosts_used"]
        rows.append({"profile": name, "baseline_p95_ms": base["p95_ms"], "p95_ms": cur["p95_ms"],
                     "limit_ms": round(limit, 3), "latency_regressed": latency_regressed,
                     "baseline_hosts": base.get("hosts_used"), "hosts": cur["hosts_used"],
                     "density_regressed": density_regressed})
        if latency_regressed:
            bad.append(f"{name}: p95 {cur['p95_ms']} ms > {limit:.3f} ms")
        if density_regressed:
            bad.append(f"{name}: hosts {cur['hosts_used']} != baseline {base['hosts_used']}")
    return {"result": "FAIL" if bad else "PASS", "tolerance": TOLERANCE, "noise_floor_ms": NOISE_FLOOR_MS,
            "rows": rows, "regressions": bad, "baseline_machine": baseline.get("machine")}


def main(argv=None) -> int:
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    profiles = run_profiles(a.quick)
    eff = efficiency()
    steady = profiles["steady-1000"]
    slo_pack_time = steady["p99_ms"] < 100.0
    perf = {"schema": "PK_PACK_PERF/1", "machine": machine(), "revision": revision(), "profiles": profiles,
            "efficiency": eff, "method": "warmup 3, perf_counter, tracemalloc peak; fixed seeds",
            "slo_pack_time_p99_under_100ms_for_1000": slo_pack_time,
            "result": "PASS" if slo_pack_time and eff["result"] == "PASS" else "FAIL"}
    write(out / "PERF.json", perf)
    base_path = PKG / "bench" / "PERF_BASELINE.json"
    if a.update_baseline:
        write(base_path, {"schema": "PK_PACK_PERF_BASELINE/1", "machine": machine(), "profiles": profiles,
                          "note": "reference envelope; regenerate only through a reviewed change (MC-24)"})
    baseline = json.loads(base_path.read_text()) if base_path.exists() else None
    g = gate(profiles, baseline)
    write(out / "PERF_GATE.json", {"schema": "PK_PACK_PERF_GATE/1", **g})
    print(f"PERF {perf['result']}  steady p99 {steady['p99_ms']} ms  efficiency {eff['fraction_within']}  gate {g['result']}")
    for name, p in profiles.items():
        print(f"  {name:<13} p50 {p['p50_ms']:>9} p95 {p['p95_ms']:>9} p99 {p['p99_ms']:>9} ms  hosts {p['hosts_used']}")
    return 0 if perf["result"] == "PASS" and g["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
