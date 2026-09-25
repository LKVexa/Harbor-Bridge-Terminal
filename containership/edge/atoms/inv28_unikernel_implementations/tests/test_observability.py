"""Health/readiness/status, metrics, logs, traces, decision ledger, explain, lineage, telemetry policy,
dashboards/alerts (MC-056..MC-066, MC-074)."""
import io
import json
import pathlib
import tempfile
import unittest

from harness import F, refusal
from inv28_unikernel_implementations.observability import MAX_SERIES, AuditLedger, Metrics, StructuredLogger, TelemetryPolicy, TraceContext

PKG = pathlib.Path(F.__file__).resolve().parent


class HealthStatus(unittest.TestCase):                                         # MC-056, MC-057
    def test_ready_world(self):
        svc = F.world()["service"]
        self.assertEqual(svc.health()["status"], "ok")
        self.assertTrue(svc.readiness()["ready"], svc.readiness())

    def test_not_ready_reasons(self):
        cases = {"no feed": (dict(with_feed=False), "advisory"), "no certs": (dict(with_certs=False), "GAP-15"),
                 "empty registry": (dict(records=[]), "registry empty")}
        for name, (kw, needle) in cases.items():
            with self.subTest(name=name):
                rd = F.world(**kw)["service"].readiness()
                self.assertFalse(rd["ready"])
                self.assertTrue(any(needle in r for r in rd["reasons"]), rd)

    def test_health_degrades_on_broken_audit_chain(self):
        w = F.world()
        w["selector"].select(F.request(), now=F.NOW)
        w["audit"]._entries[0]["kind"] = "forged"
        self.assertEqual(w["service"].health()["status"], "degraded")
        self.assertFalse(w["service"].readiness()["ready"])

    def test_status_reports_versions_and_dependencies(self):
        st = F.world()["service"].status()
        self.assertEqual(st["version"], (PKG / "VERSION").read_text().strip())
        self.assertEqual(st["registry"]["entries"], 4)
        self.assertEqual(st["policy"]["id"], "inv28-default")
        self.assertEqual(st["dependencies"]["gap15_certifications"], 5)
        self.assertFalse(st["dependencies"]["advisory_feed_stale"])
        json.dumps(st)


class MetricsTests(unittest.TestCase):                                         # MC-058, MC-061
    def test_contract_signals_emitted(self):
        w = F.world()
        w["selector"].select(F.request(), now=F.NOW)
        refusal(lambda: w["selector"].select(F.request(language="cobol"), now=F.NOW))
        w["service"].status()
        text = w["metrics"].exposition()
        for name in ("inv28_selections_total", "inv28_selection_refusals_total", "inv28_toolchains_registered",
                     "inv28_stale_reviews", "inv28_selection_latency_ms_bucket", "inv28_candidate_eliminations_total"):
            self.assertIn(name, text)
        self.assertEqual(w["metrics"].value("inv28_selections_total", toolchain="rumprun", environment="production"), 1)

    def test_undeclared_metric_or_label_refused(self):
        m = Metrics()
        with self.assertRaises(KeyError):
            m.inc("inv28_made_up")
        with self.assertRaises(KeyError):
            m.inc("inv28_selections_total", toolchain="x", environment="p", tenant="acme")

    def test_series_cap(self):
        m = Metrics()
        for i in range(MAX_SERIES + 50):
            m.inc("inv28_selections_total", toolchain=f"t{i}", environment="p")
        self.assertLessEqual(m.series_count("inv28_selections_total"), MAX_SERIES + 1)
        self.assertEqual(m.value("inv28_metric_series_dropped_total", metric="inv28_selections_total"), 50)

    def test_label_value_truncated(self):
        m = Metrics()
        m.inc("inv28_selection_refusals_total", code="X" * 500, environment="p")
        self.assertNotIn("X" * 65, m.exposition())


class Logging(unittest.TestCase):                                              # MC-059, MC-065
    def test_json_lines_with_ids_and_pseudonyms(self):
        buf = io.StringIO()
        lg = StructuredLogger(buf, pseudonym_key=b"k" * 32)
        tr = TraceContext.new()
        lg.log("info", "x", operation_id="op1", trace=tr, tenant="acme", workload_id="wl", api_token="SECRET",
               nested={"password": "p", "ok": 1})
        rec = json.loads(buf.getvalue())
        self.assertEqual(rec["trace_id"], tr.trace_id)
        self.assertEqual(rec["operation_id"], "op1")
        self.assertTrue(rec["tenant"].startswith("p:"))
        self.assertEqual(rec["api_token"], "<redacted>")
        self.assertEqual(rec["nested"]["password"], "<redacted>")
        self.assertNotIn("SECRET", buf.getvalue())
        self.assertNotIn("acme", buf.getvalue())

    def test_pseudonyms_stable_per_key(self):
        a, b = StructuredLogger(pseudonym_key=b"a" * 32), StructuredLogger(pseudonym_key=b"b" * 32)
        self.assertEqual(a.pseudonym("t"), a.pseudonym("t"))
        self.assertNotEqual(a.pseudonym("t"), b.pseudonym("t"))

    def test_bounded_fields(self):
        lg = StructuredLogger()
        rec = lg.log("info", "x", blob="y" * 10000, many=list(range(1000)))
        self.assertEqual(len(rec["blob"]), 512)
        self.assertEqual(len(rec["many"]), 64)

    def test_selection_logs(self):
        w = F.world()
        w["selector"].select(F.request(), now=F.NOW)
        refusal(lambda: w["selector"].select(F.request(language="cobol"), now=F.NOW))
        events = [json.loads(line)["event"] for line in w["logger"].lines]
        self.assertEqual(events, ["toolchain.selected", "toolchain.refused"])


