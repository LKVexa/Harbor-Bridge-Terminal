"""Benchmark harness, latency targets and regression gate (MC-034, MC-035, MC-039).

``run_suite`` measures control-path operations that are executable on any
host (validation, plan build, admission, metrics).  Data-path and real
cold-boot benchmarks require a KVM host and register as ``NOT_TESTED``
there.  ``gate`` compares results with a committed baseline and the
declared p50/p95/p99 targets; a regression beyond tolerance FAILS.
"""
from __future__ import annotations

import json
import platform
import statistics
import sys
import time
from typing import Callable

TARGETS_MS = {
    # control path (host-independent) targets, per operation
    "microvm_create_validate": {"p50": 0.05, "p95": 0.2, "p99": 0.5},
    "firecracker_plan_build": {"p50": 0.1, "p95": 0.5, "p99": 1.0},
    "admission_decision": {"p50": 1.0, "p95": 5.0, "p99": 10.0},
    "token_verify": {"p50": 0.1, "p95": 0.5, "p99": 1.0},
    # real-host targets (evidence required from a KVM host)
    "cold_boot": {"p50": 60.0, "p95": 100.0, "p99": 125.0},
    "stop_cleanup": {"p50": 10.0, "p95": 30.0, "p99": 50.0},
}
REGRESSION_TOLERANCE = 1.5  # FAIL if p95 > 1.5 x baseline p95


def measure(fn: Callable[[], object], *, n: int = 2000, warmup: int = 100) -> dict:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(n):
        t = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - t) / 1e6)
    samples.sort()
    q = lambda p: samples[min(n - 1, int(p * n))]
    return {"n": n, "p50": q(0.50), "p95": q(0.95), "p99": q(0.99), "max": samples[-1],
            "mean": statistics.fmean(samples)}


def host_profile() -> dict:
    return {"python": sys.version.split()[0], "machine": platform.machine(), "system": platform.system(),
            "release": platform.release(), "kvm": __import__("os").path.exists("/dev/kvm")}


def gate(results: dict, baseline: dict | None) -> dict:
    verdicts = {}
    for name, target in TARGETS_MS.items():
        r = results.get(name)
        if r is None:
            verdicts[name] = {"result": "NOT_TESTED", "reason": "requires KVM host" if name in {"cold_boot", "stop_cleanup"} else "not run"}
            continue
        fails = [q for q in ("p50", "p95", "p99") if r[q] > target[q]]
        b = (baseline or {}).get(name)
        regressed = bool(b and r["p95"] > b["p95"] * REGRESSION_TOLERANCE)
        verdicts[name] = {"result": "FAIL" if fails or regressed else "PASS", "target_misses": fails,
                          "regressed": regressed, "p95": round(r["p95"], 4), "baseline_p95": b and round(b["p95"], 4)}
    return verdicts


def write(path: str, payload: dict) -> None:
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
