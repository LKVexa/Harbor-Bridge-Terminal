"""GAP-004 capability provider, GAP-010 residency freshness, GAP-032 reconstruction."""
import time, unittest
from _support import E, Chainer, GuardedProvider, Residency, StaticPolicyProvider, build, ctx, prod_config
from inv21_local_service_chaining.policy import (CAPABILITY_SCHEMA, CapabilityDecision, CapabilityRequest,
                                                 CompatLocalProvider)


def req(**kw):
    base = dict(principal="p", tenant="acme", caller=None, callee="svc", operation="invoke",
                capabilities=frozenset(), topology="local", depth=0, correlation_id="dc-1")
    base.update(kw)
    return CapabilityRequest(**base)


class P:
    authoritative = True
    def __init__(self, fn): self.fn = fn; self.n = 0
    def decide(self, r): self.n += 1; return self.fn(r)


class PolicyTest(unittest.TestCase):
    def test_fail_closed_matrix(self):
        ok = lambda r, **kw: CapabilityDecision(True, 5, "g", r.correlation_id, **kw)
        cases = {
            "timeout": lambda r: (time.sleep(0.2), ok(r))[1],
            "error": lambda r: 1 / 0,
            "malformed": lambda r: {"allow": True},
            "non_bool": lambda r: CapabilityDecision("yes", 5, "g", r.correlation_id),
            "version": lambda r: ok(r, schema="PK_CAPABILITY/2"),
            "correlation": lambda r: CapabilityDecision(True, 5, "g", "dc-other"),
            "stale": lambda r: CapabilityDecision(True, 1, "g", r.correlation_id),
        }
        for why, fn in cases.items():
            g = GuardedProvider(P(fn), timeout_s=0.05, min_policy_revision=3)
            with self.assertRaises(E.ProviderUnavailable, msg=why):
                g.decide(req())
            self.assertEqual(g.stats["failures"], 1)

    def test_outage_refuses_call_before_handler(self):
        ran = []
        ch, res, prov, v = build(provider=P(lambda r: 1 / 0))
        res.place("svc", "acme", lambda hop, r: ran.append(1), abi="hop")
        with self.assertRaises(E.ProviderUnavailable):
            ch.invoke("svc", {}, ctx(v))
        self.assertEqual(ran, [])
        self.assertFalse(ch.health()["dependencies"]["policy"] == "ok")

    def test_cache_bounds_revocation_and_no_negative_cache(self):
        s = StaticPolicyProvider([("acme", "svc", "invoke")])
        inner = P(s.decide)
        g = GuardedProvider(inner, cache_ttl_s=60, cache_max=2)
        g.decide(req()); g.decide(req())
        self.assertEqual(inner.n, 1)
        s.revoke("acme", "svc")
        self.assertTrue(g.decide(req()).allow)  # within TTL: documented revocation latency
        g.invalidate(min_policy_revision=s.revision)
        self.assertFalse(g.decide(req()).allow)
        g.decide(req()); self.assertEqual(inner.n, 3)  # denial not cached
        for i in range(5):
            s.grant("acme", f"c{i}"); g.decide(req(callee=f"c{i}"))
        self.assertLessEqual(len(g._cache), 2)

    def test_cache_key_covers_every_dimension(self):
        a = req(); self.assertNotEqual(a.cache_key(), req(tenant="b").cache_key())
        for kw in ({"principal": "q"}, {"caller": "x"}, {"operation": "get"},
                   {"capabilities": frozenset({"c"})}, {"topology": "remote"}):
            self.assertNotEqual(a.cache_key(), req(**kw).cache_key(), kw)

    def test_required_capabilities_and_revocation_end_to_end(self):
        ch, res, prov, v = build(provider=StaticPolicyProvider([("acme", "svc", "invoke")],
                                                              required={"svc": {"svc.call"}}))
        res.place("svc", "acme", lambda hop, r: "ok", abi="hop")
        with self.assertRaises(E.CapabilityRefused):
            ch.invoke("svc", {}, ctx(v))
        self.assertEqual(ch.invoke("svc", {}, ctx(v, caps=["svc.call"])), "ok")
        prov.revoke("acme", "svc")
        with self.assertRaises(E.CapabilityRefused):
            ch.invoke("svc", {}, ctx(v, caps=["svc.call"]))

    def test_production_refuses_non_authoritative_wiring(self):
        with self.assertRaises(E.ValidationFailed):
            Chainer(Residency("h", default_lease_s=5), config=prod_config(),
                    policy=GuardedProvider(CompatLocalProvider()), transport=object(),
                    trusted_issuers=frozenset({"x"}))
        with self.assertRaises(E.ValidationFailed):
            Chainer(Residency("h"), config=prod_config())


