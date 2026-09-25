#!/usr/bin/env python3
"""Scale/performance and recovery benchmarks (components 60, 62).

  python tools/bench.py [--nodes 200] [--pods 4000] [--drains 20] [--out bench.json]

Measures: planning latency (capacity preflight), end-to-end drain latency
p50/p95/p99 against the in-memory API, work-queue throughput, journal append
throughput with fsync, and crash-recovery time (RTO) for an interrupted drain
with RPO=0 checked (no lost or duplicated evictions).  Numbers are only
meaningful on the target hardware; record them with the host description.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from inv04_current_orchestration.runtime import objects as o  # noqa: E402
from inv04_current_orchestration.runtime.api import InMemoryClusterAPI  # noqa: E402
from inv04_current_orchestration.runtime.drain import DrainCoordinator  # noqa: E402
from inv04_current_orchestration.runtime.journal import Journal  # noqa: E402
from inv04_current_orchestration.runtime.resilience import Backoff  # noqa: E402
from inv04_current_orchestration.runtime.scheduling import plan_drain_capacity  # noqa: E402
from inv04_current_orchestration.runtime.workqueue import WorkQueue  # noqa: E402


class _Crash(BaseException):
    pass


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def build(n_nodes, n_pods, now):
    nodes = [o.make_node(f"n{i}", last_heartbeat=now, zone=f"z{i % 3}") for i in range(n_nodes)]
    workloads = max(1, n_pods // 20)
    pods = [o.make_pod(f"w{i % workloads}-{i}", f"w{i % workloads}", f"n{(i // workloads) % n_nodes}",
                       requests={"cpu_m": 50, "memory_mi": 64, "pods": 1}) for i in range(n_pods)]
    desired: dict[str, int] = {}
    for p in pods:
        desired[p.workload] = desired.get(p.workload, 0) + 1
    pdbs = [o.DisruptionBudget(o.Meta(f"{w}-pdb"), selector=(("app", w),), max_unavailable="10%") for w in desired]
    return InMemoryClusterAPI(nodes, pods, pdbs, desired=desired)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", type=int, default=50)
    ap.add_argument("--pods", type=int, default=1000)
    ap.add_argument("--drains", type=int, default=10)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    now = time.time()
    res: dict = {"host": {"python": sys.version.split()[0], "platform": platform.platform(), "cpus": os.cpu_count()},
                 "params": vars(a)}

    api = build(a.nodes, a.pods, now)
    pods, _ = api.list_pods()
    nodes, _ = api.list_nodes()
    t = []
    for i in range(min(a.drains, a.nodes)):
        victims = [p for p in pods if p.node == f"n{i}"]
        t0 = time.perf_counter()
        plan_drain_capacity(victims, nodes, pods, f"n{i}")
        t.append(time.perf_counter() - t0)
    res["preflight_s"] = {"p50": pct(t, 50), "p95": pct(t, 95), "p99": pct(t, 99), "max": max(t)}

    d = []
    for i in range(min(a.drains, a.nodes - 1)):
        c = DrainCoordinator(api, Journal(), clock=lambda: now, sleep=lambda s: None, settle=api.run_controllers,
                             backoff=Backoff(base=0, jitter=0))
        t0 = time.perf_counter()
        r = c.drain(f"n{i}", op_id=f"bench-{i}")
        d.append((time.perf_counter() - t0, r.phase))
    lat = [x for x, _ in d]
    res["drain_s"] = {"p50": pct(lat, 50), "p95": pct(lat, 95), "p99": pct(lat, 99), "max": max(lat),
                      "outcomes": {ph: sum(1 for _, p in d if p == ph) for _, ph in d}}

    q = WorkQueue(max_depth=10 ** 6)
    t0 = time.perf_counter()
    n = 100_000
    for i in range(n):
        q.add(i % 5000)
    got = 0
    while q.depth():
        k = q.get(timeout=0)
        q.done(k)
        got += 1
    res["workqueue_ops_per_s"] = round((n + got) / (time.perf_counter() - t0))

    with tempfile.TemporaryDirectory() as dd:
        j = Journal(os.path.join(dd, "j.jsonl"))
        t0 = time.perf_counter()
        for i in range(500):
            j.append(f"op{i}", "bench", "x", {"i": i})
        res["journal_fsync_appends_per_s"] = round(500 / (time.perf_counter() - t0))

        # RTO / RPO for an interrupted drain
        api2 = build(10, 200, now)
        path = os.path.join(dd, "rto.jsonl")
        calls = [0]

        def crash(op, target):
            if op == "evict":
                calls[0] += 1
                if calls[0] == 3:
                    raise _Crash()
        api2.fault_hook = crash
        try:
            DrainCoordinator(api2, Journal(path), clock=lambda: now, sleep=lambda s: None, settle=api2.run_controllers,
                             backoff=Backoff(base=0, jitter=0)).drain("n0", op_id="rto")
        except _Crash:
            pass
        api2.fault_hook = None
        t0 = time.perf_counter()
        out = DrainCoordinator(api2, Journal(path), clock=lambda: now, sleep=lambda s: None,
                               settle=api2.run_controllers, backoff=Backoff(base=0, jitter=0)).recover()
        res["recovery"] = {"rto_s": time.perf_counter() - t0, "phase": [r.phase for r in out],
                           "duplicate_evictions": len(api2.evictions) - len(set(api2.evictions)),
                           "rpo_lost_journal_records": 0 if Journal(path).verify() else "chain-broken"}
    text = json.dumps(res, indent=2, default=str)
    if a.out:
        pathlib.Path(a.out).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
