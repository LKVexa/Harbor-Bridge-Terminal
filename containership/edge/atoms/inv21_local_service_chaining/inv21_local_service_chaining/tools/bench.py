"""Reproducible benchmark harness (GAP-022, GAP-023, GAP-024).

    python -m inv21_local_service_chaining.tools.bench --out evidence/bench.json [--n 20000]
    python -m inv21_local_service_chaining.tools.bench --check evidence/bench.json --baseline evidence/bench_baseline.json

Scenarios (each reports n, p50/p90/p99/p999/max in microseconds, and the
environment fingerprint):

* ``compat_local``       -- 4.x call(): decision + direct dispatch, no policy/audit
* ``prod_local``         -- invoke(): authenticated ctx, guarded authoritative policy
                            (thread-pool timeout guard), audit chain, admission
* ``prod_local_cached``  -- as above with a 5 s policy decision cache
* ``prod_remote_loopback`` -- full PK_LOCAL_CHAIN/1 wire encode/validate/decode, no socket
* ``prod_remote_http``   -- same over a real loopback HTTP/1.1 socket
* ``serialization``      -- cost of the JSON round-trip that local chaining avoids,
                            and an identity check proving the local path hands the
                            *same* object to the handler (zero-copy semantics)
* ``overload``           -- shed rate and recovery when in-flight is saturated
* ``tenant_overhead``    -- p99 with 1 vs 200 active tenants

The SLO in the contract (p99 local dispatch < 20 us) is evaluated against
``prod_local_cached`` and ``compat_local``; the result is recorded as measured,
never asserted. Power/thermal measurement is NOT available from userspace in the
authoring environment and is recorded as ``not_measured``.
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


def _pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]


def _summ(samples_ns):
    us = [s / 1000 for s in samples_ns]
    return {"n": len(us), "p50_us": round(_pct(us, 50), 3), "p90_us": round(_pct(us, 90), 3),
            "p99_us": round(_pct(us, 99), 3), "p999_us": round(_pct(us, 99.9), 3),
            "max_us": round(max(us), 3), "mean_us": round(statistics.fmean(us), 3)}


def _time(fn, n, warm=500):
    for _ in range(warm):
        fn()
    out = []
    pc = time.perf_counter_ns
    for _ in range(n):
        t = pc(); fn(); out.append(pc() - t)
    return _summ(out)


def run(n: int) -> dict:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, here)
    from inv21_local_service_chaining import __version__
    from inv21_local_service_chaining.admission import AdmissionController
    from inv21_local_service_chaining.audit import AuditLog
    from inv21_local_service_chaining.chain import Chainer
    from inv21_local_service_chaining.config import ChainConfig
    from inv21_local_service_chaining.context import CallContext, IdentityVerifier
    from inv21_local_service_chaining.errors import Overloaded
    from inv21_local_service_chaining.policy import GuardedProvider, StaticPolicyProvider
    from inv21_local_service_chaining.residency import Residency
    from inv21_local_service_chaining.transport import (ChainEndpoint, ChainHttpServer, HttpJsonTransport,
                                                        LoopbackTransport)

    v = IdentityVerifier({"k1": b"k" * 32})
    tok = v.issue("svc-a", "acme")
    ctx = CallContext(v.verify(tok), "t-b", credential=tok)
    cfg = ChainConfig(mode="production", residency_lease_s=60, max_in_flight=100000,
                      max_in_flight_per_tenant=100000)

    def prod(host, cache=0.0, transport=None):
        res = Residency(host, default_lease_s=60)
        ch = Chainer(res, config=cfg, policy=GuardedProvider(StaticPolicyProvider([("acme", "svc", "invoke")]),
                                                             cache_ttl_s=cache),
                     transport=transport or LoopbackTransport(None),
                     audit=AuditLog(b"a" * 32, memory_max=1024), trusted_issuers=frozenset({"pk-runtime"}),
                     verifier=v)
        return ch, res

    results = {}
    r0 = Residency("h"); r0.place("svc", "acme", lambda ch, req, p, t, tid: req)
    c0 = Chainer(r0)
    results["compat_local"] = _time(lambda: c0.call("svc", "acme", 1), n)

    ch, res = prod("h"); res.place("svc", "acme", lambda hop, r: r, abi="hop")
    results["prod_local"] = _time(lambda: ch.invoke("svc", 1, ctx), n)
    chc, resc = prod("h", cache=5.0); resc.place("svc", "acme", lambda hop, r: r, abi="hop")
    results["prod_local_cached"] = _time(lambda: chc.invoke("svc", 1, ctx), n)

    b, rb = prod("hb"); rb.place("svc", "acme", lambda hop, r: r, abi="hop")
    ep = ChainEndpoint(b, v)
    a, _ = prod("ha", transport=LoopbackTransport(ep))
    results["prod_remote_loopback"] = _time(lambda: a.invoke("svc", {"x": [1, 2, 3]}, ctx), max(1000, n // 4))
    with ChainHttpServer(ep) as srv:
        ah, _ = prod("ha", transport=HttpJsonTransport(srv.url))
        results["prod_remote_http"] = _time(lambda: ah.invoke("svc", {"x": [1, 2, 3]}, ctx), max(300, n // 40), warm=50)

    payload = {"rows": [{"id": i, "v": "x" * 32} for i in range(64)]}
    seen = []
    rz = Residency("h"); rz.place("svc", "acme", lambda hop, r: seen.append(r is payload) or r, abi="hop")
    chz, _ = prod("h", cache=5.0)
    chz.residency = rz
    chz.invoke("svc", payload, ctx)
    results["serialization"] = {
        "json_round_trip_4KiB": _time(lambda: json.loads(json.dumps(payload)), n // 4),
        "local_path_passes_same_object": all(seen),
        "note": "local path performs no serialization or copy; handlers receive the caller's object "
                "(aliasing is part of the contract: see docs/SEMANTIC_EQUIVALENCE.md)"}

    adm = AdmissionController(max_in_flight=8, max_in_flight_per_tenant=8)
    held = [adm.admit("t") for _ in range(8)]
    for h in held:
        h.__enter__()
    shed = 0
    for _ in range(1000):
        try:
            with adm.admit("t"):
                pass
        except Overloaded:
            shed += 1
    for h in held:
        h.__exit__(None, None, None)
    t0 = time.perf_counter_ns()
    with adm.admit("t"):
        pass
    results["overload"] = {"attempts_while_saturated": 1000, "shed": shed,
                           "recovery_first_admit_us": round((time.perf_counter_ns() - t0) / 1000, 3)}

    toks = [v.issue("s", f"t{i}") for i in range(200)]
    ctxs = [CallContext(v.verify(t), "t-b", credential=t) for t in toks]
    cht, rest = prod("h", cache=5.0)
    for i in range(200):
        rest.place(f"svc{i}", f"t{i}", lambda hop, r: r, abi="hop")
        cht.policy.provider.grant(f"t{i}", f"svc{i}")
    i = [0]
    def many():
        k = i[0] % 200; i[0] += 1
        cht.invoke(f"svc{k}", 1, ctxs[k])
    results["tenant_overhead"] = {"one_tenant": results["prod_local_cached"], "two_hundred_tenants": _time(many, n)}

    slo = 20.0
    return {
        "schema": "INV21_BENCH/1", "version": __version__,
        "environment": {"python": platform.python_version(), "impl": platform.python_implementation(),
                        "machine": platform.machine(), "system": platform.system(),
                        "cpus": os.cpu_count(), "threads_active": threading.active_count()},
        "results": results,
        "slo_local_dispatch_p99_under_20us": {
            "compat_local": results["compat_local"]["p99_us"] < slo,
            "prod_local_cached": results["prod_local_cached"]["p99_us"] < slo,
            "prod_local_uncached": results["prod_local"]["p99_us"] < slo},
        "power_thermal": "not_measured (no RAPL/thermal access in authoring environment)",
    }


def check(current: dict, baseline: dict, tolerance: float = 1.5, tail_tolerance: float = 2.0) -> list:
    """Regression gate: p50 may not exceed baseline x tolerance and p99 may not exceed
    baseline x tail_tolerance. (A single p99 at 1.5x flapped on the socket scenario in a
    shared container -- observed 2026-09-23 -- so the tail band is wider, the median band tight.)"""
    bad = []
    for k, v in baseline["results"].items():
        if isinstance(v, dict) and "p99_us" in v:
            cur = current["results"].get(k, {})
            if cur.get("p50_us") is None or cur["p50_us"] > v["p50_us"] * tolerance:
                bad.append(f"{k}: p50 {cur.get('p50_us')} > {v['p50_us']} x {tolerance}")
            if cur.get("p99_us") is None or cur["p99_us"] > v["p99_us"] * tail_tolerance:
                bad.append(f"{k}: p99 {cur.get('p99_us')} > {v['p99_us']} x {tail_tolerance}")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--check")
    ap.add_argument("--baseline")
    ap.add_argument("--tolerance", type=float, default=1.5)
    a = ap.parse_args(argv)
    if a.check:
        bad = check(json.load(open(a.check)), json.load(open(a.baseline)), a.tolerance)
        print(json.dumps({"regressions": bad}, indent=2))
        return 1 if bad else 0
    rep = run(a.n)
    txt = json.dumps(rep, indent=2)
    if a.out:
        open(a.out, "w").write(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
