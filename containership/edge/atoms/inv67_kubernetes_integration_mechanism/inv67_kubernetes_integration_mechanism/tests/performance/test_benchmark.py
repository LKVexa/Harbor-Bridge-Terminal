"""Reproducible benchmark harness (items 37, 38, 40, 53 - local scope).

Measures translation p50/p99 and controller reconcile throughput over the
in-memory fakes, writes raw samples to evidence/perf/, and applies the
declared SLO (translate p99 < 5 ms) plus a regression gate against the
committed baseline. This is local micro-benchmark evidence only; it is NOT
fleet-scale or soak certification (a real cluster is required for that).
"""
import json
import os
import platform
import statistics
import time
import unittest

import _support as S

OUT = S.PKG_DIR / "evidence" / "perf"
BASELINE = S.PKG_DIR / "evidence" / "perf_baseline.json"


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


class Bench(unittest.TestCase):
    def test_translate_slo_and_reconcile_throughput(self):
        pod = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "a", "labels": {"a": "b"}},
               "spec": {"containers": [{"name": f"c{i}", "image": "i", "resources": {"requests": {"cpu": "250m", "memory": "64Mi"},
                                                                                     "limits": {"cpu": "1", "memory": "1Gi"}}} for i in range(4)]}}
        for _ in range(200):
            S.translator.translate(pod)
        samples = []
        for _ in range(5000):
            t0 = time.perf_counter()
            S.translator.translate(pod)
            samples.append((time.perf_counter() - t0) * 1000)
        h = S.Harness()
        n = 300
        for i in range(n):
            h.kube.apply(S.workload(name=f"w{i}"))
        t0 = time.perf_counter()
        h.settle(3)
        dt = time.perf_counter() - t0
        self.assertEqual(h.rt.launches, n)
        res = {"translate_p50_ms": pct(samples, 50), "translate_p99_ms": pct(samples, 99),
               "translate_max_ms": max(samples), "reconcile_workloads_per_s": n / dt,
               "reconcile_passes_per_workload_note": "3 passes: finalizer add + placement + no-op observe"}
        env = {"python": platform.python_version(), "impl": platform.python_implementation(), "machine": platform.machine(),
               "system": platform.system(), "cpu_count": os.cpu_count()}
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "latest.json").write_text(json.dumps({"results": res, "environment": env,
                                                     "samples_ms_stats": {"n": len(samples), "mean": statistics.mean(samples),
                                                                          "stdev": statistics.pstdev(samples)}}, indent=2))
        self.assertLess(res["translate_p99_ms"], 5.0, "declared SLO: translation p99 under 5 ms")
        if BASELINE.exists():
            base = json.loads(BASELINE.read_text())["results"]
            cap = S.mod("capacity")
            # generous tolerance: shared CI hardware is noisy; the SLO above is the hard gate
            bad = cap.regression({k: v for k, v in base.items() if k in ("translate_p99_ms", "reconcile_workloads_per_s")},
                                 res, tolerance=3.0)
            self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
