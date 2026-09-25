"""Retry, admission, breakers, fencing, declarative config, activation, rollback, lifecycle."""
import random
import threading
import unittest

from _support import FakeClock, env
from inv52_messaging_abstraction import config as cfgm
from inv52_messaging_abstraction import lifecycle as lc
from inv52_messaging_abstraction import resilience as res
from inv52_messaging_abstraction import runtime as rt
from inv52_messaging_abstraction.adapters import BrokerRejected, BrokerUnavailable


class RetryTest(unittest.TestCase):
    def test_retries_retryable_idempotent_then_succeeds(self):
        calls, sleeps = [], []

        def op():
            calls.append(1)
            if len(calls) < 3:
                raise BrokerUnavailable("down")
            return "ok"
        out = res.RetryPolicy(max_attempts=4).run(op, idempotent=True, sleep=sleeps.append, rng=random.Random(1))
        self.assertEqual(out, "ok")
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(0 <= s <= 2.0 for s in sleeps))

    def test_never_retries_non_idempotent_or_terminal(self):
        for idem, exc in ((False, BrokerUnavailable("x")), (True, BrokerRejected("x"))):
            calls = []

            def op(exc=exc):
                calls.append(1)
                raise exc
            with self.assertRaises(type(exc)):
                res.RetryPolicy().run(op, idempotent=idem, sleep=lambda s: None)
            self.assertEqual(len(calls), 1)

    def test_bounded_attempts_and_jitter_cap(self):
        p = res.RetryPolicy(max_attempts=3, base_delay=0.1, max_delay=0.3)
        rng = random.Random(0)
        self.assertTrue(all(p.delay(a, rng) <= 0.3 for a in range(1, 10)))
        calls = []
        with self.assertRaises(BrokerUnavailable):
            p.run(lambda: calls.append(1) or (_ for _ in ()).throw(BrokerUnavailable("x")), idempotent=True,
                  sleep=lambda s: None)
        self.assertEqual(len(calls), 3)
        with self.assertRaises(ValueError):
            res.RetryPolicy(max_attempts=0)

    def test_deadline_and_cancellation(self):
        clock = FakeClock()
        ctx = res.CallContext.with_timeout(1, clock=clock)
        clock.advance(2)
        with self.assertRaises(res.DeadlineExceeded):
            ctx.check()
        ctx2 = res.CallContext.with_timeout(5, clock=clock)
        ctx2.cancel()
        with self.assertRaises(res.Cancelled):
            res.RetryPolicy().run(lambda: 1, idempotent=True, ctx=ctx2)
        ctx3 = res.CallContext.with_timeout(0.01, clock=clock)
        with self.assertRaises(res.DeadlineExceeded):  # backoff would exceed deadline
            res.RetryPolicy(base_delay=1, max_delay=1).run(
                lambda: (_ for _ in ()).throw(BrokerUnavailable("x")), idempotent=True, ctx=ctx3,
                sleep=lambda s: None, rng=random.Random(3))


class AdmissionTest(unittest.TestCase):
    def test_per_app_fairness(self):
        clock = FakeClock()
        q = res.QuotaAdmission(per_app_rate=1, per_app_burst=3, clock=clock)
        b = rt.PubSub(admission=q)
        b.allow("t", "noisy", "quiet")
        for _ in range(3):
            b.publish("noisy", "t", env("noisy"))
        with self.assertRaises(rt.Overloaded) as ctx:
            b.publish("noisy", "t", env("noisy"))
        self.assertTrue(ctx.exception.retryable)
        b.publish("quiet", "t", env("quiet"))  # unaffected by the noisy neighbour
        clock.advance(1)
        b.publish("noisy", "t", env("noisy"))  # refilled
        self.assertEqual(q.shed, {"noisy": 1})

    def test_key_table_bounded(self):
        q = res.QuotaAdmission(max_keys=2)
        q("a", "t")
        q("b", "t")
        with self.assertRaises(rt.Overloaded):
            q("c", "t")


