"""Observability and explainability (C071-C080, C091)."""
import json
import unittest

from _util import m, PKG_DIR, rt as make_rt

status = m("status")
telemetry = m("telemetry")
wire = m("wire")
alerts = m("alerts")
future = m("future")
errors = m("errors")


class StatusTest(unittest.TestCase):
    def test_status_schema_and_content(self):
        """REQ: C071 INV18-OPS-001"""
        rt = make_rt()
        w, r = rt.create(int)
        s = status.status(rt)
        self.assertEqual(wire.validate(s, "PK_FUTURE_STATUS/1"), [])
        self.assertEqual(s["version"], m().__version__)
        self.assertTrue(s["ready"])
        self.assertEqual(s["outstanding"], 1)
        self.assertIn("PK_FUTURE/1", s["contract_versions"])
        self.assertIn("max_outstanding", s["limits"])
        blob = json.dumps(s)
        self.assertNotIn(w.token, blob)
        self.assertNotIn(r.token, blob)

    def test_status_compatibility_fields_stable(self):
        """REQ: C071 C016"""
        snap = json.loads((PKG_DIR / "conformance/API_SNAPSHOT.json").read_text())
        for f in snap["required"]["PK_FUTURE_STATUS/1"]:
            self.assertIn(f, status.status(make_rt()))


class ExplainTest(unittest.TestCase):
    def test_operator_can_diagnose_predefined_incidents(self):
        """REQ: C077 C052 C097"""
        now = [0.0]
        rt = m("runtime").Runtime(m("config").ConfigStore({"environment": "test", "max_outstanding": 10,
                                                           "soft_outstanding": 5, "max_per_tenant": 10,
                                                           "stall_threshold_s": 1.0}), clock=lambda: now[0],
                                  log_sink=lambda s: (_ for _ in ()).throw(OSError("down")))
        caps = [rt.create(int) for _ in range(8)]
        now[0] = 5.0
        try:
            rt.resolve(caps[0][0], "bad")
        except TypeError:
            pass
        rt.disable(rt.admin_capability(), scope="tenant:x")
        text = status.explain(rt)
        for needle in ("WHY NOT HEALTHY", "SOFT_LIMIT_EXCEEDED", "STALLED_FUTURES", "TELEMETRY_SINK_UNAVAILABLE",
                       "DISABLED", "capacity warning", "config revision", "TYPE_MISMATCH", "audit head",
                       "policy          : INV18-PREC/1"):
            self.assertIn(needle, text)
        rt.record_invariant_violation("synthetic")
        self.assertIn("SEV1", status.explain(rt))


class LogTest(unittest.TestCase):
    def test_log_schema_and_identifiers(self):
        """REQ: C073 INV18-OPS-006"""
        rt = make_rt()
        w, r = rt.create(int, tenant="acme")
        try:
            rt.resolve(w, "x")
        except TypeError:
            pass
        rec = rt.log.records[-1]
        self.assertEqual(telemetry.validate_log(rec), [])
        self.assertEqual(rec["code"], "TYPE_MISMATCH")
        self.assertEqual(rec["future_id"], w.future_id)
        self.assertIsNotNone(rec["trace_id"])
        self.assertTrue(rec["config_revision"].startswith("cfg-"))
        self.assertNotEqual(rec["tenant"], "acme")                   # hashed under privacy policy
        self.assertEqual(rec["component"], "INV-18")

    def test_payloads_not_logged(self):
        """REQ: C073 C075 C039 INV18-SEC-004 — T15"""
        log = telemetry.StructuredLog(component="INV-18", version="x")
        rec = log.emit("info", "op", payload="RAW-PAYLOAD", value="RAW-VALUE", secret_token="SENTINEL-SECRET-1")
        blob = json.dumps(rec)
        for s in ("RAW-PAYLOAD", "RAW-VALUE", "SENTINEL-SECRET-1"):
            self.assertNotIn(s, blob)
        self.assertEqual(telemetry.validate_log(rec), [])

    def test_rate_limit_and_severity(self):
        """REQ: C073 C075 C079"""
        t = [0.0]
        log = telemetry.StructuredLog(component="INV-18", version="x", rate_per_s=5, clock=lambda: t[0])
        out = [log.emit("info", "op") for _ in range(20)]
        self.assertEqual(sum(1 for o in out if o), 5)
        self.assertIsNotNone(log.emit("error", "op"))               # errors are exempt
        self.assertEqual(log.emit("bogus", "op")["severity"], "error")
        t[0] = 2.0
        self.assertIsNotNone(log.emit("info", "op"))


