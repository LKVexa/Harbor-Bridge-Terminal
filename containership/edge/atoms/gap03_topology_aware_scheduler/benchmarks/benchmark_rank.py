"""Non-gating local benchmark for the GAP-03 1,000-candidate scoring SLO.

This is diagnostic evidence only.  Production certification must run on each
supported deployment class with controlled hardware, load, and telemetry.
"""
from __future__ import annotations

import importlib.util
import pathlib
import platform
import statistics
import sys
import time

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = PKG_DIR / "scheduler.py"
spec = importlib.util.spec_from_file_location("gap03_scheduler_bench", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
if spec.loader is None:
    raise RuntimeError(f"cannot load runtime module: {MODULE_PATH}")
spec.loader.exec_module(mod)


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * p) - 1))
    return ordered[index]


def main(runs: int = 200) -> None:
    topology = mod.Topology()
    for index in range(1001):
        topology.place(
            f"n{index:04d}",
            f"region-{index % 5}",
            f"site-{index % 25}",
            f"rack-{index % 100}",
        )
    candidates = [f"n{index:04d}" for index in range(1, 1001)]
    for _ in range(20):
        mod.rank(topology, "n0000", candidates)

    elapsed_ms: list[float] = []
    for _ in range(runs):
        started = time.perf_counter()
        mod.rank(topology, "n0000", candidates)
        elapsed_ms.append((time.perf_counter() - started) * 1000.0)

    print(f"python={sys.version.split()[0]}")
    print(f"platform={platform.platform()}")
    print(f"runs={runs}")
    print(f"candidates={len(candidates)}")
    print(f"p50_ms={statistics.median(elapsed_ms):.3f}")
    print(f"p95_ms={percentile(elapsed_ms, 0.95):.3f}")
    print(f"p99_ms={percentile(elapsed_ms, 0.99):.3f}")
    print(f"max_ms={max(elapsed_ms):.3f}")
    print("declared_slo_p99_ms=20.000")
    print("note=diagnostic_only_not_production_certification")


if __name__ == "__main__":
    main()
