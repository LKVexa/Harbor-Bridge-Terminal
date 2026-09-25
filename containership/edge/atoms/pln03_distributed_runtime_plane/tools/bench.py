"""Reproducible micro-benchmark + release-regression gate (MC-044).

python tools/bench.py [--n 20000] [--out evidence/bench.json]
Exit 1 if any percentile exceeds PERF_BUDGET.json.  Records overhead of the governed path vs core.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import platform
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT / "tests"))
from _helpers import cfg_with, config, make_plane, wire  # type: ignore  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def measure(fn, n):
    for _ in range(min(500, n)):
        fn()
    out = []
    for _ in range(n):
        t = time.perf_counter_ns()
        fn()
        out.append((time.perf_counter_ns() - t) / 1000)
    return {"n": n, "p50_us": round(pct(out, 50), 2), "p95_us": round(pct(out, 95), 2),
            "p99_us": round(pct(out, 99), 2), "max_us": round(max(out), 2)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    import time as _t
    cfg = cfg_with(limits={**config.DEFAULT["limits"], "rate_per_tenant_per_s": 1e12, "burst_per_tenant": 10**12})
    gp, tok, *_ = make_plane(cfg=cfg, clock=_t.monotonic)
    gp.state_set("api", "t1", "k", b"v" * 64, token=tok)
    counter = iter(range(10**9))
    req = json.dumps({"interface": "PK_STATE/1", "op": "get", "workload": "api", "tenant": "t1", "token": tok, "key": "k"})
    ops = {
        "core.state_get": lambda: gp.core.state_get("api", "t1", "k"),
        "governed.state_get": lambda: gp.state_get("api", "t1", "k", token=tok),
        "governed.state_set": lambda: gp.state_set("api", "t1", "k", b"v" * 64, token=tok),
        "governed.publish": lambda: gp.publish("api", "t1", "q", b"m", str(next(counter)), token=tok),
        "wire.state_get": lambda: wire.handle(gp, req),
    }
    budget = json.loads((ROOT / "PERF_BUDGET.json").read_text())["operations"]
    results, failures = {}, []
    for name, fn in ops.items():
        r = measure(fn, a.n)
        results[name] = r
        for k, ceiling in budget.get(name, {}).items():
            if r[k] > ceiling:
                failures.append(f"{name}.{k}={r[k]} > {ceiling}")
    results["overhead_governed_vs_core_p50_x"] = round(results["governed.state_get"]["p50_us"] /
                                                       max(results["core.state_get"]["p50_us"], 0.01), 1)
    report = {"schema": "pk.bench/1", "python": sys.version.split()[0], "platform": platform.platform(),
              "machine": platform.machine(), "results": results, "failures": failures,
              "status": "PASS" if not failures else "FAIL"}
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
