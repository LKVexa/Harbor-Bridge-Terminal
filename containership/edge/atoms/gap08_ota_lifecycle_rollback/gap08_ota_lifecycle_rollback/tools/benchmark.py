"""Component 34: fleet-scale benchmark suite.

Runs complete rollouts through the real controller against simulated fleets
of increasing size and reports p50/p95/p99/max per-operation latency,
throughput (node-updates/s), peak Python heap (tracemalloc), CPU time,
durable-state size and audit-log growth.  Output: JSON (``--out``) plus a
table on stdout.  Numbers measure the controller + reference file store on
the build host; they are *not* production capacity claims — rerun on the
target control-plane hardware with the selected GAP-05 backend.

    python tools/benchmark.py --sizes 100 1000 5000 --out bench.json
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import statistics
import sys
import time
import tracemalloc

import _path  # noqa: F401
from gap08_ota_lifecycle_rollback.admission import AdmissionLimits
from gap08_ota_lifecycle_rollback.harness import COMPAT, GATEKEEPER, OPERATOR, build_world, spread_waves


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def plan(n):
    sizes, s, left = [], 1, n
    while left:
        s = min(left, s)
        if left - s < s:
            s = left
        sizes.append(s)
        left -= s
        s *= 4
    return sizes


def run(n: int) -> dict:
    racks = max(2, n // 30)
    w = build_world(n, sites=3, racks_per_site=racks, max_fraction_per_domain=0.75,
                    limits=AdmissionLimits(max_wave_fanout=max(500, n), max_inflight_commands=max(2000, 2 * n),
                                           api_rate_per_s=1e6, api_burst=1e6))
    w.topology.policy = type(w.topology.policy)(max_fraction_per_domain=1.0, min_survivors_per_domain=0,
                                                max_fraction_per_site=1.0)
    c = w.controller()
    lat = {"create": [], "step": [], "gate": []}
    tracemalloc.start()
    cpu0 = time.process_time()
    t0 = time.perf_counter()
    s = time.perf_counter()
    rid = c.create(OPERATOR, bundle="v2", waves=spread_waves(w, plan(n)), environment="bench",
                   verification=w.verification(), compat_profile=COMPAT)["rollout_id"]
    lat["create"].append(time.perf_counter() - s)
    while c.status(rid)["phase"] not in ("complete",):
        s = time.perf_counter()
        c.step(OPERATOR, rid)
        lat["step"].append(time.perf_counter() - s)
        w.clock.advance(90)
        p = w.store.load(rid).state["pending"]
        ok = [k for k, o in p["outcomes"].items() if o["status"] == "ok"]
        ev = w.evidence(rid, p["cohort"], ok, applied_at=p["applied_at"])
        s = time.perf_counter()
        c.gate(GATEKEEPER, rid, ev)
        lat["gate"].append(time.perf_counter() - s)
    wall = time.perf_counter() - t0
    cpu = time.process_time() - cpu0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    all_ops = lat["step"] + lat["gate"]
    state_bytes = sum(p.stat().st_size for p in (w.root / "store").glob("*.json"))
    return {"nodes": n, "waves": len(plan(n)), "wall_s": round(wall, 4), "cpu_s": round(cpu, 4),
            "node_updates_per_s": round(n / wall, 1), "peak_heap_mb": round(peak / 2 ** 20, 2),
            "op_latency_s": {k: {"p50": round(pct(v, 50), 5), "p95": round(pct(v, 95), 5),
                                 "p99": round(pct(v, 99), 5), "max": round(max(v), 5)}
                             for k, v in {**lat, "all": all_ops}.items() if v},
            "state_bytes": state_bytes, "audit_log_bytes": (w.root / "audit.log").stat().st_size,
            "commands_sent": w.channel.sent, "store_disk": "tmpfs" if str(w.root).startswith("/dev/shm") else "local"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", nargs="+", type=int, default=[50, 200, 1000])
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = {"schema": "PK_BENCHMARK/1", "host": {"python": sys.version.split()[0], "platform": platform.platform(),
                                                "cpus": os.cpu_count()},
           "max_rss_mb_before": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
           "runs": [run(n) for n in a.sizes]}
    print(f"{'nodes':>7} {'waves':>5} {'wall s':>8} {'upd/s':>8} {'step p95':>9} {'gate p95':>9} {'heap MB':>8} {'state KB':>9}")
    for r in res["runs"]:
        L = r["op_latency_s"]
        print(f"{r['nodes']:>7} {r['waves']:>5} {r['wall_s']:>8} {r['node_updates_per_s']:>8} "
              f"{L['step']['p95']:>9} {L['gate']['p95']:>9} {r['peak_heap_mb']:>8} {r['state_bytes'] // 1024:>9}")
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=2)
    return res


if __name__ == "__main__":
    main()
