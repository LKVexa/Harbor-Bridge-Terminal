"""Reference-model benchmark and regression gate (C061-C070, C088 - reference scope only).

Measures the *Python control layer* - create/egress/teardown latency, burst and
teardown storms, per-session control-plane memory, leak convergence over churn -
with an environment fingerprint.  These numbers say nothing about Firecracker
boot time, VMM overhead, density, I/O or power; every such metric is reported
as NOT_MEASURED with the reason.  Thresholds come from
``governance/perf_thresholds.json`` and are PROPOSED until an owner approves them.

Usage: python tools/bench.py [--sessions N] [--out evidence/performance/bench.json]
"""
from __future__ import annotations

import argparse
import collections
import gc
import json
import pathlib
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
sys.path.insert(0, str(PKG / "tests"))

NOT_MEASURED = {
    "firecracker_cold_boot": "no Firecracker/KVM host in the audit environment",
    "snapshot_restore": "no snapshot artifacts exist",
    "guest_ready_first_exec": "no guest image exists",
    "vmm_rss_pss_per_session": "no VMM process",
    "host_density": "requires a qualified node",
    "block_io_network_throughput": "requires real TAP/overlay devices",
    "edge_power_thermal": "requires edge hardware and power instrumentation",
}


def pct(xs, p):
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


def run(n: int = 300, repeats: int = 3) -> dict:
    from _harness import build, token
    from inv71_heavy_agent_sandbox.control.resilience import NodeCapacity, Shape, TenantQuota
    results: dict[str, list[float]] = {"create": [], "egress": [], "teardown": []}
    mem_per_session, leak_growth = [], []
    for r in range(repeats):
        with tempfile.TemporaryDirectory() as d:
            # the external anchor sink is another system; keep it bounded so it is not
            # mistaken for controller residue
            c, ta, clock, *_ = build(d, anchors=collections.deque(maxlen=16), quotas={"t1": TenantQuota(n + 1, 10 * n, 4096 * n)},
                                     node=NodeCapacity(vcpu=10 * n, mem_mib=4096 * n, max_sessions=10 * n))
            gc.collect()
            tracemalloc.start()
            base = tracemalloc.get_traced_memory()[0]
            live = []
            for i in range(n):  # burst create
                t0 = time.perf_counter()
                s = c.create(token(ta), sid=f"b{r}-{i}", tenant="t1", shape=Shape(1, 512), idempotency_key=f"k{r}-{i}")
                results["create"].append(time.perf_counter() - t0)
                live.append(s)
            peak = tracemalloc.get_traced_memory()[0]
            mem_per_session.append((peak - base) / n)
            for s in live:
                t0 = time.perf_counter()
                c.connect(token(ta), sid=s["sid"], host="pypi.org", port=443)
                results["egress"].append(time.perf_counter() - t0)
            for s in live:  # teardown storm
                t0 = time.perf_counter()
                c.teardown(token(ta), sid=s["sid"], epoch=s["epoch"])
                results["teardown"].append(time.perf_counter() - t0)
            # churn convergence (C067-IMP-05): after the retention window, compact()
            # evicts CLOSED sessions/leases and sweeps expired idempotency keys and
            # replay nonces.  What remains is bounded caches (explain log, egress
            # decision log) plus dict capacity retained from the peak.
            clock.advance(3601)
            c.compact(retention_s=3600)
            gc.collect()
            after = tracemalloc.get_traced_memory()[0]
            tracemalloc.stop()
            leak_growth.append(after - base)
    summary = {}
    for k, xs in results.items():
        summary[k] = {"n": len(xs), "p50_ms": pct(xs, 50) * 1e3, "p95_ms": pct(xs, 95) * 1e3,
                      "p99_ms": pct(xs, 99) * 1e3, "max_ms": max(xs) * 1e3,
                      "stdev_ms": statistics.pstdev(xs) * 1e3}
    return {"schema": "PK_HEAVYBOX_BENCH/1", "scope": "reference control layer only (Python); not a microVM measurement",
            "environment": {"python": platform.python_version(), "impl": platform.python_implementation(),
                            "machine": platform.machine(), "platform": platform.platform(), "processor": platform.processor()},
            "params": {"sessions_per_repeat": n, "repeats": repeats, "warmup": "none (first repeat included)"},
            "latency": summary,
            "control_plane_bytes_per_live_session": statistics.median(mem_per_session),
            "residual_bytes_after_churn": statistics.median(leak_growth),
            "not_measured": NOT_MEASURED}


def gate(report: dict, thresholds: dict) -> dict:
    checks = []
    for metric, lim in thresholds["reference_latency_ms"].items():
        op, stat = metric.split(".")
        v = report["latency"][op][stat]
        checks.append({"metric": metric, "value": round(v, 4), "limit": lim, "status": "PASS" if v <= lim else "FAIL"})
    v = report["control_plane_bytes_per_live_session"]
    lim = thresholds["control_plane_bytes_per_live_session"]
    checks.append({"metric": "control_plane_bytes_per_live_session", "value": v, "limit": lim, "status": "PASS" if v <= lim else "FAIL"})
    v = report["residual_bytes_after_churn"]
    lim = thresholds["residual_bytes_after_churn"]
    checks.append({"metric": "residual_bytes_after_churn", "value": v, "limit": lim, "status": "PASS" if v <= lim else "FAIL"})
    for m in thresholds["production_metrics"]:
        checks.append({"metric": m, "status": "NOT_MEASURED", "reason": NOT_MEASURED.get(m, "no production path")})
    verdict = "FAIL" if any(c["status"] == "FAIL" for c in checks) else (
        "INCOMPLETE" if any(c["status"] == "NOT_MEASURED" for c in checks) else "PASS")
    return {"threshold_status": thresholds["status"], "checks": checks, "verdict": verdict}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=300)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    rep = run(a.sessions, a.repeats)
    th = json.loads((PKG / "governance" / "perf_thresholds.json").read_text())
    rep["gate"] = gate(rep, th)
    text = json.dumps(rep, indent=2)
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(text + "\n")
    print(json.dumps({k: {s: round(v, 3) for s, v in d.items() if s != "n"} for k, d in rep["latency"].items()}))
    print("bytes/session", rep["control_plane_bytes_per_live_session"], "residual", rep["residual_bytes_after_churn"],
          "gate", rep["gate"]["verdict"])
    return 1 if rep["gate"]["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
