"""Benchmark suite (MC036, MC069-MC075, MC078).

Measures verify / compose / admit / parse+validate / verify_record latency
(p50/p95/p99/max), throughput under 1/4/16 threads, per-admission memory,
serialization cost and scaling with capability count, then either writes the
baseline (--write-baseline) or compares against perf/baseline.json and exits
non-zero on a regression beyond the tolerance (the performance regression gate).

Numbers are only comparable on the same hardware class; the baseline records it.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import platform
import statistics
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.path.insert(0, str(PKG / "tests"))
import _fixtures as F  # noqa: E402
from inv29_hybrid_wasm_unikernel import admission as adm  # noqa: E402
from inv29_hybrid_wasm_unikernel import records as R  # noqa: E402
from inv29_hybrid_wasm_unikernel.model import HostImage, WasmModule, compose, verify  # noqa: E402

TOLERANCE = 1.5  # fail if p95 regresses by more than 50 %


def lat(fn, n):
    xs = []
    for _ in range(n):
        t = time.perf_counter_ns(); fn(); xs.append((time.perf_counter_ns() - t) / 1e6)
    xs.sort()
    q = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]
    return {"n": n, "p50_ms": round(q(.50), 5), "p95_ms": round(q(.95), 5), "p99_ms": round(q(.99), 5),
            "max_ms": round(xs[-1], 5), "mean_ms": round(statistics.fmean(xs), 5)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--n", type=int, default=3000)
    args = ap.parse_args()
    kr = F.keyring()
    a = F.admitter(kr, replay=adm.ReplayGuard(capacity=10_000_000))
    host = HostImage("h", frozenset({"clock", "net-send", "net-recv"}))
    mod = WasmModule("svc", frozenset({"clock", "net-send"}))
    base_req = F.request(kr)
    fresh = lambda: adm.AdmissionRequest(**{**base_req.__dict__, "nonce": adm.new_nonce()})
    rec = a.admit(fresh())
    wire = R.canonical(rec)
    res = {"latency": {
        "verify": lat(lambda: verify(mod, host), args.n),
        "compose": lat(lambda: compose(mod, host), args.n),
        "admit": lat(lambda: a.admit(fresh()), args.n),
        "parse_validate": lat(lambda: R.parse(wire, schema="PK_HYBRID_COMPOSITION/1"), args.n),
        "verify_record": lat(lambda: adm.verify_record(kr, rec, expected_key_id=F.SIGN_KEY, now=F.NOW), args.n),
    }}
    # scaling with capability count (copy/serialization analysis)
    scale = {}
    for k in (1, 64, 512, 4096):
        caps = frozenset(f"c{i}" for i in range(k))
        m, h = WasmModule("m", caps), HostImage("h", caps)
        c = compose(m, h)
        scale[str(k)] = {"compose_p50_ms": lat(lambda: compose(m, h), 200)["p50_ms"],
                         "record_bytes": len(R.canonical(json.loads(json.dumps(c, default=list))))}
    res["capability_scaling"] = scale
    # throughput / overload
    thr = {}
    for t in (1, 4, 16):
        reqs = [fresh() for _ in range(2000)]
        s = time.perf_counter()
        with ThreadPoolExecutor(t) as ex:
            list(ex.map(a.admit, reqs))
        thr[str(t)] = round(2000 / (time.perf_counter() - s), 1)
    res["admit_throughput_per_s_by_threads"] = thr
    # memory per admission (bounded replay cache dominates)
    tracemalloc.start(); before = tracemalloc.get_traced_memory()[0]
    for _ in range(2000):
        a.admit(fresh())
    res["retained_bytes_per_admission"] = round((tracemalloc.get_traced_memory()[0] - before) / 2000, 1)
    tracemalloc.stop()
    res["record_bytes"] = len(wire)
    res["hardware"] = {"python": platform.python_version(), "machine": platform.machine(),
                       "processor": platform.processor() or "unknown", "system": platform.system()}
    out = PKG / "perf"
    out.mkdir(exist_ok=True)
    (out / "latest.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res["latency"], indent=1))
    basep = out / "baseline.json"
    if args.write_baseline or not basep.exists():
        basep.write_text(json.dumps(res, indent=2) + "\n")
        print("baseline written")
        return 0
    base = json.loads(basep.read_text())
    regress = {k: (v["p95_ms"], base["latency"][k]["p95_ms"]) for k, v in res["latency"].items()
               if v["p95_ms"] > base["latency"][k]["p95_ms"] * TOLERANCE and v["p95_ms"] > 0.05}
    (out / "regression_gate.json").write_text(json.dumps({"tolerance": TOLERANCE, "regressions": regress}, indent=2))
    if regress:
        print("PERF REGRESSION", regress)
        return 1
    print("perf gate: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
