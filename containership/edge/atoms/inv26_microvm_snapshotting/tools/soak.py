"""Soak: sustained capture+restore+delete churn with memory-growth and error accounting (C067, C088 partial).

Certification needs >= 1 h on a real VMM (X014); the release evidence here is a short soak on the reference
VMM and is labelled as such.
"""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
import tracemalloc
from pathlib import Path


def run(seconds: float) -> dict:
    from ..telemetry import StructuredLogger
    from ..tests.harness import Rig
    sim = [time.time()]  # simulated wall clock: +120 s per cycle so expiry/GC paths are exercised
    r = Rig(cfg_over={"admission": {"tenant_rate_per_s": 1e6, "tenant_burst": 1e6}}, clock=lambda: sim[0])
    r.logger = StructuredLogger(stream=open("/dev/null", "w"))
    r.svc = r.build()
    tracemalloc.start()
    t_end = time.time() + seconds
    samples, ops, errors, i = [], 0, {}, 0
    t0 = time.time()
    while time.time() < t_end:
        i += 1
        sim[0] += 120
        r.boot(f"src{i}", b"x" * 65536)
        st, snap = r.svc.handle("capture", r.token(), r.capture_req(f"s{i}", vm=f"src{i}"))
        ops += 1
        if st != 200:
            errors[snap["code"]] = errors.get(snap["code"], 0) + 1
            continue
        for j in range(3):
            st, b = r.restore(snap, vm=f"d{i}-{j}")
            ops += 1
            if st != 200:
                errors[b["code"]] = errors.get(b["code"], 0) + 1
            r.hv.destroy(f"d{i}-{j}")
        r.hv.destroy(f"src{i}")
        st, b = r.svc.handle("delete", r.admin_token(), {"snapshot_id": f"s{i}"})
        ops += 1
        if st != 200:
            errors["delete:" + b["code"]] = errors.get("delete:" + b["code"], 0) + 1
        if i % 25 == 0:
            r.svc.gc(tombstone_retention_s=600, idempotency_ttl_s=600)
            cur, _ = tracemalloc.get_traced_memory()
            samples.append({"t_s": round(time.time() - t0, 1), "python_bytes": cur, "ops": ops,
                            "rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    tracemalloc.stop()
    # steady state = after the bounded caches (2 000 decision records, 500 log lines) are full
    warm = [x for x in samples if x.get("ops", 0) > 3000] or samples
    first, last = (warm[0]["python_bytes"], warm[-1]["python_bytes"]) if len(warm) > 1 else (0, 0)
    growth = (last - first) / max(first, 1)
    return {"schema": "PK_SNAPSHOT_SOAK/1", "seconds": round(time.time() - t0, 1), "operations": ops,
            "errors": errors, "memory_samples": samples[:: max(1, len(samples) // 20)],
            "python_heap_growth_ratio": round(growth, 3),
            "audit_records": r.audit.verify(), "metastore_seq": r.meta.seq,
            "metastore_live_records": len(r.meta.scan("")),
            "certifiable": False, "note": "reference VMM, short duration; >=1 h real-VMM soak required for C088",
            "result": "PASS" if not errors and growth < 0.25 else "FAIL"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run(a.seconds)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("result", "seconds", "operations", "errors", "python_heap_growth_ratio")}))
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
