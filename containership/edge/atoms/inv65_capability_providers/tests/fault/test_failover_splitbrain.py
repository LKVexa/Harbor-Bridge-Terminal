import unittest
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.resilience.failover import choose_target
from inv65_capability_providers.resilience.fencing import LeaseManager


class Clock:
    t = 0.0
    def __call__(self):
        return self.t


class FailoverSplitBrain(unittest.TestCase):
    def test_second_instance_cannot_take_live_lease(self):
        clk = Clock(); leases = LeaseManager(10, clock=clk)
        a = World(leases=leases, instance="a"); a.svc.start()
        b = World(state_dir=a.tmp, leases=leases, instance="b")
        with self.assertRaises(ProviderFault) as c:
            b.svc.start()
        self.assertEqual(c.exception.code, "PK_PROVIDER_FENCED")

    def test_stale_owner_is_fenced_after_takeover(self):
        clk = Clock(); leases = LeaseManager(10, clock=clk)
        a = World(leases=leases, instance="a"); a.svc.start(); a.link("x")
        clk.t = 11  # a's lease expires (a is partitioned but still running)
        b = World(state_dir=a.tmp, leases=leases, instance="b"); b.svc.start()
        self.assertGreater(b.svc.epoch, a.svc.epoch)
        with self.assertRaises(ProviderFault) as c:
            a.link("y")
        self.assertEqual(c.exception.code, "PK_PROVIDER_FENCED")
        b.link("z")

    def test_failover_target_respects_residency_and_health(self):
        w = World()
        cands = [{"instance_id": "eu", "region": "eu-central", "environment": "prod"},
                 {"instance_id": "w2", "region": "us-west", "environment": "prod"},
                 {"instance_id": "e1", "region": "us-east", "environment": "prod"}]
        t = choose_target(cands, tenant="acme", residency=w.residency, healthy=lambda c: True)
        self.assertEqual(t["instance_id"], "e1")  # us-west not a failover region; eu not allowed
        with self.assertRaises(ProviderFault):
            choose_target(cands, tenant="acme", residency=w.residency, healthy=lambda c: c["instance_id"] != "e1")

    def test_degraded_mode_serves_reads_only_and_refuses_link_changes(self):
        w = World(); w.svc.start(); w.link()
        w.svc.enter_degraded()
        w.call(op="get")
        with self.assertRaises(ProviderFault):
            w.call(op="set", payload={"key": "k", "value": 1})
        with self.assertRaises(ProviderFault):
            w.link("new")
        w.svc.recover(); w.call(op="set", payload={"key": "k", "value": 1})
