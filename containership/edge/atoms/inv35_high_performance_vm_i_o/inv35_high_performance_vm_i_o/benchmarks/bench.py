"""Reproducible benchmark harness for the INV-35 reference model and runtime facade.

Covers INV-35-C061..C065, C067, C069, C070, C088 (and REPO-007).  Measures the
*reference* Python implementation only: numbers characterise validation and
policy overhead, never production virtio/vhost line rate (see
docs/performance/PERFORMANCE_MODEL.md).

Usage:  python -m inv35_high_performance_vm_i_o.benchmarks.bench [--quick] [--out FILE]
Exit 0 = thresholds met, 1 = regression/threshold breach.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import platform
import statistics
import sys
import time
import tracemalloc

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
if str(PKG.parent) not in sys.path:
    sys.path.insert(0, str(PKG.parent))

import importlib  # noqa: E402

pkg = importlib.import_module(PKG.name)
rt_mod = importlib.import_module(PKG.name + ".runtime")
Descriptor, MemoryRegion, VirtQueue, QueueFull = pkg.Descriptor, pkg.MemoryRegion, pkg.VirtQueue, pkg.QueueFull
Runtime, ControlPlane, Datapath, Inv35Error = rt_mod.Runtime, rt_mod.ControlPlane, rt_mod.Datapath, rt_mod.Inv35Error

REGION = (MemoryRegion(0x10000, 0x100000),)
CTL = {"register_memory", "lifecycle", "configure", "quarantine", "read_status"}


def chain(n: int) -> dict[int, object]:
    return {i: Descriptor(i, 0x10000 + i * 256, 256, i + 1 if i + 1 < n else None) for i in range(n)}


def pct(samples: list[float]) -> dict[str, float]:
    s = sorted(samples)
    k = lambda q: s[min(len(s) - 1, int(q * len(s)))]  # noqa: E731
    return {"n": len(s), "p50_us": round(k(0.50), 3), "p95_us": round(k(0.95), 3), "p99_us": round(k(0.99), 3),
            "max_us": round(s[-1], 3), "mean_us": round(statistics.fmean(s), 3)}


def timed(fn, iters: int) -> list[float]:
    out = []
    pc = time.perf_counter_ns
    for _ in range(iters):
        t = pc()
        fn()
        out.append((pc() - t) / 1000.0)
    return out


def facade(tenants: int = 1, queues_per_tenant: int = 1):
    rt = Runtime()
    cfg = importlib.import_module(PKG.name + ".runtime.config")
    rt.config.apply(*cfg.build(environment={"submit_rate_per_s": 1e9, "submit_burst": 1e9, "tenant_share": 1.0,
                                            "max_queues_per_tenant": 64},
                               source="benchmark", author="bench"))
    rt._rebuild_policy()
    cp, dp = ControlPlane(rt), Datapath(rt)
    toks = {}
    for t in range(tenants):
        tenant = f"t{t}"
        names = {f"{tenant}-q{i}" for i in range(queues_per_tenant)}
        ctl = rt.authority.mint("bench-ctl", tenant, names, CTL)
        for n in sorted(names):
            cp.register_queue(ctl, tenant=tenant, queue=n, regions=REGION)
        toks[tenant] = (rt.authority.mint("bench-vmm", tenant, names, {"submit", "complete"}), sorted(names))
    return rt, dp, toks


def run(quick: bool) -> dict[str, object]:
    iters = 2000 if quick else 20000
    results: dict[str, object] = {}
    gc.collect()

    # Steady state: raw model vs full facade (copy/hop overhead, C064/C065).
    vq = VirtQueue("raw", REGION)
    c4 = chain(4)

    def raw_cycle():
        vq.submit(c4, 0)
        vq.complete(guest_wants_notification=False)
    results["steady_raw_model_4desc"] = pct(timed(raw_cycle, iters))

    rt, dp, toks = facade()
    tok, (qname,) = toks["t0"]

    def facade_cycle():
        dp.submit(tok, tenant="t0", queue=qname, chain=c4, head=0)
        dp.complete(tok, tenant="t0", queue=qname, guest_wants_notification=False)
    results["steady_facade_4desc"] = pct(timed(facade_cycle, iters))
    raw_p50 = results["steady_raw_model_4desc"]["p50_us"]
    results["facade_overhead_ratio_p50"] = round(results["steady_facade_4desc"]["p50_us"] / max(raw_p50, 1e-9), 3)

    # Chain-length sweep (validation cost is O(chain)).
    for n in (1, 8, 16):
        cn = chain(n)
        q = VirtQueue(f"sweep{n}", REGION)

        def cyc(q=q, cn=cn):
            q.submit(cn, 0)
            q.complete(guest_wants_notification=True)
        results[f"chain_sweep_{n}desc"] = pct(timed(cyc, iters // 2))

    # Burst: fill to depth, then drain.
    q = VirtQueue("burst", REGION)
    c1 = chain(1)
    burst = []
    for _ in range(iters // 64):
        t = time.perf_counter_ns()
        for _ in range(64):
            q.submit(c1, 0)
        for _ in range(64):
            q.complete(guest_wants_notification=False)
        burst.append((time.perf_counter_ns() - t) / 1000.0)
    results["burst_64_fill_drain"] = pct(burst)

    # Overload: refusals must be cheap and must not mutate state.
    q = VirtQueue("over", REGION)
    for _ in range(64):
        q.submit(c1, 0)
    refused = []
    for _ in range(iters):
        t = time.perf_counter_ns()
        try:
            q.submit(c1, 0)
        except QueueFull:
            pass
        refused.append((time.perf_counter_ns() - t) / 1000.0)
    results["overload_refusal"] = pct(refused)
    results["overload_state_intact"] = q.in_flight_descriptors == 64

    # Scale: many tenants/queues, per-tenant overhead (C064).
    rt, dp, toks = facade(tenants=8, queues_per_tenant=4)
    per_tenant = {}
    for tenant, (tok, names) in toks.items():
        samples = []
        for i in range(iters // 20):
            qn = names[i % len(names)]
            t = time.perf_counter_ns()
            dp.submit(tok, tenant=tenant, queue=qn, chain=c4, head=0)
            dp.complete(tok, tenant=tenant, queue=qn, guest_wants_notification=False)
            samples.append((time.perf_counter_ns() - t) / 1000.0)
        per_tenant[tenant] = pct(samples)["p50_us"]
    results["scale_8x4_per_tenant_p50_us"] = per_tenant
    vals = list(per_tenant.values())
    results["scale_tenant_fairness_spread"] = round(max(vals) / max(min(vals), 1e-9), 3)

    # Recovery: journal replay time (C057/C063).
    rt, dp, toks = facade()
    tok, (qname,) = toks["t0"]
    for _ in range(32):
        dp.submit(tok, tenant="t0", queue=qname, chain=c1, head=0)
    journal = rt.snapshot_journal()
    t = time.perf_counter_ns()
    Runtime.recover(journal, keyring=rt.keyring, regions={qname: REGION})
    results["recovery_replay_32_us"] = round((time.perf_counter_ns() - t) / 1000.0, 3)

    # Startup + memory (C061/C067).
    tracemalloc.start()
    t = time.perf_counter_ns()
    facade(tenants=4, queues_per_tenant=4)
    results["startup_16_queues_us"] = round((time.perf_counter_ns() - t) / 1000.0, 3)
    results["startup_peak_bytes"] = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    return {
        "schema": "INV35_BENCH/1",
        "version": (PKG / "VERSION").read_text().strip(),
        "quick": quick,
        "host": {"python": sys.version.split()[0], "impl": platform.python_implementation(),
                 "machine": platform.machine(), "platform": platform.platform()},
        "scope": "reference-model only; not production virtio/vhost performance",
        "results": results,
    }


def gate(report: dict[str, object], thresholds: dict[str, object]) -> list[str]:
    """Absolute ceilings from benchmarks/thresholds.json (C062/C070)."""
    breaches = []
    res = report["results"]
    for key, limits in thresholds["ceilings"].items():
        got = res.get(key)
        if got is None:
            breaches.append(f"{key}: missing from report")
            continue
        for metric, ceiling in limits.items():
            value = got[metric] if isinstance(got, dict) else got  # scalar results use key 'value'
            if value > ceiling:
                breaches.append(f"{key}.{metric}={value} > {ceiling}")
    if not res.get("overload_state_intact"):
        breaches.append("overload refusal mutated queue state")
    if res["facade_overhead_ratio_p50"] > thresholds["max_facade_overhead_ratio_p50"]:
        breaches.append(f"facade overhead ratio {res['facade_overhead_ratio_p50']} > {thresholds['max_facade_overhead_ratio_p50']}")
    if res["scale_tenant_fairness_spread"] > thresholds["max_tenant_fairness_spread"]:
        breaches.append(f"tenant spread {res['scale_tenant_fairness_spread']} > {thresholds['max_tenant_fairness_spread']}")
    return breaches


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    report = run(args.quick)
    thresholds = json.loads((HERE / "thresholds.json").read_text())
    report["breaches"] = gate(report, thresholds)
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + "\n")
    print(text)
    return 1 if report["breaches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
