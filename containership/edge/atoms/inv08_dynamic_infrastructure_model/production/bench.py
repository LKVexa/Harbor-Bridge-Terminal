"""Components 47/48 - benchmark harness, baselines, SLO budgets and regression gate.

Result format ``PK_DYN_BENCH/1`` (JSON)::

  {"schema": "PK_DYN_BENCH/1", "env": {...capture_env()...},
   "cases": {"<case>": {"unit": "seconds", "samples": n, "warmup": w,
             "p50", "p95", "p99", "max", "mean", "stdev", "throughput_per_s",
             "cpu_seconds", "peak_alloc_bytes"}}}

Methodology (48.14): ``warmup`` untimed iterations, then ``repeats`` rounds of
``iterations`` timed calls with ``time.perf_counter``; the per-call latency is taken
from every call, the percentile uses nearest-rank; GC is disabled during timing.
Comparison normalizes noise with a relative tolerance *and* an absolute floor
(both must be exceeded to count as a regression).

All budgets/thresholds in this file are PROPOSED - not approved; approver UNASSIGNED.
Storage/network resource profiles are N/A for the in-memory model and BLOCKED for a
deployed controller (no live environment).
"""
from __future__ import annotations

import gc
import json
import math
import os
import platform
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Callable

from ..model import Pool
from .core import Inv08Error, sha256_hex

SCHEMA = "PK_DYN_BENCH/1"

LATENCY_BUDGETS = {  # seconds, per Pool.tick call on a 100-node pool; PROPOSED
    "status": "PROPOSED", "approver": "UNASSIGNED",
    "tick_100": {"p50": 0.0005, "p95": 0.001, "p99": 0.002, "max": 0.05},
}
SLOS = {  # PROPOSED
    "decision_success": {"objective": 0.999, "window_days": 28, "sli": "successful ticks / valid-input ticks"},
    "decision_latency": {"objective": 0.99, "window_days": 28, "sli": "ticks with latency <= p99 budget / all ticks"},
    "status": "PROPOSED", "approver": "UNASSIGNED",
}
REGRESSION_THRESHOLDS = {"rel_tolerance": 0.25, "abs_floor_s": 0.00005, "metrics": ["p50", "p95", "p99"],
                         "status": "PROPOSED"}


def percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        raise ValueError("no samples")
    if not 0 <= q <= 100:
        raise ValueError("q out of range")
    k = max(1, math.ceil(q / 100 * len(sorted_vals)))
    return sorted_vals[k - 1]


def summarize(samples: list[float]) -> dict:
    s = sorted(samples)
    return {"samples": len(s), "p50": percentile(s, 50), "p95": percentile(s, 95), "p99": percentile(s, 99),
            "max": s[-1], "mean": statistics.fmean(s), "stdev": statistics.pstdev(s)}


def capture_env() -> dict:
    src = Path(__file__).resolve().parents[1] / "model.py"
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(), "cpu_count": os.cpu_count(),
            "optimize_flag": sys.flags.optimize,
            "model_sha256": sha256_hex(src.read_bytes()) if src.exists() else None}


def run_case(fn: Callable[[], object], *, warmup: int = 50, iterations: int = 200, repeats: int = 3,
             timer: Callable[[], float] = time.perf_counter, profile: bool = True) -> dict:
    if warmup < 0 or iterations < 1 or repeats < 1 or iterations * repeats > 10_000_000:
        raise ValueError("bad benchmark sizing")
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    was = gc.isenabled()
    gc.disable()
    if profile:
        tracemalloc.start()
    cpu0, wall0 = time.process_time(), timer()
    try:
        for _ in range(repeats):
            for _ in range(iterations):
                t0 = timer()
                fn()
                samples.append(timer() - t0)
    finally:
        wall = timer() - wall0
        cpu = time.process_time() - cpu0
        peak = tracemalloc.get_traced_memory()[1] if profile else None
        if profile:
            tracemalloc.stop()
        if was:
            gc.enable()
    out = summarize(samples)
    out.update(unit="seconds", warmup=warmup, cpu_seconds=cpu, peak_alloc_bytes=peak,
               throughput_per_s=(len(samples) / wall) if wall > 0 else None)
    return out


def _steady_pool(n: int) -> tuple[Pool, list]:
    p = Pool(min_nodes=0, max_nodes=n, per_node=4, lease_ttl=10)
    state = [0]
    p.tick(0, n * 4)

    def step():
        state[0] += 1
        p.tick(state[0], (n * 4) if state[0] % 2 else (n * 2))
    return p, step


