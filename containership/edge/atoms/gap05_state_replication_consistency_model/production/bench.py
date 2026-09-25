"""MC39 soak/burst/fleet benchmarks and MC46 capacity model + release regression gates.

Measures on the host it runs on (numbers are machine-specific and are recorded with
the platform string):

* apply latency p50/p95/p99/max for local authoring (includes sign + verify + WAL fsync
  + audit fsync), and for the pure in-memory core
* throughput (writes/s) for a burst, and memory growth (tracemalloc peak) over a soak
* vector growth with N replicas, quarantine pressure under a conflict flood
* recovery rate (WAL records replayed per second) and anti-entropy repair rate

``GATES`` are **PROPOSED** thresholds (no production SLO has been agreed by an owner);
``gate()`` reports ``met_under_proposed_target`` / ``missed`` per metric and never
converts a proposed threshold into a certified pass.
"""
from __future__ import annotations

import json
import platform
import sys
import time
import tracemalloc

from ..model import ReplicatedKey, Write
from .anti_entropy import reconcile
from .testkit import Cluster, E, T

GATES = {  # PROPOSED - requires owner sign-off before use as a release gate
    "core_apply_p99_ms": ("<=", 0.5),
    "node_write_p99_ms": ("<=", 25.0),
    "node_burst_writes_per_s": (">=", 200.0),
    "recovery_records_per_s": (">=", 2000.0),
    "soak_peak_mib": ("<=", 256.0),
    "quarantine_flood_accepted_ratio": ("==", 1.0),
}


def _pct(vals, q):
    s = sorted(vals)
    return s[min(len(s) - 1, int(q * len(s)))]


def bench_core(n=20_000):
    rk = ReplicatedKey("k", frozenset(f"s{i}" for i in range(8)), max_siblings=8)
    lat = []
    for i in range(1, n + 1):
        # single-writer supersession chain: each write dominates the previous one
        t = time.perf_counter()
        rk.apply(Write("k", str(i), "s0", (("s0", i),)))
        lat.append((time.perf_counter() - t) * 1000)
    return {"core_apply_p50_ms": _pct(lat, .5), "core_apply_p95_ms": _pct(lat, .95),
            "core_apply_p99_ms": _pct(lat, .99), "core_apply_max_ms": max(lat), "core_n": n}


def bench_node(n=400, keys=50):
    c = Cluster(("a", "b"))
    try:
        a = c.nodes["a"]
        lat = []
        t0 = time.perf_counter()
        for i in range(n):
            t = time.perf_counter()
            a.write(T, E, f"k{i % keys}", f"v{i}", principal="operator")
            lat.append((time.perf_counter() - t) * 1000)
            a.admission.advance()
        dur = time.perf_counter() - t0
        out = {"node_write_p50_ms": _pct(lat, .5), "node_write_p95_ms": _pct(lat, .95),
               "node_write_p99_ms": _pct(lat, .99), "node_write_max_ms": max(lat),
               "node_burst_writes_per_s": n / dur, "node_n": n}
        t = time.perf_counter()
        r = reconcile(a, c.nodes["b"], T, E, principal_a=c.principal("a"), principal_b=c.principal("b"))
        out["anti_entropy_keys_per_s"] = keys / (time.perf_counter() - t)
        out["anti_entropy_converged"] = r["converged"]
        wal_records = len(a.wal.records)
        t = time.perf_counter()
        a2 = c.reopen("a")
        out["recovery_records_per_s"] = wal_records / (time.perf_counter() - t)
        out["recovery_replayed"] = a2.recovery_report["replayed"]
        return out
    finally:
        c.close()


def bench_soak(rounds=3000):
    tracemalloc.start()
    rk_by_key = {}
    for i in range(rounds):
        k = f"k{i % 200}"
        rk = rk_by_key.setdefault(k, ReplicatedKey(k, frozenset({"a", "b", "c"}), max_siblings=4))
        rk.apply(Write(k, str(i), "a", (("a", i + 1),)))
        if i % 3 == 0:
            rk.apply(Write(k, f"b{i}", "b", (("b", i + 1),)))
            rk.resolve("r", "c")
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    discarded = sum(len(rk.discarded) for rk in rk_by_key.values())
    return {"soak_peak_mib": peak / 2**20, "soak_rounds": rounds,
            "soak_discarded_records_unbounded": discarded,
            "note": "core ReplicatedKey.discarded grows without bound (in-memory audit); the production node "
                    "bounds durable audit via AuditLedger segments + archive"}


def bench_vectors(replicas=(4, 16, 64)):
    out = {}
    for r in replicas:
        vec = tuple((f"s{i:03d}", 1) for i in range(r))
        w = Write("k", "v", "s000", vec)
        out[f"vector_bytes_{r}_replicas"] = len(json.dumps(w.vector))
    return out


def bench_quarantine_flood(n=200, bound=8):
    rk = ReplicatedKey("k", frozenset(f"s{i}" for i in range(n)), max_siblings=bound)
    accepted = 0
    for i in range(n):
        accepted += rk.apply(Write("k", str(i), f"s{i}", ((f"s{i}", 1),))) in ("converged", "conflict", "quarantined")
    return {"quarantine_flood_writes": n, "quarantine_depth": len(rk.quarantine),
            "quarantine_flood_accepted_ratio": accepted / n}


def bench_codec(n=2000, value_bytes=16384):
    """MC43-009: JSON canonical vs binary codec encode+decode cost for a large-value write."""
    from .schemas import canonical_bytes, make_write_doc, strict_loads, validate_write_doc
    from .transport import decode_write_bin, encode_write_bin
    doc = make_write_doc(tenant="t", environment="e", key="k", value="x" * value_bytes, site="a",
                         vector={f"s{i}": i + 1 for i in range(16)} | {"a": 1}, epoch=1)
    t = time.perf_counter()
    for _ in range(n):
        validate_write_doc(strict_loads(canonical_bytes(doc)))
    json_us = (time.perf_counter() - t) / n * 1e6
    t = time.perf_counter()
    for _ in range(n):
        decode_write_bin(encode_write_bin(doc))
    bin_us = (time.perf_counter() - t) / n * 1e6
    t = time.perf_counter()
    blob = encode_write_bin(doc)
    for _ in range(n):
        decode_write_bin(blob, lazy_value=True)
    lazy_us = (time.perf_counter() - t) / n * 1e6
    return {"codec_json_roundtrip_us": json_us, "codec_binary_roundtrip_us": bin_us,
            "codec_binary_lazy_decode_us": lazy_us, "codec_value_bytes": value_bytes,
            "codec_json_bytes": len(canonical_bytes(doc)), "codec_binary_bytes": len(blob)}


def gate(results: dict) -> dict:
    out = {}
    for metric, (op, target) in GATES.items():
        val = results.get(metric)
        if val is None:
            out[metric] = {"status": "not_measured"}
            continue
        ok = {"<=": val <= target, ">=": val >= target, "==": val == target}[op]
        out[metric] = {"value": val, "target": f"{op} {target}", "status": "met_under_proposed_target" if ok else "missed"}
    return out


def run_all(quick=False) -> dict:
    res = {"platform": platform.platform(), "python": sys.version.split()[0]}
    res.update(bench_core(5_000 if quick else 20_000))
    res.update(bench_node(120 if quick else 400))
    res.update(bench_soak(1000 if quick else 3000))
    res.update(bench_vectors())
    res.update(bench_quarantine_flood())
    res.update(bench_codec(300 if quick else 2000))
    res["gates"] = gate(res)
    return res


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run_all("--quick" in sys.argv), indent=1, default=str))
