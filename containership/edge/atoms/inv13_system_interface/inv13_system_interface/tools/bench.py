"""MC-024 -- reproducible performance / scale harness with regression gate.

    python -m inv13_system_interface.tools.bench [--out evidence/bench.json] [--gate]

Reports p50/p95/p99/max per operation (ns), startup, descriptor density,
overload shedding and a short soak. ``--gate`` compares against
BENCH_BASELINE.json ceilings (p99 per op) and exits 1 on regression.
Numbers are host-specific; the baseline records the reference machine.
"""
from __future__ import annotations

import json, os, platform, statistics, sys, tempfile, time, tracemalloc
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from inv13_system_interface.runtime import Instance, World  # noqa: E402
from inv13_system_interface.host import fs, policy, resources, descriptors, randomness, audit_sink, quotas  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def measure(fn, n):
    for _ in range(min(200, n)):
        fn()
    out = []
    for _ in range(n):
        t = time.perf_counter_ns(); fn(); out.append(time.perf_counter_ns() - t)
    return {"n": n, "p50_ns": pct(out, 50), "p95_ns": pct(out, 95), "p99_ns": pct(out, 99), "max_ns": max(out),
            "mean_ns": int(statistics.fmean(out))}


def run(n=20000):
    res = {"host": {"python": platform.python_version(), "machine": platform.machine(), "system": platform.system(),
                    "cpu_count": os.cpu_count(), "openat2": fs.openat2_available()}, "ops": {}}
    inst = Instance("b", World("w", {"filesystem"})); inst.grant_preopen("/d", "/srv/d")
    res["ops"]["lexical_resolve"] = measure(lambda: inst.resolve("/d", "a/b/c.txt"), n)
    root = Path(tempfile.mkdtemp()); (root / "a" / "b").mkdir(parents=True); (root / "a" / "b" / "c.txt").write_text("x")
    p = fs.Preopen("/d", str(root))
    res["ops"]["fs_open_close"] = measure(lambda: os.close(p.open("a/b/c.txt")), n // 4)
    saved = fs._openat2_ok; fs._openat2_ok = False
    res["ops"]["fs_open_close_walk"] = measure(lambda: os.close(p.open("a/b/c.txt")), n // 4)
    fs._openat2_ok = saved
    t = resources.ResourceTable(4096)
    def rt():
        h = t.push("fd", 1); t.get(h, "fd"); t.drop(h)
    res["ops"]["resource_push_get_drop"] = measure(rt, n)
    sys.path.insert(0, str(PKG / "tests")); import _fx  # noqa
    pe = policy.PolicyEngine(_fx.policy_doc("/srv/tenant-a"))
    res["ops"]["policy_decide"] = measure(lambda: pe.decide(tenant="tenant-a", workload="api", world="batch-file-worker",
                                                            capabilities={"filesystem", "stdio"},
                                                            preopens={"/data": "/srv/tenant-a/x"}), n)
    r = randomness.CsprngProvider(bytes_per_sec=1 << 30)
    res["ops"]["random_32b"] = measure(lambda: r.get(32), n)
    a = audit_sink.AuditSink(str(root / "audit.jsonl"), node="n", release="4.3.0", checkpoint_key=b"k" * 32)
    res["ops"]["audit_append_fsync"] = measure(lambda: a.append("w", "x", "granted", {"count": 1}), 500)
    a.close()
    t0 = time.perf_counter_ns(); policy.PolicyEngine(_fx.policy_doc("/srv/tenant-a")); fs.Preopen("/x", str(root)).close()
    res["startup_ns"] = time.perf_counter_ns() - t0
    tracemalloc.start()
    dt = descriptors.DescriptorTable()
    for i in range(10000):
        dt.mint(tenant="a", workload=f"w{i % 50}", capability="stdio", scope={}, rights={"invoke"},
                provenance={"decision": "d", "actor": "a"})
    cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    res["descriptor_density"] = {"count": 10000, "bytes_per_descriptor": cur // 10000, "peak_bytes": peak}
    ad = quotas.Admission(node_slots=64)
    admitted = sum(ad.try_admit(f"t{i % 4}") for i in range(10000))
    res["overload"] = {"offered": 10000, "admitted": admitted, "shed": ad.shed}
    for i in range(admitted):
        pass
    t_end = time.time() + float(os.environ.get("INV13_SOAK_SECONDS", "2"))
    soak = []
    while time.time() < t_end:
        t1 = time.perf_counter_ns(); os.close(p.open("a/b/c.txt")); soak.append(time.perf_counter_ns() - t1)
    third = max(1, len(soak) // 3)
    res["soak"] = {"ops": len(soak), "p99_first_third_ns": pct(soak[:third], 99), "p99_last_third_ns": pct(soak[-third:], 99)}
    p.close()
    return res


def gate(res, baseline):
    problems = []
    for op, ceil in baseline["p99_ceiling_ns"].items():
        got = res["ops"][op]["p99_ns"]
        if got > ceil:
            problems.append(f"{op}: p99 {got} ns > ceiling {ceil} ns")
    s = res["soak"]
    if s["p99_last_third_ns"] > 3 * max(1, s["p99_first_third_ns"]):
        problems.append("soak degradation > 3x")
    return problems


if __name__ == "__main__":
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    res = run()
    if "--gate" in sys.argv:
        res["gate_problems"] = gate(res, json.loads((PKG / "BENCH_BASELINE.json").read_text()))
    txt = json.dumps(res, indent=2)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True); Path(out).write_text(txt + "\n")
    print(txt)
    sys.exit(1 if res.get("gate_problems") else 0)
