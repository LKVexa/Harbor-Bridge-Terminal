"""Observability tests (MC079-MC092): endpoints, metrics, logs, traces,
decision stream, explain view, cardinality safety, alert rules."""
import io
import json
import unittest
import urllib.error
import urllib.request

import _fixtures as F
from inv29_hybrid_wasm_unikernel import deps as D
from inv29_hybrid_wasm_unikernel import telemetry as T


class TelemetryTest(unittest.TestCase):
    def setUp(self):
        self.metrics = T.Metrics()
        self.stream = io.StringIO()
        self.log = T.Logger(self.stream, version="4.3.0", release="test")
        self.decisions = T.DecisionLog(metrics=self.metrics, logger=self.log)
        self.kr = F.keyring()
        self.a = F.admitter(self.kr, on_decision=self.decisions)

    def test_decision_stream_metrics_and_explain(self):
        self.a.admit(F.request(self.kr))
        for bad in (F.request(self.kr, imports=("fs",)), F.request(self.kr, tenant="mallory")):
            try:
                self.a.admit(bad)
            except PermissionError:
                pass
        self.assertEqual(self.metrics.value("inv29_compositions_total", outcome="admitted", code="INV29-OK"), 1)
        self.assertEqual(self.metrics.value("inv29_import_refusals_total"), 1)
        ex = self.decisions.explain(module="svc")
        self.assertEqual([e["code"] for e in ex], ["INV29-OK", "INV29-E-IMPORT", "INV29-E-POLICY"])
        self.assertTrue(all(e["why"] for e in ex))

    def test_structured_logs_are_json_and_redacted(self):
        tp = T.traceparent()
        rec = self.log.log("info", "x", tp=tp, api_key="hunter2", tenant="acme")
        line = json.loads(self.stream.getvalue().splitlines()[-1])
        self.assertEqual(line["api_key"], "[REDACTED]")
        self.assertEqual(line["trace_id"], tp.split("-")[1])
        self.assertEqual(rec["version"], "4.3.0")
        self.assertNotIn("hunter2", self.stream.getvalue())

    def test_trace_context_propagation(self):
        root = T.traceparent()
        child = T.traceparent(root)
        self.assertEqual(T.trace_id(root), T.trace_id(child))
        self.assertNotEqual(root, child)
        self.assertIsNotNone(T.trace_id(T.traceparent("garbage")))
        self.assertIsNone(T.trace_id("00-zz-yy-01"))

    def test_cardinality_cap(self):
        for i in range(T.MAX_SERIES_PER_METRIC + 50):
            self.metrics.inc("inv29_c_total", tenant=f"t{i}")
        self.assertEqual(self.metrics.dropped_series, 50)
        self.assertIn('tenant="__other__"', self.metrics.exposition())
        self.metrics.inc("inv29_c2_total", tenant='x"} evil{')
        self.assertIn("__invalid__", self.metrics.exposition())

    def test_histogram_exposition(self):
        for v in (0.07, 0.3, 3, 700):
            self.metrics.observe("inv29_admission_latency_ms", v)
        text = self.metrics.exposition()
        self.assertIn('inv29_admission_latency_ms_bucket{le="+Inf"} 4', text)
        self.assertIn("inv29_admission_latency_ms_count 4", text)

    def test_http_endpoints(self):
        srv = T.serve(port=0, version_info={"version": "4.3.0", "policy_generation": 1},
                      ready=lambda: (False, {"reason": "pk_core absent"}),
                      dependencies=D.dependency_report, metrics=self.metrics, decisions=self.decisions)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            def get(path):
                try:
                    with urllib.request.urlopen(base + path, timeout=5) as r:
                        return r.status, r.read().decode()
                except urllib.error.HTTPError as e:
                    return e.code, e.read().decode()
            self.assertEqual(get("/healthz")[0], 200)
            self.assertEqual(get("/readyz")[0], 503)
            self.assertEqual(json.loads(get("/version")[1])["version"], "4.3.0")
            code, body = get("/dependencies")
            self.assertIn("INV-27", json.loads(body)["dependencies"])
            self.assertEqual(get("/metrics")[0], 200)
            self.assertEqual(get("/explain?module=svc")[0], 200)
            self.assertEqual(get("/nope")[0], 404)
        finally:
            srv.shutdown()

    def test_alert_rules_are_complete(self):
        for rule in T.ALERT_RULES:
            self.assertTrue({"alert", "severity", "class", "expr", "for", "action"} <= set(rule))
        self.assertIn("SEV1", {r["severity"] for r in T.ALERT_RULES})
        for code in ("INV29-OK", "INV29-E-LAYER", "INV29-E-IMPORT", "INV29-E-REPLAY", "INV29-E-DEPENDENCY"):
            self.assertIn(code, T.EXPLANATIONS)


if __name__ == "__main__":
    unittest.main()
