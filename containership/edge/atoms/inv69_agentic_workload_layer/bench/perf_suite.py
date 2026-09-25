"""INV-69 performance, load, soak and fleet suite (C061, C062, C063, C064, C065, C069, C088).

    python -B bench/perf_suite.py [--quick] [--soak SECONDS] [--out evidence/PERF_RESULTS.json]

Every run records an environment fingerprint, the exact configuration digest, the commit/version and the
raw sample summaries.  Network and power are reported as NOT MEASURED with the reason (adapters are
in-process; no power instrumentation — see ops/WAIVERS.json W-005) rather than as zero.
"""
from __future__ import annotations

import argparse
import cProfile
import gc
import hashlib
import io
import json
import os
import platform
import pstats
import resource
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG / "tests"))
sys.dont_write_bytecode = True
from harness import M, TOOL_IMPLS, build, ctx  # noqa: E402

E = M["errors"]
ALL = frozenset(TOOL_IMPLS)


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def summarize(xs):
    return {"n": len(xs), "p50_us": round(pct(xs, 50) * 1e6, 2), "p95_us": round(pct(xs, 95) * 1e6, 2),
            "p99_us": round(pct(xs, 99) * 1e6, 2), "max_us": round(max(xs) * 1e6, 2),
            "mean_us": round(statistics.fmean(xs) * 1e6, 2)}


def fingerprint():
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "machine": platform.machine(), "system": platform.system(), "release": platform.release(),
            "cpu_count": os.cpu_count(), "optimized_mode": not __debug__,
            "version": (PKG / "VERSION").read_text().strip(),
            "code_digest": hashlib.sha256(b"".join(p.read_bytes() for p in sorted(PKG.glob("*.py")))).hexdigest()}


def big_budget_rt(**kw):
    layers = [("base", {"schema_version": M["config"].SCHEMA_VERSION,
                        "budgets": {"max_steps": 10_000, "max_cost": 1_000_000, "max_transcript_events": 1_000_000},
                        "concurrency": {"max_active": kw.pop("max_active", 64), "max_waiting": kw.pop("max_waiting", 256),
                                        "reserved_critical": 2}})]
    return build(layers=layers, **kw)


def bench_startup():
    code = "import time;t=time.perf_counter();import inv69_agentic_workload_layer.governed;print(time.perf_counter()-t)"
    imports = []
    for _ in range(5):
        out = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, cwd=str(PKG.parent))
        imports.append(float(out.stdout.strip()))
    cons = []
    for _ in range(20):
        t = time.perf_counter()
        big_budget_rt()
        cons.append(time.perf_counter() - t)
    return {"import_governed": summarize(imports), "construct_runtime": summarize(cons)}


def bench_latency(n):
    rt = big_budget_rt()
    c = ctx(timeout=3600)
    rt.start_run("lat", principal="alice", allow=ALL, ctx=c)
    raw, kern, gov, gov_heavy = [], [], [], []
    fn = TOOL_IMPLS["search_docs"]
    a = M["runtime"].Agent("k", ALL, max_steps=10 ** 7, max_cost=10 ** 9, max_transcript_events=10 ** 7)
    for i in range(n):
        t = time.perf_counter(); fn(i); raw.append(time.perf_counter() - t)
        t = time.perf_counter(); a.step("search_docs", {"q": i}); kern.append(time.perf_counter() - t)
        t = time.perf_counter(); rt.invoke("lat", "search_docs", {"q": i}, c); gov.append(time.perf_counter() - t)
        t = time.perf_counter(); rt.invoke("lat", "run_python", {"q": i}, c); gov_heavy.append(time.perf_counter() - t)
    ev_bytes = [len(json.dumps(e, default=str)) for e in rt.events[-100:]]
    return {"raw_tool_call": summarize(raw), "kernel_step": summarize(kern), "governed_invoke_fast": summarize(gov),
            "governed_invoke_heavy": summarize(gov_heavy),
            "overhead_per_invoke_us_p50": round((pct(gov, 50) - pct(raw, 50)) * 1e6, 2),
            "storage_bytes_per_event_mean": round(statistics.fmean(ev_bytes), 1)}


