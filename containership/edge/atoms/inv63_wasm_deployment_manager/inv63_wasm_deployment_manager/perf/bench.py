"""Reproducible INV-63 benchmark + regression gate (INV-63-C061..C070, C088).

    python perf/bench.py [--out perf/results.json] [--gate]

Scenarios: cold/no-op diff at 1000 instances, request path (no-op reconcile),
steady / burst / overload through admission, scale-out and scale-in, journal
replay (recovery), startup, per-tenant overhead, memory growth, soak.
Deterministic inputs (fixed seeds, fake lattice).  --gate exits 1 when any
metric regresses past perf/thresholds.json * ci_slack_factor.
"""
import argparse, gc, json, os, pathlib, platform, statistics, sys, tempfile, time, tracemalloc

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tests"))
from _support import desired, make_env, mod, req  # noqa: E402


def pct(xs):
    xs = sorted(xs)
    q = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]
    return {"p50": q(0.50), "p95": q(0.95), "p99": q(0.99), "max": xs[-1], "n": len(xs)}


def timeit(fn, n):
    out = []
    for _ in range(n):
        t = time.perf_counter(); fn(); out.append((time.perf_counter() - t) * 1000)
    return pct(out)


def run(quick=False):
    n = 50 if quick else 300
    Manager = mod("manager").Manager
    r = {"env": {"python": platform.python_version(), "machine": platform.machine(), "cpus": os.cpu_count(),
                 "platform": platform.platform()}}
    hosts = {f"h{i}": f"z{i % 10}" for i in range(200)}
    r["diff_1000_cold_ms"] = timeit(lambda: Manager(hosts).diff("api", "v1", 1000), n // 3)
    m = Manager(hosts); m.apply(m.diff("api", "v1", 1000))
    r["diff_1000_noop_ms"] = timeit(lambda: m.diff("api", "v1", 1000), n)

    env = make_env(config_over={"max_inflight": 10000})
    env.svc.admission.rate = 1e9; env.svc.admission.burst = 10**9
    req(env, "set_desired", desired(env, count=3)); req(env, "reconcile", {"tenant": "acme", "component": "api"})
    r["handle_reconcile_noop_ms"] = timeit(lambda: req(env, "reconcile", {"tenant": "acme", "component": "api"}), n)
    t = time.perf_counter(); k = 0
    while time.perf_counter() - t < (0.5 if quick else 2.0):
        req(env, "reconcile", {"tenant": "acme", "component": "api"}); k += 1
    r["throughput_noop_reconcile_rps"] = {"value": k / (time.perf_counter() - t)}

    # burst / overload through admission (shedding must engage, not collapse)
    a = mod("resilience").Admission(max_inflight=32, tenant_rate=100, tenant_burst=50)
    ok = shed = 0
    for i in range(1000):
        try:
            a.enter(f"t{i % 4}", "batch" if i % 3 == 0 else "standard"); ok += 1
        except Exception:
            shed += 1
    r["overload_admission"] = {"admitted": ok, "shed": shed}

    # scale-out / scale-in
    env2 = make_env(config_over={"max_inflight": 10000})
    env2.svc.admission.rate = 1e9; env2.svc.admission.burst = 10**9
    req(env2, "set_desired", desired(env2, count=1))
    t = time.perf_counter()
    req(env2, "set_desired", desired(env2, count=200)); req(env2, "reconcile", {"tenant": "acme", "component": "api"})
    r["scale_out_1_to_200_ms"] = {"value": (time.perf_counter() - t) * 1000}
    t = time.perf_counter()
    req(env2, "set_desired", desired(env2, count=5)); req(env2, "reconcile", {"tenant": "acme", "component": "api"})
    r["scale_in_200_to_5_ms"] = {"value": (time.perf_counter() - t) * 1000}

    # recovery: replay 10k records; startup on empty journal
    Journal = mod("store").Journal
    d = tempfile.mkdtemp(); j = Journal(d); j.acquire()
    for i in range(10_000):
        j.append("desired_set", {"ns": f"t/c{i % 50}", "body": {"version": "v1", "count": 1}})
    t = time.perf_counter(); Journal(d); r["replay_10k_records_ms"] = {"value": (time.perf_counter() - t) * 1000}
    t = time.perf_counter(); make_env(); r["startup_empty_journal_ms"] = {"value": (time.perf_counter() - t) * 1000}

    # per-tenant overhead: request latency with 1 vs 50 tenants resident
    env3 = make_env(config_over={"max_inflight": 10000})
    env3.svc.admission.rate = 1e9; env3.svc.admission.burst = 10**9
    for i in range(50):
        req(env3, "set_desired", desired(env3, tenant=f"t{i}", count=2), tenant=f"t{i}")
    r["per_tenant_overhead"] = {
        "1_tenant_p50_ms": r["handle_reconcile_noop_ms"]["p50"],
        "50_tenants_p50_ms": timeit(lambda: req(env3, "reconcile", {"tenant": "t0", "component": "api"}, tenant="t0"), n // 2)["p50"],
        "journal_bytes_per_desired": os.path.getsize(env3.journal.path) / 50}

    # memory growth over sustained requests (soak-lite)
    gc.collect(); tracemalloc.start()
    for _ in range(2000 if quick else 10_000):
        req(env, "reconcile", {"tenant": "acme", "component": "api"})
    cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    r["tracemalloc_peak_10k_requests_mb"] = {"value": peak / 1e6}
    return r


def gate(res, th):
    slack = th["ci_slack_factor"]; fails = []
    for key in ("diff_1000_noop_ms", "diff_1000_cold_ms", "handle_reconcile_noop_ms"):
        for q, lim in th[key].items():
            if res[key][q] > lim * slack:
                fails.append(f"{key}.{q}={res[key][q]:.3f} > {lim}*{slack}")
    for key in ("startup_empty_journal_ms", "replay_10k_records_ms", "tracemalloc_peak_10k_requests_mb"):
        if res[key]["value"] > th[key]["max"] * slack:
            fails.append(f"{key}={res[key]['value']:.2f} > {th[key]['max']}*{slack}")
    if res["throughput_noop_reconcile_rps"]["value"] < th["throughput_noop_reconcile_rps"]["min"] / slack:
        fails.append("throughput below floor")
    if res["overload_admission"]["shed"] == 0:
        fails.append("admission never shed under overload")
    return fails


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--gate", action="store_true")
    ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
    res = run(a.quick)
    th = json.loads((PKG / "perf/thresholds.json").read_text())
    res["gate_failures"] = gate(res, th)
    import importlib
    sys.path.insert(0, str(PKG.parent))
    res["source_digest"] = importlib.import_module(PKG.name + ".evidence").source_digest()
    txt = json.dumps(res, indent=2, default=float)
    if a.out:
        pathlib.Path(a.out).write_text(txt + "\n")
    print(txt)
    sys.exit(1 if (a.gate and res["gate_failures"]) else 0)
