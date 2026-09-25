"""Reproducible benchmark harness and regression gate (Section 15).

Records the environment fingerprint, warms up, repeats, reports p50/p95/p99/max
per operation, throughput and retained memory per object (tracemalloc), and
compares against ``perf/baseline.json`` + ``perf/slo.json``.  Output:
evidence/bench.json.  Exit 1 when a *gating* SLO or regression threshold is
breached.  Absolute numbers are only comparable on the pinned reference
environment; in any other environment the gate runs in ADVISORY mode.
"""
from __future__ import annotations

import gc
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
sys.path.insert(0, str(PKG.parent))

from inv41_capability_security.capabilities import Authority, Forged, Membrane  # noqa: E402

REPS = int(os.environ.get("INV41_BENCH_REPS", "2000"))


def fingerprint() -> dict:
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "build": platform.python_build()[0], "compiler": platform.python_compiler(), "os": platform.platform(),
            "machine": platform.machine(), "cpu_count": os.cpu_count(), "optimize": sys.flags.optimize}


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


ROUNDS = int(os.environ.get("INV41_BENCH_ROUNDS", "5"))


def measure(fn, reps=REPS, warm=200):
    """ROUNDS independent rounds; the gate uses the best-round p50 (noise-robust on shared hosts).
    A first version gated on a single round and failed on a 2-vCPU VM from scheduler noise alone
    (grant p50 7.6 us -> 12.6 us between identical runs)."""
    for _ in range(warm):
        fn()
    round_p50 = []
    samples = []
    for _r in range(ROUNDS):
        rs = []
        for _ in range(reps):
            t = time.perf_counter_ns()
            fn()
            rs.append((time.perf_counter_ns() - t) / 1e3)  # microseconds
        round_p50.append(pct(rs, 50))
        samples += rs
    reps = len(samples)
    return {"n": reps, "rounds": ROUNDS, "best_round_p50_us": min(round_p50), "round_p50_spread": max(round_p50) / min(round_p50), "p50_us": pct(samples, 50), "p95_us": pct(samples, 95), "p99_us": pct(samples, 99),
            "max_us": max(samples), "mean_us": statistics.fmean(samples), "stdev_us": statistics.pstdev(samples),
            "throughput_per_s": 1e6 / statistics.fmean(samples)}


def retained(factory, n=2000):
    gc.collect()
    tracemalloc.start()
    s0 = tracemalloc.take_snapshot()
    keep = [factory() for _ in range(n)]
    gc.collect()
    s1 = tracemalloc.take_snapshot()
    tracemalloc.stop()
    size = sum(st.size_diff for st in s1.compare_to(s0, "filename"))
    del keep
    return round(size / n, 1)


