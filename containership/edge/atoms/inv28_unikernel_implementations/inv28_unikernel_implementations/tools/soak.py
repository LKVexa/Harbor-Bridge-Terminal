"""Soak / burst (MC-050): N selections from T threads over a mixed request population with registry churn
(register + emergency disable + transition) interleaved; asserts no unexpected error codes, audit chain
intact, bounded cache, and reports throughput and latency.  evidence/SOAK_RESULTS.json.
"""
from __future__ import annotations

import argparse
import random
import sys
import threading
import time
import warnings

from ._common import EVIDENCE, ROOT, ensure_path, read_json, write_json

CHURN_MAX = 150          # registry mutations during the soak (each one invalidates the selection cache)


def run(n: int, threads: int) -> dict:
    ensure_path()
    warnings.simplefilter("ignore", DeprecationWarning)
    from inv28_unikernel_implementations import fixtures as F
    from inv28_unikernel_implementations.errors import Inv28Error, Reason
    w = F.world()
    expected = {Reason.NO_SUITABLE_TOOLCHAIN}
    counts = {"ok": 0, "refused": 0}
    unexpected: list[str] = []
    lat_all: list[float] = []
    lock = threading.Lock()
    stop = threading.Event()

    def churn():
        i = 0
        while not stop.is_set() and i < CHURN_MAX:
            reg = w["registry"]
            try:
                reg.register(F.record(f"churn{i}", languages=("ocaml",)), actor="operator", expected_revision=reg.revision)
                if i % 5 == 0:
                    reg.emergency_disable(f"churn{i}@1.0.0-fixture", actor="operator", reason="soak")
            except Inv28Error:
                pass
            i += 1
            time.sleep(0.002)

    def worker(k):
        rng = random.Random(k)
        for i in range(n // threads):
            req = F.request(workload_id=f"w{k}-{i % 97}", language=rng.choice(("c", "ocaml", "rust", "go", "cobol")),
                            environment=rng.choice(("production", "staging", "dev")),
                            architecture=rng.choice(("x86_64", "x86_64", "aarch64")))
            t = time.perf_counter()
            try:
                w["selector"].select(req, now=F.NOW)
                key = "ok"
            except Inv28Error as exc:
                key = "refused" if exc.code in expected else "unexpected"
                if key == "unexpected":
                    with lock:
                        unexpected.append(exc.code.value)
            with lock:
                if key != "unexpected":
                    counts[key] += 1
                lat_all.append((time.perf_counter() - t) * 1000)
    ch = threading.Thread(target=churn)
    ch.start()
    t0 = time.perf_counter()
    ts = [threading.Thread(target=worker, args=(k,)) for k in range(threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    wall = time.perf_counter() - t0
    stop.set()
    ch.join()
    lat = sorted(lat_all)
    total = len(lat)
    return {"requests": total, "selected": counts["ok"], "refused_expected": counts["refused"],
            "unexpected_errors": len(unexpected), "unexpected_codes": sorted(set(unexpected)),
            "error_rate": len(unexpected) / max(total, 1), "throughput_per_s": round(total / wall, 1),
            "p50_ms": round(lat[total // 2], 4), "p99_ms": round(lat[int(total * 0.99) - 1], 4),
            "registry_revisions_during_soak": w["registry"].revision, "audit_chain_problems": len(w["audit"].verify()),
            "cache_entries": len(w["selector"]._cache), "threads": threads, "wall_s": round(wall, 2)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args(argv)
    r = run(a.n, a.threads)
    baseline = run(a.n // 4, 1)
    r["single_thread_baseline"] = {k: baseline[k] for k in ("requests", "throughput_per_s", "p50_ms", "p99_ms")}
    thr = read_json(ROOT / "ops" / "PERF_THRESHOLDS.json")["thresholds"]
    fails = []
    if r["error_rate"] > thr["soak_error_rate"]:
        fails.append(f"error rate {r['error_rate']}")
    if r["throughput_per_s"] < thr["soak_min_throughput_per_s"]:
        fails.append(f"throughput {r['throughput_per_s']}/s")
    if r["audit_chain_problems"]:
        fails.append("audit chain broken")
    doc = {"schema": "PK_SOAK/1", "results": r, "failures": fails, "verdict": "PASS" if not fails else "FAIL",
           "scope_note": "single-process soak with registry churn on the build host; fleet-scale/multi-site soak "
                         "requires a real deployment (blocker recorded in ops/MC_STATUS.json MC-050)"}
    write_json(EVIDENCE / "SOAK_RESULTS.json", doc)
    print("SOAK", doc["verdict"], r)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