class TraceTest(unittest.TestCase):
    def test_untrusted_trace_context(self):
        """REQ: C074"""
        good = "00-" + "1" * 32 + "-" + "2" * 16 + "-01"
        tc = telemetry.TraceContext.parse(good)
        self.assertEqual((tc.trace_id, tc.parent_id), ("1" * 32, "2" * 16))
        for bad in (None, "", "garbage", "00-" + "0" * 32 + "-" + "2" * 16 + "-01", good + "x",
                    "00-" + "G" * 32 + "-" + "2" * 16 + "-01", "00-" + "1" * 32 + "-" + "2" * 16 + "-01;evil=1"):
            t2 = telemetry.TraceContext.parse(bad)
            self.assertNotEqual(t2.trace_id, "0" * 32)
            self.assertRegex(t2.header(), r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")

    def test_trace_continuity_across_wire(self):
        """REQ: C074 C083"""
        rt = make_rt()
        auth, adapters = m("auth"), m("adapters")
        kr = auth.KeyRing(); kr.add("k", b"k" * 32)
        au = auth.Authenticator(kr)
        cli = adapters.RemoteClient(adapters.Link(adapters.RemoteEndpoint(rt, au)), au, "t", ["create", "inspect"])
        created = cli.create("int")["result"]
        self.assertEqual(created["traceparent"].split("-")[1], cli.trace.trace_id)
        entry = rt._entries[created["future_id"]]
        self.assertEqual(entry.trace.trace_id, cli.trace.trace_id)


class DecisionTest(unittest.TestCase):
    def test_decision_records_complete(self):
        """REQ: C076"""
        for reason in telemetry.DECISION_REASONS:
            d = telemetry.DecisionLog(4).record(reason, code="X", config_revision="cfg-1", policy_version="p",
                                                correlation_id="c", token="SENTINEL-SECRET-9")
            self.assertEqual(d["schema"], "PK_FUTURE_DECISION/1")
            self.assertNotIn("SENTINEL-SECRET-9", json.dumps(d))


class LineageTest(unittest.TestCase):
    def test_event_to_release_chain(self):
        """REQ: C078"""
        rt = make_rt()
        start = rt.audit.events[0]
        self.assertEqual(start["action"], "runtime.start")
        cfg_rev = start["details"]["config_revision"]
        self.assertEqual(cfg_rev, rt.config.active().revision_id)
        lin_p = PKG_DIR / "conformance/LINEAGE.json"
        if lin_p.exists():
            lin = json.loads(lin_p.read_text())
            self.assertEqual(status.status(rt)["lineage"]["release_id"], lin["release_id"])
            self.assertTrue(lin["artifact_digest"])
            self.assertIn("source_commit", lin)
        rb = rt.config.activate({**dict(rt.config.values()), "trace_sampling": 0.3}, author="x")
        rt.config.rollback(author="op", reason="lineage")
        self.assertIsNotNone(rt.config.active().rollback_of)       # lineage preserved through rollback


class AlertTest(unittest.TestCase):
    def _fired(self, fn):
        mt = telemetry.Metrics()
        fn(mt)
        return {a["id"] for a in alerts.evaluate(mt)}

    def test_alerts_distinguish_conditions(self):
        """REQ: C080"""
        def normal(mt):
            mt.inc("inv18_futures_created_total", 100000); mt.inc("inv18_takes_total", 99000)
            for _ in range(100):
                mt.observe("inv18_resolution_latency_seconds", 0.00005)
        self.assertEqual(self._fired(normal), set())                 # high load alone is not an alert
        self.assertIn("A1-invariant", self._fired(lambda mt: mt.inc("inv18_invariant_violations_total")))
        self.assertIn("A4-saturation", self._fired(lambda mt: mt.inc("inv18_limit_hits_total", limit="process")))
        self.assertIn("A5-tenant-abuse", self._fired(lambda mt: mt.inc("inv18_limit_hits_total", 60, limit="tenant")))
        self.assertIn("A6-auth-attack", self._fired(lambda mt: mt.inc("inv18_rejections_total", 30, code="REPLAY_DETECTED")))
        self.assertIn("A7-policy-rejection", self._fired(lambda mt: mt.inc("inv18_rejections_total", code="PERMISSION_DENIED")))
        self.assertIn("A8-dependency", self._fired(lambda mt: mt.inc("inv18_telemetry_dropped_total", sink="log_sink")))
        def abandon(mt):
            mt.inc("inv18_futures_created_total", 100); mt.inc("inv18_abandonments_total", 10, reason="writer_dropped")
        self.assertIn("A3-abandonment-abnormal", self._fired(abandon))
        def slow(mt):
            for _ in range(100):
                mt.observe("inv18_resolution_latency_seconds", 0.01)
        self.assertIn("A9-slo-latency", self._fired(slow))

    def test_every_alert_has_severity_and_runbook(self):
        """REQ: C080 C097"""
        ops = (PKG_DIR / "docs/OPERATIONS.md").read_text().lower()
        for r in alerts.load_rules():
            self.assertIn(r["severity"], ("SEV1", "SEV2", "SEV3", "SEV4"))
            anchor = r["runbook"].split("#")[1]
            self.assertIn(anchor.replace("-", " ")[:10].split(" ")[0], ops)
        dash = json.loads((PKG_DIR / "dashboards/inv18_dashboard.json").read_text())
        for p in dash["panels"]:
            for metric in p.get("metrics", []):
                self.assertIn(metric, telemetry.METRICS)


class TelemetryPolicyTest(unittest.TestCase):
    def test_policy_maps_to_configuration(self):
        """REQ: C079"""
        doc = (PKG_DIR / "docs/OBSERVABILITY.md").read_text()
        config = m("config")
        for key in ("trace_sampling", "telemetry_queue_max", "diagnostics_privileged"):
            self.assertIn(key, doc)
            self.assertIn(key, config.SCHEMA)
        self.assertIn("TP/1", doc)


class SloTest(unittest.TestCase):
    def test_slo_report_from_telemetry(self):
        """REQ: C091"""
        rt = make_rt()
        for _ in range(50):
            w, r = rt.create(int); rt.resolve(w, 1); rt.take(r)
        rep = m("slo").report(rt)
        self.assertTrue(rep["at_most_once"]["met"])
        self.assertEqual(rep["resolution_latency"]["total"], 50)
        self.assertGreaterEqual(rep["resolution_latency"]["sli"], 0.0)
        self.assertIn("burn_rate", rep["resolution_latency"])


if __name__ == "__main__":
    unittest.main()
