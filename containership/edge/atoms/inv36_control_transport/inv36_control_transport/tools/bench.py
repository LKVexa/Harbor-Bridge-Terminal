"""Performance certification harness (MC-13).

    python -m inv36_control_transport.tools.bench --profile smoke --out bench.json
    python -m inv36_control_transport.tools.bench --compare baseline.json candidate.json

Measures, with warm-up and monotonic ``perf_counter_ns`` timing:

* crypto/session layer alone: seal+open latency for 64 B / 1 KiB / 64 KiB;
* full stack over the in-memory stream: handshake latency and rate,
  end-to-end control-operation latency (send -> authorize -> dispatch -> reply);
* throughput (messages/s, bytes/s), CPU time, RSS, allocations (tracemalloc);
* per-session overhead (memory per established channel);
* burst/overload shedding behaviour and reconnect-storm cost.

Real-vsock end-to-end numbers are produced by the same harness with
``--transport vsock --peer-cid N`` on a certified VM row; this environment
cannot run them (see docs/PERFORMANCE.md).  Power/thermal is out of scope for
the reference harness and is recorded as ``not_measured``.

``--compare`` applies thresholds from ``perf/thresholds.json`` and exits 1
on a regression beyond tolerance (MC-13.026-.028).
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import pathlib
import platform
import statistics
import sys
import threading
import time
import tracemalloc

PKG = pathlib.Path(__file__).resolve().parents[1]
THRESHOLDS = PKG / "perf" / "thresholds.json"
PROFILES = {"smoke": {"iters": 300, "hs": 30, "e2e": 200, "sessions": 20},
            "full": {"iters": 5000, "hs": 300, "e2e": 3000, "sessions": 200}}
SIZES = {"small_64B": 64, "typical_1KiB": 1024, "max_64KiB": 65536}


def pct(xs: list[int] | list[float]) -> dict:
    s = sorted(xs)
    n = len(s)

    def q(p: float) -> float:
        return s[min(n - 1, max(0, int(round(p * (n - 1)))))]

    return {"n": n, "p50_us": round(q(0.5) / 1000, 2), "p95_us": round(q(0.95) / 1000, 2),
            "p99_us": round(q(0.99) / 1000, 2), "max_us": round(s[-1] / 1000, 2),
            "mean_us": round(statistics.fmean(s) / 1000, 2),
            "stdev_us": round(statistics.pstdev(s) / 1000, 2)}


def env_fingerprint() -> dict:
    import cryptography
    from cryptography.hazmat.backends.openssl.backend import backend
    gov = "unknown"
    try:
        gov = pathlib.Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip()
    except OSError:
        pass
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(), "cpus": os.cpu_count(),
            "cpu_governor": gov, "cryptography": cryptography.__version__,
            "openssl": backend.openssl_version_text()}


def bench_crypto(iters: int) -> dict:
    from ..transport import Session
    shared = hashlib.sha256(b"bench").digest()
    sid = os.urandom(16)
    out = {}
    for name, size in SIZES.items():
        a, b = Session("bench-a", "bench-b", shared, session_id=sid), Session("bench-b", "bench-a", shared,
                                                                              session_id=sid)
        payload = os.urandom(size)
        for _ in range(min(50, iters)):
            b.open(a.seal(payload))
        seal, open_ = [], []
        for _ in range(iters):
            t0 = time.perf_counter_ns()
            f = a.seal(payload)
            t1 = time.perf_counter_ns()
            b.open(f)
            t2 = time.perf_counter_ns()
            seal.append(t1 - t0)
            open_.append(t2 - t1)
        total = [x + y for x, y in zip(seal, open_, strict=True)]
        out[name] = {"seal": pct(seal), "open": pct(open_), "seal_open": pct(total),
                     "msgs_per_s": round(1e9 / statistics.fmean(total)),
                     "bytes_per_s": round(size * 1e9 / statistics.fmean(total))}
    return out


def _world():
    from ..messages import ControlMessage
    from ..testing import World
    w = World()
    handlers = {"LEASE_RENEW": lambda p, m: ControlMessage.of("STATUS_QUERY", m.tenant, b"ok")}
    return w, handlers


def bench_handshake(n: int) -> dict:
    from ..testing import connect_pair
    w, handlers = _world()
    srv = w.endpoint("bench:srv", "host_agent", "t1", handlers=handlers)
    cli = w.endpoint("bench:cli", "guest_agent", "t1")
    lat = []
    t_start = time.perf_counter()
    for _ in range(n):
        t0 = time.perf_counter_ns()
        s, c = connect_pair(srv, cli)
        lat.append(time.perf_counter_ns() - t0)
        c.close()
        s.close()
    wall = time.perf_counter() - t_start
    return {"handshake": pct(lat), "establish_per_s": round(n / wall, 1)}


def bench_e2e(n: int) -> dict:
    from ..messages import ControlMessage
    from ..testing import connect_pair
    w, handlers = _world()
    srv = w.endpoint("bench:srv", "host_agent", "t1", handlers=handlers)
    cli = w.endpoint("bench:cli", "guest_agent", "t1")
    s, c = connect_pair(srv, cli)
    stop = threading.Event()

    def serve() -> None:
        while not stop.is_set():
            try:
                s.serve_one()
            except Exception:  # noqa: BLE001
                return

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    lat = []
    cpu0 = time.process_time()
    t_start = time.perf_counter()
    for _ in range(n):
        t0 = time.perf_counter_ns()
        c.send(ControlMessage.of("LEASE_RENEW", "t1", b"lease-1"))
        c.receive()
        lat.append(time.perf_counter_ns() - t0)
    wall = time.perf_counter() - t_start
    cpu = time.process_time() - cpu0
    stop.set()
    c.close()
    t.join(2)
    return {"control_op_rtt": pct(lat), "ops_per_s": round(n / wall, 1), "cpu_s_per_op_us": round(cpu / n * 1e6, 2)}


def bench_sessions(n: int) -> dict:
    from ..testing import connect_pair
    w, handlers = _world()
    srv = w.endpoint("bench:srv", "host_agent", "t1", handlers=handlers)
    gc.collect()
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    pairs = []
    for i in range(n):
        cli = w.endpoint(f"bench:cli{i}", "guest_agent", f"t{i % 4}")
        pairs.append(connect_pair(srv, cli))
    used = tracemalloc.get_traced_memory()[0] - base
    tracemalloc.stop()
    for s, c in pairs:
        c.close()
        s.close()
    return {"sessions": n, "bytes_per_session_both_ends": round(used / n)}


def bench_overload() -> dict:
    from ..health import AdmissionController, OverloadError, Priority
    ac = AdmissionController(high_water=64, low_water=16, per_tenant=1000)
    admitted = {p.name: 0 for p in Priority}
    shed = {p.name: 0 for p in Priority}
    for i in range(1000):
        p = [Priority.CRITICAL, Priority.NORMAL, Priority.OPTIONAL][i % 3]
        try:
            ac.admit("t", p)
            admitted[p.name] += 1
        except OverloadError:
            shed[p.name] += 1
    return {"offered": 1000, "admitted": admitted, "shed": shed, "max_depth": ac.depth,
            "bounded": ac.depth <= ac.high_water + 16}


def rss_bytes() -> int:
    try:
        return int(pathlib.Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except OSError:
        return 0


def run(profile: str) -> dict:
    p = PROFILES[profile]
    t0 = time.perf_counter()
    startup0 = time.perf_counter()
    import importlib
    importlib.import_module("inv36_control_transport.endpoint")
    startup = time.perf_counter() - startup0
    res = {"schema": "inv36.bench/1", "profile": profile, "environment": env_fingerprint(),
           "method": {"timer": "perf_counter_ns (monotonic)", "warmup": "50 iterations per size",
                      "outliers": "none removed; p99/max reported", "sizes": SIZES},
           "startup_import_s": round(startup, 4), "crypto": bench_crypto(p["iters"]),
           "handshake": bench_handshake(p["hs"]), "e2e": bench_e2e(p["e2e"]), "density": bench_sessions(p["sessions"]),
           "overload": bench_overload(), "rss_bytes": rss_bytes(),
           "power_thermal": "not_measured (requires instrumented edge profile)",
           "real_vsock": "not_measured (requires certified VM row; see docs/PERFORMANCE.md)"}
    res["wall_s"] = round(time.perf_counter() - t0, 2)
    return res


def compare(baseline: dict, candidate: dict, thresholds: dict) -> list[str]:
    """Return a list of regression findings (empty = pass)."""
    bad = []
    tol = thresholds["regression_tolerance"]
    for path, limit in thresholds["absolute"].items():
        val = _dig(candidate, path)
        if val is None:
            bad.append(f"{path}: missing in candidate")
        elif val > limit:
            bad.append(f"{path}: {val} exceeds absolute limit {limit}")
    for path in thresholds["relative"]:
        b, c = _dig(baseline, path), _dig(candidate, path)
        if b is None or c is None:
            continue
        higher_is_better = path.endswith("_per_s")
        if higher_is_better and c < b * (1 - tol):
            bad.append(f"{path}: {c} < baseline {b} - {tol:.0%}")
        if not higher_is_better and c > b * (1 + tol) + thresholds.get("noise_floor_us", 0):
            bad.append(f"{path}: {c} > baseline {b} + {tol:.0%}")
    return bad


def _dig(d: dict, path: str):
    for part in path.split("."):
        if not isinstance(d, dict) or part not in d:
            return None
        d = d[part]
    return d


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=list(PROFILES), default="smoke")
    ap.add_argument("--out")
    ap.add_argument("--compare", nargs=2, metavar=("BASELINE", "CANDIDATE"))
    a = ap.parse_args(argv)
    if a.compare:
        th = json.loads(THRESHOLDS.read_text())
        bad = compare(json.loads(pathlib.Path(a.compare[0]).read_text()),
                      json.loads(pathlib.Path(a.compare[1]).read_text()), th)
        print(json.dumps({"regressions": bad, "ok": not bad}, indent=1))
        return 1 if bad else 0
    res = run(a.profile)
    text = json.dumps(res, indent=1)
    if a.out:
        pathlib.Path(a.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
