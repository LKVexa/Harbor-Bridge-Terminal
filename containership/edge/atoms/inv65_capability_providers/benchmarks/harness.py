"""Benchmark / burst / soak harness with release gates (M27).

    python -m inv65_capability_providers.benchmarks.harness --scenario all --out evidence/performance-results.json

Scenarios (benchmarks/scenarios.json): dispatch latency through the full
ProviderService stack (authn+authz+lookup+admission+dispatch), cold start with
N durable links, burst overload shedding, and a short soak checking for
unbounded growth.  Gates compare against benchmarks/baselines/*.json; a
regression beyond tolerance => exit 1.  Numbers are host-local.
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

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    __package__ = "inv65_capability_providers.benchmarks"

HERE = pathlib.Path(__file__).resolve().parent


def _world():
    from ..tests.helpers import World
    return World


def _unthrottled(w):
    from ..runtime.admission import AdmissionController
    w.svc.admission = AdmissionController(tenant_rate=1e9, tenant_burst=10**9, link_rate=1e9, link_burst=10**9)
    return w


def dispatch(n=2000):
    World = _world(); w = _unthrottled(World()); w.svc.start(); w.link()
    tok_dec = [(w.token(), w.decision("call", "primary", ["get"])) for _ in range(n)]
    lat = []
    for t, d in tok_dec:
        t0 = time.perf_counter()
        w.svc.call(t, d, link_name="primary", op="get", payload={"key": "k"})
        lat.append(time.perf_counter() - t0)
    lat.sort()
    over = sum(1 for x in lat if x > 0.001)
    return {"n": n, "p50_ms": lat[n // 2] * 1e3, "p99_ms": lat[int(n * .99)] * 1e3, "max_ms": lat[-1] * 1e3,
            "over_1ms": over, "over_1ms_ratio": over / n}


def cold_start(links=2000):
    World = _world(); w = World(); w.svc.start()
    for i in range(links):
        w.svc.store.put(("acme", "prod", "sfo1", "shop", "orders", f"l{i}"), {"schema": "x", "config_version": 1, "config": {"bucket": "b", "user": "u"}})
    w.svc.store.compact()
    t0 = time.perf_counter(); w2 = World(state_dir=w.tmp, instance="inst-b"); n = w2.svc.start()
    return {"links": n, "start_s": time.perf_counter() - t0}


def burst(n=500):
    from ..runtime.admission import AdmissionController
    World = _world(); w = World(); w.svc.admission = AdmissionController(tenant_rate=100, tenant_burst=100)
    w.svc.start(); w.link(); w.link(tenant="globex", cfg={"bucket": "g", "user": "g"})
    ok = shed = 0
    for _ in range(n):
        try:
            w.call(); ok += 1
        except Exception as e:
            if getattr(e, "code", "") == "PK_PROVIDER_OVERLOADED":
                shed += 1
            else:
                raise
    quiet = w.call(tenant="globex")["result"]["bucket"] == "g"  # noisy tenant must not starve a quiet one
    return {"n": n, "admitted": ok, "shed": shed, "quiet_tenant_admitted": quiet}


def soak(seconds=5.0):
    World = _world(); w = _unthrottled(World()); w.svc.start(); w.link()
    tracemalloc.start(); calls = 0; t_end = time.monotonic() + seconds; snaps = []
    while time.monotonic() < t_end:
        w.call(); calls += 1
        if calls % 100 == 0:
            snaps.append(tracemalloc.get_traced_memory()[0])
    tracemalloc.stop()
    growth = (snaps[-1] - snaps[len(snaps) // 2]) if len(snaps) >= 4 else 0
    return {"seconds": seconds, "calls": calls, "mem_growth_second_half_bytes": growth, "audit_events": len(w.svc.audit.events()),
            "replay_cache_entries": len(w.svc.authn._seen), "trace_ring": len(w.svc.tracer.spans),
            "note": "growth is expected until bounded buffers fill: trace ring (2048), histogram reservoir (4096), "
                    "and the replay-nonce cache, which holds one entry per token until its expiry (<=100k entries). "
                    "A short soak cannot show the nonce-cache plateau."}


def gate(results: dict, baseline: dict) -> list[str]:
    fails = []
    if results["dispatch"]["over_1ms_ratio"] > baseline["dispatch"]["max_over_1ms_ratio"]:
        fails.append(f"dispatch over-1ms ratio {results['dispatch']['over_1ms_ratio']:.4f} > {baseline['dispatch']['max_over_1ms_ratio']}")
    if results["dispatch"]["p50_ms"] > baseline["dispatch"]["p50_ms"] * (1 + baseline["tolerance"]):
        fails.append("dispatch p50 regression beyond tolerance")
    if results["cold_start"]["start_s"] > baseline["cold_start"]["max_start_s"]:
        fails.append("cold start too slow")
    if not results["burst"]["quiet_tenant_admitted"]:
        fails.append("quiet tenant starved during burst")
    if results["burst"]["shed"] == 0:
        fails.append("burst never shed load (admission control not engaged)")
    return fails


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all")
    ap.add_argument("--out")
    ap.add_argument("--soak-s", type=float, default=5.0)
    a = ap.parse_args(argv)
    res = {"host": {"python": platform.python_version(), "machine": platform.machine(), "system": platform.system()},
           "dispatch": dispatch(), "cold_start": cold_start(), "burst": burst(), "soak": soak(a.soak_s)}
    base = json.loads((HERE / "baselines" / "local.json").read_text())
    res["gate_failures"] = gate(res, base)
    res["verdict"] = "PASS" if not res["gate_failures"] else "FAIL"
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("verdict", "gate_failures")} | {"p99_ms": round(res["dispatch"]["p99_ms"], 4)}))
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
