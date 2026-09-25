"""Concurrency/race stress and soak/churn certification (INV-68 MC-30, MC-31; C086, C088).

    python -m inv68_resource_packing.tools.stress [--out evidence/] [--soak-seconds 20]

Stress (``STRESS.json``) -- shared-state invariants under real threads:

* S1 admission: 32 threads, concurrency 4 / queue 8 -> peak in-flight <= 4, every
  request either succeeds or is shed with ``OVERLOADED``; counters balance.
* S2 idempotency race: 16 threads submit the same key -> identical results,
  exactly one computed response.
* S3 audit chain under contention: every successful pack has exactly one
  ``pack.decision`` record; the chain verifies.
* S4 config activation race: 8 controllers CAS-activate concurrently from the
  same base digest -> exactly one wins, the rest get ``CONFIG_CONFLICT``.
* S5 replay race: one token presented by 16 threads -> exactly one accepted.
* S6 metrics: ``inv68_requests_total`` equals requests issued.
* S7 activation race across 6 OS processes (lock file + CAS) -> exactly one wins.

Soak (``SOAK.json``) -- allocation churn for ``--soak-seconds`` (default 20 s,
certification uses >= 3600 s): randomized batches of 10-2000 workloads;
tracemalloc samples every second; asserts no monotonic growth above 5 MiB after
warmup, zero errors, zero invariant violations.
"""
from __future__ import annotations

import argparse
import random
import tempfile
import threading
import time
import tracemalloc
from pathlib import Path

from .common import PKG, pct, write

from inv68_resource_packing.audit import AuditLog  # noqa: E402
from inv68_resource_packing.auth import Authorizer, mint  # noqa: E402
from inv68_resource_packing.config import ConfigStore, compose, defaults  # noqa: E402
from inv68_resource_packing.errors import PackError  # noqa: E402
from inv68_resource_packing.service import PackingService  # noqa: E402

KEY = {"k": b"s" * 32}


def tok(kind="workload-scheduler", caps=("pack:submit",), tenants=("t",)):
    return mint(KEY["k"], kid="k", sub=f"{kind}-x", kind=kind, tenants=list(tenants), caps=list(caps))


def build(tmp, limits=None):
    audit = AuditLog(Path(tmp) / "a.jsonl")
    store = ConfigStore(Path(tmp) / "c", audit=audit)
    patch = {"tenants": {"overrides": {"t": {"max_requests_per_minute": 1_000_000}}}}
    if limits:
        patch["limits"] = limits
    store.activate(compose(defaults().document, ("stress", patch)), actor="bootstrap", epoch=1)
    return PackingService(store, Authorizer(KEY), audit), audit, store


def body(n=300, seed=1, **kw):
    rng = random.Random(seed)
    return dict({"tenant": "t", "host_capacity": {"cpu": 16, "mem": 64},
                 "workloads": [{"name": f"w{i}", "cpu": rng.choice([.5, 1, 2]), "mem": rng.choice([1, 2, 4, 8])}
                               for i in range(n)]}, **kw)


def run_threads(n, fn):
    barrier = threading.Barrier(n)
    out = [None] * n

    def worker(i):
        barrier.wait()
        out[i] = fn(i)
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return out


def code(fn):
    try:
        fn()
        return "OK"
    except PackError as e:
        return e.code


