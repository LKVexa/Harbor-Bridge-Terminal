"""G13-MC-032 reproducible performance benchmark (and G13-MC-033 edge harness hook).

python -m gap13_policy_engine.bench [--quick] [--out PATH]

Measures, per rule-set size: bundle verify+parse+activate time, p50/p95/p99/max
evaluate latency (engine and full service path), single-thread throughput,
steady/burst behaviour, tracemalloc peak memory and process CPU time.  Uses
fixed seeds and records the environment so runs are comparable.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "tests"))


def _pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def rules(n, rng):
    out = []
    for i in range(n):
        m = {"resource": f"res-{i % max(1, n // 4)}", "action": rng.choice(["read", "write", "delete"])}
        if i % 3 == 0:
            m["resource_type"] = rng.choice(["log", "db", "bucket"])
        out.append({"name": f"r{i:05}", "effect": "deny" if i % 5 == 0 else "allow", "scope": "estate", "match": m})
    return out


def run(sizes=(100, 1000, 10000), requests=5000, burst=20000) -> dict:
    import testkit as k
    from gap13_policy_engine import PolicyEngine
    from gap13_policy_engine.authz import Authorizer, RateLimiter
    rng = random.Random(2026)
    results = {"schema": "PK_POLICY_BENCH/1", "engine_release": k.g.__version__,
               "environment": {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
                               "platform": platform.platform(), "machine": platform.machine(),
                               "cpu_count": os.cpu_count()},
               "sizes": {}}
    for n in sizes:
        rs = rules(n, rng)
        env = k.envelope(1, rs)
        tracemalloc.start()
        c0 = time.process_time()
        t0 = time.perf_counter()
        big = k.g.Limits(max_bundle_bytes=16 * 1024 * 1024, max_rules=max(10_000, n))
        res = k.verifier(limits=big).verify(env, now=k.T0)
        if not res.verified:
            raise SystemExit(f"bench bundle failed verification: {res.reason}")
        eng = PolicyEngine("prod")
        eng.activate(res)
        load_ms = (time.perf_counter() - t0) * 1000
        reqs = [{"resource": f"res-{rng.randrange(max(1, n // 4))}", "action": rng.choice(["read", "write"]),
                 "resource_type": rng.choice(["log", "db"])} for _ in range(requests)]
        lat = []
        for r in reqs:
            s = time.perf_counter()
            eng.evaluate(r)
            lat.append((time.perf_counter() - s) * 1000)
        # linear-scan reference for the compiled index (MC-029)
        lin = []
        for r in reqs[:500]:
            s = time.perf_counter()
            sorted([x for x in eng.rules if x.matches(r)], key=lambda x: (-x.specificity, x.effect != "deny", x.name))
            lin.append((time.perf_counter() - s) * 1000)
        clk = k.Clock()
        svc, _ = k.service(require_separation_of_duties=False, clock=clk,
                           authorizer=Authorizer("prod", clock=clk.wall, limiter=RateLimiter(10**9)),
                           verifier=k.verifier(limits=big), config=k.g.EngineConfig(limits=big))
        svc.load(k.principal("alice", clock=clk), env)
        app = k.principal("svc-a", ("service",), kind="service", clock=clk)
        slat = []
        for r in reqs[:2000]:
            s = time.perf_counter()
            svc.evaluate(app, {"action": r["action"], "resource": r["resource"]})
            slat.append((time.perf_counter() - s) * 1000)
        t1 = time.perf_counter()
        for i in range(burst):
            eng.evaluate(reqs[i % len(reqs)])
        burst_s = time.perf_counter() - t1
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        results["sizes"][str(n)] = {
            "load_ms": round(load_ms, 3),
            "engine_ms": {"p50": _pct(lat, .5), "p95": _pct(lat, .95), "p99": _pct(lat, .99), "max": max(lat),
                          "mean": statistics.fmean(lat)},
            "linear_scan_ms_p50": _pct(lin, .5),
            "service_ms": {"p50": _pct(slat, .5), "p95": _pct(slat, .95), "p99": _pct(slat, .99), "max": max(slat)},
            "throughput_eval_per_s": round(burst / burst_s),
            "peak_memory_bytes": peak,
            "cpu_s": round(time.process_time() - c0, 3),
        }
        for kk in ("engine_ms", "service_ms"):
            results["sizes"][str(n)][kk] = {a: round(b, 5) for a, b in results["sizes"][str(n)][kk].items()}
    results["overload"] = overload_probe()
    return results


def overload_probe() -> dict:
    """Burst beyond max_concurrency: every excess request must be shed with Overloaded, none hang."""
    import threading
    import testkit as k
    from gap13_policy_engine import errors as E
    class SlowContext:                                   # 2 ms trusted-context lookup so requests overlap
        def context(self, subject):
            time.sleep(0.002)
            return {"tenant": "t1"}
    svc, c = k.service(require_separation_of_duties=False, context=SlowContext(),
                       config=k.g.EngineConfig(limits=k.g.Limits(max_concurrency=4)))
    svc.load(k.principal("alice", clock=c), k.envelope(1))
    app = k.principal("svc-a", ("service",), kind="service", clock=c)
    shed = ok = 0
    lock = threading.Lock()
    gate = threading.Barrier(32)

    def worker():
        nonlocal shed, ok
        gate.wait()
        for _ in range(25):
            try:
                svc.evaluate(app, {"action": "read"})
                with lock:
                    ok += 1
            except E.Overloaded:
                with lock:
                    shed += 1
    ts = [threading.Thread(target=worker) for _ in range(32)]
    [t.start() for t in ts]
    [t.join(30) for t in ts]
    return {"requests": 32 * 25, "served": ok, "shed": shed, "hung_threads": sum(t.is_alive() for t in ts)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run(sizes=(100, 1000) if a.quick else (100, 1000, 10000), requests=2000 if a.quick else 5000,
              burst=5000 if a.quick else 20000)
    text = json.dumps(res, indent=2, sort_keys=True)
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