def run() -> dict:
    t_boot = time.perf_counter()
    import importlib
    import inv41_capability_security.selfcheck as sc
    importlib.reload(sc)
    selfcheck_ms = (time.perf_counter() - t_boot) * 1e3
    t0 = time.perf_counter()
    sc.run()
    selfcheck_ms = (time.perf_counter() - t0) * 1e3

    small = Authority({"s": {"read", "write"}})
    big_ops = {f"op{i}" for i in range(256)}
    big = Authority({f"r{i}": big_ops for i in range(64)})
    ref = small.grant("s")
    bigref = big.grant("r1")
    holder = small.bind_holder("h", {"s": ref})
    m = Membrane("bench")
    wrapped = m.wrap(ref)

    def denied():
        try:
            holder.use("s", "admin")
        except Forged:
            pass

    def revoke_1000():
        mm = Membrane("r")
        keep = [mm.wrap(ref) for _ in range(1000)]
        t = time.perf_counter_ns()
        mm.revoke()
        return (time.perf_counter_ns() - t) / 1e3, keep

    ops = {
        "authority_create": measure(lambda: Authority({"s": {"read", "write"}}), reps=REPS // 4),
        "grant": measure(lambda: small.grant("s")),
        "grant_256ops": measure(lambda: big.grant("r2"), reps=REPS // 4),
        "bind_holder": measure(lambda: small.bind_holder("h", {"s": ref})),
        "attenuate": measure(lambda: ref.attenuate({"read"})),
        "attenuate_256ops": measure(lambda: bigref.attenuate(big_ops), reps=REPS // 4),
        "use_allowed": measure(lambda: holder.use("s", "read")),
        "use_denied": measure(denied),
        "wrap": measure(lambda: m.wrap(ref)),
        "invoke_wrapped": measure(lambda: wrapped.invoke("read")),
    }
    rv = [revoke_1000()[0] for _ in range(20)]
    ops["revoke_1000_descendants"] = {"n": 20, "p50_us": pct(rv, 50), "p95_us": pct(rv, 95), "p99_us": pct(rv, 99), "max_us": max(rv)}

    # contention: 8 threads doing use_allowed
    count = [0]
    stop = threading.Event()

    def worker():
        n = 0
        while not stop.is_set():
            holder.use("s", "read")
            n += 1
        count[0] += n
    ts = [threading.Thread(target=worker) for _ in range(8)]
    t = time.perf_counter()
    for th in ts:
        th.start()
    time.sleep(1.0)
    stop.set()
    for th in ts:
        th.join()
    concurrent_tput = count[0] / (time.perf_counter() - t)

    memory = {"authority_bytes": retained(lambda: Authority({"s": {"read"}})),
              "reference_bytes": retained(lambda: small.grant("s")),
              "holder_bytes": retained(lambda: small.bind_holder("h", {"s": ref})),
              "wrapped_reference_bytes": retained(lambda: m.wrap(ref))}
    return {"schema": "INV41_BENCH/1", "fingerprint": fingerprint(), "reps": REPS, "selfcheck_ms": selfcheck_ms,
            "operations": ops, "concurrent_use_8_threads_per_s": concurrent_tput, "memory_per_object": memory}


def gate(result: dict) -> dict:
    slo = json.loads((PKG / "perf" / "slo.json").read_text())
    base_path = PKG / "perf" / "baseline.json"
    baseline = json.loads(base_path.read_text()) if base_path.exists() else None
    reference = slo["reference_environment"]
    fp = result["fingerprint"]
    on_reference = all(fp.get(k) == v for k, v in reference.items())
    breaches, regressions = [], []
    for op, lim in slo["latency_p99_us"].items():
        got = result["operations"][op]["p99_us"]
        if got > lim:
            breaches.append({"op": op, "p99_us": got, "limit": lim})
    for kind, lim in slo["memory_bytes_max"].items():
        if result["memory_per_object"][kind] > lim:
            breaches.append({"memory": kind, "bytes": result["memory_per_object"][kind], "limit": lim})
    if result["selfcheck_ms"] > slo["selfcheck_ms_max"]:
        breaches.append({"selfcheck_ms": result["selfcheck_ms"], "limit": slo["selfcheck_ms_max"]})
    if baseline:
        for op, b in baseline["operations"].items():
            got = result["operations"].get(op, {}).get("best_round_p50_us")
            base = b.get("best_round_p50_us", b["p50_us"])
            if got is None:
                continue
            allowed = max(base * (1 + slo["regression"]["relative"]), base + slo["regression"]["absolute_us"])
            if got > allowed and op in slo["gating_operations"]:
                regressions.append({"op": op, "best_round_p50_us": got, "baseline": base, "allowed": allowed})
    mode = "GATING" if on_reference else "ADVISORY"
    ok = not breaches and not regressions
    return {"mode": mode, "on_reference_environment": on_reference, "slo_breaches": breaches,
            "regressions": regressions, "pass": ok, "blocking": (not ok) and mode == "GATING"}


def main() -> int:
    result = run()
    result["gate"] = gate(result)
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "bench.json").write_text(json.dumps(result, indent=1))
    if "--write-baseline" in sys.argv:
        (PKG / "perf" / "baseline.json").write_text(json.dumps({"fingerprint": result["fingerprint"],
                                                                  "operations": result["operations"]}, indent=1))
    print(json.dumps(result["gate"], indent=1))
    return 1 if result["gate"]["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
