"""GAP-008/009 admission, retry, breaker; GAP-011 lifecycle; GAP-012/013 config; GAP-031 quarantine."""
import json, threading, time, unittest
from _support import (E, AdmissionController, ChainConfig, CircuitBreaker, RetryPolicy, build, ctx,
                      prod_config, peer_pair)
from inv21_local_service_chaining.config import ConfigStore
from inv21_local_service_chaining.lifecycle import Lifecycle


class AdmissionTest(unittest.TestCase):
    def test_global_and_tenant_caps_shed_without_queueing(self):
        a = AdmissionController(max_in_flight=2, max_in_flight_per_tenant=1)
        with a.admit("t1"):
            with self.assertRaises(E.Overloaded) as cm:
                with a.admit("t1"):
                    pass
            self.assertEqual(cm.exception.details["reason"], "tenant_concurrency")
            with a.admit("t2"):
                with self.assertRaises(E.Overloaded):
                    with a.admit("t3"):
                        pass
        self.assertEqual(a.snapshot()["in_flight"], 0)
        self.assertEqual(a.shed, 2)

    def test_rate_limit_and_tenant_table_bounded(self):
        a = AdmissionController(tenant_rate=0.001, tenant_burst=1, max_tenants=3)
        with a.admit("x"):
            pass
        with self.assertRaises(E.Overloaded):
            with a.admit("x"):
                pass
        for i in range(10):
            with a.admit(f"t{i}"):
                pass
        self.assertLessEqual(len(a._buckets), 3)

    def test_nested_hops_are_not_shed(self):
        ch, res, prov, v = build(grants=[("acme", "a", "invoke"), ("acme", "b", "invoke")],
                                 cfg=prod_config(max_in_flight=1, max_in_flight_per_tenant=1))
        res.place("b", "acme", lambda hop, r: "b", abi="hop")
        res.place("a", "acme", lambda hop, r: hop.call("b", r), abi="hop")
        self.assertEqual(ch.invoke("a", {}, ctx(v)), "b")

    def test_breaker_opens_half_opens_closes(self):
        b = CircuitBreaker(failure_threshold=2, reset_after_s=0.05)
        b.failure("x"); b.before("x"); b.failure("x")
        with self.assertRaises(E.CircuitOpen):
            b.before("x")
        time.sleep(0.06)
        self.assertEqual(b.state("x"), "half_open")
        b.before("x")
        with self.assertRaises(E.CircuitOpen):
            b.before("x")  # only one probe
        b.success("x"); self.assertEqual(b.state("x"), "closed")

    def test_retry_only_when_safe_and_within_deadline(self):
        r = RetryPolicy(max_attempts=3, base_backoff_s=0.001, max_backoff_s=0.002)
        t = E.TransportUnavailable("x")
        self.assertIsNotNone(r.should_retry(t, 1, "get", None, None))
        self.assertIsNone(r.should_retry(t, 1, "invoke", None, None))       # not idempotent
        self.assertIsNotNone(r.should_retry(t, 1, "invoke", "idem-1", None))
        self.assertIsNone(r.should_retry(t, 3, "get", None, None))          # attempts exhausted
        self.assertIsNone(r.should_retry(E.CapabilityRefused("x"), 1, "get", None, None))
        self.assertIsNone(r.should_retry(t, 1, "get", None, 0.0000001))     # past deadline
        with self.assertRaises(ValueError):
            RetryPolicy(max_attempts=50)

    def test_remote_retry_with_idempotency_key(self):
        a, b, lt, v, ra, rb = peer_pair([("acme", "svc", "get"), ("acme", "svc", "invoke")], [("acme", "svc", "get"), ("acme", "svc", "invoke")],
                                        {"svc": ("acme", lambda hop, r: "ok")})
        a.retry = RetryPolicy(max_attempts=3, base_backoff_s=0.001, max_backoff_s=0.001)
        lt.fail_next = ConnectionError("blip")
        from dataclasses import replace
        self.assertEqual(a.invoke("svc", {}, replace(ctx(v), operation="get")), "ok")
        self.assertEqual(lt.sent, 2)
        lt.fail_next = ConnectionError("blip")
        with self.assertRaises(E.TransportUnavailable):
            a.invoke("svc", {}, ctx(v))  # "invoke" without key: never retried


