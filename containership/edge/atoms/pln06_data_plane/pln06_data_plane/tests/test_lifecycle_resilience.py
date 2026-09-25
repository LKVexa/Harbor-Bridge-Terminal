"""WP #6 #7 #9 #10 #13 #16 #17 #25 #26 #28 #49 - lifecycle, resilience, fairness, precedence, config."""
from __future__ import annotations

import json
import pathlib
import random
import tempfile
import threading
import unittest

from _support import Env  # noqa: F401
from pln06_data_plane import config as cfgmod
from pln06_data_plane import lifecycle as lc
from pln06_data_plane import precedence as pr
from pln06_data_plane import resilience as rs
from pln06_data_plane.data_plane import Backpressure, InvalidRequest
from pln06_data_plane.scheduling import FairScheduler


def tmp():
    return pathlib.Path(tempfile.mkdtemp())


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class JournalTest(unittest.TestCase):
    def test_transitions_replay_and_illegal_moves(self):
        d = tmp()
        j = lc.TransferJournal(d / "j.jsonl")
        j.transition("a", "admitted")
        j.transition("a", "in_flight")
        j.transition("b", "admitted")
        j.transition("a", "completed")
        j.transition("a", "completed")  # idempotent duplicate terminal
        for bad in (("a", "in_flight"), ("c", "completed"), ("b", "completed"), ("b", "nonsense")):
            with self.assertRaises(lc.LifecycleError):
                j.transition(*bad)
        j2 = lc.TransferJournal(d / "j.jsonl")          # restart
        self.assertEqual(set(j2.open_transfers()), {"b"})
        self.assertEqual(j2.state["a"]["history"], ["admitted", "in_flight", "completed"])

    def test_torn_tail_tolerated_but_mid_corruption_rejected(self):
        d = tmp()
        j = lc.TransferJournal(d / "j.jsonl")
        j.transition("a", "admitted")
        with open(d / "j.jsonl", "a") as fh:
            fh.write('{"transfer_id": "b", "sta')
        self.assertEqual(lc.TransferJournal(d / "j.jsonl").replayed, 1)
        with open(d / "j.jsonl", "a") as fh:
            fh.write('\n{"transfer_id":"c","state":"admitted","ts":0}\n')
        with self.assertRaises(lc.LifecycleError):
            lc.TransferJournal(d / "j.jsonl")

    def test_fencing_blocks_stale_controller_split_brain(self):
        d = tmp()
        clk = Clock()
        lease = lc.FencingLease(d / "lease.json", ttl=10, clock=clk)
        a = lc.TransferJournal(d / "j.jsonl", lease=lease, holder="A", clock=clk)
        a.transition("x", "admitted")
        with self.assertRaises(lc.StaleController):
            lc.TransferJournal(d / "j.jsonl", lease=lease, holder="B", clock=clk)  # lease held
        clk.t = 11                                                                  # A partitioned, lease lapses
        b = lc.TransferJournal(d / "j.jsonl", lease=lease, holder="B", clock=clk)
        self.assertGreater(b.epoch, a.epoch)
        with self.assertRaises(lc.StaleController):
            a.transition("x", "in_flight")                                          # stale A fenced out
        b.transition("x", "in_flight")

    def test_backup_restore_and_checksum(self):
        d = tmp()
        j = lc.TransferJournal(d / "j.jsonl")
        j.transition("a", "admitted")
        meta = j.backup(d / "b.jsonl")
        r = lc.TransferJournal.restore(d / "b.jsonl", d / "r.jsonl", expected_sha256=meta["sha256"])
        self.assertIn("a", r.open_transfers())
        with self.assertRaises(lc.LifecycleError):
            lc.TransferJournal.restore(d / "b.jsonl", d / "r2.jsonl", expected_sha256="0" * 64)

    def test_outcome_semantics_cover_every_terminal_state(self):
        self.assertTrue(lc.TERMINAL <= set(lc.OUTCOMES))
        self.assertIn("key_service_down", lc.DEGRADED_MODES)


