"""MC65 — micro-benchmarks and a short soak.

    python -m inv02_container_substrate.tools.bench [--soak-seconds N] [--json OUT]

Reports throughput/latency for the hot paths (CAS put/get with re-hash, manifest parse,
layer unpack, Ed25519 verify, policy evaluation) plus RSS growth over the soak.  Fleet-
scale and cross-host benchmarks are out of scope for a single host (see COMPATIBILITY.md).
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import statistics
import tempfile
import time

from inv02_container_substrate import oci, policy, rootfs, store, trust
from inv02_container_substrate.tests.fixtures import make_image, make_tar


def timeit(fn, n):
    lat = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        lat.append(time.perf_counter() - t0)
    return {"n": n, "p50_ms": round(statistics.median(lat) * 1e3, 3),
            "p99_ms": round(sorted(lat)[max(0, int(n * 0.99) - 1)] * 1e3, 3),
            "ops_per_s": round(n / sum(lat), 1)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--soak-seconds", type=float, default=5.0)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = {}
    with tempfile.TemporaryDirectory() as tmp:
        s = store.ContentStore(os.path.join(tmp, "s"))
        blob = os.urandom(1 << 20)
        d = s.put(blob)
        res["cas_put_1MiB"] = timeit(lambda: s.put(os.urandom(1 << 20)), 30)
        res["cas_get_verify_1MiB"] = timeit(lambda: s.get(d), 100)
        img = make_image([[("a", "file", b"x" * 1000)]] * 3)
        res["manifest_parse"] = timeit(lambda: oci.parse_manifest(img["manifest"]), 2000)
        layer, did = make_tar([(f"f{i}", "file", os.urandom(2048)) for i in range(200)])
        c = [0]

        def unpack():
            c[0] += 1
            rootfs.apply_layer(os.path.join(tmp, f"u{c[0]}"), layer, diff_id=did)
        res["unpack_200_files"] = timeit(unpack, 20)
        sk, pk = trust.generate_keypair(b"\x09" * 32)
        msg = b"payload"
        sig = trust.ed25519_sign(sk, msg)
        res["ed25519_verify"] = timeit(lambda: trust.ed25519_verify(pk, msg, sig), 50)
        eng = policy.PolicyEngine({"version": "b", "tenants": {"t": {"workload_classes": ["w"]}}})
        rq = policy.Request("t", "w", "dev", "r:1", None, scan_state=trust.ScanState.CLEAN)
        res["policy_eval"] = timeit(lambda: eng.evaluate(rq, time.time()), 5000)
        rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        end, ops = time.time() + a.soak_seconds, 0
        while time.time() < end:
            dd = s.put(os.urandom(4096))
            s.get(dd)
            ops += 1
        s.gc(grace_s=0)
        res["soak"] = {"seconds": a.soak_seconds, "ops": ops,
                       "maxrss_growth_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - rss0,
                       "fsck_ok": s.fsck()["ok"]}
    print(json.dumps(res, indent=2))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(res, fh, indent=2)


if __name__ == "__main__":
    main()
