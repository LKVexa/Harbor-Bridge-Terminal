"""Reproducible benchmark and capacity suite (MC-042).

Deterministic seeded workloads over the engine (optionally with the fsync WAL)
measuring p50/p95/p99/max for reads, writes, CAS transactions, watch delivery
and compaction; sustained throughput; peak RSS, CPU and FD use.  Output is a
machine-readable JSON report suitable for release evidence.

    python -m inv05_current_control_state_system.bench --ops 20000 --durable /tmp/b --out bench.json

Value sizes follow a fixed distribution (70% 64B, 25% 1KiB, 5% 16KiB) and watch
fan-out uses ``--watchers`` concurrent consumers (MC-042-05).  The capacity
model in ``docs/CAPACITY.md`` is derived from these reports.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import random
import resource
import statistics
import tempfile
import threading
import time
from typing import Any

from .store import Compare, ControlStore, Put, Range
from .wal import DurableStore
from .watch import WatchHub

SIZES = [(0.70, 64), (0.25, 1024), (0.05, 16384)]


def _pct(xs: list[float]) -> dict[str, float]:
    if not xs:
        return {}
    xs = sorted(xs)
    q = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]
    return {"n": len(xs), "p50_ms": q(0.50) * 1e3, "p95_ms": q(0.95) * 1e3, "p99_ms": q(0.99) * 1e3,
            "max_ms": xs[-1] * 1e3, "mean_ms": statistics.fmean(xs) * 1e3}


def _value(rng: random.Random) -> str:
    r, acc = rng.random(), 0.0
    for p, n in SIZES:
        acc += p
        if r <= acc:
            return "x" * n
    return "x" * SIZES[-1][1]


def run(ops: int = 10_000, keys: int = 1000, watchers: int = 4, seed: int = 42, durable_dir: str | None = None,
        durability: str = "fsync") -> dict[str, Any]:
    rng = random.Random(seed)
    ds = None
    if durable_dir:
        ds = DurableStore.open(durable_dir, durability=durability)
        store = ds.store
    else:
        store = ControlStore()
    hub = WatchHub(store)
    ws = [hub.create(prefix="k/") for _ in range(watchers)]
    delivered = [0] * watchers
    lat_watch: list[float] = []
    stop = threading.Event()
    sent_at: dict[int, float] = {}

    def consume(i: int) -> None:
        while not stop.is_set():
            f = ws[i].poll(0.05)
            if f.type == "events":
                delivered[i] += len(f.events)
                if i == 0 and f.revision in sent_at:
                    lat_watch.append(time.perf_counter() - sent_at[f.revision])

    threads = [threading.Thread(target=consume, args=(i,), daemon=True) for i in range(watchers)]
    for t in threads:
        t.start()
    lat = {"write": [], "read": [], "cas": [], "range100": []}
    t_start = time.perf_counter()
    cpu0 = time.process_time()
    for i in range(ops):
        k = f"k/{rng.randrange(keys):06d}"
        r = rng.random()
        t0 = time.perf_counter()
        if r < 0.45:
            res = store.txn((), [Put(k, _value(rng))])
            sent_at[res.revision] = t0
            lat["write"].append(time.perf_counter() - t0)
        elif r < 0.85:
            store.get(k)
            lat["read"].append(time.perf_counter() - t0)
        elif r < 0.97:
            cur = store.get(k)
            store.txn([Compare(k, "MOD", "==", cur.mod_revision if cur else 0)], [Put(k, _value(rng))])
            lat["cas"].append(time.perf_counter() - t0)
        else:
            store.range(Range("k/", prefix=True, limit=100))
            lat["range100"].append(time.perf_counter() - t0)
    elapsed = time.perf_counter() - t_start
    cpu = time.process_time() - cpu0
    time.sleep(0.3)
    stop.set()
    t0 = time.perf_counter()
    dropped = store.compact(max(0, store.revision - 100))
    t_compact = time.perf_counter() - t0
    ru = resource.getrusage(resource.RUSAGE_SELF)
    try:
        fds = len(os.listdir("/proc/self/fd"))
    except OSError:
        fds = -1
    rep = {"schema": "cstate.bench/1", "seed": seed, "ops": ops, "keys": keys, "watchers": watchers,
           "durable": bool(durable_dir), "durability": durability if durable_dir else "memory",
           "platform": {"python": platform.python_version(), "machine": platform.machine(),
                        "system": platform.system(), "cpus": os.cpu_count()},
           "throughput_ops_s": ops / elapsed, "elapsed_s": elapsed, "cpu_s": cpu,
           "latency": {k: _pct(v) for k, v in lat.items()},
           "watch_delivery": _pct(lat_watch), "watch_events_delivered": delivered,
           "compaction": {"dropped": dropped, "ms": t_compact * 1e3},
           "resources": {"peak_rss_kib": ru.ru_maxrss, "open_fds": fds, "threads": threading.active_count()},
           "store": {"revision": store.revision, "history": store.history_size, "keys": store.key_count}}
    if ds:
        rep["wal_bytes"] = ds.wal.bytes_written
        ds.close()
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ops", type=int, default=10_000)
    ap.add_argument("--keys", type=int, default=1000)
    ap.add_argument("--watchers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--durable", help="WAL directory (enables fsync durability)")
    ap.add_argument("--durability", default="fsync", choices=["fsync", "group"])
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    d = a.durable
    if d == "tmp":
        d = tempfile.mkdtemp(prefix="inv05-bench-")
    rep = run(a.ops, a.keys, a.watchers, a.seed, d, a.durability)
    s = json.dumps(rep, indent=2)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(s)
    print(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