class RetryTest(unittest.TestCase):
    def test_bounded_retries_backoff_and_classification(self):
        calls, sleeps = [], []
        err = Backpressure("busy")

        def f(_dl):
            calls.append(1)
            raise err
        pol = rs.RetryPolicy(max_attempts=4, base_delay=0.1, max_delay=0.3)
        with self.assertRaises(rs.RetryExhausted):
            rs.call_with_retry(f, pol, rng=random.Random(1), sleep=sleeps.append)
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(sleeps), 3)
        self.assertTrue(all(0 <= s <= 0.3 for s in sleeps))
        calls.clear()
        with self.assertRaises(InvalidRequest):
            rs.call_with_retry(lambda _: (calls.append(1), (_ for _ in ()).throw(InvalidRequest("x")))[1], pol,
                               sleep=lambda s: None)
        self.assertEqual(len(calls), 1)  # terminal errors never retried
        for bad in ({"max_attempts": 0}, {"max_attempts": 11}, {"base_delay": -1}, {"deadline_s": 0}):
            with self.assertRaises(ValueError):
                rs.RetryPolicy(**bad)

    def test_cancellation_propagates(self):
        ev = threading.Event()
        ev.set()
        with self.assertRaises(rs.RetryExhausted):
            rs.call_with_retry(lambda d: 1, rs.RetryPolicy(), cancel=ev)

    def test_deadline_bounds_total_time(self):
        clk = Clock()

        def f(_dl):
            clk.t += 20
            raise Backpressure("slow")
        with self.assertRaises(rs.RetryExhausted):
            rs.call_with_retry(f, rs.RetryPolicy(max_attempts=10, deadline_s=30), clock=clk, sleep=lambda s: None)
        self.assertLessEqual(clk.t, 40)

    def test_circuit_breaker(self):
        clk = Clock()
        cb = rs.CircuitBreaker(threshold=2, cooldown=5, clock=clk)
        cb.failure()
        cb.failure()
        with self.assertRaises(rs.CircuitOpen):
            cb.before()
        clk.t = 6
        self.assertEqual(cb.state, "half_open")
        cb.success()
        self.assertEqual(cb.state, "closed")


class FailoverAndStallTest(unittest.TestCase):
    def test_failover_never_weakens_residency_or_isolation(self):
        pol = {"eu1": frozenset({"pii"}), "eu2": frozenset({"pii"}), "us": frozenset({"public"}),
               "eu3": frozenset({"pii"})}
        fc = rs.FailoverController(lambda: pol, {"eu1": "dedicated", "eu2": "shared", "eu3": "dedicated"},
                                   health=lambda s: s != "down", quarantined=lambda: {"eu4"})
        out = fc.choose(classification="pii", original="eu1", candidates=["us", "eu2", "eu3"])
        self.assertEqual(out["destination"], "eu3")
        self.assertEqual([r[1] for r in out["rejected"]], ["residency", "weaker_isolation"])
        with self.assertRaises(rs.FailoverRefused):
            fc.choose(classification="pii", original="eu1", candidates=["us", "eu2"])

    def test_stall_detector(self):
        clk = Clock()
        sd = rs.StallDetector(5, clock=clk)
        sd.progress("a")
        sd.progress("b")
        clk.t = 3
        sd.progress("b")
        clk.t = 6
        self.assertEqual(sd.stalled(), ["a"])
        self.assertIn("network_partition", rs.FAILURE_MODEL)

    def test_fault_injector_is_deterministic(self):
        runs = []
        for _ in range(2):
            fi = rs.FaultInjector(seed=42)
            fi.rate("send", 0.3, lambda: Backpressure("x"))
            hits = 0
            for _ in range(100):
                try:
                    fi.hit("send")
                except Backpressure:
                    hits += 1
            runs.append(hits)
        self.assertEqual(runs[0], runs[1])


