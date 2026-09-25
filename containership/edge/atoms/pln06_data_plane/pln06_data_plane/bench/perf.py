"""PLN-06 performance baseline, load/scale, efficiency, power/thermal and capacity harness.

WP #29 baseline, #30 load/scale/recovery, #31 data-path efficiency, #32 edge power/thermal,
#33 capacity model + release gate.  Stdlib only.

    python -m pln06_data_plane.bench.perf run   --out bench/results/current.json [--quick]
    python -m pln06_data_plane.bench.perf gate  --baseline bench/baseline.json --current bench/results/current.json

The gate exits 1 when any metric regresses beyond its budget in ``BUDGETS``.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import pathlib
import platform
import statistics
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from pln06_data_plane import DataPlane  # noqa: E402
from pln06_data_plane.metadata import VERSION  # noqa: E402
from pln06_data_plane.observability import process_resources  # noqa: E402

# metric -> (direction, allowed relative regression)
BUDGETS = {
    "admit_p50_us": ("lower", 0.50),
    "admit_p99_us": ("lower", 1.00),
    "admit_throughput_per_s": ("higher", 0.35),
    "governed_inline_p99_ms": ("lower", 1.00),
    "shm_throughput_mb_s": ("higher", 0.50),
    "net_throughput_mb_s": ("higher", 0.50),
    "startup_ms": ("lower", 1.00),
    "max_rss_mb": ("lower", 0.50),
}
# absolute SLO ceilings (docs/NFR.md) - violated -> gate fails regardless of baseline
SLO = {"admit_p99_us": 2000.0, "governed_inline_p99_ms": 50.0}


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def bench_admit(n):
    plane = DataPlane({"s": {"c"}}, inflight_limit=1 << 30)
    lat = []
    t0 = time.perf_counter()
    for i in range(n):
        a = time.perf_counter()
        d = plane.admit(tenant="t", workload="w", size=(i % 3) * 70_000, classification="c", destination="s")
        lat.append((time.perf_counter() - a) * 1e6)
        plane.complete(d)
    wall = time.perf_counter() - t0
    return {"admit_p50_us": pct(lat, .5), "admit_p95_us": pct(lat, .95), "admit_p99_us": pct(lat, .99),
            "admit_worst_us": max(lat), "admit_throughput_per_s": n / wall}


def bench_concurrency(levels, per):
    """Load/scale sweep for the capacity model: throughput X(N) at concurrency N."""
    out = {}
    for n in levels:
        plane = DataPlane({"s": {"c"}}, inflight_limit=1 << 30)

        def work(_, plane=plane):
            for _i in range(per):
                plane.complete(plane.admit(tenant="t", workload="w", size=100_000, classification="c", destination="s"))
        t0 = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(n) as ex:
            list(ex.map(work, range(n)))
        out[n] = n * per / (time.perf_counter() - t0)
    return out


def usl_fit(xs):
    """Universal Scalability Law fit X(N)=lambda*N/(1+a(N-1)+b N(N-1)) by coarse grid search."""
    lam = xs[min(xs)] / min(xs)
    best = (float("inf"), 0.0, 0.0)
    for ai in range(0, 101):
        a = ai / 100
        for bi in range(0, 51):
            b = bi / 1000
            err = sum((lam * n / (1 + a * (n - 1) + b * n * (n - 1)) - x) ** 2 for n, x in xs.items())
            best = min(best, (err, a, b))
    _, a, b = best
    if b > 0 and a < 1:
        n_star = ((1 - a) / b) ** 0.5
    elif a >= 1 or b > 0:
        n_star = 1.0   # contention-bound (e.g. GIL): adding concurrency does not add throughput
    else:
        n_star = None  # linear within the measured range; no saturation observed
    peak = None if n_star is None else lam * n_star / (1 + a * (n_star - 1) + b * n_star * (n_star - 1))
    return {"lambda": lam, "sigma": a, "kappa": b, "saturation_concurrency": n_star, "predicted_peak_per_s": peak,
            "interpretation": "single-process admission is serialized by one lock; scale out by sharding "
                              "planes per node/tenant group rather than by threads"}


def bench_governed(n):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
    from _support import Env  # type: ignore
    e = Env(inflight_limit=64, ptl=64)
    lat = []
    try:
        for _ in range(n):
            a = time.perf_counter()
            e.send(b"x" * 256)
            lat.append((time.perf_counter() - a) * 1e3)
        shm = []
        blob = os.urandom(8 << 20)
        for _ in range(5):
            a = time.perf_counter()
            e.send(blob, locality="same_node")
            shm.append(len(blob) / (time.perf_counter() - a) / 1e6)
    finally:
        e.close()
    return {"governed_inline_p50_ms": pct(lat, .5), "governed_inline_p99_ms": pct(lat, .99),
            "shm_throughput_mb_s": statistics.median(shm)}


def bench_network():
    from pln06_data_plane import transports as t
    secret = os.urandom(32)
    srv = t.NetworkRpcServer({"p": secret}, max_bytes=1 << 30).start()
    try:
        cli = t.NetworkRpcAdapter(srv.address, peer_id="p", secret=secret, chunk_size=1 << 20)
        blob = os.urandom(16 << 20)
        rates = []
        for i in range(3):
            a = time.perf_counter()
            cli.send({"tier": "bulk", "locality": "remote", "size": len(blob), "transfer_id": f"b{i}", "tenant": "t"}, blob)
            rates.append(len(blob) / (time.perf_counter() - a) / 1e6)
    finally:
        srv.stop()
    return {"net_throughput_mb_s": statistics.median(rates)}


def efficiency_profile():
    """#31 copy/serialization/hop accounting per adapter (static analysis of the shipped code paths)."""
    return {
        "component-model-inprocess": {"copies": 0, "serializations": 0, "hops": 0, "context_switches": 0,
                                      "note": "read-only memoryview hand-off"},
        "shared-memory": {"copies": 2, "serializations": 0, "hops": 1, "context_switches": 0,
                          "note": "writer copy into segment + reader copy out; reader can map zero-copy"},
        "network-rpc": {"copies": 3, "serializations": 1, "hops": 1, "context_switches": ">=2 per chunk",
                        "note": "JSON header per 1 MiB chunk; payload bytes not serialized"},
        "vsock-control": {"copies": 1, "serializations": 1, "hops": 1, "context_switches": 2},
        "rdma": {"status": "not shipped (waiver W-004)"},
    }


