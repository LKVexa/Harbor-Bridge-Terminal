"""C061-C064/C066: reproducible benchmark harness for INV-17 (stdlib only).

Measures, per profile in benchmarks/profiles.json:
  handoff_ns       write+read of one element with credit available (p50/p95/p99/p999/max)
  throughput       elements/s for a batched grant/write/read loop
  startup_us       Stream construction cost
  memory           tracemalloc peak for N in-flight elements
  multitenant      per-element overhead through StreamRegistry at 1..N tenants (C064)
Writes benchmarks/results/latest.json with the environment fingerprint so a run is
reproducible and comparable (tools/perf_gate.py). Numbers are measurements of THIS host.
"""
import argparse, gc, json, os, platform, statistics, sys, time, tracemalloc
from _tools_pkg import ROOT, mod

S = mod("stream"); C = mod("control")


def pct(xs, q):
    xs = sorted(xs); k = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
    return xs[k]


def handoff(n):
    s = S.Stream(int, config=S.StreamConfig(max_credit=n + 1, max_buffer=n + 1)); s.grant(n)
    pc = time.perf_counter_ns; out = []
    gc.disable()
    try:
        for i in range(n):
            t0 = pc(); s.write(i); s.read(); out.append(pc() - t0)
    finally:
        gc.enable()
    return out


def throughput(n):
    s = S.Stream(int, config=S.StreamConfig(max_credit=1024, max_buffer=1024))
    t0 = time.perf_counter(); done = 0
    while done < n:
        s.grant(1024)
        for i in range(1024): s.write(i)
        for i in range(1024): s.read()
        done += 1024
    return done / (time.perf_counter() - t0)


def startup(n=2000):
    t0 = time.perf_counter_ns()
    for _ in range(n): S.Stream(int)
    return (time.perf_counter_ns() - t0) / n / 1000


def memory(n=10000):
    gc.collect(); tracemalloc.start()
    s = S.Stream(int, config=S.StreamConfig(max_credit=n, max_buffer=n)); s.grant(n)
    for i in range(n): s.write(i)
    _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    return {"elements": n, "peak_bytes": peak, "bytes_per_element": round(peak / n, 1)}


def multitenant(tenants, per=2000):
    r = C.StreamRegistry(global_buffer_budget=1 << 30)
    toks = []
    for t in range(tenants):
        tok = r.authority.issue(f"s{t}", f"t{t}", "w", ["open", "write"])
        s = r.open(int, tenant=f"t{t}", workload="w", token=tok, stream_id=f"s{t}",
                   config=S.StreamConfig(max_credit=per, max_buffer=per)); s.grant(per); toks.append((s, tok))
    t0 = time.perf_counter_ns()
    for i in range(per):
        for t, (s, tok) in enumerate(toks):
            r.write(f"s{t}", i, tenant=f"t{t}", workload="w", token=tok)
    via_registry = (time.perf_counter_ns() - t0) / (per * tenants)
    return {"tenants": tenants, "ns_per_element_via_registry": round(via_registry, 1)}


def run(profile):
    cfg = json.loads((ROOT / "benchmarks" / "profiles.json").read_text())["profiles"][profile]
    runs = [handoff(cfg["handoff_iterations"]) for _ in range(cfg["repeats"])]
    lat = [x for r in runs for x in r]
    tp = [throughput(cfg["throughput_elements"]) for _ in range(cfg["repeats"])]
    p99 = pct(lat, 0.99)
    return {
        "component": "INV-17", "version": (ROOT / "VERSION").read_text().strip(), "profile": profile,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                        "machine": platform.machine(), "system": platform.system(), "cpu_count": os.cpu_count(),
                        "optimized": sys.flags.optimize},
        "handoff_ns": {"samples": len(lat), "p50": pct(lat, .5), "p95": pct(lat, .95), "p99": p99,
                       "p999": pct(lat, .999), "max": max(lat), "mean": round(statistics.fmean(lat), 1)},
        "throughput_eps": {"median": round(statistics.median(tp)), "min": round(min(tp)), "max": round(max(tp))},
        "startup_us": round(startup(), 2),
        "memory": memory(),
        "multitenant": [multitenant(t) for t in cfg["tenants"]],
        "slo_assessment": {"SLO-3": {"objective_ns": 1000, "p99_ns": p99, "met": p99 < 1000,
                                     "budget": "1% may exceed", "fraction_over": round(sum(1 for x in lat if x >= 1000) / len(lat), 4)}},
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--profile", default="ci-small"); ap.add_argument("--out", default=str(ROOT / "benchmarks" / "results" / "latest.json"))
    a = ap.parse_args()
    res = run(a.profile)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w").write(json.dumps(res, indent=2) + "\n")
    print(json.dumps({k: res[k] for k in ("handoff_ns", "throughput_eps", "startup_us", "slo_assessment")}, indent=1))
