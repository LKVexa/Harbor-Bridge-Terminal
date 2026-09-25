"""MC-29 / MC-35 - Performance baseline, regression thresholds, and soak harness.

    python -m pln02_application_plane.tools.bench --out evidence/perf.json
    python -m pln02_application_plane.tools.bench --soak 600 --out evidence/soak.json

Profiles: resolve at 10/50/200 components (200 = contract ceiling), full
service submit path (auth + admission + signed catalogue + policy + resolve +
durable publish + audit), burst admission, and optional soak with a leak
check (tracemalloc growth across windows). Exits non-zero when a threshold in
``perf/THRESHOLDS.json`` is breached. Results are *host-specific*; the
evidence file records the host so baselines are compared like-for-like.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from pln02_application_plane.resolver import resolve  # noqa: E402


def chain(n: int):
    comps, edges = [], []
    for i in range(n):
        c = {"name": f"c{i}", "requires": {"state": True, f"opt{i % 7}": False}, "exports": {f"i{i}": "1.0"}, "imports": {}}
        if i:
            c["imports"] = {f"i{i-1}": "1.0"}
            edges.append([f"c{i-1}", f"c{i}", f"i{i-1}"])
        comps.append(c)
    return comps, edges


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def time_many(fn, n):
    out = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        out.append(time.perf_counter() - t)
    return out


def bench_resolve(iters):
    res = {}
    for n in (10, 50, 200):
        comps, edges = chain(n)
        xs = time_many(lambda: resolve(comps, edges, {"state": "p"}), iters)
        res[f"resolve_{n}"] = {"n": iters, "p50_ms": pct(xs, 50) * 1e3, "p95_ms": pct(xs, 95) * 1e3,
                               "p99_ms": pct(xs, 99) * 1e3, "max_ms": max(xs) * 1e3,
                               "throughput_per_s": iters / sum(xs)}
    return res


def service_env(tmp):
    sys.path.insert(0, str(PKG / "tests"))
    from helpers import CONFIG, catalogue_doc, ring, token
    from pln02_application_plane.audit import AuditLedger
    from pln02_application_plane.catalogue import CatalogueClient
    from pln02_application_plane.service import ApplicationPlaneService
    from pln02_application_plane.store import RevisionStore
    r = ring()
    doc = catalogue_doc(r)
    cfg = json.loads(json.dumps(CONFIG))
    cfg["admission"] = {"tenant_rate_per_second": 10_000, "tenant_burst": 100_000}
    cfg["entitlements"] = {"acme": ["state"] + [f"opt{i}" for i in range(7)]}
    svc = ApplicationPlaneService(ring=r, catalogue=CatalogueClient(lambda: doc, r, environment="prod", site="eu-1"),
                                  store=RevisionStore(f"{tmp}/s"), audit=AuditLedger(f"{tmp}/a.jsonl", r, "aud-1"), config=cfg)
    return svc, token(r)


def bench_service(iters):
    from pln02_application_plane.context import RequestContext
    with tempfile.TemporaryDirectory() as tmp:
        svc, tok = service_env(tmp)
        xs = []
        for i in range(iters):
            comps, edges = chain(20)
            comps[0]["exports"]["i0"] = f"1.{i}"
            comps[1]["imports"]["i0"] = f"1.{i}"
            body = json.dumps({"schema": "PK_APPLICATION/1", "components": comps, "edges": edges}).encode()
            t = time.perf_counter()
            out = svc.submit(RequestContext.create("acme", "prod", "eu-1"), tok, "bench", body)
            xs.append(time.perf_counter() - t)
            if not out["ok"]:
                raise SystemExit(f"service bench failed: {out['error']}")
        return {"service_submit_20": {"n": iters, "p50_ms": pct(xs, 50) * 1e3, "p95_ms": pct(xs, 95) * 1e3,
                                      "p99_ms": pct(xs, 99) * 1e3, "max_ms": max(xs) * 1e3,
                                      "throughput_per_s": iters / sum(xs)}}


def bench_burst():
    from pln02_application_plane.admission import AdmissionController, AdmissionPolicy
    a = AdmissionController(AdmissionPolicy(tenant_rate_per_second=100, tenant_burst=50))
    rejected = 0
    t = time.perf_counter()
    for _ in range(10_000):
        try:
            with a.admit("t"):
                pass
        except Exception:
            rejected += 1
    return {"burst_admission": {"offered": 10_000, "admitted": 10_000 - rejected, "rejected": rejected,
                                "decision_us": (time.perf_counter() - t) / 10_000 * 1e6}}


def soak(seconds):
    comps, edges = chain(50)
    tracemalloc.start()
    windows, deadline = [], time.time() + seconds
    while time.time() < deadline:
        end = min(deadline, time.time() + max(1.0, seconds / 10))
        n = 0
        while time.time() < end:
            resolve(comps, edges, {"state": "p"})
            n += 1
        windows.append({"ops": n, "traced_kib": tracemalloc.get_traced_memory()[0] / 1024})
    tracemalloc.stop()
    growth = windows[-1]["traced_kib"] - windows[0]["traced_kib"] if len(windows) > 1 else 0.0
    return {"soak": {"seconds": seconds, "windows": windows, "memory_growth_kib": growth}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=200)
    ap.add_argument("--soak", type=float, default=0)
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    t0 = time.time()
    results = {**bench_resolve(args.iters), **bench_service(max(20, args.iters // 4)), **bench_burst()}
    tracemalloc.start()
    comps, edges = chain(200)
    resolve(comps, edges, {"state": "p"})
    results["resolve_200_peak_kib"] = tracemalloc.get_traced_memory()[1] / 1024
    tracemalloc.stop()
    if args.soak:
        results.update(soak(args.soak))
    thresholds = json.loads((PKG / "perf" / "THRESHOLDS.json").read_text())
    breaches = []
    for key, lim in thresholds["limits"].items():
        metric, field = key.rsplit(".", 1) if "." in key else (key, None)
        val = results.get(metric, {}).get(field) if field else results.get(metric)
        if val is None:
            continue
        if ("min" in lim and val < lim["min"]) or ("max" in lim and val > lim["max"]):
            breaches.append({"metric": key, "value": val, "limit": lim})
    evidence = {"tool": "pln02 bench", "started": t0, "host": {"python": sys.version.split()[0], "platform": platform.platform(),
                "machine": platform.machine(), "cpus": os.cpu_count()}, "results": results,
                "thresholds_version": thresholds["version"], "breaches": breaches,
                "verdict": "PASS" if not breaches else "FAIL",
                "scope_note": "single-host baseline; not a fleet-scale or constrained-edge certification"}
    text = json.dumps(evidence, indent=2, sort_keys=True)
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(text)
    print(text)
    return 0 if not breaches else 1


if __name__ == "__main__":
    raise SystemExit(main())
