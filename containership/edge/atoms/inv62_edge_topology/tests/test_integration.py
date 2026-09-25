"""Adjacent-layer integration (MC-020, MC-072): GAP-02 hardware discovery ->
INV-62 <- GAP-12 WAN health; GAP-03 scheduler and GAP-04 disconnected
controller consume it.  Uses only the public wire boundary."""
from __future__ import annotations

import unittest

from support import TENANT, client, make_service

from inv62_edge_topology.production.adapters import (DisconnectedController, HardwareDiscoveryFeed,
                                                      SchedulerAdapter, WanHealthFeed)

INVENTORY = [
    {"id": "cloud", "tier": "cloud", "caps": ["control", "gpu"], "residency": "eu"},
    {"id": "r1", "tier": "region", "parent": "cloud", "residency": "eu"},
    {"id": "s1-gw", "tier": "site", "site": "s1", "parent": "r1", "caps": ["coordinator"], "residency": "eu"},
    {"id": "s1-gw2", "tier": "site", "site": "s1", "parent": "r1", "caps": ["coordinator"], "residency": "eu"},
    {"id": "s1-d1", "tier": "device", "site": "s1", "parent": "s1-gw", "residency": "eu"},
    {"id": "s1-d2", "tier": "device", "site": "s1", "parent": "s1-gw", "caps": ["gpu"], "residency": "eu"},
]
LINKS = [("cloud", "r1", 20.0), ("r1", "s1-gw", 60.0), ("r1", "s1-gw2", 70.0), ("s1-gw", "s1-gw2", 1.0),
         ("s1-gw", "s1-d1", 2.0), ("s1-gw", "s1-d2", 3.0)]


class AdjacentLayerTest(unittest.TestCase):
    def test_end_to_end_lifecycle(self):
        svc = make_service()
        hw = HardwareDiscoveryFeed(client(svc, "topology-feed"))
        wan = WanHealthFeed(client(svc, "topology-feed"))
        sched = SchedulerAdapter(client(svc, "scheduler"))
        gw = DisconnectedController(client(svc, "node-agent", node="s1-gw"), "s1", "s1-gw")
        gw2 = DisconnectedController(client(svc, "node-agent", node="s1-gw2"), "s1", "s1-gw2")

        hw.sync(list(reversed(INVENTORY)))              # order-independent
        self.assertIsNone(hw.sync(INVENTORY))            # idempotent
        now = svc.clock()
        wan.links(LINKS, now)
        self.assertEqual(sched.place("s1-d1", "gpu"), ("s1-d2", 5.0, None))
        self.assertEqual(gw.tick()["action"], "follow-cloud")

        # uplinks fail: hysteresis needs 3 failed probes
        for i in range(1, 4):
            svc.clock.advance(5)
            wan.probes([("r1", "s1-gw", False, None), ("r1", "s1-gw2", False, None),
                        ("s1-gw", "s1-d2", True, 3.0), ("s1-gw", "s1-d1", True, 2.0), ("s1-gw", "s1-gw2", True, 1.0)],
                       svc.clock())
            if i < 3:
                self.assertEqual(gw.tick()["action"], "follow-cloud")
        self.assertEqual(gw.tick()["action"], "leader")
        self.assertEqual(gw2.tick()["action"], "follower")
        token = gw.token
        self.assertEqual(sched.place("s1-d1", "gpu")[2], "partitioned_local")
        self.assertIsNone(sched.place("s1-d1", "control"))
        svc.clock.advance(1)
        self.assertEqual(gw.tick(), {"action": "renewed", "token": token})

        # uplink recovers: 2 good probes; coordination returns to cloud and token is fenced
        for _ in range(2):
            svc.clock.advance(5)
            wan.probes([("r1", "s1-gw", True, 61.0)], svc.clock())
        self.assertEqual(gw.tick()["action"], "follow-cloud")
        with self.assertRaises(Exception):
            client(svc, "scheduler").validate_token("s1", token)
        self.assertEqual(sched.place("s1-d1", "control"), ("cloud", 83.0, None))

    def test_scheduler_respects_tenant_boundary(self):
        svc = make_service()
        HardwareDiscoveryFeed(client(svc, "topology-feed")).sync(INVENTORY)
        other = SchedulerAdapter(client(svc, "scheduler", tenant="tenant-b"))
        with self.assertRaises(Exception):
            other.place("s1-d1", "gpu")
        self.assertIn(TENANT, svc.tenants)


if __name__ == "__main__":
    unittest.main()