def convergence_ticks(max_nodes: int, demand: float, per_node: int = 4, limit: int = 10000) -> int:
    """Ticks from an empty pool until size == target (model adds all at once, so 1)."""
    p = Pool(min_nodes=0, max_nodes=max_nodes, per_node=per_node)
    for t in range(1, limit + 1):
        r = p.tick(t, demand)
        if r["size"] == r["target"]:
            return t
    raise Inv08Error("INV08.BENCH.NO_CONVERGENCE", f"no convergence in {limit} ticks")


def run_suite(*, quick: bool = False, timer=time.perf_counter) -> dict:
    it, rep, wu = (50, 2, 10) if quick else (300, 5, 100)
    _, step = _steady_pool(100)
    cases = {
        "tick_100": run_case(step, warmup=wu, iterations=it, repeats=rep, timer=timer),
        "startup_pool_100": run_case(lambda: Pool(min_nodes=100, max_nodes=100).tick(0, 0),
                                     warmup=wu // 2, iterations=max(5, it // 5), repeats=rep, timer=timer),
    }
    cases["convergence_100"] = {"unit": "ticks", "value": convergence_ticks(100, 400)}
    return {"schema": SCHEMA, "env": capture_env(), "cases": cases}


def save(result: dict, path: str | os.PathLike) -> None:
    Path(path).write_text(json.dumps(result, sort_keys=True, indent=1))


def load(path: str | os.PathLike) -> dict:
    d = json.loads(Path(path).read_text())
    if d.get("schema") != SCHEMA:
        raise Inv08Error("INV08.BENCH.BAD_RESULT", f"unsupported result schema in {path}")
    return d


def check_budgets(result: dict, budgets: dict = LATENCY_BUDGETS) -> list[str]:
    out = []
    for case, b in budgets.items():
        if not isinstance(b, dict):
            continue
        got = result["cases"].get(case)
        if got is None:
            out.append(f"{case}: missing")
            continue
        for k, lim in b.items():
            if got[k] > lim:
                out.append(f"{case}.{k}={got[k]:.6g}s > budget {lim}s")
    return out


def compare(baseline: dict, current: dict, thresholds: dict = REGRESSION_THRESHOLDS) -> dict:
    """Regression gate: fail iff some metric exceeds baseline*(1+rel) AND baseline+abs_floor."""
    if baseline.get("schema") != SCHEMA or current.get("schema") != SCHEMA:
        raise Inv08Error("INV08.BENCH.BAD_RESULT", "schema mismatch")
    regressions, missing, comparable = [], [], True
    if baseline["env"].get("machine") != current["env"].get("machine") or \
            baseline["env"].get("implementation") != current["env"].get("implementation"):
        comparable = False
    for case, b in baseline["cases"].items():
        c = current["cases"].get(case)
        if c is None:
            missing.append(case)
            continue
        if b.get("unit") == "ticks":
            if c["value"] > b["value"]:
                regressions.append({"case": case, "metric": "value", "baseline": b["value"], "current": c["value"]})
            continue
        for m in thresholds["metrics"]:
            lim = max(b[m] * (1 + thresholds["rel_tolerance"]), b[m] + thresholds["abs_floor_s"])
            if c[m] > lim:
                regressions.append({"case": case, "metric": m, "baseline": b[m], "current": c[m], "limit": lim})
    passed = not regressions and not missing and comparable
    return {"passed": passed, "comparable_env": comparable, "regressions": regressions, "missing": missing}


def error_budget_remaining(good: int, total: int, objective: float) -> float:
    """Fraction of the error budget left (1.0 = untouched, <0 = exhausted)."""
    if total < 0 or good < 0 or good > total or not 0 < objective < 1:
        raise ValueError("bad SLI inputs")
    if total == 0:
        return 1.0
    allowed = (1 - objective) * total
    return 1 - (total - good) / allowed


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="INV-08 benchmark + regression gate")
    ap.add_argument("--out", required=True)
    ap.add_argument("--baseline")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    res = run_suite(quick=a.quick)
    save(res, a.out)
    if a.baseline:
        verdict = compare(load(a.baseline), res)
        print(json.dumps(verdict, sort_keys=True))
        return 0 if verdict["passed"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
