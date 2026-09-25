"""C072 / C073 / C074 / C075 / C079 observability tests."""
import importlib
import io
import json
import unittest

import _path
t = importlib.import_module(_path.PKG + ".telemetry")


class MetricsTests(unittest.TestCase):
    def test_counters_hist_exposition(self):
        m = t.Metrics()
        m.inc("runs", status="ok")
        m.inc("runs", status="ok")
        m.observe("fuel_used", 7)
        self.assertEqual(m.value("runs", status="ok"), 2)
        text = m.exposition()
        self.assertIn('inv70_runs_total{status="ok"} 2', text)
        self.assertIn('inv70_fuel_used_bucket{le="10"} 1', text)

    def test_label_allowlist_and_cardinality_cap(self):
        m = t.Metrics()
        with self.assertRaises(ValueError):
            m.inc("runs", run_id="abc")
        m.MAX_SERIES = 3
        for i in range(10):
            m.inc("runs", tenant=str(i))
        self.assertEqual(len(m.counters), 3)
        self.assertEqual(m.dropped_series, 7)


class LogTests(unittest.TestCase):
    def test_required_fields_and_redaction(self):
        sink = io.StringIO()
        log = t.StructuredLog("4.3.0", sink=sink)
        rec = log.emit("info", "x", run_id="r1", trace_id="t1", token="abc", program=[1], note="fine")
        for f in t.StructuredLog.REQUIRED:
            self.assertIn(f, rec)
        self.assertEqual((rec["token"], rec["program"], rec["note"]), ("<redacted>", "<redacted>", "fine"))
        self.assertEqual(json.loads(sink.getvalue())["run_id"], "r1")

    def test_bounded(self):
        log = t.StructuredLog("v", capacity=5)
        for i in range(20):
            log.emit("info", "e", run_id=str(i), trace_id="t")
        self.assertEqual(len(log.records), 5)


class TraceTests(unittest.TestCase):
    def test_propagation(self):
        h = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        c = t.TraceContext.from_header(h)
        self.assertEqual((c.trace_id, c.parent_span_id, c.sampled), ("a" * 32, "b" * 16, True))
        self.assertTrue(c.header().startswith("00-" + "a" * 32))
        self.assertEqual(c.child().trace_id, c.trace_id)

    def test_malformed_restarts(self):
        for h in (None, "", "garbage", "00-" + "0" * 32 + "-" + "b" * 16 + "-01", "01-" + "a" * 32 + "-" + "b" * 16 + "-01"):
            c = t.TraceContext.from_header(h)
            self.assertEqual(len(c.trace_id), 32)
            self.assertIsNone(c.parent_span_id)


class DiagTests(unittest.TestCase):
    def test_opt_in_ttl_rate_redaction(self):
        now = [0.0]
        d = t.DiagnosticChannel(max_per_minute=2, clock=lambda: now[0])
        self.assertFalse(d.record("t1", a=1))
        d.enable("t1", 10)
        self.assertTrue(d.record("t1", secret_key="s", a=1))
        self.assertTrue(d.record("t1", a=2))
        self.assertFalse(d.record("t1", a=3))
        self.assertEqual(d.suppressed, 1)
        self.assertEqual(d.buffer[0]["secret_key"], "<redacted>")
        self.assertNotEqual(d.buffer[0]["tenant"], "t1")
        now[0] = 11
        self.assertFalse(d.record("t1", a=4))
        with self.assertRaises(ValueError):
            d.enable("t1", 99999)


class PolicyTests(unittest.TestCase):
    def test_policy_complete(self):
        for k in ("metrics", "logs", "traces", "diagnostics", "privacy", "export"):
            self.assertIn(k, t.TELEMETRY_POLICY)
        for k in ("metrics", "logs", "traces", "diagnostics"):
            self.assertGreater(t.TELEMETRY_POLICY[k]["retention_days"], 0)


if __name__ == "__main__":
    unittest.main()
