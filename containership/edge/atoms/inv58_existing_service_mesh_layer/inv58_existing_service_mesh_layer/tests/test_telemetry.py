"""MC-025: metrics catalogue, cardinality bounds, structured logs, trace propagation, privacy."""
from __future__ import annotations

import json
import unittest

from _support import CTRL_A, NODE, make_service, telemetry as T


class TelemetryTest(unittest.TestCase):
    def test_metric_catalogue_covers_rate_errors_latency_saturation_backlog(self):
        names = set(T.METRIC_CATALOG)
        for n in ("inv58_requests_total", "inv58_errors_total", "inv58_latency_seconds",
                  "inv58_saturation_ratio", "inv58_bypass_backlog", "inv58_inflight"):
            self.assertIn(n, names)

    def test_label_cardinality_is_bounded(self):
        m = T.Metrics(max_label_values=3)
        for i in range(10):
            m.inc("inv58_bypass_flows_total", tenant=f"t{i}")
        tenants = {c["labels"]["tenant"] for c in m.export()["counters"]}
        self.assertEqual(tenants, {"t0", "t1", "t2", T.OVERFLOW})
        with self.assertRaises(ValueError):
            m.inc("inv58_bypass_flows_total", wrong="x")

    def test_traceparent(self):
        good = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        tc = T.TraceContext.parse(good)
        self.assertEqual(tc.trace_id, "4bf92f3577b34da6a3ce929d0e0e4736")
        child = tc.child()
        self.assertEqual(child.trace_id, tc.trace_id)
        self.assertNotEqual(child.span_id, tc.span_id)
        for bad in (None, "", "01-" + good[3:], "00-" + "0" * 32 + "-00f067aa0ba902b7-01", good.upper(), good + "x"):
            self.assertIsNone(T.TraceContext.parse(bad))

    def test_service_propagates_trace_into_journal_and_logs(self):
        svc, clock, _ = make_service()
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        svc.reconcile(CTRL_A, "alpha", "a->b", 2, 1, traceparent=tp)
        self.assertEqual(svc.explain(CTRL_A, "alpha")[-1]["correlation_id"], "4bf92f3577b34da6a3ce929d0e0e4736")
        svc.report_flow(NODE, "alpha", "legacy-cron", "payments", False, traceparent=tp)
        rec = svc.log.records()[-1]
        self.assertEqual(rec["trace_id"], "4bf92f3577b34da6a3ce929d0e0e4736")

    def test_logs_have_stable_ids_and_pseudonymize_workloads(self):
        lines = []
        svc, clock, _ = make_service(log_sink=lines.append)
        svc.report_flow(NODE, "alpha", "legacy-cron-secret-host", "payments", False)
        rec = json.loads(lines[-1])
        for k in ("ts", "level", "component", "node", "tenant", "operation", "event", "trace_id"):
            self.assertIn(k, rec)
        self.assertNotIn("legacy-cron-secret-host", lines[-1])
        self.assertTrue(rec["fields"]["src"].startswith("p:"))

    def test_metrics_emitted_by_service(self):
        svc, clock, _ = make_service()
        svc.reconcile(CTRL_A, "alpha", "a->b", 3, 3)
        self.assertEqual(svc.metrics.value("inv58_requests_total", operation="reconcile", tenant="alpha", outcome="ok"), 1)
        self.assertIn("inv58_requests_total", svc.metrics.prometheus())


if __name__ == "__main__":
    unittest.main()
