"""M51/M52/M56/M57 - reproducible benchmark of the reference control plane.

Measures (fixed seeds, fixed op counts): token authentication, capability-checked
call, full authenticated call, start, failover time, and a concurrency sweep for
the saturation knee. Writes release/BENCHMARK.json. With --check, compares to
release/BENCHMARK_BASELINE.json and exits 1 on regression beyond tolerance.
Numbers describe THIS machine only (recorded in the output)."""
import json, os, pathlib, platform, statistics, sys, threading, time
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.path.insert(0, str(PKG / "tests")); sys.dont_write_bytecode = True
from _harness import World  # noqa: E402

TOL = 3.0   # regression if p99 > baseline * TOL (noisy shared runners)


def pct(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]


def summary(xs):
    return {"n": len(xs), "p50_ms": round(pct(xs, 50) * 1e3, 4), "p95_ms": round(pct(xs, 95) * 1e3, 4),
            "p99_ms": round(pct(xs, 99) * 1e3, 4), "max_ms": round(max(xs) * 1e3, 4), "mean_ms": round(statistics.mean(xs) * 1e3, 4)}


def run(n=300):
    w = World(limits={"rate_per_tenant": 100000.0, "burst_per_tenant": 100000, "max_inflight_per_tenant": 10000,
                      "max_inflight_global": 100000})
    w.mono = time.monotonic
    w.fabric.mono = time.monotonic
    w.deploy(app="bench")
    w.fabric.link(w.tok("deployer-a"), "api", "kv", lambda *a: 1, tenant="tenant-a", grantee=w.p["api"].id, operations=("get",))
    f, res = w.fabric, {}
    toks = [w.tok("api") for _ in range(n)]
    t = []
    for tk in toks:
        s = time.perf_counter(); w.trust.authenticate(tk, "inv60-fabric"); t.append(time.perf_counter() - s)
    res["auth_verify"] = summary(t)
    t = []
    pr = w.p["api"]
    for _ in range(n):
        s = time.perf_counter()
        f.authz.check_capability(pr, "api", "kv", "get", "tenant-a"); f.lattice.call("api", "kv", "get")
        t.append(time.perf_counter() - s)
    res["capability_checked_call"] = summary(t)
    toks = [w.tok("api") for _ in range(n)]
    t = []
    for tk in toks:
        s = time.perf_counter(); r = f.call(tk, "api", "kv", "get", tenant="tenant-a"); t.append(time.perf_counter() - s)
        assert r.code == "OK", r.to_wire()
    res["authenticated_call"] = summary(t)
    # failover time (control-plane part: declare lost -> all moved)
    t = []
    for i in range(20):
        w2 = World(hosts=("a", "b", "c"))
        for j in range(6):
            w2.deploy(f"c{j}", name=f"tenant-a/c{j}", data=f"{i}-{j}".encode())
        w2.mono.advance(9); w2.fabric.heartbeat("b"); w2.fabric.heartbeat("c")
        s = time.perf_counter(); w2.fabric.sweep(); t.append(time.perf_counter() - s)
    res["failover_control_plane"] = summary(t)
    # saturation sweep
    sweep = []
    for conc in (1, 2, 4, 8, 16):
        per = 60
        tks = [[w.tok("api") for _ in range(per)] for _ in range(conc)]
        lat, lock = [], threading.Lock()
        def worker(ts):
            loc = []
            for tk in ts:
                s = time.perf_counter(); f.call(tk, "api", "kv", "get", tenant="tenant-a"); loc.append(time.perf_counter() - s)
            with lock:
                lat.extend(loc)
        ths = [threading.Thread(target=worker, args=(x,)) for x in tks]
        s = time.perf_counter(); [x.start() for x in ths]; [x.join() for x in ths]; el = time.perf_counter() - s
        sweep.append({"concurrency": conc, "throughput_ops_s": round(conc * per / el, 1), "p99_ms": round(pct(lat, 99) * 1e3, 3)})
    best = max(sweep, key=lambda r: r["throughput_ops_s"])
    knee = next((r["concurrency"] for r in sweep if r["throughput_ops_s"] >= 0.9 * best["throughput_ops_s"]), best["concurrency"])
    res["saturation"] = {"sweep": sweep, "knee_concurrency": knee}
    slo = {"routing_overhead_p99_ms_target": 3.0, "capability_checked_call_p99_ms": res["capability_checked_call"]["p99_ms"],
           "authenticated_call_p99_ms": res["authenticated_call"]["p99_ms"],
           "met_capability_checked": res["capability_checked_call"]["p99_ms"] < 3.0,
           "met_authenticated": res["authenticated_call"]["p99_ms"] < 3.0,
           "failover_control_plane_p99_ms": res["failover_control_plane"]["p99_ms"]}
    return {"schema": "inv60.bench/1", "machine": {"python": platform.python_version(), "platform": platform.platform(),
            "cpus": os.cpu_count()}, "representative_hardware": False, "results": res, "slo_check": slo}


def main():
    out = run()
    rel = PKG / "release"; rel.mkdir(exist_ok=True)
    (rel / "BENCHMARK.json").write_text(json.dumps(out, indent=1))
    base = rel / "BENCHMARK_BASELINE.json"
    if "--set-baseline" in sys.argv or not base.exists():
        base.write_text(json.dumps(out, indent=1))
    if "--check" in sys.argv:
        b = json.loads(base.read_text())["results"]
        bad = [k for k in ("auth_verify", "capability_checked_call", "authenticated_call", "failover_control_plane")
               if out["results"][k]["p99_ms"] > b[k]["p99_ms"] * TOL]
        print(json.dumps({"regressions": bad, "tolerance_x": TOL}))
        sys.exit(1 if bad else 0)
    print(json.dumps(out["slo_check"]))


if __name__ == "__main__":
    main()
