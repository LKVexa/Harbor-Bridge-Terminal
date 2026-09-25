import unittest
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.identity.context import IdentityContext
from inv65_capability_providers.rollout.controller import RolloutController


def op(p):
    return IdentityContext("ops", "prod", "sfo1", "ops", "console", authenticated=True, principal=p)


class Rollout(unittest.TestCase):
    def test_stages_advance_and_complete(self):
        r = RolloutController(); r.start("c1")
        seen = [r.percent]
        while r.state == "in_progress":
            r.observe(0, 200); seen.append(r.percent)
        self.assertEqual(r.state, "complete"); self.assertEqual(seen[:5], [1, 5, 25, 50, 100])

    def test_auto_rollback_on_canary_errors(self):
        r = RolloutController(); r.start("c1"); r.observe(0, 200)
        self.assertEqual(r.observe(10, 200), "rolled_back"); self.assertEqual(r.percent, 0)

    def test_waits_for_min_requests(self):
        r = RolloutController(); r.start("c1"); self.assertEqual(r.observe(0, 5), "waiting")

    def test_drain_refuses_new_calls(self):
        w = World(); w.svc.start(); w.link(); w.svc.drain()
        with self.assertRaises(ProviderFault) as c:
            w.call()
        self.assertEqual(c.exception.code, "PK_PROVIDER_DISABLED")

    def test_emergency_disable_two_person_rule(self):
        w = World(); w.svc.start(); w.link()
        with self.assertRaises(ProviderFault):
            w.svc.disable([op("alice"), op("alice")], "incident")
        with self.assertRaises(ProviderFault):
            w.svc.disable([op("alice"), IdentityContext("ops", "prod", "sfo1", "ops", "console", principal="bob")], "incident")
        w.svc.disable([op("alice"), op("bob")], "incident")
        with self.assertRaises(ProviderFault):
            w.call()
        self.assertEqual(w.svc.audit.events()[-2]["action"], "provider.emergency_disable")
