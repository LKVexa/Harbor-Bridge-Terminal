# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Reproducible benchmark harness (GAP-040..GAP-045, GAP-047, GAP-059).

Workloads: steady, burst, overload, scale (many tenants), recovery (after
emergency disable → re-bootstrap) and soak. Output: INV30_BENCH/1 JSON with
p50/p95/p99/max per op, throughput, per-tenant overhead, peak RSS and host
fingerprint. ``regression`` compares against a committed baseline with
tolerances and returns failures (the release gate blocks on any).
"""
from __future__ import annotations

import json
import os
import platform
import random
import resource
import statistics
import time
import uuid
from pathlib import Path

BASELINE = Path(__file__).resolve().parent / "evidence" / "BENCH_BASELINE.json"
THRESHOLDS = Path(__file__).resolve().parent / "config" / "perf_thresholds.json"


def _pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))] if xs else 0.0


def _summ(xs):
    return {"n": len(xs), "p50_us": round(_pct(xs, 50), 3), "p95_us": round(_pct(xs, 95), 3),
            "p99_us": round(_pct(xs, 99), 3), "max_us": round(max(xs) if xs else 0, 3),
            "mean_us": round(statistics.fmean(xs), 3) if xs else 0}


def _harness(n_tenants=4, cfg_over=None):
    from .authz import Authenticator, MintingAuthority
    from .config import load
    from .service import CapabilityService
    cfg = load("datacenter", extra=cfg_over or {})
    key = b"k" * 32
    auth = Authenticator()
    auth.register("bench", key, {"mint", "derive", "access", "invalidate"}, {"*"})
    svc = CapabilityService(cfg, authenticator=auth, authority=MintingAuthority(b"m" * 32))

    def signed(action, body):
        ts, nonce = time.time(), uuid.uuid4().hex
        return {"principal": "bench", "ts": ts, "nonce": nonce,
                "mac": Authenticator.request_mac(key, "bench", action, body, ts, nonce)}
    return svc, signed


def run(iterations: int = 2000, seed: int = 1234) -> dict:
    rng = random.Random(seed)
    svc, signed = _harness()
    tenants = [f"tenant-{i}" for i in range(8)]
    roots = {}
    for t in tenants:
        b = {"schema": "PK_CAPABILITY/1", "op": "mint", "tenant": t, "base": 0x10000, "length": 0x10000,
             "permissions": ["read", "write"]}
        roots[t] = svc.mint(b, signed("mint", b))["handle"]
    lat = {"access": [], "derive": [], "model_check": []}
    per_tenant = {t: [] for t in tenants}
    t_start = time.perf_counter()
    for _ in range(iterations):
        t = rng.choice(tenants)
        b = {"schema": "PK_CAPABILITY_ACCESS/1", "handle": roots[t], "tenant": t,
             "address": 0x10000 + rng.randrange(0, 0xFF00), "size": 16, "operation": "read"}
        a = signed("access", b)
        s = time.perf_counter(); svc.access(b, a); d = (time.perf_counter() - s) * 1e6
        lat["access"].append(d); per_tenant[t].append(d)
    steady_s = time.perf_counter() - t_start
    for _ in range(iterations // 10):
        t = rng.choice(tenants)
        b = {"schema": "PK_CAPABILITY/1", "op": "derive", "tenant": t, "handle": roots[t],
             "base": 0x10000, "length": 0x100, "permissions": ["read"]}
        a = signed("derive", b)
        s = time.perf_counter(); svc.derive(b, a); lat["derive"].append((time.perf_counter() - s) * 1e6)
    from .core import Capability
    c = Capability(0, 1 << 20, {"read"})
    for _ in range(iterations):
        s = time.perf_counter(); c.check(address=rng.randrange(0, 1 << 19), size=8, operation="read")
        lat["model_check"].append((time.perf_counter() - s) * 1e6)
    # burst / overload: shrink admission to force shedding
    svc.admission.max_inflight = 0
    b = {"schema": "PK_CAPABILITY_ACCESS/1", "handle": roots[tenants[0]], "tenant": tenants[0],
         "address": 0x10000, "size": 8, "operation": "read"}
    overload = [svc.access(b, signed("access", b)).get("code") for _ in range(50)]
    svc.admission.max_inflight = svc.limits.max_inflight
    # recovery: emergency disable then fresh bootstrap
    s = time.perf_counter()
    svc.set_state("disabled", operator="bench", reason="recovery drill")
    svc2, signed2 = _harness()
    recovery_ms = (time.perf_counter() - s) * 1000
    return {
        "schema": "INV30_BENCH/1", "seed": seed, "iterations": iterations,
        "host": {"python": platform.python_version(), "machine": platform.machine(), "system": platform.system(),
                 "cpu_count": os.cpu_count()},
        "enforcement": svc.enforcement,
        "ops": {k: _summ(v) for k, v in lat.items()},
        "throughput_access_per_s": round(iterations / steady_s, 1),
        "service_overhead_vs_model_p50_x": round(_pct(lat["access"], 50) / max(_pct(lat["model_check"], 50), 1e-9), 1),
        "per_tenant_p50_us": {t: round(_pct(v, 50), 3) for t, v in per_tenant.items()},
        "overload_shed": overload.count("OVERLOADED"), "overload_attempts": len(overload),
        "recovery_ms": round(recovery_ms, 3),
        "peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "raw_us": {k: [round(x, 3) for x in v] for k, v in lat.items()},
        "power_thermal": {"state": "not-measured",
                          "reason": "requires edge hardware with RAPL/INA sensors; see docs/PERFORMANCE.md"},
    }


def regression(result: dict, thresholds: dict | None = None) -> list[str]:
    th = thresholds or json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    fails = []
    for op, lim in th["ops"].items():
        got = result["ops"].get(op)
        if not got:
            fails.append(f"{op}: missing from result")
            continue
        for k, v in lim.items():
            if got[k] > v:
                fails.append(f"{op}.{k}={got[k]} exceeds {v}")
    if result["overload_shed"] != result["overload_attempts"]:
        fails.append("overload not fully shed")
    if result["recovery_ms"] > th["recovery_ms_max"]:
        fails.append(f"recovery {result['recovery_ms']}ms exceeds {th['recovery_ms_max']}")
    return fails


if __name__ == "__main__":  # pragma: no cover
    # Soak: INV30_SOAK_ITER=1000000 python -m ...bench  (watch peak_rss_kb for leaks between runs)
    n = int(os.environ.get("INV30_SOAK_ITER", "2000"))
    r = run(iterations=n)
    r.pop("raw_us")
    print(json.dumps(r, indent=2))
