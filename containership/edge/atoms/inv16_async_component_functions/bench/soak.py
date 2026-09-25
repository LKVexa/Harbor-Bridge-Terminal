"""Long-duration soak (closure #19).  CI runs a short soak; release runs --minutes 60+.

Mixed workload (invoke/complete/cancel/trap/re-entry/refusal) with periodic
cancellation and trap storms, bounded tombstones and an EventLog sink.
Samples RSS-equivalent traced memory, tombstones, in-flight and latency each
interval; fails if post-warm-up memory slope exceeds the threshold or counts do
not reconcile after drain.
"""
from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import random
import sys
import threading
import time
import tracemalloc

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
rt = importlib.import_module(PKG.name + ".runtime")
obs = importlib.import_module(PKG.name + ".observability")


def slope(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs) or 1
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def run(seconds: float, interval: float, seed: int = 7, threads: int = 4) -> dict:
    log = obs.EventLog(capacity=2000, sample_rate=0.05)
    f = rt.AsyncFunctions("soak", declared={"a": True, "s": True, "q": True}, stateful=frozenset({"s"}),
                          reentrancy={"q": rt.ReentrancyPolicy(rt.ReentrancyMode.QUEUE, 8)},
                          concurrency_limit=256, tombstone_capacity=4096, event_sink=log)
    stop = threading.Event()
    lat = obs.Histogram()

    def worker(k):
        rng = random.Random(seed * 100 + k)
        mine = []
        while not stop.is_set():
            try:
                t0 = time.perf_counter_ns()
                c = f.invoke(rng.choice("aasq"))
                lat.record(time.perf_counter_ns() - t0)
                mine.append(c)
            except (rt.ReentrancyRefused, rt.ConcurrencyLimitReached):
                pass
            if len(mine) > rng.randint(0, 16):
                c = mine.pop(rng.randrange(len(mine)))
                try:
                    if rng.random() < 0.85:
                        f.complete(c.call_id, k)
                    else:
                        f.cancel(c.call_id, "caller")
                except (rt.TerminalConflict, rt.CallNotStarted, rt.HistoryExpired):
                    pass

    ts = [threading.Thread(target=worker, args=(k,), daemon=True) for k in range(threads)]
    tracemalloc.start()
    [t.start() for t in ts]
    series = []
    t_start = time.monotonic()
    storms = 0
    while time.monotonic() - t_start < seconds:
        time.sleep(interval)
        storms += 1
        (f.trap_all if storms % 5 == 0 else f.cancel_all)()
        s = f.snapshot()
        series.append({"t": round(time.monotonic() - t_start, 3), "mem": tracemalloc.get_traced_memory()[0],
                       "tombstones": s["tombstones"], "in_flight": s["calls_in_flight"],
                       "queued": s["calls_queued"], "invoke_p99_ns": lat.quantile(0.99)})
    stop.set()
    [t.join() for t in ts]
    f.cancel_all("drain")
    tracemalloc.stop()
    s = f.snapshot()
    warm = series[len(series) // 3:] or series
    mem_slope = slope([p["t"] for p in warm], [p["mem"] for p in warm])   # bytes/second
    res = {
        "schema": "inv16.soak/1", "seconds": seconds, "samples": len(series), "storms": storms,
        "mem_slope_bytes_per_s": round(mem_slope, 1), "max_tombstones": max(p["tombstones"] for p in series),
        "tombstone_capacity": 4096, "post_drain": {"in_flight": s["calls_in_flight"], "queued": s["calls_queued"]},
        "terminal_total": s["completed_calls"] + s["cancelled_calls"] + s["trapped_calls"],
        "double_delivery_attempts": s["double_delivery_attempts"], "event_log_dropped": log.dropped,
        "series": series,
    }
    res["pass"] = (res["post_drain"] == {"in_flight": 0, "queued": 0} and res["max_tombstones"] <= 4096
                   and abs(mem_slope) < 64 * 1024 and s["double_delivery_attempts"] == 0)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=0.25)
    ap.add_argument("--interval", type=float, default=0.5)
    ap.add_argument("--out", default=str(PKG / "evidence" / "bench" / "soak.json"))
    a = ap.parse_args(argv)
    r = run(a.minutes * 60, a.interval)
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(r, indent=2))
    print(json.dumps({k: v for k, v in r.items() if k != "series"}, indent=1))
    return 0 if r["pass"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
