"""Reproducible benchmark harness (components 62-64, 66, 71, 88).

Deterministic workloads (fixed seed, fixed message shapes), environment capture, warm-up,
N repetitions, p50/p95/p99 and throughput.  ``--gate`` compares against
``bench/thresholds.json`` and exits non-zero on regression (release gate, component 71).
Results are evidence about THIS host only; fleet/edge/soak certification is UNVERIFIED.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import random
import sys
import tempfile
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
from importlib import import_module  # noqa: E402

brokers = import_module(f"{PKG.name}.brokers")
storage = import_module(f"{PKG.name}.storage")


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def env() -> dict:
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "machine": platform.machine(), "system": platform.system(), "release": platform.release(),
            "cpu_count": os.cpu_count(), "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def run_latency(name, op, n):
    for _ in range(min(200, n)):
        op()
    lat = []
    t0 = time.perf_counter()
    for _ in range(n):
        s = time.perf_counter_ns()
        op()
        lat.append((time.perf_counter_ns() - s) / 1e6)
    wall = time.perf_counter() - t0
    return {"workload": name, "n": n, "p50_ms": round(pct(lat, .5), 5), "p95_ms": round(pct(lat, .95), 5),
            "p99_ms": round(pct(lat, .99), 5), "throughput_ops_s": round(n / wall, 1)}


def workloads(n: int):
    rng = random.Random(54)
    keys = [f"acct-{i}" for i in range(64)]
    msg = {"id": 0, "amount": 12.5, "tags": ["a", "b"]}
    log = brokers.PartitionedLog(8)
    yield run_latency("reference_log_append", lambda: log.append(rng.choice(keys), msg), n)
    fan = brokers.FanoutBroker()
    for i in range(8):
        fan.subscribe(f"s{i}")
    yield run_latency("reference_fanout_publish_8subs", lambda: fan.publish(msg), max(1000, n // 10))
    for sub in fan.subscribers.values():
        sub.clear()
    big = {"blob": "x" * 64_000}
    yield run_latency("reference_fanout_publish_64KB_8subs", lambda: fan.publish(big), max(200, n // 50))
    with tempfile.TemporaryDirectory() as d:
        dl = storage.DurableLog(d, 4, fsync="never")
        yield run_latency("durable_append_fsync_never", lambda: dl.append(rng.choice(keys), msg), max(1000, n // 5))
        dl.close()
    with tempfile.TemporaryDirectory() as d:
        dl = storage.DurableLog(d, 4, fsync="always")
        yield run_latency("durable_append_fsync_always", lambda: dl.append(rng.choice(keys), msg), max(200, n // 50))
        dl.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--out", default=str(PKG / "evidence" / "benchmark.json"))
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args(argv)
    res = {"schema": "inv54.benchmark/1", "environment": env(), "results": list(workloads(a.n))}
    pathlib.Path(a.out).write_text(json.dumps(res, indent=2))
    print(json.dumps(res["results"], indent=1))
    if a.gate:
        th = json.loads((PKG / "bench" / "thresholds.json").read_text())["p99_ms_max"]
        bad = [r["workload"] for r in res["results"] if r["workload"] in th and r["p99_ms"] > th[r["workload"]]]
        if bad:
            print("PERFORMANCE GATE FAILED:", bad)
            return 1
        print("performance gate passed (host-local thresholds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
