"""Performance benchmarks (50): transition, admission, drain throughput,
persistence overhead (fsync on/off), restart-recovery time, and telemetry
render cost.  Emits JSON; thresholds live in docs/CAPACITY.md."""
from __future__ import annotations

import json
import pathlib
import statistics
import sys
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.path.insert(0, str(PKG / "tests"))
from helpers import Harness  # noqa: E402

from gap01_edge_node_supervisor.config import SupervisorConfig  # noqa: E402


def timed(fn, n):
    xs = []
    for i in range(n):
        t = time.perf_counter(); fn(i); xs.append(time.perf_counter() - t)
    xs.sort()
    return {"n": n, "p50_ms": round(1000 * xs[n // 2], 3), "p99_ms": round(1000 * xs[int(n * .99) - 1], 3),
            "mean_ms": round(1000 * statistics.mean(xs), 3)}


def run(n_workloads=500, fsync=False) -> dict:
    cfg = SupervisorConfig(rate_burst=100_000, rate_per_second=100_000, max_workloads=100_000,
                           max_queue_depth=100_000)
    h = Harness(config=cfg)
    h.ctl.store.fsync = fsync; h.ctl.audit.fsync = fsync
    h.make_ready()
    out = {"fsync": fsync, "workloads": n_workloads}
    out["admit"] = timed(lambda i: h.admit(f"w{i}"), n_workloads)
    out["status"] = timed(lambda i: h.call("cp", "status"), 200)
    t = time.perf_counter(); r = h.call("cp", "drain"); dt = time.perf_counter() - t
    out["drain"] = {"workloads": n_workloads, "seconds": round(dt, 4), "complete": r["result"]["complete"],
                    "per_workload_ms": round(1000 * dt / n_workloads, 3)}
    t = time.perf_counter(); h.restart(); out["restart_recovery_s"] = round(time.perf_counter() - t, 4)
    t = time.perf_counter(); h.ctl.metrics.render(); out["metrics_render_ms"] = round(1000 * (time.perf_counter() - t), 3)
    h2 = Harness(config=cfg); h2.ctl.store.fsync = fsync
    out["transition_cycle"] = timed(lambda i: (h2.call("hr", "report_health", {"signal": "runtime", "ok": True}),
                                               h2.call("cp", "transition", {"to": "ready"}),
                                               h2.call("cp", "cordon")), 100)
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    print(json.dumps({"no_fsync": run(n, False), "fsync": run(min(n, 200), True)}, indent=2))
