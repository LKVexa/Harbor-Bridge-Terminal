#!/usr/bin/env python3
"""Reproducible benchmark / load / soak harness and regression gate (MC-044/045/047).

    python tools/bench.py --n 2000 [--fsync] [--threads 8] [--soak-seconds 0]
                          [--out perf/results.json] [--baseline perf/baseline.json] [--gate]

Measures, on a fresh durable store: admission latency p50/p95/p99/max
(sequential and concurrent), throughput, overload behaviour (shed count at a
bulkhead of 4 with 32 threads), startup replay time, RSS growth and journal
bytes per admission.  With ``--gate`` exits non-zero if any threshold in
``perf/thresholds.json`` or the baseline regression tolerance is violated.
Seeded and self-contained: identical inputs on every run.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import resource
import statistics
import sys
import tempfile
import threading
import time

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "inv66_enterprise_wasm_control_plane" / "tests"))

import support  # noqa: E402
from inv66_enterprise_wasm_control_plane.errors import ControlPlaneError  # noqa: E402
from inv66_enterprise_wasm_control_plane.resilience import Bulkhead  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def rss_mb():
    try:
        with open("/proc/self/statm") as fh:
            return int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 2**20
    except OSError:
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def build(path, fsync):
    import io
    from inv66_enterprise_wasm_control_plane.adapters import DeliveryAck, RulePolicyEngine

    class CountingDeploymentManager:          # acks without retaining manifests (the double must not leak)
        count = 0

        def deliver(self, delivery_id, lattice, manifest, timeout_s, traceparent):
            CountingDeploymentManager.count += 1
            return DeliveryAck(delivery_id, True, "bench")
    from inv66_enterprise_wasm_control_plane.observability import JsonLogger, Metrics
    from inv66_enterprise_wasm_control_plane.service import ControlPlaneService
    from inv66_enterprise_wasm_control_plane.store import JournalStore
    store = JournalStore(path, "bench", anchor_key=support.ANCHOR_KEY, fsync=fsync, lease_ttl_s=3600)
    return ControlPlaneService(org="acme", store=store, authenticator=support.authenticator(time.time),
                               initial_config=support.config(), policy_engine=RulePolicyEngine([], "b"),
                               deployer=CountingDeploymentManager(), metrics=Metrics(),
                               logger=JsonLogger(io.StringIO(), min_level="warn"))


def run(n, fsync, threads, soak_s):
    tmp = tempfile.mkdtemp(prefix="inv66-bench-")
    svc = build(tmp, fsync)
    svc.decision_cache = 1000                 # small cache so boundedness is measurable in a short run
    stop = svc.start_background(0.05)         # production ops loop: compaction/anchoring off the request path
    comp = support.component()
    toks = [support.token("user:ops", time.time) for _ in range(n + 64 * threads + 64)]
    ti = iter(toks)
    for i in range(1500):                      # warm-up so rss0 excludes one-time allocations
        svc.admit(support.token("user:ops", time.time), support.request([comp], rid=f"w{i}"))
    import gc
    gc.collect()
    rss0 = rss_mb()
    lat = []
    t0 = time.perf_counter()
    for i in range(n):
        req = support.request([comp], rid=f"s{i}")
        a = time.perf_counter()
        svc.admit(next(ti), req)
        lat.append((time.perf_counter() - a) * 1000)
    seq_s = time.perf_counter() - t0

    clat, lock = [], threading.Lock()

    def worker(k):
        for j in range(64):
            req = support.request([comp], rid=f"c{k}-{j}")
            with lock:
                tok = next(ti)
            a = time.perf_counter()
            svc.admit(tok, req)
            with lock:
                clat.append((time.perf_counter() - a) * 1000)
    ts = [threading.Thread(target=worker, args=(k,)) for k in range(threads)]
    c0 = time.perf_counter()
    [t.start() for t in ts]
    [t.join() for t in ts]
    conc_s = time.perf_counter() - c0

    # overload: tiny bulkhead, many threads -> must shed, never hang
    svc.bulkhead = Bulkhead(4)
    shed = [0]
    extra = [support.token("user:ops", time.time) for _ in range(32 * 4)]

    def burst(k):
        for j in range(4):
            try:
                svc.admit(extra[k * 4 + j], support.request([comp], rid=f"b{k}-{j}"))
            except ControlPlaneError as e:
                if e.error.code == "OVERLOADED":
                    with lock:
                        shed[0] += 1
    bs = [threading.Thread(target=burst, args=(k,)) for k in range(32)]
    [t.start() for t in bs]
    [t.join() for t in bs]
    svc.bulkhead = Bulkhead(svc.policy.max_inflight)

    soak = None
    if soak_s > 0:
        end, cnt, sl = time.time() + soak_s, 0, []
        while time.time() < end:
            a = time.perf_counter()
            svc.admit(support.token("user:ops", time.time), support.request([comp], rid=f"k{cnt}"))
            sl.append((time.perf_counter() - a) * 1000)
            cnt += 1
        soak = {"seconds": soak_s, "admissions": cnt, "p99_ms": pct(sl, 99), "rss_mb_end": rss_mb()}

    import gc
    gc.collect()
    rss_growth = (rss_mb() - rss0) / (n + threads * 64 + 128) * 10_000
    stop.set()
    records = svc.store.head_seq
    jbytes = sum(p.stat().st_size for p in pathlib.Path(tmp).rglob("*.jsonl") if p.name != "anchors.jsonl")
    svc.store.release()
    r0 = time.perf_counter()
    build(tmp, fsync)
    replay_ms = (time.perf_counter() - r0) * 1000
    total = n + threads * 64
    return {
        "schema": "PK_ECP_PERF_RESULTS/1", "ts": time.time(), "n": n, "threads": threads, "fsync": fsync,
        "env": {"python": sys.version.split()[0], "platform": platform.platform(), "cpu_count": os.cpu_count(),
                "machine": platform.machine()},
        "admission_latency_ms": {"p50": pct(lat, 50), "p95": pct(lat, 95), "p99": pct(lat, 99), "max": max(lat),
                                 "mean": statistics.mean(lat)},
        "concurrent_latency_ms": {"p50": pct(clat, 50), "p99": pct(clat, 99), "max": max(clat)},
        "throughput_per_s": {"sequential": n / seq_s, "concurrent": threads * 64 / conc_s},
        "overload": {"attempts": 128, "shed": shed[0]},
        "startup_replay_ms": replay_ms, "replayed_records": records,
        "startup_replay_ms_per_10k_records": replay_ms / max(1, records) * 10_000,
        "rss_growth_mb_per_10k_admissions": rss_growth,
        "journal_bytes_per_admission": jbytes / max(1, records),
        "soak": soak,
    }


def gate(res, thr, baseline):
    fails = []
    for k, lim in thr["admission_latency_ms"].items():
        if res["admission_latency_ms"][k] > lim:
            fails.append(f"latency {k} {res['admission_latency_ms'][k]:.2f}ms > {lim}ms")
    if res["throughput_per_s"]["sequential"] < thr["throughput_min_per_s"]:
        fails.append("throughput below minimum")
    for k in ("startup_replay_ms_per_10k_records", "rss_growth_mb_per_10k_admissions", "journal_bytes_per_admission"):
        if res[k] > thr[k + "_max"]:
            fails.append(f"{k} {res[k]:.1f} > {thr[k + '_max']}")
    if res["overload"]["shed"] == 0:
        fails.append("overload produced no shedding (bulkhead ineffective)")
    if baseline:
        tol = 1 + thr["regression_tolerance"]
        for k in ("p95", "p99"):
            b = baseline["admission_latency_ms"][k]
            if res["admission_latency_ms"][k] > max(b * tol, b + 1.0):
                fails.append(f"regression: {k} {res['admission_latency_ms'][k]:.2f} vs baseline {b:.2f}")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--fsync", action="store_true")
    ap.add_argument("--soak-seconds", type=float, default=0)
    ap.add_argument("--out", default=str(HERE / "perf" / "results.json"))
    ap.add_argument("--baseline")
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    res = run(a.n, a.fsync, a.threads, a.soak_seconds)
    thr = json.loads((HERE / "perf" / "thresholds.json").read_text())
    base = json.loads(pathlib.Path(a.baseline).read_text()) if a.baseline and pathlib.Path(a.baseline).exists() else None
    res["gate"] = {"failures": gate(res, thr, base)}
    res["gate"]["verdict"] = "PASS" if not res["gate"]["failures"] else "FAIL"
    pathlib.Path(a.out).write_text(json.dumps(res, indent=2))
    print(json.dumps({k: res[k] for k in ("admission_latency_ms", "throughput_per_s", "overload", "gate")}, indent=2))
    return 1 if a.gate and res["gate"]["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