class ResidencyTest(unittest.TestCase):
    def test_expired_lease_is_never_served_locally(self):
        ch, res, prov, v = build(grants=[("acme", "svc", "invoke")])
        res.place("svc", "acme", lambda hop, r: "LOCAL", abi="hop", lease_s=0.02)
        self.assertEqual(ch.invoke("svc", {}, ctx(v)), "LOCAL")
        time.sleep(0.03)
        with self.assertRaises(E.TransportUnavailable):  # goes remote, not served stale
            ch.invoke("svc", {}, ctx(v))
        self.assertGreaterEqual(res.stale_hits, 1)
        self.assertTrue(res.renew("svc", epoch=0, lease_s=5))
        self.assertEqual(ch.invoke("svc", {}, ctx(v)), "LOCAL")

    def test_epoch_arbitration_and_watchers(self):
        res = Residency("h")
        events = []
        res.watch(lambda e, n, p: events.append((e, n)))
        res.watch(lambda *a: 1 / 0)  # broken watcher tolerated
        res.place("a", "t", lambda *a: 1, epoch=2)
        with self.assertRaises(E.ResidencyStale):
            res.place("a", "t", lambda *a: 2, epoch=1)
        res.place("a", "t", lambda *a: 3, epoch=3)
        self.assertEqual(res.inspect("a").epoch, 3)
        self.assertEqual(events, [("placed", "a"), ("placed", "a")])
        with self.assertRaises(E.CrossTenantChain):
            res.place("a", "other", lambda *a: 1, epoch=9)

    def test_bounds(self):
        res = Residency("h", max_placements=2)
        res.place("a", "t", lambda *a: 1); res.place("b", "t", lambda *a: 1)
        with self.assertRaises(E.ValidationFailed):
            res.place("c", "t", lambda *a: 1)
        for bad in ("../x", "a b", "x" * 200):
            with self.assertRaises(ValueError):
                Residency("h").place(bad, "t", lambda *a: 1)

    def test_restart_restore_requires_reconcile(self):
        res = Residency("h")
        h = lambda *a: "v"
        res.place("a", "t", h, epoch=1); res.place("b", "t", h, epoch=1)
        snap = res.snapshot()
        fresh = Residency("h")
        self.assertEqual(fresh.restore(snap, {"a": h, "b": h}), 2)
        self.assertIsNone(fresh.resolve("a"))  # unverified not served
        out = fresh.reconcile([{"callee": "a", "tenant": "t", "epoch": 1}])
        self.assertEqual(out, {"confirmed": ["a"], "evicted": ["b"]})
        self.assertIsNotNone(fresh.resolve("a")); self.assertIsNone(fresh.inspect("b"))
        self.assertGreater(fresh.revision, snap["revision"])
        with self.assertRaises(E.ValidationFailed):
            Residency("other").restore(snap, {})

    def test_unhealthy_placement_suppressed(self):
        res = Residency("h"); res.place("a", "t", lambda *a: 1)
        res.set_health("a", False)
        self.assertIsNone(res.resolve("a")); self.assertEqual(res.suppressed_hits, 1)


if __name__ == "__main__":
    unittest.main()
