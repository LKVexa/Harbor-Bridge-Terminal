"""Reproducible PLN-01 benchmark suite (MC-031, MC-032, MC-041).

Scenarios: chain (deep dependency), fanout (wide), service-path (full request
pipeline incl. auth/quota/audit), burst (concurrent submitters), and a
resource probe (peak traced memory).  Output is JSON, consumed by
``tools/perf_gate.py`` against ``conformance/perf_baseline.json``.

Developer/CI evidence only: fleet-scale and power figures require the
production reference hardware named in docs/PERFORMANCE.md.
"""
from __future__ import annotations

import json
import os
import pathlib
import platform
import sys
import tempfile
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pln01_intent_plane import IntentGraph, plan  # noqa: E402
from pln01_intent_plane.config import build_config  # noqa: E402
from pln01_intent_plane.service import IntentPlaneService  # noqa: E402
from pln01_intent_plane.store import DurableStore  # noqa: E402
from pln01_intent_plane.trust import HmacTokenAuthenticator, KeyProvider  # noqa: E402


def _p(samples, q):
    s = sorted(samples)
    return s[min(len(s) - 1, int(q * len(s)))]


def chain(n: int) -> dict:
    g = IntentGraph(max_nodes=n)
    prev = None
    t = time.perf_counter()
    for i in range(n):
        prev = g.declare("b", "p", f"n{i:06d}", {"i": i}, after=() if prev is None else (prev,))
    d = time.perf_counter() - t
    lat = []
    for _ in range(5):
        t = time.perf_counter()
        plan(g, {})
        lat.append(time.perf_counter() - t)
    return {"nodes": n, "declare_s": d, "plan_p50_s": _p(lat, .5), "plan_max_s": max(lat)}


def fanout(n: int) -> dict:
    g = IntentGraph(max_nodes=n + 1, max_dependencies_per_node=256)
    root = g.declare("b", "p", "root", {})
    t = time.perf_counter()
    for i in range(n):
        g.declare("b", "p", f"leaf{i:06d}", {"i": i}, after=(root,))
    d = time.perf_counter() - t
    t = time.perf_counter()
    plan(g, {})
    return {"nodes": n + 1, "declare_s": d, "plan_s": time.perf_counter() - t}


def _service(durable: bool):
    keys = KeyProvider(b"x" * 32)
    auth = HmacTokenAuthenticator(keys)
    cfg = build_config([("bench", {"limits": {"max_nodes": 200000}, "quotas": {
        "tenant_rate_per_second": 1e9, "tenant_burst": 10**9, "tenant_max_nodes": 200000,
        "max_concurrent_requests": 64, "max_queue_depth": 10000}})], author="bench")
    st = DurableStore(tempfile.mkdtemp(), keys, fsync=False, snapshot_every=10**9) if durable else None
    svc = IntentPlaneService(config=cfg, authenticator=auth, store=st, log_sink=lambda _l: None)
    return svc, auth.issue("bench", "service", [("intent:admin", "*")])


def service_path(n: int, durable: bool) -> dict:
    svc, tok = _service(durable)
    lat = []
    for i in range(n):
        req = {"schema": "PK_DECLARATION/1", "operation": "declare", "node": ["b", "p", f"n{i}"],
               "spec": {"i": i}, "request_id": f"r{i}"}
        t = time.perf_counter()
        r = svc.submit(req, credential=tok)
        lat.append(time.perf_counter() - t)
        if not r["ok"]:
            raise RuntimeError(r)
    return {"requests": n, "durable": durable, "p50_s": _p(lat, .5), "p99_s": _p(lat, .99),
            "throughput_rps": n / sum(lat)}


def burst(n: int, workers: int) -> dict:
    svc, tok = _service(False)

    def one(i):
        return svc.submit({"schema": "PK_DECLARATION/1", "operation": "declare", "node": ["b", "p", f"n{i}"],
                           "spec": {}, "request_id": f"b{i}"}, credential=tok)["ok"]
    t = time.perf_counter()
    with ThreadPoolExecutor(workers) as ex:
        ok = sum(ex.map(one, range(n)))
    el = time.perf_counter() - t
    return {"requests": n, "workers": workers, "ok": ok, "elapsed_s": el, "throughput_rps": n / el}


def memory(n: int) -> dict:
    tracemalloc.start()
    g = IntentGraph(max_nodes=n)
    for i in range(n):
        g.declare("b", "p", f"n{i}", {"i": i})
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"nodes": n, "peak_bytes": peak, "bytes_per_node": peak / n}


def run(scale: float = 1.0) -> dict:
    s = lambda x: max(10, int(x * scale))  # noqa: E731
    return {
        "environment": {"python": platform.python_version(), "machine": platform.machine(),
                        "system": platform.system(), "cpus": os.cpu_count()},
        "chain_10k": chain(s(10_000)),
        "fanout_10k": fanout(s(10_000)),
        "service_memory": service_path(s(2_000), False),
        "service_durable": service_path(s(1_000), True),
        "burst": burst(s(2_000), 16),
        "memory_10k": memory(s(10_000)),
    }


if __name__ == "__main__":
    scale = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    print(json.dumps(run(scale), indent=2))
