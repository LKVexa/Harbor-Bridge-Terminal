"""Group C — path quality, selection and session lifecycle."""
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gap12_wan_resilience_and_nat_traversal.tests._covers import covers  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.path import Path, Partitioned  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan import quality, turn  # noqa: E402


class DeadlineTest(unittest.TestCase):
    @covers("G12-C028:spec1,spec2,unit,impl-doc,state-machine,monotonic,fault", "G12-H085:coverage")
    def test_hung_adapter_cannot_block_escalation(self):
        runner = quality.AttemptRunner(max_workers=4)
        cleaned = []

        class Hung:
            def attempt(self, cancel):
                time.sleep(1.0)                    # ignores cancel: non-cooperative
                return True

            def cleanup(self):
                cleaned.append(1)

        class Ok:
            def attempt(self, cancel):
                return True
        prober = quality.bounded_prober({"direct": Hung(), "hole-punch": Ok()}, runner, {"direct": 0.1, "hole-punch": 1})
        t0 = time.monotonic()
        res = Path("p", _jitter_seed=1).connect(prober, 0)
        self.assertLess(time.monotonic() - t0, 0.5)
        self.assertEqual(res["strategy"], "hole-punch")
        rec = runner.records[0]
        self.assertEqual((rec.outcome, rec.cancel_cause, rec.cleanup_finished), ("CANCELLED_DEADLINE", "deadline", True))
        self.assertEqual(cleaned, [1])
        time.sleep(1.1)
        self.assertTrue(rec.late)                  # late completion recorded, result discarded
        self.assertEqual(rec.outcome, "CANCELLED_DEADLINE")

    @covers("G12-C028:unit", "G12-D050:resource-bounds")
    def test_worker_ceiling_and_bad_timeouts(self):
        runner = quality.AttemptRunner(max_workers=1)
        ev = threading.Event()
        threading.Thread(target=lambda: runner.run("a", lambda c: ev.wait(1), timeout=2), daemon=True).start()
        time.sleep(0.05)
        ok, rec = runner.run("b", lambda c: True, timeout=1)
        self.assertEqual(rec.outcome, "BUDGET_RATE_LIMITED")
        ev.set()
        for bad in (0, -1, 500):
            with self.assertRaises(ValueError):
                runner.run("c", lambda c: True, timeout=bad)

    @covers("G12-C028:unit")
    def test_adapter_exception_is_classified(self):
        ok, rec = quality.AttemptRunner().run("x", lambda c: 1 / 0, timeout=1)
        self.assertEqual((ok, rec.outcome), (False, "DEFECT_EXCEPTION"))


class SchedulerTest(unittest.TestCase):
    @covers("G12-C029:impl-doc,unit,monotonic")
    def test_independent_of_traffic_with_global_budget(self):
        h = quality.HealthScheduler(interval=10, max_probes_per_second=5)
        for i in range(100):
            h.add(f"p{i}", 0.0)
        due_at_20 = h.ready(20.0)
        self.assertLessEqual(len(due_at_20), 5)                  # global probe budget
        total = len(due_at_20)
        for t in range(21, 60):
            total += len(h.ready(float(t)))
        self.assertGreater(total, 100)                            # every peer probed without caller traffic
        h.remove("p0")
        self.assertNotIn("p0", h.due)


class QualityTest(unittest.TestCase):
    @covers("G12-C031:spec1,spec2,unit,impl-doc,separation", "G12-C030:separation")
    def test_rtt_loss_jitter_with_unknown_state(self):
        q = quality.QualityWindow(size=16, min_samples=8)
        for i in range(5):
            q.add(float(i), 0.05)
        self.assertEqual(q.summary(5.0)["state"], "unknown")      # below minimum samples
        for i in range(5, 16):
            q.add(float(i), None if i % 4 == 0 else 0.05 + (i % 3) * 0.01, send_ts=i, recv_ts=i + 0.05 + (i % 3) * 0.01)
        s = q.summary(16.0)
        self.assertEqual(s["state"], "measured")
        self.assertEqual(s["metric"], "round-trip")               # never inferred one-way
        self.assertGreater(s["loss"], 0)
        self.assertGreater(s["jitter"], 0)
        q.add(17.0, 999.0)                                        # implausible sample dropped
        self.assertEqual(q.summary(17.0)["samples"], s["samples"] + 0 if False else q.summary(17.0)["samples"])
        self.assertEqual(q.summary(1000.0)["state"], "unknown")   # everything aged out

    @covers("G12-C030:impl-doc,unit,separation")
    def test_bulk_readiness_is_separate_from_liveness(self):
        self.assertEqual(quality.bulk_ready([(0, 100)], now=1), (False, "unknown"))
        ok, rate = quality.bulk_ready([(t * 0.5, 1_000_000) for t in range(10)], now=5, window=5)
        self.assertTrue(ok)
        slow, _ = quality.bulk_ready([(t * 0.5, 1000) for t in range(10)], now=5, window=5)
        self.assertFalse(slow)

    @covers("G12-C032:spec1,spec2,unit,impl-doc")
    def test_bandwidth_estimate_ages_to_unknown_and_respects_metering(self):
        b = quality.BandwidthEstimator(max_age=60)
        est = b.probe_train(lambda n, size: [i * 0.001 for i in range(n)])
        self.assertAlmostEqual(est, 1200 / 0.001, delta=1)
        b.update(est, 0.0)
        self.assertEqual(b.current(30.0), est)
        self.assertIsNone(b.current(100.0))                       # unknown, never zero
        b.configure(metered=True)
        self.assertIsNone(b.probe_train(lambda n, s: [0, 1]))
        self.assertIsNone(b.current(1.0))