class LifecycleConfigTest(unittest.TestCase):
    def test_transition_table(self):
        lc = Lifecycle()
        with self.assertRaises(E.NotReady):
            lc.require_serving()
        lc.transition("ready", reason="boot")
        with self.assertRaises(E.ValidationFailed):
            lc.transition("initializing", reason="x")
        lc.transition("quarantined", reason="incident", actor="oncall")
        with self.assertRaises(E.Quarantined):
            lc.require_serving()
        lc.transition("stopped", reason="shutdown")
        for s in ("ready", "degraded", "quarantined"):
            with self.assertRaises(E.ValidationFailed):
                lc.transition(s, reason="x")

    def test_emergency_disable_blocks_all_calls_and_is_audited(self):
        ch, res, prov, v = build(grants=[("acme", "svc", "invoke")])
        res.place("svc", "acme", lambda hop, r: "ok", abi="hop")
        ch.quarantine(reason="INC-1", actor="oncall")
        with self.assertRaises(E.Quarantined):
            ch.invoke("svc", {}, ctx(v))
        self.assertFalse(ch.health()["ready"])
        ch.release(reason="INC-1 resolved", actor="oncall")
        self.assertEqual(ch.invoke("svc", {}, ctx(v)), "ok")
        kinds = [r["kind"] for r in ch.audit.records()]
        self.assertIn("quarantine", kinds); self.assertIn("release", kinds)

    def test_stalled_handler_is_suppressed(self):
        ch, res, prov, v = build(grants=[("acme", "slow", "invoke")], cfg=prod_config(handler_stall_s=0.01))
        res.place("slow", "acme", lambda hop, r: time.sleep(0.03) or "late", abi="hop")
        self.assertEqual(ch.invoke("slow", {}, ctx(v)), "late")
        self.assertFalse(res.inspect("slow").healthy)
        with self.assertRaises(E.TransportUnavailable):
            ch.invoke("slow", {}, ctx(v))  # no longer served locally

    def test_config_schema_overrides_and_rejections(self):
        doc = {"schema": "PK_CHAIN_CONFIG/1", "max_depth": 6,
               "overrides": {"environment": {"prod": {"mode": "production", "max_depth": 3}},
                             "site": {"eu-1": {"max_in_flight": 10, "max_in_flight_per_tenant": 5}}}}
        self.assertEqual(ChainConfig.from_mapping(doc).max_depth, 6)
        c = ChainConfig.from_mapping(doc, environment="prod", site="eu-1")
        self.assertEqual((c.mode, c.max_depth, c.max_in_flight), ("production", 3, 10))
        for bad in ({"schema": "PK_CHAIN_CONFIG/1", "max_depth": 0},
                    {"schema": "PK_CHAIN_CONFIG/2"}, {"max_depth": 3},
                    {"schema": "PK_CHAIN_CONFIG/1", "overrides": {"site": {"x": {"max_depth": 999}}}},
                    {"schema": "PK_CHAIN_CONFIG/1", "max_in_flight": 5, "max_in_flight_per_tenant": 6}):
            with self.assertRaises(E.ValidationFailed):
                ChainConfig.from_mapping(bad, site="x")

    def test_atomic_activation_provenance_and_rollback(self):
        ch, res, prov, v = build()
        store = ConfigStore(ch.config)
        ch.bind(store)
        seen = []
        store.on_activate(lambda cfg: seen.append(cfg.max_depth))
        r2 = store.activate(prod_config(max_depth=7), author="alice", source="git:abc123")
        self.assertEqual((r2.revision, r2.author, ch.max_depth), (2, "alice", 7))
        self.assertEqual(len(r2.digest), 64)
        self.assertEqual(ch.config_revision, 2)
        self.assertEqual([r for r in ch.audit.records() if r["kind"] == "config_activated"][-1]["source"], "git:abc123")
        def bad(cfg):
            if cfg.max_depth == 9:
                raise RuntimeError("downstream refused")
        store.on_activate(bad)
        with self.assertRaises(E.ValidationFailed):
            store.activate(prod_config(max_depth=9), author="bob", source="manual")
        self.assertEqual((store.current.revision, ch.max_depth), (2, 7))  # rolled back
        rb = store.rollback(author="alice")
        self.assertEqual((rb.config.max_depth, ch.max_depth), (4, 4))
        with self.assertRaises(E.ValidationFailed):
            store.activate(prod_config(), author="", source="x")

    def test_production_config_cannot_activate_on_dev_wiring(self):
        from inv21_local_service_chaining.chain import Chainer
        from inv21_local_service_chaining.residency import Residency
        dev = Chainer(Residency("h"))
        with self.assertRaises(E.ValidationFailed):
            dev.apply_config(prod_config())


if __name__ == "__main__":
    unittest.main()
