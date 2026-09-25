"""GAP-018 audit chain, GAP-019 health/metrics export, GAP-020 privacy/retention/explain."""
import json, os, tempfile, unittest
from _support import AUDIT_KEY, E, AuditLog, build, ctx
from inv21_local_service_chaining.audit import read_jsonl, verify
from inv21_local_service_chaining.telemetry import DecisionLedger, Metrics


class AuditTest(unittest.TestCase):
    def _log(self, path=None):
        log = AuditLog(AUDIT_KEY, lineage={"release": "4.3.0", "config": "abc"}, path=path)
        for i in range(5):
            log.append("decision", n=i)
        return log

    def test_verifies_and_detects_every_tamper_class(self):
        log = self._log(); recs = log.records()
        self.assertTrue(verify(recs, AUDIT_KEY)["ok"])
        edit = [dict(r) for r in recs]; edit[2]["n"] = 99
        self.assertEqual(verify(edit, AUDIT_KEY)["why"], "mac")
        self.assertEqual(verify(recs[:2] + recs[3:], AUDIT_KEY)["why"], "sequence_gap")
        swap = recs[:]; swap[1], swap[2] = swap[2], swap[1]
        self.assertFalse(verify(swap, AUDIT_KEY)["ok"])
        self.assertFalse(verify(recs, b"x" * 32)["ok"])
        self.assertEqual(verify(recs[:-1], AUDIT_KEY, expected_head=log.head())["why"],
                         "head_mismatch_truncation")

    def test_durable_file_sink(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "audit.jsonl")
            log = self._log(p); log.close()
            self.assertTrue(verify(read_jsonl(p), AUDIT_KEY, expected_head=log.head())["ok"])
            self.assertEqual(read_jsonl(p)[0]["kind"], "genesis")

    def test_sink_failure_fails_closed(self):
        log = self._log()
        class Broken:
            def write(self, *_): raise OSError("disk full")
            def flush(self): pass
            def fileno(self): return -1
        log._fh = Broken()
        with self.assertRaises(E.InternalError):
            log.append("decision")
        self.assertEqual(log.sink_errors, 1)

    def test_refusals_and_grants_audited_without_payload(self):
        ch, res, prov, v = build(grants=[("acme", "svc", "invoke")])
        res.place("svc", "acme", lambda hop, r: "ok", abi="hop")
        ch.invoke("svc", {"card": "4111-SECRET"}, ctx(v))
        with self.assertRaises(E.CapabilityRefused):
            ch.invoke("nope", {"card": "4111-SECRET"}, ctx(v, trace="t-2"))
        dump = json.dumps(ch.audit.records())
        self.assertNotIn("SECRET", dump); self.assertNotIn("svc-a", dump)  # subject pseudonymised
        self.assertTrue(verify(ch.audit.records(), AUDIT_KEY)["ok"])


class TelemetryTest(unittest.TestCase):
    def test_prometheus_export_and_cardinality_cap(self):
        m = Metrics(max_label_values=3, max_series=50)
        for i in range(10):
            m.inc("hops", callee=f"c{i}")
        text = m.prometheus()
        self.assertIn('inv21_hops_total{callee="__other__"} 7', text)
        m.observe_us("lat", 3); m.observe_us("lat", 10 ** 7)
        self.assertIn('inv21_lat_bucket{le="+Inf"} 2', m.prometheus())
        for i in range(100):
            m.inc(f"s{i}")
        self.assertGreater(m.dropped_series, 0)
        self.assertIn('\\"', Metrics()._label and __import__("inv21_local_service_chaining.telemetry",
                      fromlist=["_esc"])._esc('a"b'))

    def test_health_readiness_and_dependency_status(self):
        ch, res, prov, v = build()
        h = ch.health()
        self.assertTrue(h["ready"]); self.assertEqual(h["mode"], "production")
        self.assertTrue(h["dependencies"]["policy_authoritative"])
        self.assertIn("inv21_ready 1", ch.export_metrics())
        self.assertIn("inv21_saturation_ratio", ch.export_metrics())
        ch.audit.sink_errors = 1
        self.assertFalse(ch.health()["ready"])

    def test_sampling_keeps_refusals_retention_and_explain(self):
        led = DecisionLedger(max_events=3, sample_rate=0.0, max_age_s=1000)
        from inv21_local_service_chaining.telemetry import DecisionEvent
        import time
        led.record(DecisionEvent("a", "t", "x", "local", "r", 0, 1, ts=time.time()))
        led.record(DecisionEvent("a", "t", "x", "refused", "cycle", 0, 1, ts=time.time()))
        self.assertEqual([e.route for e in led.events()], ["refused"])
        self.assertEqual(led.sampled_out, 1)
        led.record(DecisionEvent("a", "t", "old", "refused", "r", 0, 1, ts=time.time() - 5000))
        self.assertEqual(len(led.explain("old")), 0)
        self.assertTrue(led.redact("alice").startswith("p-")); self.assertNotIn("alice", led.redact("alice"))

    def test_explain_view_over_chain(self):
        ch, res, prov, v = build(grants=[("acme", "a", "invoke"), ("acme", "b", "invoke")])
        res.place("b", "acme", lambda hop, r: 1, abi="hop")
        res.place("a", "acme", lambda hop, r: hop.call("b", r), abi="hop")
        ch.invoke("a", {}, ctx(v, trace="tr-9"))
        ex = ch.explain("tr-9")
        self.assertEqual([(e["callee"], e["depth"], e["route"]) for e in ex], [("a", 0, "local"), ("b", 1, "local")])


if __name__ == "__main__":
    unittest.main()
