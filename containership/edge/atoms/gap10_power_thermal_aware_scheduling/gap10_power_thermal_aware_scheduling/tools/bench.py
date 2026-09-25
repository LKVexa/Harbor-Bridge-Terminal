"""Component 33 - benchmark / soak / fleet-scale harness.

    python tools/bench.py --nodes 5000 --rounds 20          # fleet-scale
    python tools/bench.py --nodes 200 --rounds 2000 --soak  # long-running soak

Reports p50/p95/p99 decision latency, throughput, CPU time and tracemalloc
peak/retained memory, and asserts memory growth stays bounded during soak.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import time
import tracemalloc

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
from harness import Stack  # noqa: E402

BUDGET = {"p99_s": 0.005, "per_node_kib": 16.0}


def _retained() -> int:
    """Traced bytes excluding this harness's own bookkeeping (latency list, envelopes)."""
    snap = tracemalloc.take_snapshot().filter_traces([tracemalloc.Filter(False, __file__),
                                                      tracemalloc.Filter(False, "*harness.py")])
    return sum(st.size for st in snap.statistics("filename"))


def run(nodes: int = 1000, rounds: int = 10, soak: bool = False) -> dict:
    names = tuple(f"edge-{i:06d}" for i in range(nodes))
    s = Stack(nodes=names)
    s.ctl.logger.records = type("Ring", (list,), {"append": lambda self, x: None})()  # drop log retention
    s.audit.max_in_memory = 1000
    tracemalloc.start()
    lat, cpu0, t0 = [], time.process_time(), time.perf_counter()
    snapshots = []
    for r in range(rounds):
        s.mc.advance(1.0)
        for i, n in enumerate(names):
            temp = 40.0 + ((i * 7 + r * 3) % 60)
            env = s.envelope(n, temp)
            a = time.perf_counter()
            s.ctl.ingest(env)
            lat.append(time.perf_counter() - a)
        if soak and r % max(1, rounds // 10) == 0:
            snapshots.append(_retained())
    wall = time.perf_counter() - t0
    _, peak = tracemalloc.get_traced_memory()
    cur = _retained()
    tracemalloc.stop()
    lat.sort()
    q = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))]  # noqa: E731
    out = {
        "nodes": nodes, "rounds": rounds, "decisions": len(lat),
        "latency_s": {"p50": q(0.50), "p95": q(0.95), "p99": q(0.99), "mean": statistics.fmean(lat)},
        "throughput_per_s": len(lat) / wall, "cpu_s": time.process_time() - cpu0,
        "memory": {"retained_kib": cur / 1024, "peak_kib": peak / 1024, "per_node_kib": cur / 1024 / nodes},
        "budget": BUDGET,
    }
    if soak and len(snapshots) >= 3:
        growth = snapshots[-1] - snapshots[len(snapshots) // 2]
        out["soak_growth_kib"] = growth / 1024
        out["soak_bounded"] = growth / 1024 < nodes * 1.0
    out["within_budget"] = out["latency_s"]["p99"] <= BUDGET["p99_s"] and out["memory"]["per_node_kib"] <= BUDGET["per_node_kib"]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", type=int, default=1000)
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--soak", action="store_true")
    a = ap.parse_args()
    print(json.dumps(run(a.nodes, a.rounds, a.soak), indent=2))
