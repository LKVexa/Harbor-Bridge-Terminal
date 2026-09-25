"""Reproducible baseline of the tier's *control-plane overhead* (INV-40-C061..C064, C088).

Measures the FullVmService request path over FakeProvider (hypervisor time
excluded by construction) - latency percentiles per operation, sustained and
burst throughput, overload shedding, and journal/audit bytes per guest.  It is
NOT a hardware benchmark: boot time and guest density on real KVM hosts are
blocked on hardware (blocker HW-KVM) and are never inferred from these numbers.
"""
from __future__ import annotations

import json
import os
import pathlib
import platform
import secrets
import statistics
import sys
import tempfile
import threading
import time
import tracemalloc

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG / "tests"))
from _support import keys, req, tok  # noqa: E402
from fvt import errors  # noqa: E402
from fvt.provider import FakeProvider  # noqa: E402
from fvt.service import FullVmService  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p / 100 * len(xs)))], 3)


def run(n=300) -> dict:
    kp = keys()
    d = tempfile.mkdtemp()
    tracemalloc.start()
    svc = FullVmService(provider=FakeProvider(), keys=kp, state_dir=d, sleep=lambda s: None,
                        config={"tenant_guest_quota": 100000, "tenant_memory_quota_mib": 1 << 30,
                                "max_concurrent_ops": 64, "max_queue": 64})
    lat = {"create": [], "boot": [], "stop": [], "destroy": []}
    t_all = time.perf_counter()
    for i in range(n):
        t0 = time.perf_counter()
        iid = svc.create(tok(kp), req(name=f"g{i}", mem=256))["instance_id"]
        lat["create"].append((time.perf_counter() - t0) * 1000)
        for op in ("boot", "stop", "destroy"):
            t0 = time.perf_counter()
            getattr(svc, op)(tok(kp), iid)
            lat[op].append((time.perf_counter() - t0) * 1000)
    steady_s = time.perf_counter() - t_all
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    # burst: 64 threads x 4 creates against max_concurrent_ops=4, max_queue=8
    burst_dir = tempfile.mkdtemp()
    b = FullVmService(provider=FakeProvider(), keys=kp, state_dir=burst_dir, sleep=lambda s: None,
                      config={"max_concurrent_ops": 4, "max_queue": 8, "tenant_guest_quota": 100000,
                              "tenant_memory_quota_mib": 1 << 30, "op_timeout_ms": 200})
    b.provider.delay_s = 0.02
    ids = [b.create(tok(kp), req(name=f"b{i}", mem=256))["instance_id"] for i in range(256)]
    outcome = {"ok": 0}

    def boot(iid):
        try:
            b.boot(tok(kp), iid)
            outcome["ok"] += 1
        except errors.OpError as e:
            outcome[e.code] = outcome.get(e.code, 0) + 1
    th = [threading.Thread(target=boot, args=(i,)) for i in ids]
    t0 = time.perf_counter()
    [x.start() for x in th]
    [x.join() for x in th]
    burst_s = time.perf_counter() - t0
    wal = os.path.getsize(pathlib.Path(d) / "journal.wal")
    aud = os.path.getsize(pathlib.Path(d) / "audit.jsonl")
    return {"schema": "PK_FULL_VM_BENCH/1", "scope": "control-plane overhead over FakeProvider; not hardware",
            "host": {"python": platform.python_version(), "machine": platform.machine(), "cpus": os.cpu_count()},
            "guests": n,
            "latency_ms": {op: {"p50": pct(v, 50), "p95": pct(v, 95), "p99": pct(v, 99), "max": round(max(v), 3),
                                "mean": round(statistics.mean(v), 3)} for op, v in lat.items()},
            "steady_lifecycles_per_s": round(n / steady_s, 1),
            "burst": {"requests": len(ids), "seconds": round(burst_s, 3), "outcomes": outcome,
                      "shed_counter": b.admission.shed},
            "tracemalloc_peak_kib": peak // 1024,
            "journal_bytes_per_lifecycle": round(wal / n, 1), "audit_bytes_per_lifecycle": round(aud / n, 1),
            "p99_create_ms": pct(lat["create"], 99), "p99_boot_ms": pct(lat["boot"], 99)}


if __name__ == "__main__":
    print(json.dumps(run(int(sys.argv[1]) if len(sys.argv) > 1 else 300), indent=1))