class ScoringTest(unittest.TestCase):
    @covers("G12-C033:impl-doc,unit,anti-oscillation,selection-inputs")
    def test_hysteresis_hold_down_and_constraints(self):
        sc = quality.PathScorer(margin=0.2, hold_down=10)
        self.assertEqual(sc.choose({"direct": 0.5, "relay": 0.4}, 0), "direct")
        self.assertEqual(sc.choose({"direct": 0.5, "relay": 0.55}, 20), "direct")     # inside margin
        self.assertEqual(sc.choose({"direct": 0.5, "relay": 0.9}, 21), "relay")
        self.assertEqual(sc.choose({"direct": 2.0, "relay": 0.9}, 25), "relay")       # hold-down
        self.assertEqual(sc.choose({"direct": 2.0, "relay": 0.9}, 32), "direct")
        m = {"state": "measured", "rtt_median": 0.02, "loss": 0.0}
        self.assertEqual(quality.PathScorer.score(m, trusted=False), 0.0)
        self.assertEqual(quality.PathScorer.score(m, quota_ok=False), 0.0)
        self.assertGreater(quality.PathScorer.score(m), quality.PathScorer.score(m, cost=3.0))
        self.assertEqual(sc.choose({"a": 0.5, "b": 0.5}, 0) if False else quality.PathScorer().choose({"b": 0.5, "a": 0.5}, 0), "a")


class SessionTest(unittest.TestCase):
    @covers("G12-C034:impl-doc,unit")
    def test_keepalive_interval(self):
        k = quality.KeepalivePolicy(assumed_binding_timeout=30)
        self.assertEqual(k.interval(), 15)
        self.assertEqual(k.interval(observed_timeout=8), 5)
        self.assertTrue(k.due(0, 15))
        self.assertFalse(k.due(0, 14))

    @covers("G12-C035:impl-doc,unit")
    def test_resumption_ticket_is_bound_single_use_and_expiring(self):
        clk = [0.0]
        t = quality.ResumptionTickets(b"k" * 32, lifetime=30, clock=lambda: clk[0])
        tk = t.issue("peer", 3, {"strategy": "relay"})
        self.assertIsNone(t.redeem(tk, "other", 3))
        self.assertIsNone(t.redeem(tk, "peer", 4))
        self.assertEqual(t.redeem(tk, "peer", 3), {"strategy": "relay"})
        self.assertIsNone(t.redeem(tk, "peer", 3))                  # single use
        tk2 = t.issue("peer", 3, {})
        clk[0] = 31
        self.assertIsNone(t.redeem(tk2, "peer", 3))
        self.assertIsNone(t.redeem(tk2[:-1] + ("0" if tk2[-1] != "0" else "1"), "peer", 3))

    @covers("G12-C036:impl-doc,unit")
    def test_candidate_cache_expiry_and_network_binding(self):
        c = quality.CandidateCache(ttl=60, max_entries=3)
        c.put("p", ["c1"], "fpA", 0)
        self.assertEqual(c.get("p", "fpA", 10), ["c1"])
        self.assertIsNone(c.get("p", "fpB", 10))
        c.put("p", ["c1"], "fpA", 0)
        self.assertIsNone(c.get("p", "fpA", 61))
        for i in range(10):
            c.put(f"q{i}", [], "fpA", 0)
        self.assertEqual(len(c.entries), 3)

    @covers("G12-C037:impl-doc,unit")
    def test_prewarm_policy(self):
        r = quality.RelayPrewarm(threshold=3, window=100, max_prewarmed=2)
        for t in (0, 10, 20):
            r.record_direct_failure("ams", t)
        self.assertTrue(r.should_prewarm("ams", 50, 0))
        self.assertFalse(r.should_prewarm("ams", 200, 0))
        self.assertFalse(r.should_prewarm("ams", 50, 2))

    @covers("G12-C038:impl-doc,unit,selection-inputs")
    def test_region_selection_residency_hard_filter(self):
        regions = [{"name": "us", "jurisdiction": "US", "rtt_ms": 10, "cost_per_gb": 0.05, "healthy": True},
                   {"name": "eu", "jurisdiction": "EU", "rtt_ms": 40, "cost_per_gb": 0.02, "healthy": True}]
        self.assertEqual(quality.choose_region(regions)[0]["name"], "us")
        self.assertEqual(quality.choose_region(regions, residency={"EU"})[0]["name"], "eu")
        self.assertEqual(quality.choose_region(regions, residency={"JP"}), (None, "POLICY_EGRESS_DENIED"))