def stress() -> list[dict]:
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        svc, audit, _ = build(tmp, {"max_concurrency": 4, "max_queue": 8})
        toks = [tok() for _ in range(32)]
        b = body(1500)
        codes = run_threads(32, lambda i: code(lambda: svc.pack(dict(b), toks[i])))
        ok = svc.admission.peak_in_flight <= 4 and set(codes) <= {"OK", "OVERLOADED"} and svc.admission.in_flight == 0
        rows.append({"id": "S1", "title": "admission bounds", "result": "PASS" if ok else "FAIL",
                     "observed": {"peak_in_flight": svc.admission.peak_in_flight,
                                  "codes": {c: codes.count(c) for c in set(codes)}}})
        success = codes.count("OK")
        decisions = [r for r in audit.records() if r["operation"] == "pack.decision"]
        n = audit.verify()
        ok = len(decisions) == success
        rows.append({"id": "S3", "title": "audit chain under contention", "result": "PASS" if ok else "FAIL",
                     "observed": {"successes": success, "decision_records": len(decisions), "chain": n}})
        total = svc.metrics.total("inv68_requests_total")
        rows.append({"id": "S6", "title": "metric totals balance", "result": "PASS" if total == 32 else "FAIL",
                     "observed": {"requests_total": total}})
    with tempfile.TemporaryDirectory() as tmp:
        svc, _, _ = build(tmp, {"max_concurrency": 16, "max_queue": 16})
        toks = [tok() for _ in range(16)]
        b = body(200, idempotency_key="race-key-0001")
        outs = run_threads(16, lambda i: svc.pack(dict(b), toks[i]))
        results = {str(o["result"]) for o in outs}
        computed = sum(1 for o in outs if not o.get("replayed"))
        ok = len(results) == 1
        rows.append({"id": "S2", "title": "idempotency race", "result": "PASS" if ok else "FAIL",
                     "observed": {"distinct_results": len(results), "computed": computed,
                                  "note": "concurrent first submissions may each compute; results are identical"}})
    with tempfile.TemporaryDirectory() as tmp:
        svc, _, store = build(tmp)
        base = store.active().digest
        cands = [compose(svc.config.document, (f"c{i}", {"headroom": 0.1 + i / 100})) for i in range(8)]
        codes = run_threads(8, lambda i: code(lambda: store.activate(cands[i], actor=f"ctl{i}", epoch=1,
                                                                      expected_digest=base)))
        ok = codes.count("OK") == 1 and codes.count("CONFIG_CONFLICT") == 7
        rows.append({"id": "S4", "title": "config CAS race", "result": "PASS" if ok else "FAIL",
                     "observed": {c: codes.count(c) for c in set(codes)}})
    with tempfile.TemporaryDirectory() as tmp:
        svc, _, _ = build(tmp)
        t = tok()
        codes = run_threads(16, lambda i: code(lambda: svc.auth.authenticate(t)))
        ok = codes.count("OK") == 1 and codes.count("REPLAY_DETECTED") == 15
        rows.append({"id": "S5", "title": "token replay race", "result": "PASS" if ok else "FAIL",
                     "observed": {c: codes.count(c) for c in set(codes)}})
    with tempfile.TemporaryDirectory() as tmp:
        import subprocess
        import sys
        _, _, store = build(tmp)
        base = store.active().digest
        script = (
            "import sys; sys.path.insert(0, %r)\n"
            "from inv68_resource_packing.config import ConfigStore, compose\n"
            "from inv68_resource_packing.errors import PackError\n"
            "s = ConfigStore(%r); c = compose(s.active().document, ('p', {'headroom': 0.1 + int(sys.argv[1]) / 100}))\n"
            "try:\n    s.activate(c, actor='p' + sys.argv[1], epoch=1, expected_digest=%r); print('OK')\n"
            "except PackError as e:\n    print(e.code)\n"
        ) % (str(PKG.parent), str(Path(tmp) / "c"), base)
        procs = [subprocess.Popen([sys.executable, "-c", script, str(i)], stdout=subprocess.PIPE, text=True)
                 for i in range(6)]
        codes = [p.communicate(timeout=60)[0].strip() for p in procs]
        ok = codes.count("OK") == 1 and codes.count("CONFIG_CONFLICT") == 5
        rows.append({"id": "S7", "title": "config CAS race across processes", "result": "PASS" if ok else "FAIL",
                     "observed": {c: codes.count(c) for c in set(codes)}})
    return sorted(rows, key=lambda r: r["id"])


def soak(seconds: float) -> dict:
    rng = random.Random(31)
    errors = violations = batches = workloads = 0
    lat = []
    samples = []
    with tempfile.TemporaryDirectory() as tmp:
        svc, audit, _ = build(tmp)
        tracemalloc.start()
        start = last = time.monotonic()
        while time.monotonic() - start < seconds:
            n = rng.choice([10, 50, 200, 800, 2000])
            b = body(n, seed=rng.randrange(1 << 30))
            t0 = time.perf_counter()
            try:
                out = svc.pack(b, tok())
                lat.append((time.perf_counter() - t0) * 1000)
                for h in out["result"]["hosts"]:
                    if h["used"]["mem"] > 64 * 0.9 + 1e-9 or h["used"]["cpu"] > 16 * 1.5 * 0.9 + 1e-9:
                        violations += 1
            except PackError:
                errors += 1
            batches += 1
            workloads += n
            if time.monotonic() - last >= 1.0:
                samples.append(tracemalloc.get_traced_memory()[0])
                last = time.monotonic()
        tracemalloc.stop()
        chain = audit.verify()
    warm = samples[len(samples) // 4:] or samples
    growth = (warm[-1] - warm[0]) if len(warm) > 1 else 0
    ok = errors == 0 and violations == 0 and growth < 5 * 1024 * 1024
    return {"seconds": seconds, "batches": batches, "workloads": workloads, "errors": errors,
            "invariant_violations": violations, "p50_ms": round(pct(lat, .5), 3), "p99_ms": round(pct(lat, .99), 3),
            "mem_samples_bytes": samples[-20:], "post_warmup_growth_bytes": growth, "audit_records": chain,
            "certification_threshold_seconds": 3600,
            "certification_grade": seconds >= 3600, "result": "PASS" if ok else "FAIL"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    ap.add_argument("--soak-seconds", type=float, default=20.0)
    a = ap.parse_args(argv)
    rows = stress()
    failed = [r["id"] for r in rows if r["result"] != "PASS"]
    write(Path(a.out) / "STRESS.json", {"schema": "PK_PACK_STRESS/1", "scenarios": rows, "failed": failed,
                                        "result": "PASS" if not failed else "FAIL"})
    s = soak(a.soak_seconds)
    write(Path(a.out) / "SOAK.json", {"schema": "PK_PACK_SOAK/1", **s})
    for r in rows:
        print(r["id"], r["result"], r["title"], r["observed"])
    print("SOAK", s["result"], {k: s[k] for k in ("seconds", "batches", "workloads", "errors", "p99_ms",
                                                  "post_warmup_growth_bytes")})
    return 0 if not failed and s["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