def bench_throughput(n, threads):
    rt = big_budget_rt()
    c = ctx(timeout=3600)
    rt.start_run("tp", principal="alice", allow=ALL, ctx=c)
    t = time.perf_counter()
    cpu = time.process_time()
    for i in range(n):
        rt.invoke("tp", "search_docs", i, c)
    single = n / (time.perf_counter() - t)
    cpu_per_op = (time.process_time() - cpu) / n
    rt2 = big_budget_rt()
    runs = [f"r{i}" for i in range(threads)]
    for r in runs:
        rt2.start_run(r, principal="alice", allow=ALL, ctx=c)
    t = time.perf_counter()
    with ThreadPoolExecutor(threads) as p:
        list(p.map(lambda i: rt2.invoke(runs[i % threads], "search_docs", i, c), range(n)))
    multi = n / (time.perf_counter() - t)
    return {"single_thread_ops_s": round(single, 1), f"threads_{threads}_ops_s": round(multi, 1),
            "cpu_s_per_op": round(cpu_per_op * 1e6, 2), "cpu_unit": "us",
            "note": "CPython GIL + one runtime-wide event-chain lock: throughput does not scale with threads (C065 finding)"}


def bench_memory(runs, tenants):
    gc.collect()
    tracemalloc.start()
    rt = big_budget_rt(max_active=runs + 8, max_waiting=0)
    base = tracemalloc.get_traced_memory()[0]
    per_tenant = {}
    for i in range(runs):
        tenant = f"t{i % tenants}"
        c = ctx(tenant=tenant, timeout=3600)
        rt.start_run(f"m{i}", principal="alice", allow=ALL, ctx=c)
        rt.invoke(f"m{i}", "search_docs", i, c)
        rt.finish_run(f"m{i}")
        per_tenant[tenant] = per_tenant.get(tenant, 0) + 1
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"runs": runs, "tenants": tenants, "bytes_per_completed_run": round((cur - base) / runs, 1),
            "peak_bytes": peak, "retained_bytes": cur - base,
            "per_tenant_runs": per_tenant,
            "per_tenant_overhead_bytes": round((cur - base) / tenants, 1),
            "note": "completed runs stay in GovernedRuntime.runs and events (unbounded) — C065/C067 finding; export+prune needed"}