class FairnessTest(unittest.TestCase):
    def test_drr_weights_bounds_and_no_starvation(self):
        s = FairScheduler(quantum=10, weights={"heavy": 3}, max_queue=1000, max_per_tenant=500)
        for _ in range(300):
            s.enqueue("heavy", 10)
        for _ in range(100):
            s.enqueue("light", 10)
        order = [s.dequeue().tenant for _ in range(200)]
        self.assertAlmostEqual(order.count("heavy") / order.count("light"), 3, delta=0.2)
        gaps = [i for i, t in enumerate(order) if t == "light"]
        self.assertLessEqual(max(b - a for a, b in zip(gaps, gaps[1:])), 4)  # starvation bound
        g = FairScheduler(max_queue=1)
        g.enqueue("a", 1)
        with self.assertRaises(Backpressure):
            g.enqueue("b", 1)
        f = FairScheduler(max_queue=5, max_per_tenant=1)
        f.enqueue("a", 1)
        with self.assertRaises(Backpressure):
            f.enqueue("a", 1)

    def test_large_cost_eventually_served(self):
        s = FairScheduler(quantum=1)
        s.enqueue("big", 50)
        s.enqueue("small", 1)
        got = {s.dequeue().tenant, s.dequeue().tenant}
        self.assertEqual(got, {"big", "small"})
        self.assertIsNone(s.dequeue())


class PrecedenceTest(unittest.TestCase):
    def test_higher_rank_wins_and_soft_constraints_only_rank(self):
        v = pr.evaluate({"security": lambda: (False, "frozen"), "residency": lambda: (False, "x"),
                         "cost": lambda: (False, "expensive")})
        self.assertEqual(v.decided_by, "security")
        v = pr.evaluate({"residency": lambda: (True, ""), "cost": lambda: (False, "expensive")},
                        candidates=["a", "b"], preferences={"cost": lambda c: {"a": 2, "b": 1}[c],
                                                            "locality": lambda c: {"a": 1, "b": 2}[c]})
        self.assertTrue(v.allowed)
        self.assertEqual(v.ranked, ("b", "a"))  # cost outranks locality
        with self.assertRaises(ValueError):
            pr.evaluate({"secruity": lambda: (True, "")})
        order = [pr.evaluate({n: (lambda: (False, "")) for n in pr.PRECEDENCE[i:5]}).decided_by for i in range(5)]
        self.assertEqual(order, list(pr.PRECEDENCE[:5]))


class ConfigTest(unittest.TestCase):
    def test_overlays_validation_and_security_floor(self):
        c = cfgmod.load({"residency": {"eu": ["pii"]}}, [{"context": "far_edge", "inflight_limit": 8}])
        self.assertEqual((c["context"], c["inflight_limit"], c["require_authentication"]), ("far_edge", 8, True))
        for bad in ({"require_authentication": False}, {"context": "mars"}, {"inflight_limit": True},
                    {"per_tenant_inflight_limit": 99}, {"typo": 1}, {"residency": {"eu": "pii"}}):
            with self.assertRaises(InvalidRequest):
                cfgmod.load(bad)
        self.assertFalse(cfgmod.load({"require_authentication": False}, environment="dev")["require_authentication"])
        for ctx in cfgmod.DEPLOYMENT_CONTEXTS.values():
            self.assertIn("offline_ok", ctx)

    def test_history_canary_rollback_emergency(self):
        d = tmp()
        applied = []
        cc = cfgmod.ConfigController(d / "h.jsonl", applied.append)
        c1 = cfgmod.load({"residency": {"eu": ["pii"]}})
        c2 = cfgmod.load({"residency": {"eu": ["pii", "public"]}})
        with self.assertRaises(InvalidRequest):
            cc.propose(c1, revision="r1", author="a", approver="a")    # no self-approval
        cc.propose(c1, revision="r1", author="a", approver="b")
        with self.assertRaises(InvalidRequest):
            cc.propose(c2, revision="r2", author="a", approver="b", canary=applied.append, probe=lambda: False)
        self.assertEqual(applied[-1], c1)                               # canary rolled back
        cc.propose(c2, revision="r3", author="a", approver="b", canary=lambda c: None)  # failed revisions are never reused
        cc.rollback(author="oncall")
        self.assertEqual(applied[-1], c1)
        cc.emergency_disable(author="oncall", reason="incident")
        hist = [json.loads(x)["status"] for x in (d / "h.jsonl").read_text().splitlines()]
        self.assertEqual(hist, ["active", "canary_failed", "active", "rolled_back_to", "emergency_disable"])
        self.assertEqual(cfgmod.ConfigController(d / "h.jsonl", applied.append).active["revision"], "r1")


if __name__ == "__main__":
    unittest.main()
