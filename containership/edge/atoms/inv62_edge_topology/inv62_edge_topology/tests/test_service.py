"""End-to-end service behaviour: policy-aware routing and failover (MC-010,
MC-045), degraded modes (MC-046), decision records/explain (MC-066/067),
health/metrics/logs/traces/lineage (MC-061 .. MC-069)."""
from __future__ import annotations

import json
import unittest

from support import TENANT, client, seeded

from inv62_edge_topology.production import errors, wire


class PolicyRoutingTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.feed = seeded()
        self.sched = client(self.svc, "scheduler")

    def test_residency_precedes_latency(self):
        self.feed.apply([{"kind": "add_node", "node": "s1-d3", "tier": "device", "site": "s1", "parent": "s1-gw",
                          "caps": ["gpu"], "residency": "us"},
                         {"kind": "connect", "a": "s1-d1", "b": "s1-d3", "latency_ms": 0.5}])
        r = self.sched.resolve("s1-d1", "gpu", explain=True)["result"]
        self.assertEqual(r["node"], "s1-d2")
        rej = [c for c in r["considered"] if c["node"] == "s1-d3"][0]
        self.assertEqual(rej["layer"], "residency")
        self.assertEqual(self.sched.resolve("s1-d1", "gpu", residency=["us"])["result"]["node"], "s1-d3")

    def test_unlabelled_nodes_fail_closed_under_residency(self):
        self.feed.apply([{"kind": "add_node", "node": "s1-d4", "tier": "device", "site": "s1", "parent": "s1-gw",
                          "caps": ["tpu"]}, {"kind": "connect", "a": "s1-gw", "b": "s1-d4", "latency_ms": 1}])
        with self.assertRaises(errors.TopoError) as cm:
            self.sched.resolve("s1-d1", "tpu")
        self.assertEqual(cm.exception.code, "TOPO.NO_CAPABLE_NODE")
        self.assertIn("decision_id", cm.exception.details)

    def test_cross_site_failover_disabled_by_default(self):
        self.feed.apply([{"kind": "add_node", "node": "s2-gw", "tier": "site", "site": "s2", "parent": "r1", "residency": "eu"},
                         {"kind": "add_node", "node": "s2-d1", "tier": "device", "site": "s2", "parent": "s2-gw",
                          "caps": ["npu"], "residency": "eu"},
                         {"kind": "connect", "a": "r1", "b": "s2-gw", "latency_ms": 5},
                         {"kind": "connect", "a": "s2-gw", "b": "s2-d1", "latency_ms": 1}])
        with self.assertRaises(errors.TopoError):
            self.sched.resolve("s1-d1", "npu")
        svc2, feed2 = seeded(policy={"allow_cross_site_failover": True})
        feed2.apply([{"kind": "add_node", "node": "s2-gw", "tier": "site", "site": "s2", "parent": "r1", "residency": "eu"},
                     {"kind": "add_node", "node": "s2-d1", "tier": "device", "site": "s2", "parent": "s2-gw",
                      "caps": ["npu"], "residency": "eu"},
                     {"kind": "connect", "a": "r1", "b": "s2-gw", "latency_ms": 5},
                     {"kind": "connect", "a": "s2-gw", "b": "s2-d1", "latency_ms": 1}])
        self.assertEqual(client(svc2, "scheduler").resolve("s1-d1", "npu")["result"]["node"], "s2-d1")

    def test_failover_when_preferred_node_lost(self):
        self.feed.apply([{"kind": "set_link_state", "a": "s1-gw", "b": "s1-d2", "up": False}])
        r = self.sched.resolve("s1-d1", "gpu")
        self.assertEqual((r["result"]["node"], r["result"]["latency_ms"]), ("cloud", 82.0))

    def test_slo_and_exclude_and_cost(self):
        with self.assertRaises(errors.TopoError):
            self.sched.resolve("s1-d1", "control", max_latency_ms=50)
        self.assertEqual(self.sched.resolve("s1-d1", "gpu", exclude=["s1-d2"])["result"]["node"], "cloud")
        self.feed.apply([{"kind": "add_node", "node": "s1-d5", "tier": "device", "site": "s1", "parent": "s1-gw",
                          "caps": ["cache"], "residency": "eu"},
                         {"kind": "connect", "a": "s1-gw", "b": "s1-d5", "latency_ms": 4}])
        self.assertEqual(self.sched.resolve("s1-d1", "cache")["result"]["node"], "s1-gw")
        self.assertEqual(self.sched.resolve("s1-d1", "cache", prefer="cost")["result"]["node"], "s1-d5")

    def test_stale_links_excluded_or_degraded(self):
        now = self.svc.clock()
        self.feed.apply([{"kind": "connect", "a": "s1-gw", "b": "s1-d2", "latency_ms": 3, "measured_at": now - 100}])
        self.assertEqual(self.sched.resolve("s1-d1", "gpu")["result"]["node"], "cloud")
        svc2, feed2 = seeded(policy={"stale_link_behaviour": "degrade"})
        feed2.apply([{"kind": "connect", "a": "s1-gw", "b": "s1-d2", "latency_ms": 3, "measured_at": svc2.clock() - 100}])
        r = client(svc2, "scheduler").resolve("s1-d1", "gpu")
        self.assertEqual((r["result"]["node"], r["outcome"], r["degraded_mode"]), ("s1-d2", "degraded", "stale_data"))

    def test_partitioned_origin_answers_locally_degraded(self):
        self.feed.apply([{"kind": "set_link_state", "a": "r1", "b": "s1-gw", "up": False},
                         {"kind": "set_link_state", "a": "r1", "b": "s1-gw2", "up": False}])
        r = self.sched.resolve("s1-d1", "gpu")
        self.assertEqual((r["result"]["node"], r["degraded_mode"]), ("s1-d2", "partitioned_local"))
        with self.assertRaises(errors.TopoError):
            self.sched.resolve("s1-d1", "control")

    def test_explain_view(self):
        dec = self.sched.resolve("s1-d1", "gpu")["decision_id"]
        text = self.svc.explain(self.svc.authn.issue("a", "auditor", [TENANT]), dec)
        for token in ("s1-d2", "selected", "security > tenant_isolation > residency", "graph revision"):
            self.assertIn(token, text)
        with self.assertRaises(errors.TopoError):
            self.svc.explain(self.svc.authn.issue("a", "auditor", ["other"]), dec)


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.feed = seeded()

    def _env(self, **kw):
        e = {"protocol": "PK_TOPO_NEAREST/1", "op": "resolve", "tenant": TENANT, "request_id": "req-proto001",
             "credential": self.svc.authn.issue("s", "scheduler", [TENANT]),
             "body": {"origin": "s1-d1", "capability": "gpu"}}
        e.update(kw)
        return json.loads(self.svc.handle(wire.encode(e)))

    def test_every_response_matches_response_schema(self):
        for resp in (self._env(), self._env(protocol="PK_TOPO_NEAREST/7"), self._env(credential="z" * 20)):
            wire.validate_response(resp)

    def test_version_negotiation(self):
        r = self._env(protocol="PK_TOPO_NEAREST/2", accept_versions=[2, 1])
        self.assertEqual(r["protocol"], "PK_TOPO_NEAREST/1")
        r = self._env(protocol="PK_TOPO_NEAREST/2")
        self.assertEqual(r["error"]["code"], "TOPO.UNSUPPORTED_VERSION")
        self.assertEqual(r["error"]["details"]["supported"], [1])
        r = self._env(required_features=["explain"])
        self.assertNotIn("error", r)
        r = self._env(required_features=["teleport"])
        self.assertEqual(r["error"]["details"]["missing_features"], ["teleport"])

    def test_not_ready_before_config(self):
        from inv62_edge_topology.production.config import StaticSecretProvider
        from inv62_edge_topology.production.service import TopologyService
        from support import SECRETS
        cold = TopologyService(StaticSecretProvider(SECRETS))
        r = json.loads(cold.handle(wire.encode({"protocol": "PK_TOPO_NEAREST/1", "op": "resolve", "tenant": TENANT,
                                                "request_id": "req-cold0001", "credential": "x" * 20,
                                                "body": {"origin": "a", "capability": "b"}})))
        self.assertEqual((r["error"]["code"], r["outcome"]), ("TOPO.NOT_READY", "retryable_failure"))
        self.assertFalse(cold.health()["ready"])

    def test_error_codes_are_stable_and_unique(self):
        reg = errors.registry()
        self.assertTrue(all(c.startswith("TOPO.") for c in reg))
        self.assertEqual(len({(e.code) for e in reg.values()}), len(reg))
        for e in reg.values():
            self.assertIn(e.outcome, set(errors.Outcome))


