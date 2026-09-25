"""Performance benchmark suite (#33): p50/p95/p99/max latency, throughput, memory.

Usage: python tools/benchmark.py [--n 500] [--threads 8] [--out bench.json]
Emits PK_BENCHMARK/1 JSON; release gates compare against budgets in
ops/slo-budgets.json (regression > budget fails the release evidence gate).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import statistics
import sys
import threading
import time
import tracemalloc

import _path  # noqa: F401

from gap07_artifact_provenance_signing.registry import verify_stream
from gap07_artifact_provenance_signing.signing import verify_signature
from gap07_artifact_provenance_signing.tests.fixtures import PKI, Env, T0


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def summarize(name, xs):
    return {"name": name, "n": len(xs), "p50_ms": round(pct(xs, 50) * 1e3, 3), "p95_ms": round(pct(xs, 95) * 1e3, 3),
            "p99_ms": round(pct(xs, 99) * 1e3, 3), "max_ms": round(max(xs) * 1e3, 3), "mean_ms": round(statistics.fmean(xs) * 1e3, 3)}


def timed(fn, n):
    out = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        out.append(time.perf_counter() - t)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    results = []
    cold = time.perf_counter()
    e = Env()
    results.append({"name": "cold_start_env", "ms": round((time.perf_counter() - cold) * 1e3, 3)})
    for alg in ("ed25519", "ecdsa-p256-sha256", "ecdsa-p384-sha384", "rsa-pss-sha256-3072"):
        pki = PKI(alg)
        t = pki.trust()
        env = pki.signer().sign(b"x", "code", now=T0)
        d = hashlib.sha256(b"x").hexdigest()
        results.append(summarize(f"verify_signature_{alg}", timed(lambda: verify_signature(env, digest_hex=d, kind="code", trust=t, now=T0), a.n)))
    req = e.full_request()
    e.ctl.cfg.decision_cache_ttl_s = -1  # measure uncached full pipeline
    results.append(summarize("admission_full_pipeline_uncached", timed(lambda: e.ctl.admit(req), a.n)))
    e.ctl.cfg.decision_cache_ttl_s = 300
    results.append(summarize("admission_cached", timed(lambda: e.ctl.admit(req), a.n)))
    blob = os.urandom(64 * 1024 * 1024)
    dg = "sha256:" + hashlib.sha256(blob).hexdigest()
    t = time.perf_counter()
    verify_stream(io.BytesIO(blob), dg)
    el = time.perf_counter() - t
    results.append({"name": "stream_hash_64MiB", "seconds": round(el, 4), "MiB_per_s": round(64 / el, 1)})
    lat, lock = [], threading.Lock()
    e.ctl.cfg.decision_cache_ttl_s = -1

    def w():
        xs = timed(lambda: e.ctl.admit(req), a.n // a.threads)
        with lock:
            lat.extend(xs)

    t = time.perf_counter()
    ts = [threading.Thread(target=w) for _ in range(a.threads)]
    [x.start() for x in ts]
    [x.join() for x in ts]
    wall = time.perf_counter() - t
    tracemalloc.start()  # memory measured on a separate pass so tracing does not distort latency
    for _ in range(50):
        e.ctl.admit(req)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    r = summarize(f"admission_concurrent_{a.threads}t", lat)
    r.update(throughput_per_s=round(len(lat) / wall, 1), peak_traced_MiB=round(peak / 2**20, 2))
    results.append(r)
    doc = {"schema": "PK_BENCHMARK/1", "python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
           "cpu_count": os.cpu_count(), "results": results,
           "note": "edge-node power/thermal impact must be measured on target hardware; this harness reports CPU-side latency only"}
    text = json.dumps(doc, indent=2)
    if a.out:
        open(a.out, "w").write(text + "\n")
    print(text)
    return doc


if __name__ == "__main__":
    main()
