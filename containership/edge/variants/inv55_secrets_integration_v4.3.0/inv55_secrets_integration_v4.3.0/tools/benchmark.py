#!/usr/bin/env python3
"""Benchmark harness + regression gate (checklist #61-#64, #69, #70, #87-partial).

Scenarios (in-process, InMemoryProvider -- measures *component* overhead, not Vault):
  steady      sequential resolve+use, cache warm
  cold        cache disabled: every resolve reaches the provider
  burst       16 threads x N ops
  overload    admission cap 8 with 32 threads -> measures shed rate, p99 of admitted
  per_tenant  64 tenants round-robin -> per-tenant overhead vs single tenant

Usage:
  python tools/benchmark.py --write-baseline evidence/benchmark_baseline.json
  python tools/benchmark.py --compare evidence/benchmark_baseline.json [--tolerance 0.5]

The gate fails when p99 of any scenario regresses by more than ``tolerance`` (fraction) relative
to baseline AND exceeds the absolute NFR bound (steady p99 < 5 ms, contract SLO).  Baselines are
host-specific; record the host fingerprint and only compare like with like.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import pathlib
import platform
import statistics
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from inv55_secrets_integration.audit import AuditChain, MemoryAuditSink  # noqa: E402
from inv55_secrets_integration.config import ConfigController, load_layers  # noqa: E402
from inv55_secrets_integration.identity import HmacJwtAuthenticator, PolicyEngine, Rule  # noqa: E402
from inv55_secrets_integration.providers.base import InMemoryProvider  # noqa: E402
from inv55_secrets_integration.resilience import AdmissionController  # noqa: E402
from inv55_secrets_integration.service import SecretsService, ServiceLimits  # noqa: E402

NFR_STEADY_P99_S = 0.005


def _svc(cache_ttl=30.0, max_in_flight=100_000, tenants=("t0",)):
    authn = HmacJwtAuthenticator(b"k" * 32, "inv55-idp", "inv55", time.time)
    pol = PolicyEngine()
    pol.replace([Rule(t, "*", "*", frozenset({"resolve", "use", "rotate", "scope"})) for t in tenants])
    cfg = ConfigController()
    cfg.activate(load_layers(ROOT / "config", "dev"))
    adm = AdmissionController(time.monotonic, max_in_flight=max_in_flight, tenant_rate=1e9, tenant_burst=1e9,
                              workload_rate=1e9, workload_burst=1e9)
    s = SecretsService(provider=InMemoryProvider(), authenticator=authn, policy=pol,
                       audit=AuditChain(MemoryAuditSink(), b"k"), config=cfg, admission=adm,
                       limits=ServiceLimits(cache_ttl_s=cache_ttl, max_leases_per_subject=10**9,
                                            max_active_leases=10**9))
    s.start()
    creds = {}
    for t in tenants:
        admin = authn.issue("admin", t, ["rotator", "secret-admin"], 3600)
        s.rotate({"protocol": "PK_SECRET_ROTATE/1", "credential": admin, "name": "k", "value": "x" * 32,
                  "idempotency_key": "bench-seed-01"})
        s.set_scope({"protocol": "PK_SECRET_SCOPE/1", "credential": admin, "name": "k", "apps": ["app"]})
        creds[t] = authn.issue("app", t, ["consumer"], 3600)
    return s, creds


def _op(s, cred) -> tuple[float, bool]:
    t0 = time.perf_counter()
    r = s.resolve({"protocol": "PK_SECRET_RESOLVE/1", "credential": cred, "name": "k"})
    ok = r["ok"]
    if ok:
        ok = s.use({"protocol": "PK_SECRET_RESOLVE/1", "credential": cred, "name": "k",
                    "lease_id": r["lease_id"]})["ok"]
    return time.perf_counter() - t0, ok


def _stats(samples: list[float], ok: int, total: int, wall: float) -> dict:
    samples = sorted(samples) or [0.0]
    q = lambda p: samples[min(len(samples) - 1, int(p * len(samples)))]  # noqa: E731
    return {"n": total, "ok": ok, "shed_rate": round(1 - ok / total, 4) if total else 0.0,
            "p50_s": q(0.50), "p95_s": q(0.95), "p99_s": q(0.99), "p999_s": q(0.999), "max_s": samples[-1],
            "mean_s": statistics.fmean(samples), "throughput_ops_s": round(total / wall, 1)}


def run(n: int) -> dict:
    out = {}
    s, c = _svc()
    [_op(s, c["t0"]) for _ in range(min(200, n))]  # warm-up
    t = time.perf_counter()
    res = [_op(s, c["t0"]) for _ in range(n)]
    out["steady"] = _stats([r[0] for r in res], sum(r[1] for r in res), n, time.perf_counter() - t)

    s, c = _svc(cache_ttl=0)
    t = time.perf_counter()
    res = [_op(s, c["t0"]) for _ in range(n)]
    out["cold"] = _stats([r[0] for r in res], sum(r[1] for r in res), n, time.perf_counter() - t)

    s, c = _svc()
    t = time.perf_counter()
    with ThreadPoolExecutor(16) as ex:
        res = list(ex.map(lambda _: _op(s, c["t0"]), range(n)))
    out["burst"] = _stats([r[0] for r in res], sum(r[1] for r in res), n, time.perf_counter() - t)

    s, c = _svc(max_in_flight=8)
    t = time.perf_counter()
    with ThreadPoolExecutor(32) as ex:
        res = list(ex.map(lambda _: _op(s, c["t0"]), range(n)))
    admitted = [r[0] for r in res if r[1]]
    out["overload"] = _stats(admitted, len(admitted), n, time.perf_counter() - t)

    tenants = tuple(f"t{i}" for i in range(64))
    s, c = _svc(tenants=tenants)
    t = time.perf_counter()
    res = [_op(s, c[tenants[i % 64]]) for i in range(n)]
    out["per_tenant"] = _stats([r[0] for r in res], sum(r[1] for r in res), n, time.perf_counter() - t)
    out["per_tenant"]["overhead_vs_steady_p50"] = round(out["per_tenant"]["p50_s"] / out["steady"]["p50_s"], 3)
    return out


def host() -> dict:
    return {"python": platform.python_version(), "impl": platform.python_implementation(),
            "machine": platform.machine(), "system": platform.system(), "cpus": os.cpu_count()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--write-baseline")
    ap.add_argument("--compare")
    ap.add_argument("--tolerance", type=float, default=0.5)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    result = {"tool": "inv55-benchmark/1", "host": host(), "n": a.n, "scenarios": run(a.n),
              "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    text = json.dumps(result, indent=1)
    if a.out:
        pathlib.Path(a.out).write_text(text)
    if a.write_baseline:
        pathlib.Path(a.write_baseline).write_text(text)
    print(text)
    verdict = 0
    if result["scenarios"]["steady"]["p99_s"] >= NFR_STEADY_P99_S:
        print(f"GATE FAIL: steady p99 {result['scenarios']['steady']['p99_s']:.6f}s >= NFR {NFR_STEADY_P99_S}s")
        verdict = 1
    if a.compare:
        base = json.loads(pathlib.Path(a.compare).read_text())
        if base["host"] != result["host"]:
            print("GATE WARN: baseline host differs; comparison is advisory only")
        for name, cur in result["scenarios"].items():
            b = base["scenarios"].get(name)
            if b and cur["p99_s"] > b["p99_s"] * (1 + a.tolerance) and base["host"] == result["host"]:
                print(f"GATE FAIL: {name} p99 {cur['p99_s']:.6f}s > baseline {b['p99_s']:.6f}s x{1 + a.tolerance}")
                verdict = 1
    return verdict


if __name__ == "__main__":
    sys.exit(main())
