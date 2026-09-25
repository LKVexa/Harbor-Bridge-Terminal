"""Performance baseline (50) -- p50/p95/p99 for the hot paths, written to
``evidence/perf_baseline.json`` with the host descriptor.  Numbers are only
meaningful for the host that produced them; the regression gate (52)
compares like with like and refuses a comparison across hosts."""
from __future__ import annotations

import json
import os
import platform
import statistics
import sys
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

import fixtures  # noqa: E402
from gap09_unified_observability.components import ed25519  # noqa: E402
from gap09_unified_observability.components.canonical import canonical_bytes, submission_envelope  # noqa: E402
from gap09_unified_observability.components.signals import parse_traceparent  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def measure(name, fn, n):
    ts = []
    tracemalloc.start()
    for i in range(n):
        t0 = time.perf_counter_ns()
        fn(i)
        ts.append(time.perf_counter_ns() - t0)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"name": name, "n": n, "p50_us": pct(ts, 50) / 1e3, "p95_us": pct(ts, 95) / 1e3, "p99_us": pct(ts, 99) / 1e3,
            "mean_us": statistics.fmean(ts) / 1e3, "peak_alloc_kib": round(peak / 1024, 1)}


def main(out: str | None = None, quick: bool = False) -> dict:
    k = 5 if quick else 1
    samples = [fixtures.sample(signal=f"s{i}") for i in range(10)]
    env = submission_envelope("rep-a", "b", 1000, samples, "k1")
    msg = canonical_bytes(env)
    sig = ed25519.sign(fixtures.SK_A, msg)
    ingest, *_ = fixtures.make_stack(fixtures.tmpdir(), tenant_series=10**6, rate=1e12)
    pre = [fixtures.signed([fixtures.sample(signal=f"s{i % 100}", at=100 + i // 100)], sid=f"b{i}") for i in range(400 // k)]
    results = [
        measure("canonicalize_10_samples", lambda i: canonical_bytes(env), 2000 // k),
        measure("ed25519_verify", lambda i: ed25519.verify(fixtures.PK_A, msg, sig), 200 // k),
        measure("traceparent_parse", lambda i: parse_traceparent("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"), 5000 // k),
        measure("verified_ingest_1_sample_fsync", lambda i: ingest.submit(**pre[i]), len(pre)),
    ]
    doc = {"schema": "GAP09-PERF/1", "host": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                                             "machine": platform.machine(), "system": platform.system()},
           "quick": quick, "results": results}
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True)
    return doc


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = main(os.path.join(here, "evidence", "perf_baseline.json"))
    for r in d["results"]:
        print(f"{r['name']:34s} p50 {r['p50_us']:9.1f}us  p95 {r['p95_us']:9.1f}us  p99 {r['p99_us']:9.1f}us")