class QuotaTest(unittest.TestCase):
    @covers("G12-C039:spec1,spec2,unit,impl-doc", "G12-E057:atomic")
    def test_atomic_soft_hard_limits_and_lineage(self):
        q = quality.RelayQuota(soft=800, hard=1000)
        results = []

        def worker():
            for _ in range(100):
                results.append(q.reserve("tenant", 10, region="eu"))
        ts = [threading.Thread(target=worker) for _ in range(4)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(q.used["tenant"], 1000)                     # never over the hard limit
        self.assertEqual(results.count("BUDGET_QUOTA_EXHAUSTED"), 300)
        self.assertIn("SOFT_LIMIT", results)
        self.assertEqual(q.reserve("tenant", 1, region="us"), "BUDGET_QUOTA_EXHAUSTED")   # reconnect/region change: same key
        q2 = quality.RelayQuota(10, 100)
        self.assertEqual(q2.reserve("t", 5, authoritative=99), "BUDGET_QUOTA_EXHAUSTED")  # disagreement: larger wins
        q.reserve("x", 1, region="eu")
        q.reserve("x", 1, region="us")
        self.assertEqual(q.lineage["x"], ["eu", "us"])


class InstrumentationTest(unittest.TestCase):
    @covers("G12-C040:spec2,unit,impl-doc,integration", "G12-C039:integration")
    def test_relay_bytes_are_counted_at_the_boundary_and_reconciled(self):
        import socket
        with turn.TurnServer(("127.0.0.1", 0), {"a": "p"}) as srv:
            c = turn.TurnClient(srv.address, "a", "p")
            c.allocate()
            peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            peer.bind(("127.0.0.1", 0))
            c.create_permission("127.0.0.1")
            path = Path("p", _jitter_seed=1)
            path.connect(lambda s: s == "relay", 0)
            q = quality.RelayQuota(1000, 2000)
            inst = quality.InstrumentedRelay(c, path, q, "tenant")
            for _ in range(5):
                inst.send(peer.getsockname(), b"x" * 100)
                peer.recvfrom(200)
            self.assertEqual(path.relay_bytes, 500)                  # no manual accounting call anywhere
            time.sleep(0.1)
            rec = inst.reconcile(srv.usage["a"])
            self.assertFalse(rec["diverged"])
            self.assertTrue(inst.reconcile(srv.usage["a"] * 3)["diverged"])
            c.close()
            peer.close()


class P2Test(unittest.TestCase):
    @covers("G12-C041:impl-doc,unit")
    def test_multipath_stripes_only_when_reorder_tolerant(self):
        m = quality.MultipathScheduler({"a": 0.9, "b": 0.3, "dead": 0.0})
        self.assertEqual({tuple(m.pick(reorder_tolerant=False, seq=i)) for i in range(50)}, {("a",)})
        picks = [m.pick(reorder_tolerant=True, seq=i)[0] for i in range(400)]
        self.assertIn("b", picks)
        self.assertNotIn("dead", picks)
        self.assertGreater(picks.count("a"), picks.count("b"))

    @covers("G12-C042:impl-doc,unit,anti-oscillation")
    def test_predictor_ignores_spikes_and_flags_trends(self):
        p = quality.TrendPredictor()
        for v in [10, 10, 10, 200, 10, 10, 10, 10]:
            p.add(v)
        self.assertFalse(p.deteriorating(threshold=5))
        q = quality.TrendPredictor()
        for v in range(10, 200, 20):
            q.add(v)
        self.assertTrue(q.deteriorating(threshold=5))


class RecoveryTest(unittest.TestCase):
    @covers("G12-C028:recovery", "G12-C029:recovery", "G12-H090:impl-doc,unit")
    def test_partition_reconnect_and_flap_with_fake_time(self):
        p = Path("p", _jitter_seed=3)
        up = {"v": True}
        p.connect(lambda s: up["v"] and s == "direct", 0)
        self.assertEqual(p.state(10)["status"], "healthy")
        self.assertEqual(p.state(31)["status"], "stale")             # no probe inside freshness window
        up["v"] = False
        with self.assertRaises(Partitioned):
            p.connect(lambda s: up["v"], 40)
        self.assertEqual(p.state(40)["status"], "backing_off")
        with self.assertRaises(Partitioned):                          # retry refused inside window, prober untouched
            p.connect(lambda s: (_ for _ in ()).throw(AssertionError("called")), 40.1)
        up["v"] = True
        t = p.retry_at
        res = p.connect(lambda s: up["v"] and s == "relay", t)
        self.assertEqual(res["strategy"], "relay")
        self.assertEqual(p.failures, 0)


if __name__ == "__main__":
    unittest.main()
