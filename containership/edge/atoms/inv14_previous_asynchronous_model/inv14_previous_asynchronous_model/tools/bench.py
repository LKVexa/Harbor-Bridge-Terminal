"""Benchmark suite (component P2-24; C061-C070, C088).

Measures on the executing host (never extrapolated to others):
  ready_poll_us      latency of a poll whose member is already ready
  wake_latency_us    signal() in another thread -> poll() returns
  timeout_overshoot_ms  observed wait minus requested timeout (1 ms ticks)
  throughput_polls_s ready polls per second, one thread
  fanout_us          poll over N members, last member ready (N = 1, 64, 1024, 4096)
  alloc_bytes_per_poll  tracemalloc peak per ready poll
  import_ms          cold import time of the package in a subprocess
Power and thermal are not measurable here and are reported NOT_MEASURED.
Thresholds live in ops/perf_thresholds.json with status PROPOSED; a met value
is reported as met_under_proposed_threshold, never as an approved pass.
"""
import argparse, json, platform, statistics, subprocess, sys, threading, time, tracemalloc
import _path  # noqa
import polling as P


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q / 100 * (len(xs) - 1))))]


def summary(xs):
    return {"n": len(xs), "p50": pct(xs, 50), "p95": pct(xs, 95), "p99": pct(xs, 99), "max": max(xs)}


def run(n=2000):
    ps = P.PollSet("o")
    p = P.Pollable("x", "o"); p.signal()
    lat = []
    for _ in range(n):
        t = time.perf_counter_ns(); ps.poll([p], timeout_ticks=1); lat.append((time.perf_counter_ns() - t) / 1000)
    wake = []
    for _ in range(max(50, n // 20)):
        q = P.Pollable("w", "o"); box = {}
        def sig():
            time.sleep(0.0005); box["t"] = time.perf_counter_ns(); q.signal()
        th = threading.Thread(target=sig); th.start()
        ps.poll([q], timeout_ticks=1000); end = time.perf_counter_ns(); th.join()
        wake.append((end - box["t"]) / 1000)
    over = []
    for _ in range(20):
        t = time.perf_counter(); ps.poll([P.Pollable("t", "o")], timeout_ticks=5); over.append((time.perf_counter() - t) * 1000 - 5)
    t0 = time.perf_counter(); k = 0
    while time.perf_counter() - t0 < 0.5:
        ps.poll([p], timeout_ticks=1); k += 1
    thr = k / (time.perf_counter() - t0)
    fan = {}
    for size in (1, 64, 1024, 4096):
        ms = [P.Pollable(f"m{i}", "o") for i in range(size)]; ms[-1].signal()
        xs = []
        for _ in range(20 if size > 1000 else 100):
            t = time.perf_counter_ns(); ps.poll(ms, timeout_ticks=1); xs.append((time.perf_counter_ns() - t) / 1000)
        fan[str(size)] = summary(xs)
    tracemalloc.start(); tracemalloc.reset_peak()
    base = tracemalloc.get_traced_memory()[0]
    for _ in range(200):
        ps.poll([p], timeout_ticks=1)
    peak = tracemalloc.get_traced_memory()[1] - base; tracemalloc.stop()
    imp = []
    for _ in range(3):
        t = time.perf_counter()
        subprocess.run([sys.executable, "-B", "-c", "import sys; sys.path.insert(0, %r); import polling" % str(_path.PKG)], check=True)
        imp.append((time.perf_counter() - t) * 1000)
    return {"host": {"python": platform.python_version(), "machine": platform.machine(), "system": platform.system()},
            "ready_poll_us": summary(lat), "wake_latency_us": summary(wake), "timeout_overshoot_ms": summary(over),
            "throughput_polls_s": round(thr), "fanout_us": fan, "alloc_peak_bytes_200_polls": peak,
            "import_ms": summary(imp), "power": "NOT_MEASURED", "thermal": "NOT_MEASURED"}


def compare(res, thresholds):
    out = []
    for t in thresholds["thresholds"]:
        cur = res
        for part in t["metric"].split("."):
            cur = cur[part]
        out.append({"metric": t["metric"], "value": cur, "limit": t["max"],
                    "result": "met_under_proposed_threshold" if cur <= t["max"] else "NOT_MET"})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=2000); a = ap.parse_args()
    r = run(a.n)
    th = json.load(open(_path.PKG / "ops" / "perf_thresholds.json"))
    r["threshold_status"] = th["status"]; r["comparison"] = compare(r, th)
    print(json.dumps(r, indent=1))
    raise SystemExit(0 if all(c["result"] != "NOT_MET" for c in r["comparison"]) else 1)
