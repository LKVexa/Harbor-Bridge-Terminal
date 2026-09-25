"""Shared test fixtures (import-path setup + small cluster builders)."""
from __future__ import annotations

import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv04_current_orchestration.runtime import objects as o  # noqa: E402
from inv04_current_orchestration.runtime.api import InMemoryClusterAPI  # noqa: E402


class FakeClock:
    def __init__(self, t: float = 1_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


REQ = {"cpu_m": 100, "memory_mi": 128, "pods": 1}


def cluster(n_nodes=3, workloads=None, *, min_available=None, zones=None, heartbeat=None, **node_kw):
    """Build an InMemoryClusterAPI with replicas spread round-robin."""
    workloads = workloads or {"web": 3}
    nodes = [o.make_node(f"n{i}", zone=(zones[i] if zones else ""), last_heartbeat=heartbeat or 0.0, **node_kw)
             for i in range(n_nodes)]
    pods = []
    k = 0
    for w, count in sorted(workloads.items()):
        for i in range(count):
            pods.append(o.make_pod(f"{w}-{i}", w, f"n{k % n_nodes}", requests=REQ))
            k += 1
    pdbs = [o.DisruptionBudget(o.Meta(f"{w}-pdb"), selector=(("app", w),), min_available=m)
            for w, m in sorted((min_available or {}).items())]
    return InMemoryClusterAPI(nodes, pods, pdbs, desired=dict(workloads))
