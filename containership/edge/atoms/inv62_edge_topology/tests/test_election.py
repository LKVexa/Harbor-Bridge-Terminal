"""Fenced leases / split-brain protection (MC-048) and quarantine/freeze
controls (MC-049)."""
from __future__ import annotations

import tempfile
import unittest

from support import TENANT, client, seeded

from inv62_edge_topology.production import errors


def partition(feed):
    feed.apply([{"kind": "set_link_state", "a": "r1", "b": "s1-gw", "up": False},
                {"kind": "set_link_state", "a": "r1", "b": "s1-gw2", "up": False}])


class LeaseTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.feed = seeded()
        self.gw = client(self.svc, "node-agent", node="s1-gw")
        self.gw2 = client(self.svc, "node-agent", node="s1-gw2")

    def test_single_holder_and_monotonic_terms(self):
        lease = self.gw.acquire("s1", "s1-gw")["result"]
        self.assertEqual((lease["holder"], lease["term"]), ("s1-gw", 1))
        with self.assertRaises(errors.TopoError) as cm:
            self.gw2.acquire("s1", "s1-gw2")
        self.assertEqual(cm.exception.code, "TOPO.CONFLICT")
        self.assertEqual(self.gw.acquire("s1", "s1-gw")["result"]["term"], 1)  # re-acquire by holder keeps term
        self.svc.clock.advance(11)
        with self.assertRaises(errors.TopoError) as cm:
            self.gw2.acquire("s1", "s1-gw2")  # preferred candidate s1-gw still reachable
        self.assertEqual(cm.exception.details["preferred"], "s1-gw")
        self.assertEqual(self.gw.acquire("s1", "s1-gw")["result"]["term"], 2)

    def test_fencing_rejects_stale_leader(self):
        t1 = self.gw.acquire("s1", "s1-gw")["result"]["fencing_token"]
        sched = client(self.svc, "scheduler")
        self.assertTrue(sched.validate_token("s1", t1)["result"]["valid"])
        op = self.svc.authn.issue("op", "operator", [TENANT])
        self.svc.admin(op, "quarantine", tenant=TENANT, node="s1-gw")
        t2 = self.gw2.acquire("s1", "s1-gw2")["result"]["fencing_token"]
        self.assertGreater(t2, t1)
        with self.assertRaises(errors.TopoError) as cm:
            sched.validate_token("s1", t1)
        self.assertEqual(cm.exception.code, "TOPO.STALE_LEADER")
        with self.assertRaises(errors.TopoError) as cm:
            self.gw.renew("s1", "s1-gw", t1)
        self.assertEqual(cm.exception.code, "TOPO.STALE_LEADER")

    def test_minority_side_cannot_acquire(self):
        # three voters; isolate s1-gw3 from the other two
        self.feed.apply([{"kind": "add_node", "node": "s1-gw3", "tier": "site", "site": "s1", "parent": "r1",
                          "caps": ["coordinator"], "residency": "eu"},
                         {"kind": "connect", "a": "s1-gw3", "b": "r1", "latency_ms": 5, "up": False}])
        gw3 = client(self.svc, "node-agent", node="s1-gw3")
        with self.assertRaises(errors.TopoError) as cm:
            gw3.acquire("s1", "s1-gw3")
        self.assertEqual(cm.exception.code, "TOPO.FORBIDDEN")
        self.assertEqual(self.gw.acquire("s1", "s1-gw")["result"]["holder"], "s1-gw")

    def test_ineligible_and_foreign_candidates_refused(self):
        dev = client(self.svc, "node-agent", node="s1-d1")
        with self.assertRaises(errors.TopoError) as cm:
            dev.acquire("s1", "s1-d1")
        self.assertEqual(cm.exception.code, "TOPO.NO_COORDINATOR")
        cloud = client(self.svc, "node-agent", node="cloud")
        with self.assertRaises(errors.TopoError) as cm:
            cloud.acquire("s1", "cloud")
        self.assertEqual(cm.exception.code, "TOPO.INVALID_TOPOLOGY")

    def test_partition_status_lifecycle_and_reconciliation(self):
        dc = client(self.svc, "disconnected-controller")
        self.assertEqual(dc.status("s1")["result"]["state"], "connected")
        partition(self.feed)
        r = dc.status("s1")
        self.assertEqual((r["outcome"], r["result"]["state"], r["result"]["mode"]), ("degraded", "partitioned", "partitioned_local"))
        tok = self.gw.acquire("s1", "s1-gw")["result"]["fencing_token"]
        self.feed.apply([{"kind": "set_link_state", "a": "r1", "b": "s1-gw", "up": True}])
        r = dc.status("s1")["result"]
        self.assertEqual((r["state"], r["coordinator"]), ("connected", None))
        with self.assertRaises(errors.TopoError):
            client(self.svc, "scheduler").validate_token("s1", tok)
        self.assertEqual(self.svc.metrics.get("inv62_partitions"), 1)
        self.assertEqual(self.svc.metrics.get("inv62_local_elections"), 1)

    def test_terms_survive_restart(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            gw = client(svc, "node-agent", node="s1-gw")
            t = gw.acquire("s1", "s1-gw")["result"]["term"]
            svc.clock.advance(20)
            t2 = gw.acquire("s1", "s1-gw")["result"]["term"]
            from support import make_service
            svc2 = make_service(state_dir=d, clock=svc.clock)
            self.assertIsNone(svc2.leases.current(f"{TENANT}/s1", svc.clock()))  # leases never restored
            svc2.clock.advance(20)
            t3 = client(svc2, "node-agent", node="s1-gw").acquire("s1", "s1-gw")["result"]["term"]
            self.assertEqual((t, t2, t3), (1, 2, 3))


class FreezeQuarantineTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.feed = seeded()
        self.op = lambda: self.svc.authn.issue("op", "operator", [TENANT])  # noqa: E731

    def test_freeze_blocks_automated_changes_but_not_reads(self):
        self.svc.admin(self.op(), "freeze")
        with self.assertRaises(errors.TopoError) as cm:
            self.feed.retry = __import__("inv62_edge_topology.production.resilience", fromlist=["x"]).RetryPolicy(max_attempts=1)
            self.feed.apply([{"kind": "remove_node", "node": "s1-d2"}])
        self.assertEqual(cm.exception.code, "TOPO.FROZEN")
        self.assertEqual(client(self.svc, "scheduler").resolve("s1-d1", "gpu")["result"]["node"], "s1-d2")
        self.assertEqual(self.svc.health()["mode"], "frozen")
        self.svc.admin(self.op(), "unfreeze")
        self.feed.apply([{"kind": "remove_node", "node": "s1-d2"}])

    def test_quarantine_excludes_from_routing_and_is_audited(self):
        self.svc.admin(self.op(), "quarantine", tenant=TENANT, node="s1-d2")
        r = client(self.svc, "scheduler").resolve("s1-d1", "gpu", explain=True)["result"]
        self.assertEqual(r["node"], "cloud")
        self.assertIn({"node": "s1-d2", "latency_ms": 5.0, "verdict": "rejected", "layer": "security",
                       "reason": "node quarantined"}, r["considered"])
        self.svc.admin(self.op(), "release", tenant=TENANT, node="s1-d2")
        self.assertEqual(client(self.svc, "scheduler").resolve("s1-d1", "gpu")["result"]["node"], "s1-d2")
        events = [r["event"] for r in self.svc.audit.records]
        self.assertIn("admin.quarantine", events)
        self.assertIn("admin.release", events)

    def test_admin_requires_operator_and_tenant(self):
        with self.assertRaises(errors.TopoError):
            self.svc.admin(self.svc.authn.issue("op", "operator", ["tenant-z"]), "quarantine", tenant=TENANT, node="s1-d2")
        with self.assertRaises(errors.TopoError):
            self.svc.admin(self.op(), "self-destruct")


if __name__ == "__main__":
    unittest.main()
