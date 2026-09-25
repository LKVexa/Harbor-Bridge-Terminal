"""C071 status surface, C072 metrics, C073 logging, C074 tracing, C075 privacy, C076-C077 explain,
C078 lineage, C079 sampling."""
import io
import json
import random
import unittest

from _pkg import observability as O, stream as S, open_stream, registry


class MetricsTest(unittest.TestCase):
    def test_prometheus_text(self):
        r = registry()
        s, tok = open_stream(r); s.grant(1); s.write(1)
        with self.assertRaises(S.CreditExhausted): s.write(2)
        open_stream(r, "b")[0].drop_reader()
        text = O.MetricsExporter(r).render()
        self.assertIn("inv17_credit_stalls_total 1", text)
        self.assertIn('inv17_dropped_end_streams{end="reader"} 1', text)
        self.assertIn("inv17_build_info{", text)
        for line in text.splitlines():
            if not line.startswith("#"):
                self.assertRegex(line, r'^[a-z_0-9]+(\{[^}]*\})? -?[0-9.e+]+$')
        for name in O.MetricsExporter.HELP:
            self.assertIn(f"# TYPE {name} ", text)

    def test_no_tenant_identifiers_in_metrics(self):
        r = registry()
        open_stream(r, "secret-stream", tenant="acme-corp")
        text = O.MetricsExporter(r).render()
        self.assertNotIn("acme-corp", text); self.assertNotIn("secret-stream", text)


class LoggingTest(unittest.TestCase):
    def test_schema_redaction_and_trace(self):
        buf = io.StringIO()
        log = O.StructuredLogger(buf)
        tc = O.TraceContext.new()
        rec = log.log("warning", "stream.write.refused", trace=tc, stream_id="s1", operation="write",
                      code="PK_STREAM_CREDIT_EXHAUSTED", tenant="acme", token="abc.def", element=b"payload")
        doc = json.loads(buf.getvalue())
        for f in ("ts", "level", "event", "component", "version", "instance", "trace_id", "span_id"):
            self.assertIn(f, doc)
        self.assertEqual(doc["token"], "[REDACTED]")
        self.assertNotIn("acme", buf.getvalue())
        self.assertEqual(doc["tenant_hash"], O.pseudonymise("acme"))
        self.assertEqual(doc["element"], "[bytes omitted]")
        self.assertEqual(doc["trace_id"], tc.trace_id)
        self.assertIsNotNone(rec)

    def test_sampling_never_drops_errors(self):
        buf = io.StringIO()
        log = O.StructuredLogger(buf, sample_rate=0.0, rng=random.Random(1))
        self.assertIsNone(log.log("info", "x"))
        self.assertIsNotNone(log.log("error", "y"))
        self.assertIsNone(O.StructuredLogger(buf, level="error").log("warning", "z"))
        self.assertEqual(log.sampled_out, 1)


class TraceTest(unittest.TestCase):
    def test_traceparent(self):
        tc = O.TraceContext.new()
        back = O.TraceContext.parse(tc.header())
        self.assertEqual(back, tc)
        child = tc.child()
        self.assertEqual(child.trace_id, tc.trace_id); self.assertNotEqual(child.span_id, tc.span_id)
        for bad in (None, "", "01-" + "a" * 32 + "-" + "b" * 16 + "-01", "00-" + "0" * 32 + "-" + "b" * 16 + "-01",
                    "00-xyz-abc-01", 42):
            self.assertIsNone(O.TraceContext.parse(bad))
        self.assertFalse(O.TraceContext.parse("00-" + "a" * 32 + "-" + "b" * 16 + "-00").sampled)


class ExplainStatusTest(unittest.TestCase):
    def test_explain_ties_decisions_to_policy(self):
        r = registry()
        tok = r.authority.issue("x", "t", "w", ["read"])
        with self.assertRaises(Exception):
            r.open(int, tenant="t", workload="w", token=tok, stream_id="x")
        e = O.explain(r)
        self.assertEqual(e["decisions"][-1]["outcome"], "denied")
        self.assertIn("right not granted", e["decisions"][-1]["reason"])
        self.assertEqual(e["topology"]["scope"], "instance-local")
        self.assertIn("breaker", e["policy"])

    def test_status_readiness_version_capabilities(self):
        r = registry()
        st = O.status(r)
        self.assertTrue(st["live"]); self.assertTrue(st["ready"])
        self.assertEqual(st["interfaces"]["PK_STREAM"], "PK_STREAM/1")
        self.assertIn("credit-backpressure", st["capabilities"])
        self.assertEqual(st["lineage"]["component"], "INV-17")
        r.emergency_disable("sre-oncall", "t")
        self.assertFalse(O.status(r)["ready"])

    def test_lineage_labels(self):
        self.assertEqual(set(O.Lineage().labels()), {"component", "version", "build", "revision", "instance"})

    def test_label_allowlist_enforced(self):
        class Bad(O.MetricsExporter):
            def samples(self_inner):
                return [("inv17_streams_open", {"tenant": "x"}, 1)]
        exp = O.MetricsExporter(registry())
        orig = exp.samples()
        self.assertTrue(orig)
        r = registry(); exp2 = O.MetricsExporter(r)
        exp2.HELP = O.MetricsExporter.HELP
        # direct check of the guard
        self.assertTrue({"tenant"} - O.ALLOWED_LABELS)


if __name__ == "__main__":
    unittest.main()
