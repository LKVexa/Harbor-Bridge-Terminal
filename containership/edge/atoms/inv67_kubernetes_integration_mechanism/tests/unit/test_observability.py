"""Metrics, logs, traces, health endpoint, explain view, status conditions, audit (items 13, 28, 41-45)."""
import io
import json
import logging
import unittest
import urllib.request

import _support as S

O = S.observability


class Obs(unittest.TestCase):
    def test_metrics_render_and_cardinality_cap(self):
        m = O.Metrics()
        m.inc("inv67_refused_total", {"reason": "UnsupportedField"})
        m.observe("inv67_reconcile_seconds", 0.002)
        txt = m.render()
        self.assertIn('inv67_refused_total{reason="UnsupportedField"} 1', txt)
        self.assertIn('inv67_reconcile_seconds_bucket{le="0.005"} 1', txt)
        for i in range(2100):
            m.inc("x", {"i": str(i)})
        self.assertGreater(m.dropped_series, 0)

    def test_structured_redacted_logs(self):
        buf = io.StringIO()
        lg = O.get_logger("inv67.test", buf)
        O.log(lg, logging.INFO, "hello", token="abc", ns="a")
        rec = json.loads(buf.getvalue())
        self.assertEqual(rec["msg"], "hello")
        self.assertEqual(rec["token"], "[REDACTED]")
        self.assertEqual(rec["ns"], "a")

    def test_trace_propagation(self):
        t = O.Tracer()
        with t.span("outer") as tp:
            with t.span("inner"):
                pass
        with t.span("remote", parent=tp):
            pass
        outer, inner, remote = t.spans[1], t.spans[0], t.spans[2]
        self.assertEqual(inner["trace"], outer["trace"])
        self.assertEqual(inner["parent"], outer["span"])
        self.assertEqual(remote["trace"], outer["trace"])
        self.assertIsNone(O.Tracer.parse("00-" + "0" * 32 + "-" + "0" * 16 + "-01"))
        self.assertIsNone(O.Tracer.parse("junk"))

    def test_health_endpoints(self):
        c = S.Clock()
        h = O.Health("4.3.0", stall_after=30, clock=c)
        h.checks["dep"] = lambda: True
        m = O.Metrics(); m.inc("inv67_translated_total")
        srv = h.serve(metrics=m)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            def get(p):
                with urllib.request.urlopen(base + p, timeout=5) as r:
                    return io.BytesIO(r.read())
            self.assertEqual(json.load(get("/version"))["version"], "4.3.0")
            self.assertTrue(json.load(get("/readyz"))["ok"])
            self.assertIn("inv67_translated_total", get("/metrics").read().decode())
            c.tick(31)
            with self.assertRaises(urllib.error.HTTPError) as e:
                get("/healthz")
            self.assertEqual(e.exception.code, 503)
            h.progressed()
            h.checks["dep"] = lambda: (_ for _ in ()).throw(RuntimeError())
            with self.assertRaises(urllib.error.HTTPError):
                get("/readyz")
        finally:
            srv.shutdown()
            srv.server_close()

    def test_explain_redacts(self):
        obj = {"metadata": {"namespace": "a", "name": "b", "generation": 2, "finalizers": ["f"]},
               "spec": {"template": {"spec": {"containers": [{"name": "c"}]}}},
               "status": {"phase": "Pending", "lastError": {"code": "X", "detail": {"password": "p"}}, "conditions": []}}
        e = O.explain(obj)
        self.assertEqual(e["units"], ["c"])
        self.assertNotIn('"p"', json.dumps(e))


class Conditions(unittest.TestCase):
    def test_transition_time_only_changes_on_flip(self):
        st = S.status
        c = st.set_condition([], "Ready", False, "A", "m", 1, now="2026-01-01T00:00:00Z")
        c = st.set_condition(c, "Ready", False, "B", "m2", 2, now="2026-01-02T00:00:00Z")
        self.assertEqual(c[0]["lastTransitionTime"], "2026-01-01T00:00:00Z")
        c = st.set_condition(c, "Ready", True, "C", "x" * 2000, 3, now="2026-01-03T00:00:00Z")
        self.assertEqual(c[0]["lastTransitionTime"], "2026-01-03T00:00:00Z")
        self.assertEqual(len(c[0]["message"]), 512)
        with self.assertRaises(ValueError):
            st.set_condition(c, "Bogus", True, "r", "m", 1)


class Audit(unittest.TestCase):
    def test_chain_detects_edit_reorder_delete_truncate(self):
        a = S.audit.AuditLog(hmac_key=S.KEY)
        for i in range(5):
            a.append("ctl", "act", f"t{i}", "ok", password="pw")
        recs = a.records
        self.assertTrue(S.audit.AuditLog.verify(recs, a.head, S.KEY)[0])
        self.assertEqual(recs[0]["detail"]["password"], "[REDACTED]")
        edited = [dict(r) for r in recs]; edited[2]["outcome"] = "denied"
        self.assertFalse(S.audit.AuditLog.verify(edited)[0])
        self.assertFalse(S.audit.AuditLog.verify([recs[1], recs[0]] + recs[2:])[0])
        self.assertFalse(S.audit.AuditLog.verify(recs[:2] + recs[3:])[0])
        self.assertFalse(S.audit.AuditLog.verify(recs[:-1], a.head)[0])   # tail truncation
        self.assertFalse(S.audit.AuditLog.verify(recs, a.head, b"z" * 32)[0])

    def test_persisted_reload(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "audit.jsonl")
            a = S.audit.AuditLog(p); a.append("x", "y", "z", "ok")
            b = S.audit.AuditLog(p); b.append("x", "y2", "z", "ok")
            self.assertTrue(S.audit.AuditLog.verify(b.records, b.head)[0])
            self.assertEqual(len(b.records), 2)


class Capacity(unittest.TestCase):
    def test_model_and_regression_gate(self):
        cap = S.mod("capacity")
        m = cap.Model(workers=4)
        self.assertGreater(m.throughput(), 0)
        self.assertTrue(m.saturated(m.throughput()))
        self.assertFalse(m.saturated(m.throughput() * 0.5))
        self.assertEqual(cap.regression({"t_p99_ms": 1.0, "r_per_s": 100}, {"t_p99_ms": 1.1, "r_per_s": 90}), [])
        self.assertEqual(len(cap.regression({"t_p99_ms": 1.0, "r_per_s": 100}, {"t_p99_ms": 2, "r_per_s": 10})), 2)
        self.assertTrue(cap.regression({"t_p99_ms": 1.0}, {}))


if __name__ == "__main__":
    unittest.main()
