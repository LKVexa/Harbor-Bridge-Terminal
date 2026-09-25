"""Resource/capacity benchmark (closure #22): memory per call/tombstone, throughput, contention, recovery."""
from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import sys
import threading
import time
import tracemalloc

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
rt = importlib.import_module(PKG.name + ".runtime")


def mem_per(n, fn):
    tracemalloc.start()
    b = tracemalloc.get_traced_memory()[0]
    keep = fn(n)
    a = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    del keep
    return (a - b) / n


def tombstone_bytes(n):
    """Retained bytes per tombstone: measured after the live CallStates are released."""
    f = rt.AsyncFunctions("m", declared={"a": True}, tombstone_capacity=n)
    tracemalloc.start()
    b = tracemalloc.get_traced_memory()[0]
    for _ in range(n):
        f.complete(f.invoke("a").call_id, None)
    a = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    return (a - b) / n


def live_calls(n):
    f = rt.AsyncFunctions("m", declared={"a": True})
    return f, [f.invoke("a") for _ in range(n)]


def tombstones(n):
    f = rt.AsyncFunctions("m", declared={"a": True}, tombstone_capacity=n)
    base = [f.invoke("a") for _ in range(n)]
    for c in base:
        f.complete(c.call_id, None)
    return f


def throughput(op_mix, seconds, threads, limit=None):
    f = rt.AsyncFunctions("t", declared={"a": True}, concurrency_limit=limit, tombstone_capacity=4096)
    stop = time.monotonic() + seconds
    counts = [0] * threads

    def w(k):
        n = 0
        while time.monotonic() < stop:
            try:
                c = f.invoke("a")
            except rt.ConcurrencyLimitReached:
                n += 1
                continue
            if op_mix == "complete":
                f.complete(c.call_id, 1)
            else:
                f.cancel(c.call_id, "caller")
            n += 1
        counts[k] = n

    ts = [threading.Thread(target=w, args=(k,)) for k in range(threads)]
    [t.start() for t in ts]; [t.join() for t in ts]
    return sum(counts) / seconds


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=0.5)
    ap.add_argument("--out", default=str(PKG / "evidence" / "bench" / "capacity.json"))
    a = ap.parse_args(argv)
    out = {"schema": "inv16.bench.capacity/1"}
    out["bytes_per_live_call"] = round(mem_per(20_000, live_calls), 1)
    out["bytes_per_tombstone"] = round(tombstone_bytes(20_000), 1)
    out["ops_per_s"] = {f"{mix}_t{t}": round(throughput(mix, a.seconds, t))
                        for mix in ("complete", "cancel") for t in (1, 4, 16)}
    out["limit_sweep_ops_per_s"] = {str(lim): round(throughput("complete", a.seconds / 2, 8, lim))
                                    for lim in (1, 8, 64, 1024)}
    # recovery: saturate then drain
    f = rt.AsyncFunctions("r", declared={"a": True}, concurrency_limit=10_000)
    cs = [f.invoke("a") for _ in range(10_000)]
    t0 = time.perf_counter()
    f.cancel_all("shutdown")
    out["drain_10k_calls_ms"] = round((time.perf_counter() - t0) * 1e3, 3)
    c = f.invoke("a"); f.complete(c.call_id, 1)
    out["recovered_after_drain"] = f.calls_in_flight == 0
    # capacity model: in_flight = rate * duration (Little's law); memory = in_flight*live + cap*tomb
    out["capacity_model"] = ("mem_bytes ~= rate_per_s * mean_duration_s * bytes_per_live_call"
                             " + tombstone_capacity * bytes_per_tombstone")
    out["example_1k_rps_200ms_64k_tomb_MiB"] = round((1000 * 0.2 * out["bytes_per_live_call"]
                                                     + 65_536 * out["bytes_per_tombstone"]) / 2 ** 20, 2)
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
