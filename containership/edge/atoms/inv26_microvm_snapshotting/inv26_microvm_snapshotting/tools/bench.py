"""Reproducible benchmark + regression gate for the INV-26 restore/capture path
(C061-C067, C069, C070, C088 partial, X014 partial).

What it measures: the full service path (authn, authz, grant verification and
durable consumption, admission, metadata CAS, blob read, per-chunk
AES-256-GCM, DEK unwrap, framing, hypervisor load/resume, entropy injection)
with the **reference** hypervisor. The VMM's own restore cost is therefore
NOT included: these numbers bound INV-26's *overhead*, they are not the
end-to-end p99 restore SLO. ``certifiable`` is always false unless the
adapter is a real VMM — the gate refuses to let fixture or reference timings
satisfy performance acceptance.

Percentiles are computed from raw per-operation samples (nearest-rank).
Environment fingerprint (CPU model, cores, kernel, Python, crypto library)
is recorded with every run.

``python -m inv26_microvm_snapshotting.tools.bench --profile quick --out evidence/BENCH.json``
``python -m inv26_microvm_snapshotting.tools.bench --compare bench/baseline.json evidence/BENCH.json``
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import resource
import sys
import tempfile
import threading
import time
import tracemalloc
from pathlib import Path


def pct(samples: list[float], p: float) -> float:
    s = sorted(samples)
    if not s:
        return float("nan")
    k = max(0, min(len(s) - 1, math.ceil(p / 100 * len(s)) - 1))
    return round(s[k], 4)


def summary(samples: list[float]) -> dict:
    return {"n": len(samples), "p50": pct(samples, 50), "p95": pct(samples, 95), "p99": pct(samples, 99),
            "max": round(max(samples), 4) if samples else None,
            "mean": round(sum(samples) / len(samples), 4) if samples else None}


def env_fingerprint() -> dict:
    cpu = "unknown"
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    import cryptography
    return {"cpu": cpu, "cores": os.cpu_count(), "kernel": platform.release(), "python": platform.python_version(),
            "machine": platform.machine(), "cryptography": cryptography.__version__,
            "kvm_present": os.path.exists("/dev/kvm")}


def _rig(mem_mib: float):
    from ..tests.harness import Rig
    r = Rig(tempfile.mkdtemp(prefix="inv26-bench-"),
            cfg_over={"admission": {"max_inflight": 256, "per_tenant": 256, "max_queue": 512,
                                    "tenant_rate_per_s": 1e6, "tenant_burst": 1e6}})
    r.boot("vm-src", os.urandom(int(mem_mib * 1024 * 1024)))
    return r


def scenario_restore(mem_mib: float, n: int) -> dict:
    r = _rig(mem_mib)
    snap = r.capture(vm="vm-src")
    tok = r.token()
    lat, svc_ms, cpu = [], [], []
    for i in range(n):
        g = r.grant(snap, vm=f"b{i}")
        req = r.restore_req(snap, g, vm=f"b{i}")
        c0, t0 = time.process_time(), time.perf_counter()
        st, body = r.svc.handle("restore", tok, req)
        lat.append((time.perf_counter() - t0) * 1000)
        cpu.append((time.process_time() - c0) * 1000)
        if st != 200:
            raise RuntimeError(body)
        svc_ms.append(body["restore_ms"])
        r.hv.destroy(f"b{i}")
    return {"memory_mib": mem_mib, "request_ms": summary(lat), "restore_path_ms": summary(svc_ms),
            "cpu_ms": summary(cpu)}


def scenario_capture(mem_mib: float, n: int) -> dict:
    r = _rig(mem_mib)
    lat = []
    for i in range(n):
        vm = f"c{i}"
        r.hv.boot(vm, os.urandom(int(mem_mib * 1024 * 1024)))
        t0 = time.perf_counter()
        r.capture(sid=f"c{i}", vm=vm)
        lat.append((time.perf_counter() - t0) * 1000)
    return {"memory_mib": mem_mib, "request_ms": summary(lat)}


def scenario_load(concurrency: int, per_worker: int, tenants: int, mem_mib: float = 1) -> dict:
    """Steady/burst/overload: N workers, T tenants, all restores; records rejections separately."""
    from ..tests.harness import Rig
    r = Rig(tempfile.mkdtemp(prefix="inv26-load-"),
            cfg_over={"admission": {"max_inflight": 16, "per_tenant": 8, "max_queue": 32,
                                    "tenant_rate_per_s": 1e6, "tenant_burst": 1e6}})
    snaps = []
    for t in range(tenants):
        r.boot(f"src-{t}", os.urandom(int(mem_mib * 1024 * 1024)))
        snaps.append(r.capture(sid=f"s{t}", tenant=f"t{t}", vm=f"src-{t}"))
    toks = [r.token(tenant=f"t{t}") for t in range(tenants)]
    lat: list[float] = []
    rejected = {"SNAP_OVERLOADED": 0}
    other: dict[str, int] = {}
    lock = threading.Lock()

    def worker(w):
        for i in range(per_worker):
            t = (w + i) % tenants
            vm = f"w{w}-{i}"
            g = r.grant(snaps[t], vm=vm)
            t0 = time.perf_counter()
            st, body = r.svc.handle("restore", toks[t], r.restore_req(snaps[t], g, vm=vm))
            ms = (time.perf_counter() - t0) * 1000
            with lock:
                if st == 200:
                    lat.append(ms)
                elif body["code"] in rejected:
                    rejected[body["code"]] += 1
                else:
                    other[body["code"]] = other.get(body["code"], 0) + 1
            r.hv.destroy(vm)
    t0 = time.perf_counter()
    ts = [threading.Thread(target=worker, args=(w,)) for w in range(concurrency)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    wall = time.perf_counter() - t0
    return {"concurrency": concurrency, "tenants": tenants, "ok": len(lat), "rejected": rejected,
            "unexpected_errors": other, "throughput_per_s": round(len(lat) / wall, 1), "latency_ms": summary(lat),
            "admission_rejected_total": r.metrics.total("inv26_admission_rejected_total")}


def scenario_overhead_breakdown(mem_mib: float = 16) -> dict:
    """C064/C065: where the time and copies go for one restore of mem_mib."""
    from .. import crypto
    from ..service import frame, unframe
    r = _rig(mem_mib)
    snap = r.capture(vm="vm-src")
    v = r.meta.get("snap/s1")[1]
    ctx = r.svc._ctx(v)
    env = v["manifest"]["envelope"]
    out = {}
    t0 = time.perf_counter(); blob = r.blobs.get("t1", "s1", 1); out["storage_read_ms"] = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter(); plain = crypto.open_envelope(blob, env=env, ctx=ctx, kms=r.kms)
    out["aead_decrypt_ms"] = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter(); unframe(plain); out["unframe_ms"] = (time.perf_counter() - t0) * 1000
    tracemalloc.start()
    r.restore(snap, vm="vm-x")
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    size = len(plain)
    out = {k: round(v, 3) for k, v in out.items()}
    out.update({"memory_mib": mem_mib, "image_bytes": size, "peak_python_alloc_bytes": peak,
                "peak_alloc_over_image": round(peak / size, 2),
                "copies_identified": [
                    "blob read into memory (1x ciphertext)",
                    "AEAD output as a list of chunks, then one join (2x plaintext transiently)",
                    "unframe slices state/memory (1x plaintext)",
                    "adapter writes memory file for VMM load (1x plaintext on tmpfs)"],
                "optimization_candidates": [
                    "stream-decrypt chunks directly into the VMM memory file after full-tag pre-verification pass",
                    "memoryview slicing in unframe to avoid a copy (decrypt side already uses memoryview)",
                    "UFFD memory backend (Firecracker) to page in lazily from a decrypted cache"]})
    return out


PROFILES = {
    "quick": {"restore": [(1, 60), (16, 20)], "capture": [(1, 15)], "load": [(4, 15, 2), (16, 15, 4)]},
    "full": {"restore": [(1, 400), (16, 120), (64, 40)], "capture": [(1, 60), (16, 20)],
             "load": [(4, 100, 2), (16, 100, 8), (64, 40, 8)]},
}


def run(profile: str) -> dict:
    p = PROFILES[profile]
    t0 = time.time()
    res = {"schema": "PK_SNAPSHOT_BENCH/1", "profile": profile, "adapter": "reference", "certifiable": False,
           "certifiable_reason": "reference hypervisor: VMM restore cost excluded; not an SLO measurement",
           "environment": env_fingerprint(),
           "restore": [scenario_restore(m, n) for m, n in p["restore"]],
           "capture": [scenario_capture(m, n) for m, n in p["capture"]],
           "load": [scenario_load(c, n, t) for c, n, t in p["load"]],
           "breakdown": scenario_overhead_breakdown(16),
           "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    res["seconds"] = round(time.time() - t0, 2)
    return res


def compare(baseline: dict, current: dict) -> dict:
    """C070 regression gate: fail when overhead p99 regresses beyond the budget."""
    checks = []
    budget = baseline.get("regression_budget", {"p99_ratio": 1.5, "abs_slack_ms": 1.0})
    base = {r["memory_mib"]: r for r in baseline["restore"]}
    for r in current["restore"]:
        b = base.get(r["memory_mib"])
        if not b:
            continue
        limit = b["restore_path_ms"]["p99"] * budget["p99_ratio"] + budget["abs_slack_ms"]
        checks.append({"metric": f"restore_path_ms.p99@{r['memory_mib']}MiB", "baseline": b["restore_path_ms"]["p99"],
                       "current": r["restore_path_ms"]["p99"], "limit": round(limit, 4),
                       "pass": r["restore_path_ms"]["p99"] <= limit})
    for r in current["load"]:
        if r["unexpected_errors"]:
            checks.append({"metric": f"load c={r['concurrency']} unexpected errors", "pass": False,
                           "current": r["unexpected_errors"]})
    return {"schema": "PK_SNAPSHOT_PERF_GATE/1", "checks": checks, "result": "PASS" if all(c["pass"] for c in checks)
            else "FAIL", "certifiable": current.get("certifiable", False),
            "note": "PASS here guards INV-26 overhead only; the p99 restore SLO needs a real-VMM run (X014)."}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="quick", choices=sorted(PROFILES))
    ap.add_argument("--out")
    ap.add_argument("--compare", nargs=2, metavar=("BASELINE", "CURRENT"))
    a = ap.parse_args(argv)
    if a.compare:
        res = compare(json.loads(Path(a.compare[0]).read_text()), json.loads(Path(a.compare[1]).read_text()))
    else:
        res = run(a.profile)
    txt = json.dumps(res, indent=1, sort_keys=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt + "\n")
    print(txt if a.compare else json.dumps({"restore": [(r["memory_mib"], r["restore_path_ms"]) for r in res["restore"]],
                                            "seconds": res["seconds"]}))
    return 0 if res.get("result", "PASS") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
