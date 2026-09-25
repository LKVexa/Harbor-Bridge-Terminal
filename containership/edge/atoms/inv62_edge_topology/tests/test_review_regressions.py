"""Regression tests for the independent adversarial review of 4.3.0
(findings R1-R6 and the suspected items S1-S4; see AUDIT_REPORT.md)."""
from __future__ import annotations

import json
import tempfile
import unittest

from support import TENANT, client, make_service, seeded

from inv62_edge_topology.production import errors, wire
from inv62_edge_topology.production.resilience import RetryPolicy


def raw_apply(svc, cred, node, rid="req-rev00001"):
    return json.loads(svc.handle(wire.encode({"protocol": "PK_TOPO_GRAPH/1", "op": "apply", "tenant": TENANT,
                                              "request_id": rid, "credential": cred,
                                              "body": {"mutations": [{"kind": "remove_node", "node": node}]}})))


class ReviewRegressionTest(unittest.TestCase):
    def test_R1_replay_is_refused_after_restart(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            cred = svc.authn.issue("f", "topology-feed", [TENANT])
            self.assertNotIn("error", raw_apply(svc, cred, "s1-d1"))
            again = make_service(state_dir=d, clock=svc.clock)
            self.assertEqual(raw_apply(again, cred, "s1-d2", "req-rev00002")["error"]["code"], "TOPO.REPLAYED")
            self.assertIn("s1-d2", again.tenants[TENANT].topo.nodes)
            again.checkpoint()  # survives compaction too
            third = make_service(state_dir=d, clock=svc.clock)
            self.assertEqual(raw_apply(third, cred, "s1-d2", "req-rev00003")["error"]["code"], "TOPO.REPLAYED")

    def test_R2_removed_or_ineligible_holder_loses_lease(self):
        svc, feed = seeded()
        gw = client(svc, "node-agent", node="s1-gw")
        tok = gw.acquire("s1", "s1-gw")["result"]["fencing_token"]
        feed.apply([{"kind": "remove_node", "node": "s1-d1"}, {"kind": "remove_node", "node": "s1-d2"},
                    {"kind": "remove_node", "node": "s1-gw"}])
        with self.assertRaises(errors.TopoError):
            gw.renew("s1", "s1-gw", tok)
        with self.assertRaises(errors.TopoError) as cm:
            client(svc, "scheduler").validate_token("s1", tok)
        self.assertEqual(cm.exception.code, "TOPO.STALE_LEADER")
        self.assertGreater(client(svc, "node-agent", node="s1-gw2").acquire("s1", "s1-gw2")["result"]["term"], tok)

    def test_R3_probe_hysteresis_survives_checkpoint_and_restart(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            t = svc.clock()
            feed.apply([{"kind": "probe", "a": "r1", "b": "s1-gw", "ok": False, "at": t}])
            svc.checkpoint()
            feed.apply([{"kind": "probe", "a": "r1", "b": "s1-gw", "ok": False, "at": t}])
            feed.apply([{"kind": "probe", "a": "r1", "b": "s1-gw", "ok": False, "at": t}])
            key = frozenset(("r1", "s1-gw"))
            before = (svc.tenants[TENANT].topo.links[key].up, svc.tenants[TENANT].health[key].state)
            again = make_service(state_dir=d, clock=svc.clock)
            after = (again.tenants[TENANT].topo.links[key].up, again.tenants[TENANT].health[key].state)
            self.assertEqual(before, after)
            self.assertFalse(after[0])

    def test_R4_rejected_batch_does_not_touch_live_health(self):
        svc, feed = seeded()
        feed.retry = RetryPolicy(max_attempts=1)
        t = svc.clock()
        feed.apply([{"kind": "probe", "a": "r1", "b": "s1-gw", "ok": False, "at": t}])
        key = frozenset(("r1", "s1-gw"))
        snap = svc.tenants[TENANT].health[key].to_dict()
        for _ in range(3):
            with self.assertRaises(errors.TopoError):
                feed.apply([{"kind": "probe", "a": "r1", "b": "s1-gw", "ok": False, "at": t},
                            {"kind": "remove_node", "node": "nope"}])
        self.assertEqual(svc.tenants[TENANT].health[key].to_dict(), snap)

    def test_R5_future_timestamps_rejected(self):
        svc, feed = seeded()
        feed.retry = RetryPolicy(max_attempts=1)
        for m in ({"kind": "set_link_state", "a": "s1-gw", "b": "s1-d2", "up": True, "measured_at": svc.clock() + 1e6},
                  {"kind": "probe", "a": "r1", "b": "s1-gw", "ok": True, "at": svc.clock() + 3600}):
            with self.assertRaises(errors.TopoError) as cm:
                feed.apply([m])
            self.assertEqual(cm.exception.code, "TOPO.INVALID_TOPOLOGY")
        feed.apply([{"kind": "probe", "a": "r1", "b": "s1-gw", "ok": True, "at": svc.clock() + 5}])  # within skew

    def test_R6_unknown_node_message_intact(self):
        svc, feed = seeded()
        feed.retry = RetryPolicy(max_attempts=1)
        with self.assertRaises(errors.TopoError) as cm:
            feed.apply([{"kind": "remove_node", "node": "nope"}])
        self.assertEqual(cm.exception.message, "unknown node 'nope'")

    def test_S1_idempotency_key_bound_to_principal(self):
        svc, feed = seeded()
        body = {"mutations": [{"kind": "add_node", "node": "s1-dz", "tier": "device", "site": "s1", "parent": "s1-gw"}]}

        def send(sub):
            return json.loads(svc.handle(wire.encode({"protocol": "PK_TOPO_GRAPH/1", "op": "apply", "tenant": TENANT,
                                                      "request_id": "req-idemp002", "idempotency_key": "idem-shared0001",
                                                      "credential": svc.authn.issue(sub, "topology-feed", [TENANT]),
                                                      "body": body})))
        self.assertNotIn("error", send("feed-a"))
        self.assertEqual(send("feed-b")["error"]["code"], "TOPO.IDEMPOTENCY_MISMATCH")

    def test_S2_tightened_limits_do_not_brick_recovery_and_are_refused_live(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            with self.assertRaises(errors.TopoError):
                svc.activate_config(__import__("support").base_config(limits={"max_nodes": 3}), author="x",
                                    source="y", expected_generation=1)
            again = make_service(state_dir=d, clock=svc.clock, limits={"max_nodes": 3})
            self.assertEqual(len(again.tenants[TENANT].topo.nodes), 6)
            with self.assertRaises(errors.TopoError) as cm:
                client(again, "topology-feed").apply([{"kind": "add_node", "node": "s1-dq", "tier": "device", "site": "s1", "parent": "s1-gw"}])
            self.assertEqual(cm.exception.code, "TOPO.QUOTA_EXCEEDED")

    def test_S3_trackers_dropped_with_node(self):
        svc, feed = seeded()
        feed.apply([{"kind": "probe", "a": "s1-gw", "b": "s1-d2", "ok": True, "at": svc.clock()}])
        feed.apply([{"kind": "remove_node", "node": "s1-d2"}])
        self.assertFalse([k for k in svc.tenants[TENANT].health if "s1-d2" in k])

    def test_S4_explain_is_not_an_existence_oracle(self):
        svc, feed = seeded()
        dec = client(svc, "scheduler").resolve("s1-d1", "gpu")["decision_id"]
        other = svc.authn.issue("a", "auditor", ["tenant-z"])
        msgs = []
        for did in (dec, "dec-0-00000000"):
            with self.assertRaises(errors.TopoError) as cm:
                svc.explain(other, did)
            msgs.append((cm.exception.code, cm.exception.message))
        self.assertEqual(msgs[0], msgs[1])

    def test_S5_wal_bounded_and_expired_nonces_pruned(self):
        with tempfile.TemporaryDirectory() as d:
            svc, feed = seeded(state_dir=d)
            svc.WAL_COMPACT_BYTES = 20_000
            for i in range(200):
                raw_apply(svc, svc.authn.issue("f", "topology-feed", [TENANT]), "nope", f"req-bad{i:05d}")
            self.assertLess(svc.store.wal.stat().st_size, 25_000)
            svc.clock.advance(2000)
            self.assertEqual(svc.export_state()["nonces"], [])
            again = make_service(state_dir=d, clock=svc.clock)
            self.assertEqual(len(again.tenants[TENANT].topo.nodes), 6)

    def test_S6_failed_nonce_persist_does_not_consume_nonce(self):
        svc, feed = seeded()
        cred = svc.authn.issue("f", "topology-feed", [TENANT])
        orig = svc.authn.on_spend

        def boom(k, e):
            raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE, "disk")
        svc.authn.on_spend = boom
        self.assertEqual(raw_apply(svc, cred, "s1-d1")["error"]["code"], "TOPO.DEPENDENCY_UNAVAILABLE")
        svc.authn.on_spend = orig
        self.assertNotIn("error", raw_apply(svc, cred, "s1-d1", "req-rev00009"))


if __name__ == "__main__":
    unittest.main()
