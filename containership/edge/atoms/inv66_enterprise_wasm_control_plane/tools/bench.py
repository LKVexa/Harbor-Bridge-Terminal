"""Reproducible benchmark / load / soak harness (MC-044, MC-047).

    python tools/bench.py [--quick] [--soak-seconds N] [--out release/bench.json]

Scenarios (each records environment + parameters + raw percentiles):

* latency_fsync_{1,3,20}c   serial admissions, durable journal (fsync on), N components
* latency_nofsync_3c        same, fsync off (isolates storage cost)
* throughput_threads_8      8 concurrent clients, fsync on
* burst_overload            max_inflight=4, 32 simultaneous clients -> shed fraction
* replay_startup            restart time vs journal records
* memory                    tracemalloc peak and RSS delta over the run
* soak                      optional: constant load for N seconds, RSS/FD/series drift

Numbers are for the machine they ran on; ``environment`` is recorded with them and
the perf gate compares like with like only.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import statistics
import sys
import tempfile
import threading
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from inv66_enterprise_wasm_control_plane.production.errors import EcpError  # noqa: E402
from inv66_enterprise_wasm_control_plane.production.testing import Estate  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p / 100 * len(xs)))], 4) if xs else None


def summary(xs):
    return {"n": len(xs), "p50_ms": pct(xs, 50), "p95_ms": pct(xs, 95), "p99_ms": pct(xs, 99), "max_ms": round(max(xs), 4),
            "mean_ms": round(statistics.fmean(xs), 4)}


def rss_kb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def latency(n, comps, fsync=True):
    e = Estate(fsync=fsync)
    tok = e.token("ops", ttl=3600)
    names = [f"c{i}" for i in range(comps)]
    reqs = [e.request(*names) for _ in range(n)]
    for r in reqs[:20]:  # warm-up
        e.service.admit(dict(r, request_id=r["request_id"] + "w"), tok)
    xs = []
    for r in reqs:
        t = time.perf_counter()
        d = e.service.admit(r, tok)
        xs.append((time.perf_counter() - t) * 1000)
        assert d["admitted"], d["reasons"]
    size = e.service.journal.disk_bytes()
    return {**summary(xs), "components": comps, "fsync": fsync,
            "journal_bytes_per_admission": round(size / (n + 20), 1)}


def throughput(n_per, threads=8):
    e = Estate()
    tok = e.token("ops", ttl=3600)
    reqs = [[e.request(f"t{t}x{i}") for i in range(n_per)] for t in range(threads)]
    errs = []

    def run(rs):
        for r in rs:
            try:
                e.service.admit(r, tok)
            except EcpError as x:
                errs.append(x.code)
    ts = [threading.Thread(target=run, args=(rs,)) for rs in reqs]
    t0 = time.perf_counter()
    [t.start() for t in ts]
    [t.join() for t in ts]
    dt = time.perf_counter() - t0
    return {"threads": threads, "admissions": threads * n_per, "seconds": round(dt, 3),
            "admissions_per_s": round(threads * n_per / dt, 1), "errors": len(errs)}


def burst():
    e = Estate(max_inflight=4, per_tenant_inflight=4, fsync=True)
    tok = e.token("ops", ttl=3600)
    reqs = [e.request(f"b{i}") for i in range(32)]
    out = {"ok": 0, "shed": 0}
    gate = threading.Barrier(32)

    def run(r):
        gate.wait()
        try:
            e.service.admit(r, tok)
            out["ok"] += 1
        except EcpError as x:
            if x.code == "ECP_OVERLOADED":
                out["shed"] += 1
    ts = [threading.Thread(target=run, args=(r,)) for r in reqs]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return {**out, "clients": 32, "max_inflight": 4, "shed_fraction": round(out["shed"] / 32, 3),
            "shed_counter": e.service.metrics.value("ecp_shed_total", tenant="payments")}


def replay(records):
    e = Estate(fsync=False)
    tok = e.token("ops", ttl=3600)
    for i in range(records):
        e.service.admit(e.request(f"r{i}"), tok)
    t = time.perf_counter()
    s = e.open()
    dt = time.perf_counter() - t
    return {"journal_records": s.journal.head[0], "replay_seconds": round(dt, 4),
            "records_per_s": round(s.journal.head[0] / dt, 1), "journal_bytes": s.journal.disk_bytes()}


def soak(seconds):
    e = Estate(fsync=False, segment_records=2000)
    tok_t = time.time()
    tok = e.token("ops", ttl=3600)
    samples = []
    n = 0
    t_end = time.time() + seconds
    while time.time() < t_end:
        e.service.admit(e.request(f"s{n % 500}"), tok)
        n += 1
        if n % 500 == 0:
            samples.append({"t": round(time.time() - tok_t, 2), "rss_kb": rss_kb(), "fds": len(os.listdir("/proc/self/fd")),
                            "series": e.service.metrics.series_count(), "idem": len(e.service.idem),
                            "inventory": len(e.service.inventory)})
    return {"seconds": seconds, "admissions": n, "samples": samples[:: max(1, len(samples) // 20)],
            "fd_drift": samples[-1]["fds"] - samples[0]["fds"] if samples else 0,
            "series_final": e.service.metrics.series_count(), "inventory_final": len(e.service.inventory)}


def environment():
    return {"python": platform.python_version(), "impl": platform.python_implementation(), "os": platform.system(),
            "kernel": platform.release(), "machine": platform.machine(), "cpus": os.cpu_count(),
            "tmpdir_fs": tempfile.gettempdir()}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--soak-seconds", type=float, default=0)
    ap.add_argument("--out", default=str(ROOT / "release" / "bench.json"))
    a = ap.parse_args(argv)
    n = 150 if a.quick else 600
    rss0 = rss_kb()
    res = {"schema": "PK_ECP_BENCH/1", "environment": environment(), "started": time.time(), "quick": a.quick,
           "scenarios": {}}
    sc = res["scenarios"]
    sc["latency_fsync_1c"] = latency(n, 1)
    sc["latency_fsync_3c"] = latency(n, 3)
    sc["latency_fsync_20c"] = latency(n // 3, 20)
    sc["latency_nofsync_3c"] = latency(n, 3, fsync=False)
    sc["throughput_threads_8"] = throughput(n // 8 or 1)
    sc["burst_overload"] = burst()
    sc["replay_startup"] = replay(1000 if a.quick else 5000)
    # memory is measured in its own pass: tracemalloc slows every allocation and would distort timings
    tracemalloc.start()
    latency(150, 3)
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    sc["memory"] = {"tracemalloc_peak_kb": peak // 1024, "rss_max_kb": rss_kb(), "rss_start_kb": rss0,
                    "method": "separate traced pass: 150 admissions x 3 components"}
    if a.soak_seconds:
        sc["soak"] = soak(a.soak_seconds)
    res["finished"] = time.time()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("p50_ms", "p99_ms", "admissions_per_s", "shed_fraction", "replay_seconds", "tracemalloc_peak_kb", "fd_drift")} for k, v in sc.items()}, indent=1))


if __name__ == "__main__":
    main()
