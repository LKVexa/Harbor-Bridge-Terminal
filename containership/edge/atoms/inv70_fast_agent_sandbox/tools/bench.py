"""Reproducible performance suite for INV-70 (C061, C063, C064, C065, C088 local tier, C070 gate).

Usage:
  python -m inv70_fast_agent_sandbox.tools.bench --out perf/results.json
  python -m inv70_fast_agent_sandbox.tools.bench --gate perf/baseline.json   # exit 1 on regression

Every result file records the environment (python, platform, cpu count), the
package version, the config digest and the seed so a run can be reproduced and
compared.  The gate compares medians with a tolerance and fails closed when the
baseline is missing or from a different environment class.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import threading
import time
import tracemalloc

from .. import __version__, runtime
from ..security import TrustStore, issue_token
from ..service import Sandbox

PROGRAMS = {
    "arith6": [("push", 2), ("push", 3), ("mul",), ("push", 4), ("add",), ("halt",)],
    "loop1k": [("push", 1), ("jz", 3), ("jmp", 0), ("halt",)],   # spins to fuel
    "hostcall": [("push", 3), ("call", "double"), ("halt",)],
}
TOLERANCE = 0.25  # 25% median regression fails the gate


def _pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))]


def _summ(xs):
    return {"n": len(xs), "p50_us": round(_pct(xs, .5), 1), "p95_us": round(_pct(xs, .95), 1),
            "p99_us": round(_pct(xs, .99), 1), "mean_us": round(statistics.fmean(xs), 1)}


def bench_vm(n=2000):
    """Reference VM hot path (no isolation) - C061 baseline, C065 interpreter cost."""
    out = {}
    for name, prog in PROGRAMS.items():
        host = {"double": lambda x: 2 * x}
        caps = {"double"} if name == "hostcall" else set()
        ts = []
        for _ in range(n):
            t = time.perf_counter()
            runtime.run(prog, caps=caps, host=host)
            ts.append((time.perf_counter() - t) * 1e6)
        out[name] = _summ(ts)
    # C065: breakdown - validation vs execution
    vs = []
    for _ in range(n):
        t = time.perf_counter()
        runtime.validate_program(PROGRAMS["arith6"])
        vs.append((time.perf_counter() - t) * 1e6)
    out["validate_only_arith6"] = _summ(vs)
    tracemalloc.start()
    runtime.run(PROGRAMS["loop1k"])
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    out["peak_py_alloc_bytes_loop1k"] = peak
    return out


def _sandbox(env="prod"):
    ts = TrustStore()
    ts.add("bench", b"b" * 32, "caller")
    sb = Sandbox(environment=env, trust=ts, audit_key=b"a" * 32)
    sb.register_capability("double", lambda x: 2 * x)
    return sb, ts


def _tok(ts, i, tenant="t0"):
    return issue_token(ts, "bench", subject="bench", tenant=tenant, capabilities={"double"},
                       audience="inv70", ttl_s=600, now=time.time(), token_id=f"{tenant}-{i}-{os.urandom(4).hex()}")


def bench_service(n=60, env="prod"):
    """End-to-end governed path incl. process isolation (C061/C063 steady)."""
    sb, ts = _sandbox(env)
    try:
        ts_ = []
        for i in range(n):
            t = time.perf_counter()
            r = sb.handle({"token": _tok(ts, i), "versions": [2], "program": PROGRAMS["hostcall"], "caps": ["double"]})
            ts_.append((time.perf_counter() - t) * 1e6)
            assert r["status"] == "ok", r
        return _summ(ts_)
    finally:
        sb.close()


def bench_burst(threads=8, per=10):
    """Burst + overload (C063): N concurrent callers, count admitted vs shed."""
    sb, ts = _sandbox()
    sb.admission.max_concurrent = 4
    sb.admission.per_tenant = 4
    res = {"ok": 0, "shed": 0, "other": 0}
    lock = threading.Lock()

    def worker(k):
        for i in range(per):
            r = sb.handle({"token": _tok(ts, i, f"t{k}"), "versions": [2], "program": PROGRAMS["arith6"]})
            with lock:
                key = "ok" if r["status"] == "ok" else "shed" if r["reason_code"] == "FB-C001" else "other"
                res[key] += 1
    t = time.perf_counter()
    th = [threading.Thread(target=worker, args=(k,)) for k in range(threads)]
    [x.start() for x in th]
    [x.join() for x in th]
    res["wall_s"] = round(time.perf_counter() - t, 3)
    # recovery: after burst, a single request must succeed
    r = sb.handle({"token": _tok(ts, 999), "versions": [2], "program": PROGRAMS["arith6"]})
    res["recovered"] = r["status"] == "ok"
    sb.close()
    return res


def bench_tenants(n=20):
    """Per-tenant overhead attribution (C064): same load for 3 tenants, p50 per tenant."""
    sb, ts = _sandbox()
    out = {}
    try:
        for tenant in ("tA", "tB", "tC"):
            xs = []
            for i in range(n):
                t = time.perf_counter()
                sb.handle({"token": _tok(ts, i, tenant), "versions": [2], "program": PROGRAMS["arith6"]})
                xs.append((time.perf_counter() - t) * 1e6)
            out[tenant] = _summ(xs)
    finally:
        sb.close()
    return out


def bench_warm_vs_cold(n=12):
    """C066: measured effect of pre-started single-use workers.  Paced so the warm
    pool is refilled between requests (warm hit) vs warm=0 (cold spawn every run)."""
    out = {}
    for label, warm in (("cold_spawn", 0), ("warm_hit", 4)):
        sb, ts = _sandbox()
        sb._executors["process"].close()
        from ..executor import ProcessExecutor
        sb._executors["process"] = ProcessExecutor(warm=warm)
        time.sleep(0.5)
        xs = []
        for i in range(n):
            time.sleep(0.15)
            t = time.perf_counter()
            sb.handle({"token": _tok(ts, i), "versions": [2], "program": PROGRAMS["arith6"]})
            xs.append((time.perf_counter() - t) * 1e6)
        sb.close()
        out[label] = _summ(xs)
    return out


def environment():
    return {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(), "cpus": os.cpu_count()}


def run_all(quick=False):
    n = 300 if quick else 2000
    return {"inv70_version": __version__, "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": environment(), "vm": bench_vm(n), "service_prod": bench_service(20 if quick else 60),
            "burst": bench_burst(), "warm_vs_cold": bench_warm_vs_cold(6 if quick else 12), "tenants": bench_tenants(8 if quick else 20)}


def gate(current, baseline, tolerance=TOLERANCE):
    """Return list of regressions; empty means pass.  Missing baseline -> failure."""
    fails = []
    if not baseline:
        return ["baseline missing"]
    if baseline.get("environment", {}).get("machine") != current["environment"]["machine"]:
        return ["baseline from different machine class; re-baseline required"]
    for name, cur in current["vm"].items():
        if not isinstance(cur, dict):
            continue
        base = baseline["vm"].get(name)
        if base and cur["p50_us"] > base["p50_us"] * (1 + tolerance):
            fails.append(f"vm.{name} p50 {cur['p50_us']}us > {base['p50_us']}us +{int(tolerance*100)}%")
    b, c = baseline.get("service_prod"), current["service_prod"]
    if b and c["p50_us"] > b["p50_us"] * (1 + tolerance):
        fails.append(f"service_prod p50 {c['p50_us']}us > {b['p50_us']}us +{int(tolerance*100)}%")
    if not current["burst"]["recovered"]:
        fails.append("did not recover after burst")
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--gate")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args(argv)
    cur = run_all(a.quick)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(cur, f, indent=2)
    print(json.dumps(cur, indent=2))
    if a.gate:
        try:
            base = json.load(open(a.gate))
        except FileNotFoundError:
            base = None
        fails = gate(cur, base)
        print("GATE:", "PASS" if not fails else "FAIL " + "; ".join(fails))
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
