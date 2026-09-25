"""Reproducible local performance baseline (MC-041, MC-043, MC-044, MC-046, MC-049).

Drives the real service path (store + reconciler + emulator + API) on local disk.
Numbers are a baseline for THIS host only; thresholds are PROPOSED and unapproved
(governance/THRESHOLDS.json), so the regression gate reports
``within_proposed`` rather than PASS.
"""
from __future__ import annotations

import io
import json
import os
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc

from _common import PKG, write_json

sys.path.insert(0, str(PKG / "tests"))
from test_production import Rig, report  # noqa: E402

from inv34_legacy_cpu_expansion_path.production.adapters.emulator import FaultPlan  # noqa: E402


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def summarize(xs):
    return {"n": len(xs), "p50_ms": pct(xs, 50) * 1e3, "p95_ms": pct(xs, 95) * 1e3, "p99_ms": pct(xs, 99) * 1e3,
            "max_ms": max(xs) * 1e3, "mean_ms": statistics.fmean(xs) * 1e3}


def run(n_vms: int, burst: bool, faults: bool) -> dict:
    with tempfile.TemporaryDirectory() as td:
        vms = {f"vm-{i}": (1, 64) for i in range(n_vms)}
        rig = Rig(td, FaultPlan((["timeout_after", "", "", ""] * (n_vms // 4)) if faults else []), vms=vms)
        sub, rec, obs = [], [], []
        tracemalloc.start()
        t_all = time.perf_counter()
        for rnd in range(1, 4):
            for vm in vms:
                t = time.perf_counter(); rig.svc.submit(vm, f"{vm}-r{rnd}", 1 + rnd * 4); sub.append(time.perf_counter() - t)
            if not burst:
                pass
            for _ in range(2):
                rig.svc.clock = rig.store._clock = (lambda base=time.time() + 10_000 * rnd: base)
                for vm in vms:
                    t = time.perf_counter(); rig.svc.reconcile_once(vm); rec.append(time.perf_counter() - t)
            rig.svc.clock = rig.store._clock = time.time
            for vm in vms:
                online = rig.hv.guest_tick(vm)
                t = time.perf_counter(); rig.svc.observe(report(vm, f"0-{online - 1}", rnd)); obs.append(time.perf_counter() - t)
        wall = time.perf_counter() - t_all
        cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        conv = sum(1 for vm in vms if rig.svc.status(vm)["converged"])
        disk = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(td) for f in fs)
        return {"vms": n_vms, "burst": burst, "faults": faults, "submit": summarize(sub), "reconcile": summarize(rec),
                "observe": summarize(obs), "wall_s": wall, "peak_py_heap_kib": peak / 1024,
                "state_bytes_per_vm": disk / n_vms, "converged": conv, "hotadd_actions": rig.hv.hotadd_actions,
                "expected_actions": 3 * n_vms}


def main() -> int:
    t0 = time.perf_counter()
    import inv34_legacy_cpu_expansion_path.production.service  # noqa: F401
    startup = time.perf_counter() - t0
    scen = [run(10, False, False), run(50, True, False), run(50, True, True)]
    thresholds = json.loads((PKG / "governance/THRESHOLDS.json").read_text())
    checks = []
    for s in scen:
        for op in ("submit", "reconcile", "observe"):
            lim = thresholds["latency_ms"][op]["p99"]["value"]
            checks.append({"scenario": f"{s['vms']}vm/burst={s['burst']}/faults={s['faults']}", "op": op,
                           "p99_ms": round(s[op]["p99_ms"], 3), "proposed_limit_ms": lim,
                           "result": "within_proposed" if s[op]["p99_ms"] <= lim else "exceeds_proposed"})
        checks.append({"scenario": f"{s['vms']}vm faults={s['faults']}", "op": "no_duplicate_hotadd",
                       "result": "ok" if s["hotadd_actions"] == s["expected_actions"] else "DUPLICATE_OR_MISSING",
                       "observed": s["hotadd_actions"], "expected": s["expected_actions"]})
    out = {"schema": "INV34_PERF_BASELINE/1", "host": {"python": platform.python_version(), "machine": platform.machine()},
           "import_startup_ms": startup * 1e3, "scenarios": scen, "regression_gate": checks,
           "threshold_status": thresholds["status"],
           "not_measured": ["real hypervisor adapter latency", "network hop", "power/thermal (MC-047)",
                            "fleet-scale / soak (MC-059)"]}
    write_json("governance/PERF_BASELINE.json", out)
    bad = [c for c in checks if c["result"] not in ("within_proposed", "ok")]
    print(json.dumps({"checks": len(checks), "not_within": bad}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
