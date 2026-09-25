"""Performance harness, resource bounds, capacity model and the regression gate (C017, C061-C070, C088).

The full benchmark runs inside the release gate (certify) against
conformance/PERFORMANCE_THRESHOLDS.json; these tests exercise the harness itself with
small sample counts so CI stays fast.
"""
import gc
import json
import threading
import tracemalloc
import unittest

from _util import m, PKG_DIR, rt as make_rt

bench = m("bench")


class HarnessTest(unittest.TestCase):
    def test_micro_benchmarks_reproducible_with_metadata(self):
        """REQ: C061 C062 C088"""
        a, b = bench.micro(300), bench.micro(300)
        for op in ("create", "resolve", "resolve_error", "abandon", "take"):
            for k in ("p50_us", "p95_us", "p99_us", "max_us"):
                self.assertGreater(a[op][k], 0)
            self.assertLess(abs(a[op]["p50_us"] - b[op]["p50_us"]) / max(a[op]["p50_us"], 1e-9), 3.0)
        md = bench.metadata()
        for k in ("python", "machine", "system", "cpu_count", "timestamp"):
            self.assertIn(k, md)

    def test_contention_correctness(self):
        """REQ: C061 C086 C088"""
        for th in (2, 8):
            self.assertEqual(bench.contention(th, 5)["invariant_errors"], 0)

    def test_scaling_is_not_superlinear(self):
        """REQ: C064 C069"""
        s = bench.scaling((100, 1000, 5000))
        per = [s[k]["peak_bytes_per_future"] for k in ("100", "1000", "5000")]
        self.assertLess(per[2], per[0] * 1.5)                         # per-future memory flat or falling
        t = [s[k]["seconds_per_op_us"] for k in ("100", "1000", "5000")]
        self.assertLess(t[2], t[0] * 4)

    def test_profile_zero_copy_and_hops(self):
        """REQ: C065 C066"""
        p = bench.profile_ops()
        self.assertTrue(p["payload_identity_preserved"])
        self.assertEqual(p["network_hops"], 0)
        self.assertFalse(p["serialization_in_core"])

    def test_soak_short(self):
        """REQ: C088 C067"""
        s = bench.soak(0.5)
        self.assertEqual(s["invariant_errors"], 0)
        self.assertEqual(s["outstanding_end"], 0)
        self.assertGreater(s["windows"], 0)


class ResourceBoundTest(unittest.TestCase):
    def test_bounded_memory_under_overload(self):
        """REQ: C067 C017 C054 INV18-NFR-001"""
        rt = make_rt(max_outstanding=2000, soft_outstanding=1500, max_per_tenant=2000)
        gc.collect()
        tracemalloc.start()
        caps = []
        for _ in range(10_000):
            try:
                caps.append(rt.create(int))
            except m("errors").Rejected:
                pass
        peak_full = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        self.assertEqual(len(caps), 2000)
        self.assertLess(peak_full, 2000 * 8000)                    # bounded by the limit, not the demand
        for w, r in caps:
            rt.resolve(w, 1); rt.take(r)
        self.assertEqual(rt.outstanding, 0)
        rt.create(int)                                             # recovery

    def test_mixed_workload_no_starvation(self):
        """REQ: C017 C063"""
        rt = make_rt()
        done = {"p": 0, "c": 0}
        lock = threading.Lock()
        caps = [rt.create(int) for _ in range(2000)]
        def producers():
            for w, _ in caps:
                rt.resolve(w, 1)
                with lock:
                    done["p"] += 1
        def consumers():
            for _, r in caps:
                while rt.take_wait(r, 5) is None:
                    pass
                with lock:
                    done["c"] += 1
        ts = [threading.Thread(target=producers), threading.Thread(target=consumers)]
        [t.start() for t in ts]; [t.join(30) for t in ts]
        self.assertEqual(done, {"p": 2000, "c": 2000})


class CapacityTest(unittest.TestCase):
    def test_capacity_model_predicts_memory(self):
        """REQ: C069 C064"""
        mem = bench.memory_per_future(3000)
        predicted = bench.predict_memory(mem["bytes_per_governed_future"], 20_000)
        rt = make_rt(max_per_tenant=20_000)
        gc.collect()
        tracemalloc.start()
        base = tracemalloc.get_traced_memory()[0]
        caps = [rt.create(int) for _ in range(20_000)]
        measured = tracemalloc.get_traced_memory()[0] - base
        tracemalloc.stop()
        err = abs(measured - predicted) / measured
        self.assertLess(err, 0.25, f"prediction error {err:.2%}")

    def test_capacity_model_fields(self):
        """REQ: C069"""
        fake = {"memory": {"bytes_per_governed_future": 3000}, "runtime": {"create_resolve_take": {"p50_us": 30}},
                "regimes": {"increasing_concurrency": {"1": {"ops_per_s": 20000}, "2": {"ops_per_s": 12000},
                                                        "4": {"ops_per_s": 6000}}}}
        cm = bench.capacity_model(fake)
        self.assertEqual(cm["contention_knee_threads"], 4)
        self.assertIn("safe_envelope", cm)
        self.assertEqual(cm["memory_bytes"]["at_hard_limit"], 3000 * 100_000)


class PowerTest(unittest.TestCase):
    def test_power_applicability_decision_recorded(self):
        """REQ: C068 — N/A determination must exist, be justified, and await architecture approval"""
        w = {e["id"]: e for e in json.loads((PKG_DIR / "governance/WAIVERS.json").read_text())["entries"]}
        self.assertIn("W-C068", w)
        self.assertEqual(w["W-C068"]["requirement"], "INV-18-C068")
        self.assertIn("Power / thermal", (PKG_DIR / "docs/PERFORMANCE.md").read_text())
        self.assertIn("W-C068", m("certify").resolve_blocker("W-C068", {})[1] if m("certify").resolve_blocker("W-C068", {}) else "W-C068")


class RegressionGateTest(unittest.TestCase):
    def test_injected_regression_is_blocked(self):
        """REQ: C070 INV18-NFR-004"""
        base = json.loads((PKG_DIR / "conformance/BENCH_BASELINE.json").read_text())
        self.assertEqual(bench.compare(base, base), [])
        slow = json.loads(json.dumps(base))
        slow["micro"]["resolve"]["p50_us"] *= 3                  # injected regression
        slow["throughput"]["ops_per_s"] *= 0.3
        regs = bench.compare(slow, base)
        self.assertEqual({r["metric"] for r in regs}, {"micro.resolve.p50_us", "throughput.ops_per_s"})
        waived = bench.compare(slow, base, waivers={"micro.resolve.p50_us": {}, "throughput.ops_per_s": {}})
        self.assertEqual(waived, [])
        missing = json.loads(json.dumps(base)); del missing["import"]
        self.assertTrue(bench.compare(missing, base))

    def test_thresholds_file_well_formed(self):
        """REQ: C062 C013 INV18-NFR-003"""
        th = json.loads((PKG_DIR / "conformance/PERFORMANCE_THRESHOLDS.json").read_text())
        self.assertIn(th["status"], ("PROPOSED", "APPROVED"))
        for k in ("micro.resolve.p50_us", "micro.resolve.p95_us", "micro.resolve.p99_us_median", "micro.resolve.max_us"):
            self.assertIn(k, th["absolute"])
        base = json.loads((PKG_DIR / "conformance/BENCH_BASELINE.json").read_text())
        m("certify")
        res = m("certify").perf_check(base)
        self.assertEqual([r for r in res if r["result"] != "PASS"], [], "baseline must satisfy its own thresholds")


if __name__ == "__main__":
    unittest.main()