class ObservabilityTest(unittest.TestCase):
    def test_health_surface_has_no_topology_or_secrets(self):
        svc, feed = seeded()
        h = svc.health()
        blob = json.dumps(h)
        for s in ("s1-gw", "secret://", "k1k1"):
            self.assertNotIn(s, blob)
        self.assertTrue(h["ready"])
        self.assertEqual(h["config"]["generation"], 1)
        self.assertIn("artifact_digest", h["release"])

    def test_metrics_logs_traces_and_lineage(self):
        sink: list = []
        svc, feed = seeded()
        svc.logger.sink = sink
        svc.tracer.sample_rate = 1.0
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        r = client(svc, "scheduler").call("PK_TOPO_NEAREST/1", "resolve", {"origin": "s1-d1", "capability": "gpu"},
                                          traceparent=tp)
        self.assertTrue(r["traceparent"].startswith("00-" + "a" * 32))
        self.assertEqual(svc.tracer.finished[-1].parent_id, "b" * 16)
        rec = [x for x in sink if x["event"] == "request"][-1]
        for k in ("tenant", "op", "outcome", "request_id", "trace_id", "decision_id", "config_generation", "release"):
            self.assertIn(k, rec)
        self.assertEqual(rec["trace_id"], "a" * 32)
        d = svc.decisions.get(r["decision_id"])
        self.assertEqual((d.graph_revision, d.config_generation), (svc.tenants[TENANT].topo.revision, 1))
        text = svc.metrics.exposition()
        self.assertIn('inv62_requests_total{family="PK_TOPO_NEAREST",op="resolve",outcome="success"}', text)
        self.assertIn("inv62_request_latency_ms_bucket", text)

    def test_label_cardinality_is_capped(self):
        svc, feed = seeded(telemetry={"max_label_values": 3})
        for i in range(10):
            svc.metrics.inc("x", tenant=f"t{i}")
        self.assertEqual(svc.metrics.get("x", tenant="__overflow__"), 7)

    def test_node_names_pseudonymised_in_logs(self):
        svc, feed = seeded()
        rec = svc.logger.log("info", "t", node="s1-gw")
        self.assertNotEqual(rec["node"], "s1-gw")
        self.assertEqual(rec["node"], svc.logger.pseudonym("s1-gw"))


if __name__ == "__main__":
    unittest.main()
