"""Measure the 4.3.0 hot path against the frozen 4.2.0 runtime (benchmarks/reference/).
Median of per-run p50/p99 over N runs; writes benchmarks/results/version-compare.json."""
import gc, importlib.util, json, statistics, sys, time
from _tools_pkg import ROOT, mod


def load_old():
    sp = importlib.util.spec_from_file_location("inv17_stream_420", ROOT / "benchmarks" / "reference" / "stream_4_2_0.py")
    m = importlib.util.module_from_spec(sp); sys.modules[sp.name] = m; sp.loader.exec_module(m); return m


def h(S, n=50000):
    s = S.Stream(int, config=S.StreamConfig(max_credit=n + 1, max_buffer=n + 1)); s.grant(n)
    pc = time.perf_counter_ns; o = []
    gc.disable()
    try:
        for i in range(n):
            t = pc(); s.write(i); s.read(); o.append(pc() - t)
    finally:
        gc.enable()
    o.sort(); return o[len(o) // 2], o[int(.99 * len(o))]


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    old, new = load_old(), mod("stream")
    r = {"4.2.0": [], "4.3.0": []}
    for _ in range(runs):
        r["4.2.0"].append(h(old)); r["4.3.0"].append(h(new))
    out = {v: {"median_p50_ns": statistics.median(a for a, _ in x), "median_p99_ns": statistics.median(b for _, b in x)} for v, x in r.items()}
    out["p50_ratio_new_over_old"] = round(out["4.3.0"]["median_p50_ns"] / out["4.2.0"]["median_p50_ns"], 3)
    out["runs"] = runs
    (ROOT / "benchmarks" / "results" / "version-compare.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out))