def bench_load_shapes():
    out = {}
    # steady
    rt = big_budget_rt(max_active=16, max_waiting=16)
    lat = []
    for i in range(200):
        c = ctx(timeout=10)
        t = time.perf_counter()
        rt.start_run(f"s{i}", principal="alice", allow=ALL, ctx=c)
        rt.invoke(f"s{i}", "search_docs", i, c)
        rt.finish_run(f"s{i}")
        lat.append(time.perf_counter() - t)
    out["steady"] = summarize(lat)

    # burst / overload: 256 concurrent run starts against 16 active + 16 waiting
    rt = big_budget_rt(max_active=16, max_waiting=16)
    hold = threading.Event()
    results = {"ok": 0, "shed": 0, "timeout": 0}
    lock = threading.Lock()

    def burst(i):
        c = ctx(timeout=0.5)
        try:
            rt.start_run(f"b{i}", principal="alice", allow=ALL, ctx=c)
            hold.wait(0.05)
            rt.invoke(f"b{i}", "search_docs", i, c)
            rt.finish_run(f"b{i}")
            k = "ok"
        except E.AgentError as e:
            k = "shed" if e.code == "AGT-CAP-003" else "timeout" if e.code == "AGT-TMO-001" else e.code
        with lock:
            results[k] = results.get(k, 0) + 1
    t = time.perf_counter()
    with ThreadPoolExecutor(64) as p:
        list(p.map(burst, range(256)))
    out["burst_overload"] = dict(results, wall_s=round(time.perf_counter() - t, 3), admission=rt.admission.stats())

    # recovery: after overload, steady latency returns
    lat = []
    for i in range(100):
        c = ctx(timeout=10)
        t = time.perf_counter()
        rt.start_run(f"rec{i}", principal="alice", allow=ALL, ctx=c)
        rt.invoke(f"rec{i}", "search_docs", i, c)
        rt.finish_run(f"rec{i}")
        lat.append(time.perf_counter() - t)
    out["recovery_after_overload"] = summarize(lat)

    # scale-out / scale-in: executors share one durable store; runs are adopted on scale-in (fencing)
    durable = M["sandbox"].DurableExecutionAdapter()
    fleet = [build(durable=durable, executor_id=f"ex-{k}", node=f"node-{k % 2}") for k in range(4)]
    started = 0
    for i in range(40):
        ex = fleet[i % 4]
        ex.start_run(f"f{i}", principal="alice", allow=ALL, ctx=ctx())
        ex.invoke(f"f{i}", "search_docs", i, ctx())
        started += 1
    # scale-in: executors 2,3 removed -> their runs adopted by 0,1 after lease expiry
    adopted = 0
    t = time.perf_counter()
    for i in range(40):
        if i % 4 in (2, 3):
            owner, fence, _, zone = durable.leases[f"f{i}"]
            durable.leases[f"f{i}"] = (owner, fence, 0.0, zone)
            fleet[i % 2].adopt(f"f{i}", principal="alice", allow=ALL, ctx=ctx(), source_executor=owner)
            adopted += 1
    out["scale_out_in"] = {"executors_out": 4, "executors_in": 2, "runs": started, "adopted": adopted,
                           "adopt_wall_s": round(time.perf_counter() - t, 4),
                           "duplicate_side_effects": 0 if all(len(set(x["key"] for x in f.fast.executions)) ==
                                                              len(f.fast.executions) for f in fleet) else "FOUND"}
    return out


def bench_soak(seconds, archive=False):
    rt = big_budget_rt(max_active=128, max_waiting=0)
    archived = []
    tracemalloc.start()
    samples = []
    t0 = time.perf_counter()
    i = 0
    refused = None
    while time.perf_counter() - t0 < seconds:
        c = ctx(timeout=60)
        try:
            rt.start_run(f"k{i}", principal="alice", allow=ALL, ctx=c)
            rt.invoke(f"k{i}", "search_docs", i, c)
        except E.AgentError as e:
            refused = {"code": e.code, "after_runs": i, "at_s": round(time.perf_counter() - t0, 3),
                       "reasons": rt.status()["reasons"]}
            break
        finally:
            if f"k{i}" in rt.runs and not rt.runs[f"k{i}"].lifecycle.terminal:
                rt.finish_run(f"k{i}")
        i += 1
        if archive and i % 100 == 0:
            rt.archive(lambda k, r: archived.append(1))
        if i % 200 == 0:
            samples.append((time.perf_counter() - t0, tracemalloc.get_traced_memory()[0], threading.active_count(),
                            len(rt.events)))
    if archive:
        rt.archive(lambda k, r: archived.append(1))   # final archive so the residual window is not counted as growth
    gc.collect()
    total_growth = tracemalloc.get_traced_memory()[0] - (samples[0][1] if samples else 0)
    # Attribute growth: the INV-57/INV-70/71 adapters simulate EXTERNAL stores (leases, checkpoints, effect keys,
    # sandbox dedup keys).  Clear them to measure what INV-69 itself retains.
    for store in (rt.durable.effects, rt.durable.leases, rt.durable.checkpoints, rt.durable._fence_counter):
        store.clear()
    for sbx in (rt.fast, rt.heavy):
        sbx.executions.clear()
        sbx._seen_keys.clear()
    gc.collect()
    own_growth = tracemalloc.get_traced_memory()[0] - (samples[0][1] if samples else 0)
    tracemalloc.stop()
    xs = [s[0] for s in samples]
    ys = [s[1] for s in samples]
    slope = statistics.linear_regression(xs, ys).slope if len(samples) > 2 else 0.0
    return {"seconds": seconds, "archive": archive, "runs": i, "self_protection_refusal": refused, "samples": len(samples), "mem_slope_bytes_per_s": round(slope, 1),
            "bytes_per_run": round((ys[-1] - ys[0]) / max(1, (i - 200)), 1) if len(ys) > 1 else None,
            "threads_start_end": [samples[0][2], samples[-1][2]] if samples else None,
            "events_retained": len(rt.events),
            "adapter_store_bytes_per_run": round((total_growth - own_growth) / max(1, i - 200), 1),
            "inv69_owned_bytes_per_run": round(own_growth / max(1, i - 200), 1),
            "leak_verdict": ("GROWTH" if own_growth / max(1, i - 200) > 256 else "FLAT (<256 B INV-69-owned per run)")
            if len(ys) > 1 else "insufficient samples"}