class BreakerFencingTest(unittest.TestCase):
    def test_guarded_sink_opens_and_half_opens(self):
        clock = FakeClock()
        br = res.CircuitBreaker(failure_threshold=2, reset_after=10, clock=clock)

        class Flaky:
            fail = True
            got = []

            def append(self, m):
                if self.fail:
                    raise ConnectionError
                self.got.append(m)
        f = Flaky()
        b = rt.PubSub()
        b.allow("t", "a")
        b.subscribe("t", lambda m: True, res.GuardedSink(f, br))
        for _ in range(3):
            b.publish("a", "t", env())
        self.assertEqual(br.state, "open")
        self.assertEqual(b.dead_letter[-1]["errors"][0]["code"], "PK_MSG_CIRCUIT_OPEN")
        clock.advance(11)
        f.fail = False
        self.assertEqual(br.state, "half_open")
        self.assertEqual(b.publish("a", "t", env()), 1)
        self.assertEqual(br.state, "closed")

    def test_fencing_refuses_stale_owner(self):
        clock = FakeClock()
        fo = res.FencedOwnership(lease_s=10, clock=clock)
        t1 = fo.acquire("sub:orders", "ctrl-a")
        with self.assertRaises(res.StaleOwner):
            fo.acquire("sub:orders", "ctrl-b")
        clock.advance(11)
        t2 = fo.acquire("sub:orders", "ctrl-b")  # a's lease expired (split-brain window closed)
        self.assertGreater(t2, t1)
        with self.assertRaises(res.StaleOwner):
            fo.check("sub:orders", t1)  # stale controller cannot act
        fo.check("sub:orders", t2)


BASE = {"metadata": {"name": "inv52", "version": "1", "author": "ops"},
        "topics": [{"name": "orders", "publishers": ["shop"]}]}


class ConfigTest(unittest.TestCase):
    def test_defaults_are_secure_and_valid(self):
        cfg = cfgm.layered()
        self.assertEqual(cfgm.validate(cfg), [])
        self.assertEqual(cfg["topics"], [])  # nobody may publish by default
        self.assertEqual(cfg["predicate_view"], "frozen")
        self.assertGreater(cfg["limits"]["dedup_window"], 0)

    def test_overlays_replace_lists_and_merge_maps(self):
        site = {"limits": {"max_payload_bytes": 4096}, "topics": [{"name": "orders", "publishers": ["edge-shop"]}]}
        cfg = cfgm.layered(BASE, {"metadata": {"version": "2"}}, site)
        self.assertEqual(cfg["limits"]["max_payload_bytes"], 4096)
        self.assertEqual(cfg["limits"]["max_dead_letters"], 10_000)
        self.assertEqual(cfg["topics"][0]["publishers"], ["edge-shop"])
        self.assertEqual(cfg["metadata"], {"name": "inv52", "version": "2", "author": "ops"})

    def test_validation_catches_every_class(self):
        bad = cfgm.layered(BASE, {"limits": {"max_payload_bytes": 1, "bogus": 1}, "predicate_view": "x",
                                  "topics": [{"name": "t", "publishers": ["*"]}, {"name": "t"}],
                                  "telemetry": {"sample_rate": 2}, "extra": 1,
                                  "admission": {"per_app_rate": 0, "per_app_burst": 1}})
        bad["metadata"]["password"] = "hunter2"
        probs = " | ".join(cfgm.validate(bad))
        for needle in ("max_payload_bytes", "unknown limit bogus", "predicate_view", "wildcard", "duplicate topic",
                       "sample_rate", "unknown top-level", "secret material", "per_app_rate"):
            self.assertIn(needle, probs)
        self.assertEqual(cfgm.validate("nope"), ["config must be an object"])

    def test_activation_is_atomic_and_invalid_keeps_previous(self):
        m = cfgm.ConfigManager()
        m.activate(BASE, author="alice", change_ref="CHG-1")
        bus1 = m.bus
        with self.assertRaises(cfgm.ConfigInvalid):
            m.activate(BASE, {"topics": [{"name": "x", "publishers": ["*"]}]}, author="bob")
        self.assertIs(m.bus, bus1)
        self.assertEqual(len(m.generations), 1)

    def test_provenance_recorded(self):
        m = cfgm.ConfigManager()
        p = m.activate(BASE, author="alice", change_ref="CHG-7", layer_names=["base"])
        self.assertEqual((p["author"], p["version"], p["change_ref"], p["layers"]), ("alice", "1", "CHG-7", ["base"]))
        self.assertEqual(len(p["digest"]), 64)
        self.assertIn("T", p["activated_at"])
        with self.assertRaises(rt.InvalidArgument):
            m.activate(BASE, author=" ")

    def test_subscriptions_survive_activation_and_rollback(self):
        m = cfgm.ConfigManager()
        m.activate(BASE, author="a")
        sink = []
        m.bus.subscribe("orders", lambda x: True, sink)
        m.activate(BASE, {"topics": [{"name": "orders", "publishers": ["shop", "pos"]}]}, author="a")
        m.bus.publish("pos", "orders", env("pos"))
        p = m.rollback(author="oncall", reason="bad change")
        self.assertIn("rollback", p["change_ref"])
        with self.assertRaises(rt.TopicDenied):
            m.bus.publish("pos", "orders", env("pos"))
        m.bus.publish("shop", "orders", env("shop"))
        self.assertEqual(len(sink), 2)

    def test_automatic_rollback_on_failed_health_check(self):
        m = cfgm.ConfigManager(health_check=lambda b: "orders" in b.publishers)
        m.activate(BASE, author="a")
        good = m.bus
        with self.assertRaises(cfgm.ConfigInvalid):
            m.activate(BASE, {"topics": []}, author="a")
        self.assertIs(m.bus, good)

    def test_rollback_without_history(self):
        with self.assertRaises(cfgm.ConfigRollbackUnavailable):
            cfgm.ConfigManager().rollback(author="x", reason="y")

    def test_no_partial_state_visible_during_activation(self):
        m = cfgm.ConfigManager()
        m.activate(BASE, author="a")
        stop = threading.Event()
        seen_bad = []

        def reader():
            while not stop.is_set():
                b = m.bus
                if "orders" not in b.publishers:
                    seen_bad.append(1)
        t = threading.Thread(target=reader)
        t.start()
        for i in range(50):
            m.activate(BASE, {"metadata": {"version": str(i)}}, author="a")
        stop.set()
        t.join()
        self.assertEqual(seen_bad, [])


