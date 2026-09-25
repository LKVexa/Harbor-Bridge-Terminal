"""Benchmark baselines (component 61). Writes certification/BENCHMARK_BASELINE.json.

Single-process CPython numbers for the *reference* host. They are baselines
for regression detection of this model only, never production performance.
"""
import json
import os
import pathlib
import platform
import statistics
import sys
import threading
import time
import tracemalloc

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from inv15_new_asynchronous_abi.host import AsyncHost, Limits  # noqa: E402
from inv15_new_asynchronous_abi.adapters import SchedulerAdapter  # noqa: E402

N = int(os.environ.get("INV15_BENCH_N", "20000"))


def pct(xs):
    xs = sorted(xs)
    return {"p50": xs[len(xs) // 2], "p95": xs[int(.95 * len(xs))], "p99": xs[int(.99 * len(xs))],
            "max": xs[-1], "n": len(xs)}


def run():
    lim = Limits(instance=N, workload=N, tenant=N, process=N, tenant_share=1.0, tombstones=N,
                 mem_instance=1 << 34, mem_tenant=1 << 34, mem_process=1 << 34)
    h = AsyncHost(lim, max_slots=N)
    v = h.register("bench", tenant="t", workload="w")
    ops = {k: [] for k in ("call", "complete", "wait", "take", "cancel", "teardown")}
    t = time.perf_counter_ns
    hm = AsyncHost(lim, max_slots=N)
    vm = hm.register("mem", tenant="t", workload="w")
    tracemalloc.start()
    keep = [vm.call()[1] for _ in range(N)]
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del keep
    hs = []
    for _ in range(N):
        a = t(); hs.append(v.call()[1]); ops["call"].append(t() - a)
    for x in hs[: N // 2]:
        a = t(); h.complete(x, b"x"); ops["complete"].append(t() - a)
        a = t(); v.wait([x]); ops["wait"].append(t() - a)
        a = t(); v.take(x); ops["take"].append(t() - a)
    for x in hs[N // 2:]:
        a = t(); v.cancel(x); ops["cancel"].append(t() - a)
    for _ in range(20):
        w = h.register(f"td{_}", tenant="t", workload="w")
        for _i in range(200):
            w.call()
        a = t(); h.teardown(w); ops["teardown"].append(t() - a)
    # scheduler adapter overhead, separated from core publication
    h2 = AsyncHost(lim, max_slots=N)
    v2 = h2.register("s", tenant="t", workload="w")
    xs = [v2.call()[1] for _ in range(N // 4)]
    a = t()
    for x in xs:
        h2.complete(x, 0)
    core = (t() - a) / len(xs)
    h3 = AsyncHost(lim, max_slots=N)
    v3 = h3.register("s", tenant="t", workload="w")
    SchedulerAdapter(h3, lambda view: None)
    xs = [v3.call()[1] for _ in range(N // 4)]
    a = t()
    for x in xs:
        h3.complete(x, 0)
    with_adapter = (t() - a) / len(xs)
    # concurrency: 8 threads call+cancel
    h4 = AsyncHost(lim, max_slots=N)
    vs = [h4.register(f"c{i}", tenant="t", workload="w") for i in range(8)]
    per = N // 8

    def worker(vv):
        for _ in range(per):
            vv.cancel(vv.call()[1])

    a = time.perf_counter()
    th = [threading.Thread(target=worker, args=(vv,)) for vv in vs]
    [x.start() for x in th]
    [x.join() for x in th]
    el = time.perf_counter() - a
    return {
        "subject": "inv15 reference host 4.3.0 (CPython model, not a production host)",
        "environment": {"python": platform.python_version(), "impl": platform.python_implementation(),
                        "machine": platform.machine(), "system": platform.system()},
        "n": N,
        "latency_ns": {k: pct(v) for k, v in ops.items()},
        "throughput_ops_per_s": {k: round(len(v) / (sum(v) / 1e9)) for k, v in ops.items() if k != "teardown"},
        "call_alloc_bytes_per_live_row": round(cur / N),
        "call_alloc_peak_bytes": peak,
        "declared_row_bytes": 256,
        "accounting_gap_ratio": round(cur / N / 256, 2),
        "adapter_overhead_ns_per_publication": round(with_adapter - core),
        "concurrent_8_threads_call_cancel_ops_per_s": round(2 * per * 8 / el),
    }


def main():
    rep = run()
    out = pathlib.Path(os.environ.get("INV15_BENCH_OUT", ROOT / "certification" / "BENCHMARK_BASELINE.json"))
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("throughput_ops_per_s", "call_alloc_bytes_per_live_row")}))


if __name__ == "__main__":
    main()
