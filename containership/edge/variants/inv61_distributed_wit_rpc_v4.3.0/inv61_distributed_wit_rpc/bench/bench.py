"""Reproducible INV-61 benchmarks (M28 / C061-C064, C088).

    python bench/bench.py [--quick] [--out evidence/bench_results.json]

Scenarios
  codec_roundtrip      encode+decode of a request envelope (pure framing cost)
  pipeline_inproc      full server pipeline (MAC, replay, authz, admission, decode,
                       dispatch to a no-op callee, encode) without sockets -> the
                       "framing overhead" SLO (p99 < 50us, callee excluded)
  loopback_steady      1 client, sequential calls over TCP loopback
  loopback_burst       32 concurrent callers on one multiplexed connection
  overload             admission ceiling 8, 64 concurrent callers: shed ratio
  per_tenant           8 tenants concurrently: per-tenant p99 spread
  soak                 sustained load for --soak-s seconds: RSS growth + error count
Records environment, p50/p95/p99/max, throughput and peak RSS.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import resource
import secrets
import statistics
import sys
import tempfile
import threading
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
P = PKG.name
codec = __import__(f"{P}.codec", fromlist=["x"]); security = __import__(f"{P}.security", fromlist=["x"])
transport = __import__(f"{P}.transport", fromlist=["x"]); server = __import__(f"{P}.server", fromlist=["x"])
resilience = __import__(f"{P}.resilience", fromlist=["x"]); rpc = __import__(f"{P}.rpc", fromlist=["x"])
wit_model = __import__(f"{P}.wit_model", fromlist=["x"])
KV = wit_model.parse((PKG / "wit" / "kv.wit").read_text())[0]


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def summary(lat_s, wall_s=None):
    us = [x * 1e6 for x in lat_s]
    d = {"n": len(us), "p50_us": round(pct(us, .5), 2), "p95_us": round(pct(us, .95), 2),
         "p99_us": round(pct(us, .99), 2), "max_us": round(max(us), 2), "mean_us": round(statistics.fmean(us), 2)}
    if wall_s:
        d["throughput_per_s"] = round(len(us) / wall_s, 1)
    return d


def rss_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def make_service(tenants=("default",), admission=None, principals=("bench",)):
    ring = security.KeyRing()
    keys = {}
    for p in principals:
        keys[p] = security.Key(f"{p}-k", p, secrets.token_bytes(32)); ring.add(keys[p])
    d = pathlib.Path(tempfile.mkdtemp())
    grants = [security.Grant(p, t, KV.qualified, "*") for p in principals for t in tenants]
    svc = server.RpcService(node_id="bench", keyring=ring, policy=security.Policy(grants),
                            audit=security.AuditLog(d / "a.jsonl", secrets.token_bytes(32), fsync=False),
                            admission=admission or resilience.AdmissionController(max_inflight=4096, per_tenant_inflight=4096,
                                                                                tenant_rate=1e7, tenant_burst=1e7))
    svc.export(KV, "echo", lambda b: b, inline=True)
    svc.export(KV, "get", lambda k: 1, inline=True)
    svc.export(KV, "slow", lambda ms: time.sleep(ms / 1000) or True)
    return svc, keys


def envelope(key, func="get", args=("k",), tenant="default"):
    f = KV.funcs[func]
    now = int(time.time() * 1000)
    env = {"request_id": secrets.token_hex(8), "sender": "", "tenant": tenant, "nonce": secrets.token_hex(16),
           "issued_ms": now, "deadline_ms": now + 5000, "interface": KV.qualified, "version": KV.version,
           "function": func, "fp": rpc.fingerprint(f.param_types(), f.result_types()), "idempotency_key": None,
           "traceparent": None, "args": codec.encode(("tuple", tuple(KV.resolve(t) for _, t in f.params)), list(args)),
           "key_id": "", "mac": b""}
    return security.sign(env, key)


def bench_codec(n):
    k = security.Key("x", "x", secrets.token_bytes(32))
    env = envelope(k)
    lat = []
    for _ in range(n):
        t = time.perf_counter()
        codec.decode(codec.REQUEST_ENVELOPE, codec.encode(codec.REQUEST_ENVELOPE, env))
        lat.append(time.perf_counter() - t)
    return summary(lat)


def bench_pipeline(n, pooled=False):
    svc, keys = make_service()
    if pooled:
        svc.exports[(KV.qualified, "get")].inline = False
    # Measure pipeline overhead with an inline callee: bypass the worker pool hop
    # separately by timing both.
    bodies = [codec.encode(codec.REQUEST_ENVELOPE, envelope(keys["bench"])) for _ in range(n)]
    lat = []
    for b in bodies:
        t = time.perf_counter()
        svc.handle(b)
        lat.append(time.perf_counter() - t)
    svc.close()
    return summary(lat)


def run_calls(client, n, func="get", args=("k",)):
    lat = []
    for _ in range(n):
        t = time.perf_counter()
        r = client.call_once(KV, func, list(args))
        lat.append(time.perf_counter() - t)
        assert r["status"] == "ok", r
    return lat


def bench_loopback_steady(n):
    svc, keys = make_service()
    srv = transport.RpcServer(svc).start()
    c = transport.RpcClient(*srv.address, keys["bench"])
    c.connect()
    run_calls(c, 50)  # warm-up
    t0 = time.perf_counter()
    lat = run_calls(c, n)
    wall = time.perf_counter() - t0
    c.close(); srv.close(); svc.close()
    return summary(lat, wall)


def bench_burst(n, conc=32):
    svc, keys = make_service()
    srv = transport.RpcServer(svc).start()
    c = transport.RpcClient(*srv.address, keys["bench"]); c.connect()
    lat, lock = [], threading.Lock()

    def w():
        mine = run_calls(c, n // conc)
        with lock:
            lat.extend(mine)
    t0 = time.perf_counter()
    ts = [threading.Thread(target=w) for _ in range(conc)]
    [t.start() for t in ts]; [t.join() for t in ts]
    wall = time.perf_counter() - t0
    c.close(); srv.close(); svc.close()
    return dict(summary(lat, wall), concurrency=conc)


def bench_overload(conc=64):
    svc, keys = make_service(admission=resilience.AdmissionController(max_inflight=8, per_tenant_inflight=8,
                                                                      tenant_rate=1e7, tenant_burst=1e7))
    srv = transport.RpcServer(svc).start()
    c = transport.RpcClient(*srv.address, keys["bench"]); c.connect()
    res, lock = [], threading.Lock()

    def w():
        r = c.call_once(KV, "slow", [50])
        with lock:
            res.append(r["status"])
    ts = [threading.Thread(target=w) for _ in range(conc)]
    t0 = time.perf_counter()
    [t.start() for t in ts]; [t.join() for t in ts]
    wall = time.perf_counter() - t0
    c.close(); srv.close(); svc.close()
    return {"callers": conc, "admitted": res.count("ok"), "shed_overloaded": res.count("overloaded"),
            "other": len(res) - res.count("ok") - res.count("overloaded"), "wall_s": round(wall, 3),
            "shed_is_fast": wall < 1.0}


def bench_per_tenant(n, tenants=8):
    names = [f"t{i}" for i in range(tenants)]
    svc, keys = make_service(tenants=names)
    srv = transport.RpcServer(svc).start()
    out, lock = {}, threading.Lock()

    def w(t):
        c = transport.RpcClient(*srv.address, keys["bench"], tenant=t); c.connect()
        lat = run_calls(c, n // tenants)
        c.close()
        with lock:
            out[t] = summary(lat)["p99_us"]
    ts = [threading.Thread(target=w, args=(t,)) for t in names]
    [t.start() for t in ts]; [t.join() for t in ts]
    srv.close(); svc.close()
    vals = list(out.values())
    return {"tenants": tenants, "p99_us_by_tenant": out, "p99_spread_ratio": round(max(vals) / min(vals), 2)}


def bench_soak(seconds):
    svc, keys = make_service()
    srv = transport.RpcServer(svc).start()
    c = transport.RpcClient(*srv.address, keys["bench"]); c.connect()
    start_rss, errors, n, statuses = rss_mb(), 0, 0, {}
    t0 = time.monotonic()
    end = t0 + seconds
    mid_rss = None
    while time.monotonic() < end:
        r = c.call_once(KV, "echo", [list(range(64))])
        n += 1
        if r["status"] != "ok":
            errors += 1
            statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        if mid_rss is None and time.monotonic() - t0 > seconds / 2:
            mid_rss = rss_mb()
    c.close(); srv.close(); svc.close()
    end_rss = rss_mb()
    return {"seconds": seconds, "calls": n, "errors": errors, "error_statuses": statuses,
            "rss_start_mb": start_rss, "rss_mid_mb": mid_rss, "rss_end_mb": end_rss,
            "rss_second_half_growth_mb": round(end_rss - (mid_rss or end_rss), 1),
            "replay_cache_entries_end": len(svc.replay)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--soak-s", type=float, default=60.0)
    ap.add_argument("--out", default=str(PKG / "evidence" / "bench_results.json"))
    a = ap.parse_args()
    n = 2000 if a.quick else 20000
    res = {
        "schema": "inv61-bench/1", "version": (PKG / "VERSION").read_text().strip(),
        "env": {"python": platform.python_version(), "impl": platform.python_implementation(),
                "machine": platform.machine(), "system": platform.system(), "cpus": os.cpu_count()},
        "codec_roundtrip": bench_codec(n),
        "pipeline_inproc": bench_pipeline(n),
        "pipeline_inproc_pooled_callee": bench_pipeline(n, pooled=True),
        "loopback_steady": bench_loopback_steady(n // 4),
        "loopback_burst": bench_burst(n // 2),
        "overload": bench_overload(),
        "per_tenant": bench_per_tenant(n // 4),
        "soak": bench_soak(5 if a.quick else a.soak_s),
    }
    res["peak_rss_mb"] = rss_mb()
    pathlib.Path(a.out).parent.mkdir(exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