class Tracing(unittest.TestCase):                                              # MC-060
    def test_propagation(self):
        parent = TraceContext.new()
        child = TraceContext.from_traceparent(parent.traceparent())
        self.assertEqual(child.trace_id, parent.trace_id)
        self.assertEqual(child.parent_span_id, parent.span_id)
        self.assertEqual(child.child().trace_id, parent.trace_id)

    def test_malformed_starts_new_trace(self):
        for bad in ("", "garbage", "00-" + "0" * 32 + "-" + "1" * 16 + "-01", None, "01-abc"):
            with self.subTest(bad=bad):
                t = TraceContext.from_traceparent(bad)
                self.assertEqual(len(t.trace_id), 32)
                self.assertEqual(t.parent_span_id, "")

    def test_trace_id_reaches_logs(self):
        w = F.world()
        tr = TraceContext.new()
        w["selector"].select(F.request(), now=F.NOW, trace=tr)
        self.assertEqual(json.loads(w["logger"].lines[-1])["trace_id"], tr.trace_id)


class LedgerExplainLineage(unittest.TestCase):                                 # MC-062, MC-063, MC-064
    def test_ledger_persists_and_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "audit.jsonl"
            led = AuditLedger(path)
            for i in range(5):
                led.append("selection", {"i": i})
            again = AuditLedger(path)
            self.assertEqual(again.head, led.head)
            self.assertEqual(again.verify(), [])
            lines = path.read_text().splitlines()
            del lines[2]
            path.write_text("\n".join(lines) + "\n")
            self.assertTrue(AuditLedger(path).verify())

    def test_every_decision_recorded(self):
        w = F.world()
        r = w["selector"].select(F.request(), now=F.NOW)
        refusal(lambda: w["selector"].select(F.request(language="cobol"), now=F.NOW))
        kinds = [e["kind"] for e in w["audit"].entries()]
        self.assertEqual(kinds[-2:], ["selection", "refusal"])
        self.assertEqual(w["audit"].find(decision_id=r.decision_id)[0]["payload"]["toolchain"], r.ref)

    def test_explain_refusal_and_policy_change_note(self):
        w = F.world()
        _, ref = refusal(lambda: w["selector"].select(F.request(language="cobol"), now=F.NOW))
        text = w["service"].explain(ref.decision_id)
        self.assertIn("Unmet constraints", text)
        self.assertIn("TC_LANGUAGE_UNSUPPORTED", text)
        from inv28_unikernel_implementations.policy import SelectionPolicy, default_policy
        base = default_policy()
        w["selector"].set_policy(SelectionPolicy(base.policy_id, 2, base.environments))
        self.assertIn("policy has changed", w["service"].explain(ref.decision_id))

    def test_explain_unknown(self):
        with self.assertRaises(Exception):
            F.world()["service"].explain("nope")

    def test_lineage_graph(self):
        w = F.world()
        r = w["selector"].select(F.request(), now=F.NOW)
        g = w["service"].lineage(r.decision_id, release_manifest_sha256="a" * 64)
        kinds = [n["kind"] for n in g["nodes"]]
        self.assertEqual(kinds, ["component_release", "policy", "registry_revision", "decision", "toolchain",
                                 "gap15_certificate"])
        self.assertEqual(g["nodes"][4]["record_digest"], r.record_digest)


class PoliciesAndDashboards(unittest.TestCase):                               # MC-065, MC-066
    def test_telemetry_policy_file_matches_code(self):
        doc = json.loads((PKG / "ops" / "TELEMETRY_POLICY.json").read_text())
        self.assertEqual(doc["policy"], TelemetryPolicy().to_dict())

    def test_alerts_reference_declared_metrics(self):
        from inv28_unikernel_implementations.observability import METRIC_LABELS
        alerts = json.loads((PKG / "ops" / "alerts.json").read_text())
        dash = json.loads((PKG / "ops" / "dashboards.json").read_text())
        self.assertGreaterEqual(len(alerts["alerts"]), 6)
        for a in alerts["alerts"]:
            self.assertTrue(any(m in a["expr"] for m in METRIC_LABELS), a["name"])
            self.assertIn(a["severity"], ("page", "ticket"))
            self.assertTrue(a["runbook"].startswith("ops/RUNBOOK.md#"))
        for p in dash["panels"]:
            self.assertTrue(any(m in p["query"] for m in METRIC_LABELS), p["title"])


class RecurringReview(unittest.TestCase):                                      # MC-074
    def test_reviews_due_and_overdue(self):
        w = F.world(records=[F.record("a", interval_days=15), F.record("b", review=False), F.record("c")])
        due = w["service"].reviews_due(F.NOW)
        self.assertEqual([d["toolchain"] for d in due], ["b@1.0.0-fixture", "a@1.0.0-fixture"])
        self.assertTrue(due[0]["overdue"])
        self.assertFalse(due[1]["overdue"])


if __name__ == "__main__":
    unittest.main()
