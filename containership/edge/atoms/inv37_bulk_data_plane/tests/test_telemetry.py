"""Telemetry primitives (C072-C079)."""
from __future__ import annotations

import io
import json
import unittest

from _support import pkg

T = pkg.telemetry


class TelemetryTest(unittest.TestCase):
    def test_traceparent(self):
        tp = "00-" + "1" * 32 + "-" + "2" * 16 + "-01"
        c = T.TraceContext.parse(tp)
        self.assertEqual((c.trace_id, c.span_id, c.sampled), ("1" * 32, "2" * 16, True))
        ch = c.child()
        self.assertEqual(ch.trace_id, c.trace_id)
        self.assertNotEqual(ch.span_id, c.span_id)
        for bad in (None, "", "00-" + "0" * 32 + "-" + "2" * 16 + "-01", "ff-xyz", "00-" + "G" * 32 + "-" + "2" * 16 + "-01"):
            self.assertEqual(len(T.TraceContext.parse(bad).trace_id), 32)

    def test_logger_redacts_and_levels(self):
        s = io.StringIO()
        lg = T.StructuredLogger(node="n1", stream=s, level="info")
        lg.log("debug", "x", "hidden")
        lg.log("info", "op", "m", tenant="t_1", payload="SECRETBYTES", token="abc", size=3)
        rec = json.loads(s.getvalue())
        self.assertEqual(rec["payload"], "<redacted>")
        self.assertEqual(rec["token"], "<redacted>")
        self.assertEqual(rec["size"], 3)
        for k in ("node", "component", "op", "tenant", "workload", "transfer_id", "trace_id"):
            self.assertIn(k, rec)
        self.assertNotIn("SECRETBYTES", s.getvalue())

    def test_percentiles(self):
        h = T.Histogram()
        for i in range(1, 101):
            h.observe(i)
        p = h.percentiles()
        self.assertEqual((p["p50"], p["p95"], p["p99"], p["max"]), (51, 95, 99, 100))

    def test_prometheus_and_pseudonym(self):
        m = T.Metrics()
        m.inc("x_total", reason="a")
        m.observe("lat", 0.1)
        text = m.prometheus()
        self.assertIn('inv37_x_total{reason="a"} 1', text)
        self.assertIn("inv37_lat_p99", text)
        a, b = T.pseudonym(b"k", "acme"), T.pseudonym(b"k2", "acme")
        self.assertNotEqual(a, b)
        self.assertNotIn("acme", a)

    def test_lineage(self):
        lin = T.release_lineage()
        self.assertEqual(lin["version"], pkg.__version__)
        self.assertTrue(lin["source_digest"].startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
