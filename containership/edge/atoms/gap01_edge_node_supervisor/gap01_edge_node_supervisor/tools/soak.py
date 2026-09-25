"""Soak / burst / fleet-scale simulation (49).

Runs N simulated nodes (each a full controller over fake runtimes) through
high-churn admit/drain/restart cycles for a duration, then checks invariants
and memory growth (tracemalloc).  Usage: python tools/soak.py [nodes] [seconds]
"""
from __future__ import annotations

import json
import pathlib
import random
import sys
import time
import tracemalloc

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.path.insert(0, str(PKG / "tests"))
from helpers import Harness  # noqa: E402

from gap01_edge_node_supervisor.config import SupervisorConfig  # noqa: E402
from gap01_edge_node_supervisor.store import AuditLog  # noqa: E402


def main(nodes=20, seconds=20.0, seed=1) -> dict:
    rnd = random.Random(seed)
    cfg = SupervisorConfig(rate_burst=100_000, rate_per_second=100_000, max_queue_depth=10_000)
    fleet = [Harness(config=cfg) for _ in range(nodes)]
    tracemalloc.start()
    base = tracemalloc.take_snapshot()
    ops = cycles = violations = 0
    end = time.time() + seconds
    while time.time() < end:
        for i, h in enumerate(fleet):
            h.call("hr", "report_health", {"signal": "runtime", "ok": True})
            h.call("cp", "transition", {"to": "ready"})
            for j in range(rnd.randrange(1, 30)):
                h.admit(f"c{cycles}-{j}", rnd.choice(["trusted", "hostile", "untrusted"]))
                ops += 1
            h.call("cp", "drain")
            h.clock.advance(100); h.ctl.tick()
            if h.ctl.sup.state == "stopped" and h.ctl.sup.workloads:
                violations += 1
            fleet[i] = Harness(config=cfg)  # node replaced (fresh boot) — churn
            ops += 4
        cycles += 1
    import gc
    gc.collect()
    snap = tracemalloc.take_snapshot()
    growth = sum(s.size_diff for s in snap.compare_to(base, "filename"))
    audit_ok = all(AuditLog.verify(h.ctl.dir / "audit.jsonl")[0] for h in fleet)
    return {"nodes": nodes, "seconds": seconds, "cycles": cycles, "ops": ops,
            "ops_per_s": round(ops / seconds, 1), "invariant_violations": violations,
            "audit_chains_ok": audit_ok, "tracemalloc_growth_kb": round(growth / 1024, 1)}


if __name__ == "__main__":
    a = sys.argv[1:]
    print(json.dumps(main(int(a[0]) if a else 20, float(a[1]) if len(a) > 1 else 20.0), indent=2))
