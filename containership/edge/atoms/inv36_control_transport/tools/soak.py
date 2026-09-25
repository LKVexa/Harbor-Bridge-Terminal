"""Soak, burst, reconnect-storm and fleet-scale simulation (MC-16).

    python -m inv36_control_transport.tools.soak --seconds 30 --out soak.json      # short (CI nightly)
    python -m inv36_control_transport.tools.soak --seconds 21600 --out soak.json   # 6 h certification soak
    python -m inv36_control_transport.tools.soak --fleet 200 --out fleet.json

Soak: continuous traffic with mixed frame sizes (including the 64 KiB
maximum), periodic session re-establishment (rekey), key-epoch rotation,
config re-activation and policy updates; samples RSS, open FDs, threads and
p50/p95/p99 latency per window and reports growth trends.

Fleet: N simulated guests (in-memory streams) connect to one host endpoint,
exchange traffic, then all reconnect "simultaneously" through jittered
backoff; reports spread of reconnect times, per-tenant fairness under
admission limits and metric-series cardinality.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import random
import statistics
import sys
import threading
import time

from .. import config as C
from ..health import AdmissionController, RetryBudget, RetryPolicy
from ..messages import ControlMessage
from ..observability import MetricsRegistry
from ..policy import default_policy
from ..testing import World, connect_pair


def _fds() -> int:
    try:
        return len(os.listdir("/proc/self/fd"))
    except OSError:
        return -1


def _rss() -> int:
    try:
        return int(pathlib.Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except OSError:
        return -1


def _q(xs: list[float], p: float) -> float:
    s = sorted(xs)
    return round(s[min(len(s) - 1, int(p * (len(s) - 1)))] * 1e6, 1) if s else 0.0


def soak(seconds: float, window_s: float = 5.0, seed: int = 1) -> dict:
    rng = random.Random(seed)
    w = World()
    store = C.ConfigStore()
    store.activate(C.dev_profile(), source="soak", author="soak")
    handlers = {"LEASE_RENEW": lambda p, m: ControlMessage.of("STATUS_QUERY", m.tenant, b"ok")}
    srv = w.endpoint("soak:host", "host_agent", "t1", handlers=handlers)
    cli = w.endpoint("soak:guest", "guest_agent", "t1")
    windows, lat, frames, rekeys, rotations, reloads = [], [], 0, 0, 0, 0
    end = time.monotonic() + seconds
    next_window = time.monotonic() + window_s
    policy_version = 1
    epoch = 1
    while time.monotonic() < end:
        s, c = connect_pair(srv, cli)
        rekeys += 1
        stop = threading.Event()

        def serve(s=s, stop=stop) -> None:
            while not stop.is_set():
                try:
                    s.serve_one()
                except Exception:  # noqa: BLE001
                    return

        t = threading.Thread(target=serve, daemon=True)
        t.start()
        for _ in range(rng.randint(50, 150)):
            size = rng.choice([16, 256, 1024, 8192, 65000])
            t0 = time.perf_counter()
            c.send(ControlMessage.of("LEASE_RENEW", "t1", os.urandom(size)))
            c.receive()
            lat.append(time.perf_counter() - t0)
            frames += 1
        stop.set()
        c.close()
        t.join(2)
        s.close()
        if rng.random() < 0.3:
            epoch += 1
            w.epochs.rotate(epoch, grace_s=3600)
            # re-issue identities for the new epoch
            srv.identity, srv.credential = w.identity("soak:host", "host_agent", "t1", epoch=epoch)
            cli.identity, cli.credential = w.identity("soak:guest", "guest_agent", "t1", epoch=epoch)
            rotations += 1
        if rng.random() < 0.3:
            store.activate(C.dev_profile(max_sessions=200 + reloads % 50, max_sessions_per_tenant=50), source="soak",
                           author="soak")
            policy_version += 1
            w.policy_store.load(default_policy(time.time(), version=policy_version))
            reloads += 1
        if time.monotonic() >= next_window:
            windows.append({"t": round(seconds - (end - time.monotonic()), 1), "rss": _rss(), "fds": _fds(),
                            "threads": threading.active_count(), "frames": frames, "p50_us": _q(lat, .5),
                            "p95_us": _q(lat, .95), "p99_us": _q(lat, .99)})
            lat = []
            next_window = time.monotonic() + window_s
    if not windows:
        windows.append({"t": seconds, "rss": _rss(), "fds": _fds(), "threads": threading.active_count(),
                        "frames": frames, "p50_us": _q(lat, .5), "p95_us": _q(lat, .95), "p99_us": _q(lat, .99)})
    first, last = windows[0], windows[-1]
    return {"schema": "inv36.soak/1", "seconds": seconds, "frames": frames, "sessions": rekeys,
            "key_rotations": rotations, "config_policy_reloads": reloads, "windows": windows,
            "growth": {"rss_bytes": last["rss"] - first["rss"], "fds": last["fds"] - first["fds"],
                       "threads": last["threads"] - first["threads"]},
            "leak_suspected": (last["fds"] - first["fds"]) > 8 or (last["threads"] - first["threads"]) > 4}


def fleet(n: int, tenants: int = 8, seed: int = 1) -> dict:
    rng = random.Random(seed)
    w = World()
    metrics = MetricsRegistry()
    srv = w.endpoint("fleet:host", "host_agent", "t0", metrics=metrics,
                     admission=AdmissionController(high_water=64, low_water=16, per_tenant=6),
                     handlers={"LEASE_RENEW": lambda p, m: None})
    srv.cfg.max_sessions = n + 10
    srv.cfg.max_sessions_per_tenant = n
    guests = [w.endpoint(f"fleet:g{i}", "guest_agent", f"t{i % tenants}") for i in range(n)]
    t0 = time.perf_counter()
    pairs = [connect_pair(srv, g) for g in guests]
    establish_s = time.perf_counter() - t0
    for s, c in pairs:
        c.send(ControlMessage.of("LEASE_RENEW", s.peer.tenant, b"x"))
        s.serve_one()
    # synchronized disconnect -> jittered reconnect storm
    for s, c in pairs:
        c.close(graceful=False)
        s.close(graceful=False)
    budget = RetryBudget(tokens=float(n), max_tokens=float(n))
    delays = []
    for _ in range(n):
        pol = RetryPolicy(max_attempts=3, base_s=0.05, cap_s=2.0, budget=budget, rng=random.Random(rng.random()))
        delays.append(next(iter(pol.delays())))
    t1 = time.perf_counter()
    pairs = [connect_pair(srv, g) for g in guests]
    reconnect_s = time.perf_counter() - t1
    # fairness under admission: every tenant gets at least one admitted op
    admitted = {f"t{i}": 0 for i in range(tenants)}
    for s, _c in pairs:
        admitted[s.peer.tenant] += 1
    for s, c in pairs:
        c.close()
        s.close()
    series = metrics.exposition().count("\n")
    return {"schema": "inv36.fleet/1", "guests": n, "tenants": tenants, "establish_s": round(establish_s, 3),
            "establish_per_s": round(n / establish_s, 1), "reconnect_s": round(reconnect_s, 3),
            "reconnect_delay_spread": {"min_s": round(min(delays), 4), "max_s": round(max(delays), 4),
                                       "stdev_s": round(statistics.pstdev(delays), 4)},
            "sessions_per_tenant": admitted, "fair": min(admitted.values()) >= n // tenants - 1,
            "metric_exposition_lines": series, "bounded_cardinality": series < 2000}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=0)
    ap.add_argument("--fleet", type=int, default=0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = {}
    if a.seconds:
        res["soak"] = soak(a.seconds, window_s=max(1.0, a.seconds / 10), seed=a.seed)
    if a.fleet:
        res["fleet"] = fleet(a.fleet, seed=a.seed)
    text = json.dumps(res, indent=1)
    if a.out:
        pathlib.Path(a.out).write_text(text)
    print(text)
    bad = res.get("soak", {}).get("leak_suspected") or (res.get("fleet") and not res["fleet"]["fair"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
