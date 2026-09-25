"""Reproducible benchmark harness (C061-C064, C066, C069, C088).

    python benchmarks/bench.py [--size-mib 64] [--quick] [--out FILE]

Measures, on the current host only: startup, manifest throughput, receive
throughput and per-chunk latency percentiles for the legacy copy receiver, the
durable checkpoint path and the shared-memory zero-copy path; copy counts from
CopyCounter *and* independently from tracemalloc peak allocation; steady,
burst, overload, recovery and scale-out load profiles against FairAdmission;
per-tenant service overhead; CPU time and peak RSS.  Power/thermal is not
measurable here and is reported as ``not_measured``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import statistics
import sys
import tempfile
import threading
import time
import tracemalloc
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
t_import = time.perf_counter()
pkg = __import__(HERE.name)
IMPORT_S = time.perf_counter() - t_import
from importlib import import_module  # noqa: E402

shm = import_module(HERE.name + ".shm_transport")
tel = import_module(HERE.name + ".telemetry")
quota = import_module(HERE.name + ".quota")


def pct(vals):
    s = sorted(vals)
    q = lambda p: s[min(len(s) - 1, int(round(p * (len(s) - 1))))]  # noqa: E731
    return {"p50": q(.5), "p95": q(.95), "p99": q(.99), "max": s[-1], "n": len(s)}


def legacy_receive(data, m):
    tracemalloc.start()
    r = pkg.Receiver(m)
    lat = []
    t0 = time.perf_counter()
    c = m["chunk"]
    for i in range(m["chunk_count"]):
        s = time.perf_counter()
        r.accept(i, memoryview(data)[i * c:(i + 1) * c])
        lat.append(time.perf_counter() - s)
    out = r.assemble()
    dt = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert hashlib.sha256(out).digest() == hashlib.sha256(data).digest()
    return {"seconds": dt, "mib_s": len(data) / dt / 2**20, "chunk_latency_s": pct(lat), "peak_alloc_bytes": peak,
            "copies_per_object": 2, "peak_alloc_over_size": round(peak / len(data), 3)}


def shm_receive(data, m):
    key = os.urandom(32)
    region = shm.SharedRegion(len(data), transfer_id="bench", tenant="b", key=key)
    counter = shm.CopyCounter()
    shm.produce_into(region.buf, data, counter)
    tracemalloc.start()
    rx = shm.ZeroCopyReceiver(m, region.buf, counter=counter)
    lat = []
    t0 = time.perf_counter()
    for i in range(m["chunk_count"]):
        s = time.perf_counter()
        rx.commit(i)
        lat.append(time.perf_counter() - s)
    v = rx.object_view()
    dt = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    ok = hashlib.sha256(v).digest() == hashlib.sha256(data).digest()
    v.release()
    del rx
    region.close()
    assert ok
    return {"seconds": dt, "mib_s": len(data) / dt / 2**20, "chunk_latency_s": pct(lat), "peak_alloc_bytes": peak,
            "peak_alloc_over_size": round(peak / len(data), 4), **counter.as_dict()}


def durable_receive(data, m, fsync):
    ck = import_module(HERE.name + ".checkpoint")
    with tempfile.TemporaryDirectory() as d:
        s = ck.CheckpointStore(d, seal_key=os.urandom(32), fsync=fsync)
        lease = s.acquire("bench", "n")
        s.create(lease, m, tenant="b")
        c = m["chunk"]
        lat, ver = [], set()
        t0 = time.perf_counter()
        for i in range(m["chunk_count"]):
            st = time.perf_counter()
            view = memoryview(data)[i * c:(i + 1) * c]
            hashlib.sha256(view).hexdigest()
            ver.add(i)
            s.write_chunk(lease, i, i * c, view, ver, "receiving")
            lat.append(time.perf_counter() - st)
        t1 = time.perf_counter()
        st = s.load("bench")
        recovery = time.perf_counter() - t1
        dt = t1 - t0
        assert len(st["verified"]) == m["chunk_count"]
    return {"fsync": fsync, "seconds": dt, "mib_s": len(data) / dt / 2**20, "chunk_latency_s": pct(lat),
            "restart_recovery_s": recovery}


def load_profiles():
    out = {}
    a = quota.FairAdmission(max_active=8, max_bytes=1 << 40, max_pending=64, default=quota.TenantQuota(1, 8, 1 << 40))
    lat = []
    for _ in range(5000):  # steady
        s = time.perf_counter(); g = a.acquire("t", 1); a.release(g); lat.append(time.perf_counter() - s)
    out["steady_admission_latency_s"] = pct(lat)
    rejected = {"n": 0}
    lock = threading.Lock()

    def burst_worker():
        try:
            g = a.acquire("t", 1, timeout=0.0)
            time.sleep(0.01)
            a.release(g)
        except pkg.BulkDataPlaneError:
            with lock:
                rejected["n"] += 1

    ths = [threading.Thread(target=burst_worker) for _ in range(64)]
    t0 = time.perf_counter()
    for t in ths: t.start()
    for t in ths: t.join()
    out["burst"] = {"offered": 64, "capacity": 8, "rejected": rejected["n"], "seconds": time.perf_counter() - t0}
    out["overload_rejection_ratio"] = round(rejected["n"] / 64, 3)
    out["recovery"] = {"active_after_burst": a.metrics()["active"], "recovered": a.metrics()["active"] == 0}
    scale = {}
    for n in (1, 2, 4, 8):
        a2 = quota.FairAdmission(max_active=n, max_bytes=1 << 40, max_pending=10_000, default=quota.TenantQuota(1, n, 1 << 40))
        done = {"n": 0}
        data = os.urandom(1 << 20)

        def w():
            for _ in range(8):
                g = a2.acquire("t", 1, timeout=10)
                hashlib.sha256(data).digest()
                a2.release(g)
                with lock:
                    done["n"] += 1

        ts = [threading.Thread(target=w) for _ in range(n)]
        t0 = time.perf_counter()
        for t in ts: t.start()
        for t in ts: t.join()
        scale[str(n)] = round(done["n"] * 1.0 / (time.perf_counter() - t0), 2)
    out["scale_out_mib_hashed_per_s"] = scale
    return out


def service_overhead(data, m):
    sup = import_module(HERE.name + ".config")
    sec = import_module(HERE.name + ".security")
    with tempfile.TemporaryDirectory() as d:
        kf = Path(d) / "k.json"
        kf.write_text(json.dumps({"keys": {"k": os.urandom(32).hex()}, "active": "k"})); os.chmod(kf, 0o600)
        layer = sup.load_layer({"profile": "test", "security": {"key_file": str(kf)}, "checkpoint": {"enabled": False},
                                "limits": {"host_memory_budget": "64GiB"}}, layer="t")
        t0 = time.perf_counter()
        mgr = sup.ConfigManager(probe=shm.probe())
        cfg = mgr.build([("t", layer)], author="bench"); mgr.activate(cfg)
        ring = sec.KeyRing.from_file(kf)
        dp = pkg.BulkDataPlane(cfg, keyring=ring, caps=mgr.probe)
        startup = time.perf_counter() - t0
        per = {}
        for tenant in ("a", "b"):
            tok = sec.mint(ring, sub=tenant, tenant=tenant, actions=["create-transfer", "write-chunk", "finalize"])
            dp.create_transfer(tok, m, transfer_id=f"s{tenant}", transport="copy")
            c = m["chunk"]
            lat = []
            for i in range(m["chunk_count"]):
                s = time.perf_counter()
                dp.accept_chunk(tok, f"s{tenant}", i, memoryview(data)[i * c:(i + 1) * c])
                lat.append(time.perf_counter() - s)
            dp.finalize(tok, f"s{tenant}")
            per[tenant] = pct(lat)
    return {"startup_s": startup, "per_tenant_chunk_latency_s": per}


def repeated(fn, n, *a):
    """Run ``fn`` n times; report per-field medians so single noisy runs on
    shared hosts do not trip the regression gate (p99 on one run is noisy)."""
    runs = [fn(*a) for _ in range(n)]
    out = dict(runs[0])
    for k in ("seconds", "mib_s", "peak_alloc_bytes", "peak_alloc_over_size", "restart_recovery_s"):
        if k in out:
            out[k] = statistics.median(r[k] for r in runs)
    out["chunk_latency_s"] = {q: statistics.median(r["chunk_latency_s"][q] for r in runs) for q in runs[0]["chunk_latency_s"]}
    out["repeats"] = n
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--size-mib", type=int, default=64)
    ap.add_argument("--chunk-kib", type=int, default=1024)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    size = (8 if a.quick else a.size_mib) << 20
    data = os.urandom(size)
    t0 = time.perf_counter()
    m = pkg.manifest(data, a.chunk_kib << 10)
    manifest_s = time.perf_counter() - t0
    small = data[: 8 << 20]
    ms = pkg.manifest(small, 64 << 10)
    res = {
        "schema": "INV37_BENCH/1",
        "lineage": tel.release_lineage(),
        "host": {"platform": platform.platform(), "machine": platform.machine(), "cpus": os.cpu_count(),
                 "python": sys.version.split()[0]},
        "params": {"object_bytes": size, "chunk_bytes": a.chunk_kib << 10, "repeat": a.repeat},
        "import_s": IMPORT_S,
        "manifest_mib_s": size / manifest_s / 2**20,
        "legacy_copy_receiver": repeated(legacy_receive, a.repeat, data, m),
        "shm_zero_copy_receiver": repeated(shm_receive, a.repeat, data, m) if shm.probe()["shared_memory"] else {"status": "unsupported"},
        "durable_checkpoint_fsync": repeated(durable_receive, a.repeat, small, ms, True),
        "durable_checkpoint_nofsync": repeated(durable_receive, a.repeat, small, ms, False),
        "load_profiles": load_profiles(),
        "service": service_overhead(small, ms),
        "power_thermal": {"status": "not_measured", "reason": "no RAPL/thermal sensors accessible in this environment"},
    }
    ru = resource.getrusage(resource.RUSAGE_SELF)
    res["cpu_user_s"], res["cpu_sys_s"], res["peak_rss_kib"] = ru.ru_utime, ru.ru_stime, ru.ru_maxrss
    text = json.dumps(res, indent=1, sort_keys=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
