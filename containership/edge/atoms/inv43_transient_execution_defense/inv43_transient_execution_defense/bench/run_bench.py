"""Checklists 34, 35, 36: reproducible benchmark harness, threshold gate,
capacity measurements.

    python -m inv43_transient_execution_defense.bench.run_bench [--out DIR] [--n N] [--gate]

What it measures (on the machine it runs on, recorded with the environment):

* ``decide_latency``  - PostureRegistry.decide end-to-end (authz, freshness,
  policy, audit append, metrics, explain) over N decisions: p50/p95/p99/max.
* ``core_latency``    - MitigationState.may_cotenant alone.
* ``submit_latency``  - attested read-back intake.
* ``syscall_ns``      - getppid() round trip: the kernel-entry cost that
  spectre_v2/meltdown-class mitigations tax.  This is a *baseline of the
  node as configured*, not a per-mitigation cost: attributing cost to one
  mitigation requires an A/B boot with that mitigation disabled, which this
  harness cannot do from userspace (STATUS item 34 remains BLOCKED on that).
* ``memory``          - tracemalloc bytes per node posture entry and per
  explain record (capacity model input, checklist 36).

``--gate`` compares against ``perf/thresholds.json``.  Every threshold there
is PROPOSED (no approver), so a met threshold reports
``met_under_proposed_threshold`` and never ``PASS``.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import statistics
import sys
import time
import tracemalloc

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE.parent
if str(PKG.parent) not in sys.path:
    sys.path.insert(0, str(PKG.parent))
sys.path.insert(0, str(PKG / "tests"))

from _harness import Fleet, W, pkg  # noqa: E402


def pct(xs, q):
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round(q / 100 * (len(xs) - 1)))))
    return xs[k]


def summarise(samples_s):
    us = [s * 1e6 for s in samples_s]
    return {"n": len(us), "p50_us": round(pct(us, 50), 2), "p95_us": round(pct(us, 95), 2),
            "p99_us": round(pct(us, 99), 2), "max_us": round(max(us), 2), "mean_us": round(statistics.fmean(us), 2)}


def bench(n: int) -> dict:
    f = Fleet(nodes=tuple(f"n{i:03d}" for i in range(50)))
    try:
        sub = []
        for node in f.roots:
            env = f.envelope(node)
            t = time.perf_counter()
            f.reg.submit(f"collector-{node}", env)
            sub.append(time.perf_counter() - t)
        nodes = sorted(f.roots)
        dec = []
        for i in range(n):
            t = time.perf_counter()
            f.reg.decide("sched", nodes[i % 50], W(f"a{i % 5}"), W(f"b{i % 3}"), tier="microvm")
            dec.append(time.perf_counter() - t)
        st = f.reg._nodes[nodes[0]]["state"]
        core = []
        for _ in range(n):
            t = time.perf_counter()
            st.may_cotenant("a", "b")
            core.append(time.perf_counter() - t)
        sc = []
        for _ in range(5):
            k = 20000
            t = time.perf_counter_ns()
            for _ in range(k):
                os.getppid()
            sc.append((time.perf_counter_ns() - t) / k)
        tracemalloc.start()
        g = Fleet(nodes=tuple(f"m{i:03d}" for i in range(100)))
        a0 = tracemalloc.get_traced_memory()[0]
        for node in g.roots:
            g.attest(node)
        a1 = tracemalloc.get_traced_memory()[0]
        for i in range(500):
            g.reg.decide("sched", "m000", W("a"), W("b"), tier="microvm")
        a2 = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        g.close()
        return {
            "decide_latency": summarise(dec),
            "core_latency": summarise(core),
            "submit_latency": summarise(sub),
            "syscall_ns": {"median": round(statistics.median(sc), 1), "runs": [round(x, 1) for x in sc]},
            "memory": {"bytes_per_node_posture": int((a1 - a0) / 100),
                       "bytes_per_decision_incl_explain_and_audit": int((a2 - a1) / 500)},
        }
    finally:
        f.close()


def environment() -> dict:
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(), "cpu_count": os.cpu_count(),
            "component_version": pkg.__version__, "optimized_mode": not __debug__}


def gate(results: dict, thresholds: dict) -> dict:
    out = {"schema": "INV43_PERF_GATE/1", "threshold_status": thresholds.get("status"), "checks": []}
    for metric, lim in thresholds["limits"].items():
        group, field = metric.split(".")
        val = results[group][field]
        ok = val <= lim
        verdict = ("met_under_proposed_threshold" if ok else "exceeded_proposed_threshold") \
            if thresholds.get("status") != "APPROVED" else ("PASS" if ok else "FAIL")
        out["checks"].append({"metric": metric, "value": val, "limit": lim, "verdict": verdict})
    out["overall"] = "FAIL" if any(c["verdict"] in ("FAIL", "exceeded_proposed_threshold") for c in out["checks"]) \
        else ("PASS" if thresholds.get("status") == "APPROVED" else "NOT_CERTIFIED_THRESHOLDS_UNAPPROVED")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--out", default=str(PKG / "evidence" / "perf"))
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args(argv)
    res = {"schema": "INV43_BENCH/1", "environment": environment(), "results": bench(a.n)}
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "baseline.json").write_text(json.dumps(res, indent=2, sort_keys=True))
    rc = 0
    if a.gate:
        g = gate(res["results"], json.loads((PKG / "perf" / "thresholds.json").read_text()))
        (out / "gate.json").write_text(json.dumps(g, indent=2, sort_keys=True))
        print(json.dumps(g, indent=2))
        rc = 1 if g["overall"] == "FAIL" else 0
    print(json.dumps(res["results"], indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
