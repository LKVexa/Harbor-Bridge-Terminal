"""Fault-injection recovery suite (MC-050, MC-078): link flap, node loss,
repeated partition/reconnect, multi-site isolation, controller loss and
restart, stale controller, dependency faults, disaster restore."""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from support import TENANT, client, make_service, seeded

from inv62_edge_topology.production import errors
from inv62_edge_topology.production.resilience import RetryPolicy


def probe(feed, pairs, ok, at):
    feed.apply([{"kind": "probe", "a": a, "b": b, "ok": ok, "at": at, **({"latency_ms": 60.0} if ok else {})}
                for a, b in pairs])


UPLINKS = [("r1", "s1-gw"), ("r1", "s1-gw2")]


class FaultInjectionTest(unittest.TestCase):
    def test_link_flap_is_suppressed(self):
        svc, feed = seeded()
        t = svc.clock()
        for cycle in range(4):
            for _ in range(3):
                t += 1; probe(feed, [("r1", "s1-gw")], False, t)
            for _ in range(2):
                t += 1; probe(feed, [("r1", "s1-gw")], True, t)
        link = svc.tenants[TENANT].topo.links[frozenset(("r1", "s1-gw"))]
        self.assertFalse(link.up)  # held down while flapping
        self.assertEqual(svc.tenants[TENANT].health[frozenset(("r1", "s1-gw"))].state.value, "flapping")

    def test_repeated_partition_reconnect_cycles(self):
        svc, feed = seeded()
        dc = client(svc, "disconnected-controller")
        gw = client(svc, "node-agent", node="s1-gw")
        terms = []
        t = svc.clock()
        for cycle in range(5):
            for _ in range(3):
                t += 60; svc.clock.t = t; probe(feed, UPLINKS, False, t)
            self.assertTrue(dc.status("s1")["result"]["partitioned"])
            terms.append(gw.acquire("s1", "s1-gw")["result"]["term"])
            for _ in range(2):
                t += 60; svc.clock.t = t; probe(feed, UPLINKS, True, t)
            r = dc.status("s1")["result"]
            self.assertEqual((r["partitioned"], r["coordinator"]), (False, None))
        self.assertEqual(terms, [1, 2, 3, 4, 5])
        self.assertEqual(svc.metrics.get("inv62_partitions"), 5)

    def test_multi_site_isolation(self):
        svc, feed = seeded()
        feed.apply([{"kind": "add_node", "node": "s2-gw", "tier": "site", "site": "s2", "parent": "r1",
                     "caps": ["coordinator"], "residency": "eu"},
                    {"kind": "connect", "a": "r1", "b": "s2-gw", "latency_ms": 9}])
        dc = client(svc, "disconnected-controller")
        feed.apply([{"kind": "set_link_state", "a": "r1", "b": "s2-gw", "up": False}])
        self.assertTrue(dc.status("s2")["result"]["partitioned"])
        self.assertFalse(dc.status("s1")["result"]["partitioned"])
        client(svc, "node-agent", node="s2-gw").acquire("s2", "s2-gw")
        self.assertIsNone(dc.status("s1")["result"]["coordinator"])

    def test_node_loss_and_region_loss(self):
        svc, feed = seeded()
        sched = client(svc, "scheduler")
        feed.apply([{"kind": "remove_node", "node": "s1-d2"}])
        self.assertEqual(sched.resolve("s1-d1", "gpu")["result"]["node"], "cloud")
        feed.apply([{"kind": "set_link_state", "a": "cloud", "b": "r1", "up": False}])
        with self.assertRaises(errors.TopoError):
            sched.resolve("s1-d1", "gpu")
        self.assertTrue(client(svc, "disconnected-controller").status("s1")["result"]["partitioned"])

    def test_controller_crash_restart_and_stale_leader(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            old = client(svc, "node-agent", node="s1-gw").acquire("s1", "s1-gw")["result"]["fencing_token"]
            del svc  # crash: nothing flushed beyond the WAL
            svc2 = make_service(state_dir=d)
            svc2.clock.advance(100)
            sched = client(svc2, "scheduler")
            with self.assertRaises(errors.TopoError) as cm:
                sched.validate_token("s1", old)
            self.assertEqual(cm.exception.code, "TOPO.STALE_LEADER")  # no lease survives restart
            new = client(svc2, "node-agent", node="s1-gw").acquire("s1", "s1-gw")["result"]["fencing_token"]
            self.assertGreater(new, old)

    def test_state_store_fault_opens_breaker_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            feed.retry = RetryPolicy(max_attempts=1)
            rev = svc.tenants[TENANT].topo.revision
            with mock.patch("inv62_edge_topology.production.persistence.open", side_effect=OSError("disk"), create=True):
                for _ in range(5):
                    with self.assertRaises(errors.TopoError) as cm:
                        feed.apply([{"kind": "remove_node", "node": "s1-d2"}])
                    self.assertEqual(cm.exception.code, "TOPO.DEPENDENCY_UNAVAILABLE")
                with self.assertRaises(errors.TopoError) as cm:
                    feed.apply([{"kind": "remove_node", "node": "s1-d2"}])
                self.assertEqual(cm.exception.code, "TOPO.OVERLOADED")
            self.assertEqual(svc.tenants[TENANT].topo.revision, rev)
            self.assertFalse(svc.health()["ready"])
            svc.clock.advance(6)
            feed.apply([{"kind": "remove_node", "node": "s1-d2"}])
            self.assertEqual(svc.breaker.state, "closed")

    def test_disaster_total_state_loss_restore_from_backup(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as d2:
            svc, feed = seeded(state_dir=d)
            client(svc, "node-agent", node="s1-gw").acquire("s1", "s1-gw")
            backup = svc.export_state()
            for root, _, files in os.walk(d):
                for f in files:
                    os.remove(os.path.join(root, f))
            fresh = make_service(state_dir=d2, clock=svc.clock)
            fresh.import_state(backup)
            fresh.checkpoint()
            again = make_service(state_dir=d2, clock=svc.clock)
            self.assertEqual(again.export_state()["tenants"], backup["tenants"])
            self.assertEqual(again.leases.term(f"{TENANT}/s1"), 1)


if __name__ == "__main__":
    unittest.main()
