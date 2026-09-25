"""Item 22 benchmark corpus (C061-C070, C088). Stdlib only.

    python conformance/performance/bench.py [--quick] [--out evidence/benchmarks/bench.json]

Records raw samples, host profile and percentiles, then enforces thresholds.json.
Exit 0 = within budget, 1 = budget breached.
"""
from __future__ import annotations

import argparse, json, os, pathlib, platform, statistics, subprocess, sys, time, tracemalloc

HERE = pathlib.Path(__file__).resolve()
PKG = HERE.parents[2]
sys.path.insert(0, str(PKG.parent))
import importlib  # noqa: E402
m = importlib.import_module(PKG.name + ".model")
st = importlib.import_module(PKG.name + ".store")
az = importlib.import_module(PKG.name + ".authz")


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def summarize(xs):
    return {"n": len(xs), "p50": pct(xs, 50), "p95": pct(xs, 95), "p99": pct(xs, 99), "max": max(xs),
            "mean": statistics.fmean(xs)}


def timeit(fn, n, warm=20):
    for _ in range(warm):
        fn()
    out = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        out.append(time.perf_counter() - t)
    return out


def spec(i, regs=4, ver="1.0"):
    return m.DeviceSpec(f"d{i}", "paravirtual", ver, frozenset(f"r{j}" for j in range(regs)), "why", "sec")


def max_catalogue():
    c = m.DeviceCatalogue("prod")
    for i in range(m.MAX_DEVICES):
        c.register(spec(i, m.MAX_AGGREGATE_REGISTERS // m.MAX_DEVICES))
    return c


def run(quick=False):
    n = 200 if quick else 2000
    raw = {}
    raw["import_seconds"] = []
    for _ in range(3 if quick else 10):
        t = time.perf_counter()
        subprocess.run([sys.executable, "-c", f"import {PKG.name}"], cwd=str(PKG.parent), check=True)
        raw["import_seconds"].append(time.perf_counter() - t)
    raw["register_small"] = timeit(lambda: m.DeviceCatalogue("prod").register(spec(0)), n)
    big = max_catalogue()
    names = list(big.devices)

    def reg_big():
        c = m.DeviceCatalogue("prod")
        c.devices = dict(big.devices)
        c.devices.pop(names[-1])
        c.register(big.devices[names[-1]])
    raw["register_max_catalogue"] = timeit(reg_big, n // 4)
    counter = iter(range(10**9))
    raw["replace_diff"] = timeit(lambda: big.replace(spec(0, 64, f"2.{next(counter)}")), n // 4)
    raw["export_max_catalogue"] = timeit(big.export, n // 10)
    export_bytes = len(m.canonical_json(big.export()))
    tracemalloc.start()
    max_catalogue()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    clock = [1_800_000_000.0]
    v = az.Verifier(audience="a", keys={"k": ("i", b"k")}, clock=lambda: clock[0])
    s = st.CatalogueStore("prod", v, mutation_burst=10**9)
    caps = ["catalogue.register", "catalogue.activate", "catalogue.approve"]
    seq = iter(range(10**9))

    def tok(sub):
        return az.mint_token(b"k", key_id="k", issuer="i", subject=sub, audience="a", capabilities=caps,
                             environments=["prod"], nonce=f"b{next(seq)}", now=clock[0])
    i2 = iter(range(10**6))

    def cycle():
        c = s.propose(tok("p"), "register", m.DeviceSpec(f"x{next(i2)}", "paravirtual", "1.0", frozenset(), "w", "s"))
        s.approve(tok("q"), c["candidate"])
        s.activate(tok("p"), c["candidate"], expected_digest=c["base"])
    raw["store_activation_cycle"] = timeit(cycle, min(m.MAX_DEVICES - 25, 30), warm=5)
    summary = {k: summarize(v) for k, v in raw.items()}
    summary["max_catalogue_export_bytes"] = export_bytes
    summary["max_catalogue_peak_alloc_mb"] = peak / 2**20
    return raw, summary


def enforce(summary, budgets):
    checks = {
        "import_seconds_p95": summary["import_seconds"]["p95"],
        "register_small_p99": summary["register_small"]["p99"],
        "register_max_catalogue_p99": summary["register_max_catalogue"]["p99"],
        "replace_diff_p99": summary["replace_diff"]["p99"],
        "export_max_catalogue_p99": summary["export_max_catalogue"]["p99"],
        "store_activation_cycle_p99": summary["store_activation_cycle"]["p99"],
        "max_catalogue_export_bytes": summary["max_catalogue_export_bytes"],
        "max_catalogue_rss_growth_mb": summary["max_catalogue_peak_alloc_mb"],
    }
    return {k: {"measured": v, "budget": budgets[k], "pass": v <= budgets[k]} for k, v in checks.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    raw, summary = run(a.quick)
    budgets = json.loads((HERE.parent / "thresholds.json").read_text())["budgets"]
    verdict = enforce(summary, budgets)
    doc = {"schema": "INV25_BENCH_RESULT/1", "host": {"python": sys.version.split()[0],
           "impl": platform.python_implementation(), "machine": platform.machine(),
           "system": platform.system(), "release": platform.release(), "cpus": os.cpu_count()},
           "quick": a.quick, "summary": summary, "verdict": verdict,
           "pass": all(x["pass"] for x in verdict.values()), "raw_samples": raw}
    text = json.dumps(doc, indent=1, sort_keys=True)
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(text)
    print(json.dumps({k: doc[k] for k in ("host", "verdict", "pass")}, indent=1))
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
