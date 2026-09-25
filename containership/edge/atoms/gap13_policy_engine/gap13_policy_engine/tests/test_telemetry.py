"""G13-MC-022..026 metrics, logging, tracing, redaction, lineage."""
import unittest

import testkit as k
from gap13_policy_engine.telemetry import Lineage, Metrics, Redactor, Tracer, StructuredLogger, EVENT_IDS


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.svc, self.c = k.service(require_separation_of_duties=False,
                                     lineage=Lineage("5.0.0", "sha256:abc", "topology-svc", "topo-42"))
        self.svc.load(k.principal("alice", clock=self.c), k.envelope(1))
        self.app = k.principal("svc-a", ("service",), kind="service", clock=self.c)

    def test_metrics(self):
        self.svc.evaluate(self.app, {"action": "read"})
        self.svc.evaluate(self.app, {"action": "write"})
        m = self.svc.metrics
        self.assertEqual(m.counter("verdicts"), 2)
        self.assertEqual(m.counter("default_denies"), 1)
        self.assertEqual(m.counter("rule_hits", rule="allow-read"), 1)
        self.assertIsNotNone(m.quantile("evaluate_latency_ms", 0.99))
        text = m.prometheus()
        for name in ("g13_verdicts_total", "g13_evaluate_latency_ms_bucket", "g13_bundle_generation",
                     "g13_bundle_age_seconds", "g13_bundle_activations_total"):
            self.assertIn(name, text)
        self.assertNotIn('tenant="t1"', text)

    def test_cardinality_guard(self):
        m = Metrics()
        m.max_series = 10
        for i in range(50):
            m.inc("x", rule=f"r{i}")
        self.assertLessEqual(len(m.counters), 11)

    def test_logging_stable_ids_privacy(self):
        self.svc.evaluate(self.app, {"action": "read", "resource": "doc-secret"})
        rec = self.svc.log.lines[-1]
        self.assertEqual(rec["event_id"], "G13-L001")
        for f in ("component", "node", "site", "environment"):
            self.assertIn(f, rec)
        self.assertTrue(rec["tenant"].startswith("p:"))
        self.assertNotIn("doc-secret", repr(self.svc.log.lines))
        with self.assertRaises(ValueError):
            StructuredLogger(Redactor()).log("G13-L999")
        self.assertEqual(len(EVENT_IDS), len(set(EVENT_IDS.values())))

    def test_tracing_propagation(self):
        tp = "00-" + "1" * 32 + "-" + "2" * 16 + "-01"
        v = self.svc.evaluate(self.app, {"action": "read"}, traceparent=tp)
        span = self.svc.tracer.finished[-1]
        self.assertEqual((v["trace_id"], span.parent_id), ("1" * 32, "2" * 16))
        self.assertEqual(Tracer.parse("00-" + "0" * 32 + "-" + "2" * 16 + "-01"), (None, None))
        self.assertEqual(Tracer.parse("garbage"), (None, None))

    def test_redaction_allowlist(self):
        r = Redactor(b"salt")
        out = r.apply({"effect": "allow", "tenant": "t1", "request": {"x": 1}, "unknown": "zz"})
        self.assertEqual(set(out), {"effect", "tenant"})
        self.assertEqual(out["tenant"], r.pseudonym("t1"))

    def test_lineage(self):
        v = self.svc.evaluate(self.app, {"action": "read"})
        self.assertEqual(v["lineage"]["topology_snapshot"], "topo-42")
        self.assertEqual(v["lineage"]["engine_artifact_digest"], "sha256:abc")


if __name__ == "__main__":
    unittest.main()