class LifecycleTest(unittest.TestCase):
    def test_legal_and_illegal_transitions(self):
        life = lc.Lifecycle()
        with self.assertRaises(rt.InvalidTransition):
            life.to(lc.READY, actor="x", reason="skip")
        for s in (lc.CONFIGURED, lc.READY, lc.DEGRADED, lc.READY, lc.DRAINING, lc.STOPPED):
            life.to(s, actor="op", reason="t")
        with self.assertRaises(rt.InvalidTransition):
            life.to(lc.READY, actor="op", reason="dead")
        self.assertEqual(len(life.history), 6)

    def test_bootstrap_to_ready_and_emergency_disable(self):
        mb, rep = lc.bootstrap([BASE], author="alice")
        self.assertEqual(rep["state"], lc.READY)
        mb.bus.subscribe("orders", lambda m: True, [])
        self.assertEqual(mb.publish("shop", "orders", env("shop")), 1)
        mb.emergency_disable(actor="oncall", reason="incident 42")
        with self.assertRaises(lc.NotServing):
            mb.publish("shop", "orders", env("shop"))
        self.assertEqual(mb.health()["status"], "unhealthy")

    def test_security_dependency_outage_fails_closed_noncritical_degrades(self):
        state = {"idp": True, "telemetry": True}
        deps = {"idp": (lambda: state["idp"], "security"), "telemetry": (lambda: state["telemetry"], "noncritical")}
        mb, rep = lc.bootstrap([BASE], author="a", dependencies=deps)
        mb.bus.subscribe("orders", lambda m: True, [])
        state["telemetry"] = False
        self.assertEqual(mb.publish("shop", "orders", env("shop")), 1)  # degraded mode keeps serving
        state["idp"] = False
        from inv52_messaging_abstraction.security import TrustUnavailable
        with self.assertRaises(TrustUnavailable):
            mb.publish("shop", "orders", env("shop"))
        self.assertEqual(mb.lifecycle.state, lc.DEGRADED)
        self.assertFalse(mb.health()["ready"])
        state["idp"] = True
        mb.publish("shop", "orders", env("shop"))
        self.assertEqual(mb.lifecycle.state, lc.READY)

    def test_bootstrap_refuses_ready_when_critical_dependency_down(self):
        _, rep = lc.bootstrap([BASE], author="a", dependencies={"broker": (lambda: False, "critical")})
        self.assertEqual(rep["state"], lc.CONFIGURED)


if __name__ == "__main__":
    unittest.main()