def profile_hot_path(n=2000):
    rt = big_budget_rt()
    c = ctx(timeout=3600)
    rt.start_run("prof", principal="alice", allow=ALL, ctx=c)
    pr = cProfile.Profile()
    pr.enable()
    for i in range(n):
        rt.invoke("prof", "search_docs", {"q": i, "body": ["x"] * 8}, c)
    pr.disable()
    s = io.StringIO()
    st = pstats.Stats(pr, stream=s).sort_stats("tottime")
    rows = []
    for (fn, line, name), (cc, nc, tt, ct, _) in sorted(st.stats.items(), key=lambda kv: -kv[1][2])[:15]:
        rows.append({"function": f"{Path(fn).name}:{line}:{name}", "calls_per_invoke": round(nc / n, 2),
                     "tottime_us_per_invoke": round(tt / n * 1e6, 2)})
    calls = {f"{Path(fn).name}:{name}": nc / n for (fn, line, name), (cc, nc, tt, ct, _) in st.stats.items()}
    return {"top_by_tottime": rows,
            "duplicate_work_counters": {k: round(v, 2) for k, v in calls.items()
                                        if any(x in k for x in ("check_bounds", "_canonical_bytes", "lineage", "_digest",
                                                                "dumps", "handshake"))}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--soak", type=float, default=None)
    ap.add_argument("--out", default=str(PKG / "evidence" / "PERF_RESULTS.json"))
    a = ap.parse_args(argv)
    n = 300 if a.quick else 2000
    res = {"schema": "PK_AGENT_PERF_RESULTS/1", "quick": a.quick, "fingerprint": fingerprint(), "started_at": time.time(),
           "config_digest": big_budget_rt().eff.digest,
           "not_measured": {"network": "adapters are in-process; no network hop exists to measure in this archive",
                            "power_thermal": "no power instrumentation / edge hardware (W-005, C068)"}}
    res["startup"] = bench_startup()
    res["latency"] = bench_latency(n)
    res["throughput"] = bench_throughput(n, 8)
    res["memory"] = bench_memory(500 if a.quick else 2000, 10)
    res["load_shapes"] = bench_load_shapes()
    secs = a.soak if a.soak is not None else (3 if a.quick else 10)
    res["soak"] = bench_soak(secs)
    res["soak_with_archive"] = bench_soak(secs, archive=True)
    res["profile"] = profile_hot_path(500 if a.quick else 2000)
    res["rusage_maxrss_kb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    res["finished_at"] = time.time()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({"latency": res["latency"]["governed_invoke_fast"], "throughput": res["throughput"],
                      "burst": res["load_shapes"]["burst_overload"], "soak": res["soak"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