def power_thermal():
    """#32 read RAPL energy and thermal zones where the platform exposes them."""
    out = {"rapl_uj": None, "thermal_c": []}
    rapl = pathlib.Path("/sys/class/powercap/intel-rapl:0/energy_uj")
    try:
        out["rapl_uj"] = int(rapl.read_text())
    except (OSError, ValueError):
        pass
    for z in sorted(pathlib.Path("/sys/class/thermal").glob("thermal_zone*/temp")):
        try:
            out["thermal_c"].append(int(z.read_text()) / 1000)
        except (OSError, ValueError):
            pass
    out["available"] = out["rapl_uj"] is not None or bool(out["thermal_c"])
    return out


def run(quick: bool) -> dict:
    t0 = time.perf_counter()
    import importlib

    import pln06_data_plane.service as svc
    importlib.reload(svc)
    startup_ms = (time.perf_counter() - t0) * 1e3
    energy0 = power_thermal()
    res = {"schema": "PK_PERF_RESULT/1", "version": VERSION, "python": platform.python_version(),
           "machine": platform.machine(), "platform": platform.platform(), "cpu_count": os.cpu_count(),
           "quick": quick, "ts": time.time(), "startup_ms": startup_ms}
    res.update(bench_admit(5_000 if quick else 50_000))
    res.update(bench_governed(100 if quick else 1000))
    res.update(bench_network())
    sweep = bench_concurrency([1, 2, 4, 8] if quick else [1, 2, 4, 8, 16, 32], 500 if quick else 3000)
    res["concurrency_sweep"] = {str(k): v for k, v in sweep.items()}
    res["capacity_model"] = usl_fit(sweep)
    res["efficiency"] = efficiency_profile()
    energy1 = power_thermal()
    res["power_thermal"] = {"before": energy0, "after": energy1}
    res["max_rss_mb"] = process_resources()["max_rss_bytes"] / 1e6
    return res


def gate(baseline: dict, current: dict) -> list[str]:
    failures = []
    for metric, (direction, tol) in BUDGETS.items():
        b, c = baseline.get(metric), current.get(metric)
        if b is None or c is None:
            failures.append(f"{metric}: missing (baseline={b}, current={c})")
            continue
        if direction == "lower" and c > b * (1 + tol):
            failures.append(f"{metric}: {c:.3f} > {b:.3f} * {1 + tol}")
        if direction == "higher" and c < b * (1 - tol):
            failures.append(f"{metric}: {c:.3f} < {b:.3f} * {1 - tol}")
    for metric, ceiling in SLO.items():
        if current.get(metric, float("inf")) > ceiling:
            failures.append(f"{metric}: SLO ceiling {ceiling} exceeded ({current.get(metric)})")
    return failures


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    r.add_argument("--quick", action="store_true")
    g = sub.add_parser("gate")
    g.add_argument("--baseline", required=True)
    g.add_argument("--current", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        res = run(a.quick)
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(res, indent=2, sort_keys=True))
        print(json.dumps({k: res[k] for k in BUDGETS}, indent=2))
        return 0
    fails = gate(json.loads(pathlib.Path(a.baseline).read_text()), json.loads(pathlib.Path(a.current).read_text()))
    for f in fails:
        print("PERF-GATE FAIL", f)
    print("PERF-GATE", "FAIL" if fails else "PASS")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
