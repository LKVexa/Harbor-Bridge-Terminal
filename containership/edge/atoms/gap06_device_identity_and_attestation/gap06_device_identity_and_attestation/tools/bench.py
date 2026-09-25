"""MC-39 / MC-42: baseline, burst and bounded-growth measurement.

Measures the complete service path (challenge + attest with event log) on the
software attester, the verifier alone, and state growth over a soak.  Numbers
are *this container's* baseline, not production thresholds.  Writes
evidence/bench.json.
"""
import json
import os
import platform
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import _kit as k  # noqa: E402

from ..mc import ratelimit  # noqa: E402
from ..mc.errors import Gap06Error  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p))]


def main(n=400, nodes=20):
    w = k.World()
    w.svc.admission = ratelimit.Admission(rate=1e9, burst=1e9, global_rate=1e9, global_burst=1e9)
    tpms = {f"n{i}": w.enrol(f"n{i}") for i in range(nodes)}
    w.publish_for(tpms["n0"])
    lat = []
    tracemalloc.start()
    m0 = tracemalloc.get_traced_memory()[0]
    t_start = time.perf_counter()
    for i in range(n):
        name = f"n{i % nodes}"
        w.mono.advance(0.05)
        t0 = time.perf_counter()
        r = w.svc.attest(k.node_principal(name), w.attest_msg(name, tpms[name], idem=f"b{i}"))
        lat.append((time.perf_counter() - t0) * 1000)
        assert r["decision"] == "trusted"
    wall = time.perf_counter() - t_start
    m1 = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    # soak: 3 more rounds, check challenge table stays bounded by the TTL window
    sizes = []
    for rnd in range(3):
        for i in range(n):
            name = f"n{i % nodes}"
            w.mono.advance(0.5)
            w.svc.attest(k.node_principal(name), w.attest_msg(name, tpms[name], idem=f"s{rnd}-{i}"))
        sizes.append(len(w.store.items("challenges")))
    # burst: 2000 requests in one instant against default admission
    adm = ratelimit.Admission()
    ok = rej = 0
    for i in range(2000):
        try:
            adm.admit(f"p{i % 50}", 0.0); ok += 1
        except Gap06Error:
            rej += 1
    res = {"schema": "GAP06-BENCH/1", "env": {"python": sys.version.split()[0], "platform": platform.platform(),
                                              "cpus": os.cpu_count()},
           "attest_path": {"n": n, "p50_ms": round(statistics.median(lat), 3), "p99_ms": round(pct(lat, 0.99), 3),
                           "max_ms": round(max(lat), 3), "throughput_per_s": round(n / wall, 1)},
           "memory": {"traced_growth_bytes": m1 - m0, "per_attestation_bytes": round((m1 - m0) / n)},
           "soak": {"challenge_table_sizes": sizes, "bounded": max(sizes) <= 2 * nodes + 70,
                    "idempotency_rows": len(w.store.items("idempotency")),
                    "note": "idempotency rows grow per request: retention/TTL for them is NOT implemented"},
           "burst": {"requests": 2000, "admitted": ok, "rejected": rej}}
    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/bench.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
