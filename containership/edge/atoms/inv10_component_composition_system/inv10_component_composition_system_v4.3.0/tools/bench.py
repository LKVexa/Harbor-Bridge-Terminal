"""MC-37: reproducible link-latency benchmark (contract SLO: p99 < 200 ms @ 200 components).

Usage: python tools/bench.py [--components 200] [--iterations 500] [--seed 7] [--json out.json]
Graph: seeded random DAG, fan-in <= 4, one export per component, ~10% externals.
"""
import argparse, json, platform, random, statistics, sys, time
import _path  # noqa: F401
from inv10_component_composition_system.composition import Unit, compose


def graph(n, seed):
    rng = random.Random(seed)
    units, ext = [], set()
    for i in range(n):
        deps = rng.sample(range(i), min(i, rng.randint(0, 4))) if i else []
        imports = {f"pk:c{d}/api@1.0.0" for d in deps}
        if rng.random() < 0.1:
            e = f"wasi:x/e{rng.randint(0, 20)}@0.2.0"
            imports.add(e)
            ext.add(e)
        units.append(Unit(f"c{i}", frozenset(imports), frozenset({f"pk:c{i}/api@1.0.0"})))
    rng.shuffle(units)
    return units, frozenset(ext)


def run(n=200, iterations=500, seed=7):
    units, ext = graph(n, seed)
    for _ in range(20):
        compose(units, external=ext)
    samples = []
    for _ in range(iterations):
        t = time.perf_counter()
        compose(units, external=ext)
        samples.append((time.perf_counter() - t) * 1000)
    samples.sort()
    q = lambda p: samples[min(len(samples) - 1, int(p * len(samples)))]
    return {"components": n, "iterations": iterations, "seed": seed,
            "p50_ms": round(q(0.50), 3), "p95_ms": round(q(0.95), 3), "p99_ms": round(q(0.99), 3),
            "max_ms": round(samples[-1], 3), "mean_ms": round(statistics.mean(samples), 3),
            "slo_p99_ms": 200, "slo_met": q(0.99) < 200,
            "host": {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine()}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--components", type=int, default=200)
    ap.add_argument("--iterations", type=int, default=500)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--json")
    a = ap.parse_args()
    res = run(a.components, a.iterations, a.seed)
    print(json.dumps(res, indent=2))
    if a.json:
        open(a.json, "w").write(json.dumps(res, indent=2) + "\n")
    sys.exit(0 if res["slo_met"] else 1)
