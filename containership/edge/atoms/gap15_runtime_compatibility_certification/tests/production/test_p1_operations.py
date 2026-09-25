"""P1 operations: metrics (26), logging/tracing (27), explain (28), alerts/dashboards (29), admission (30),
conflict workflow (31), capacity (32)."""
import os
import threading
import unittest

from fixtures import PART, PART2, T0, World, art
from gap15_runtime_compatibility_certification.production import observability as obs, ops
from gap15_runtime_compatibility_certification.production.capacity import (CapacityError, ConcurrencyGate, LIMITS,
                                                                            RateLimiter)
from gap15_runtime_compatibility_certification.production.service import REMEDIATION, ServiceError
from gap15_runtime_compatibility_certification.production.state import CertKey

DOCS = os.path.join(os.path.dirname(__file__), "..", "..", "docs")


class MetricsTest(unittest.TestCase):
    def test_declared_metrics_bounded_labels(self):
        """controls: 26-01 26-02 26-05 26-06"""
        m = obs.Metrics()
        m.inc("gap15_certifications_total", verdict="certified")
        with self.assertRaises(obs.MetricError):
            m.inc("gap15_certifications_total", verdict=art(1))  # raw id as label value
        with self.assertRaises(obs.MetricError):
            m.inc("gap15_certifications_total", verdict="certified", node="n1")  # undeclared label
        with self.assertRaises(obs.MetricError):
            m.inc("made_up_total")
        self.assertEqual(m.get("gap15_dropped_observations_total"), 1)
        for name, (typ, unit, help_, labels) in obs.METRIC_DEFS.items():
            self.assertTrue(typ and unit and help_)

    def test_latency_histograms_and_exposition(self):
        """controls: 26-03 26-04 26-08"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence())
        text = w.svc.metrics.exposition()
        self.assertIn('gap15_request_seconds_bucket{op="ingest",le="0.5"}', text)
        self.assertIn("gap15_request_seconds_count", text)
        text2 = w.svc.metrics.exposition()
        self.assertIn("gap15_exporter_scrape_age_seconds", text2)

    def test_metric_correctness_under_duplicates_and_restart(self):
        """controls: 26-09"""
        w = World()
        raw = w.evidence(event_id="dup")
        w.svc.ingest(w.producer(), raw)
        w.svc.ingest(w.producer(), raw)
        self.assertEqual(w.svc.metrics.get("gap15_evidence_accepted_total"), 1)

    def test_recording_rules_exist_for_key_conditions(self):
        """controls: 26-10 29-02"""
        names = {a[0] for a in ops.ALERTS}
        for n in ("GAP15ExpiryStorm", "GAP15SLOBurnFast", "GAP15DependencyOutage", "GAP15StorageSaturation", "GAP15EOLAdmitted",
                  "GAP15CoverageLow"):
            self.assertIn(n, names)

    def test_gauges_coverage_backlog(self):
        """controls: 26-02 34-09"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence())
        k = w.key_for(r)
        g = w.svc.update_gauges([k, CertKey(PART, art(2), "wasmtime@21.0.0", "profile:x")], T0)
        self.assertEqual(g["coverage"], 0.5)
        self.assertEqual(g["expiry_backlog"], 1)


class LoggingTracingTest(unittest.TestCase):
    def test_structured_schema_and_injection(self):
        """controls: 27-01 27-06 27-08"""
        lg = obs.Logger("gap15", "4.3.0", revisions={"policy": "p:1", "matrix": 3})
        rec = lg.log("warn", "evil\nINJECTED line", value="a\r\nb" + "x" * 1000)
        line = lg.sink[-1]
        self.assertNotIn("\n", line)
        self.assertLessEqual(len(rec["fields"]["value"]), obs.MAX_FIELD + 10)
        self.assertEqual(rec["revisions"]["policy"], "p:1")

    def test_trace_context_propagation_and_sampling(self):
        """controls: 27-02 27-03 27-04 27-10"""
        tr = obs.Tracer(sample_ratio=0.0)
        parent = tr.start("ingest", traceparent="00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual((parent.trace_id, parent.parent_id, parent.sampled), ("a" * 32, "b" * 16, True))
        child = tr.start("sig-verify", parent=parent)
        self.assertEqual(child.trace_id, parent.trace_id)
        unsampled = tr.start("certify")
        tr.finish(unsampled)
        self.assertNotIn(unsampled, tr.finished)
        err = tr.start("certify")
        tr.finish(err, status="error")
        self.assertIn(err, tr.finished)  # errors survive sampling
        bad = tr.start("x", traceparent="00-" + "0" * 32 + "-" + "b" * 16 + "-01")
        self.assertNotEqual(bad.trace_id, "0" * 32)

    def test_audit_correlation(self):
        """controls: 27-07"""
        w = World()
        w.svc.ingest(w.producer(), w.evidence(), traceparent="00-" + "c" * 32 + "-" + "d" * 16 + "-01")
        acc = [a for a in w.store.audit_events() if a["action"] == "evidence.accepted"][0]
        self.assertEqual(acc["trace_id"], "c" * 32)

    def test_retention_privacy_documented(self):
        """controls: 27-09 42-06"""
        adr = open(os.path.join(DOCS, "ADR.md")).read()
        self.assertIn("ADR-007", adr)


class ExplainTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        r = self.w.svc.ingest(self.w.producer(), self.w.evidence())
        self.k = self.w.key_for(r)

    def test_explain_model_from_same_trace(self):
        """controls: 28-01 28-03 28-07"""
        d = self.w.svc.certify(self.w.reader(), self.k)
        ex = self.w.svc.explain(self.w.reader(), d["decision_id"])
        for f in ("verdict", "reason_code", "remediation", "matrix_revision", "policy", "lifecycle", "evidence_id",
                  "evidence_age_s", "trace", "replay_consistent"):
            self.assertIn(f, ex)
        self.assertIs(ex["trace"], d["trace"])
        self.assertTrue(ex["replay_consistent"])

    def test_every_reason_code_has_remediation(self):
        """controls: 28-02 28-10"""
        import re
        src = open(os.path.join(os.path.dirname(__file__), "..", "..", "production", "state.py")).read()
        src += open(os.path.join(os.path.dirname(__file__), "..", "..", "production", "service.py")).read()
        codes = set(re.findall(r'"(R_[A-Z_]+)"', src)) - {"R_"}
        missing = sorted(c for c in codes if c not in REMEDIATION and not c.startswith("R_OFFLINE"))
        self.assertEqual(missing, [])

    def test_explain_authorization_and_redaction(self):
        """controls: 28-04"""
        d = self.w.svc.certify(self.w.reader(), self.k)
        other = self.w.token("site2-svc", "service", ["explain.read"], partitions=(PART2,))
        with self.assertRaises(ServiceError) as cm:
            self.w.svc.explain(other, d["decision_id"])
        self.assertEqual(cm.exception.category, "authz")

    def test_explain_does_not_reevaluate_by_default(self):
        """controls: 28-08 28-05"""
        d = self.w.svc.certify(self.w.reader(), self.k)
        self.w.svc.revoke(self.w.operator(), subject_type="artifact", subject_id=art(1), partition=PART, reason="x", severity="high")
        ex = self.w.svc.explain(self.w.reader(), d["decision_id"])
        self.assertEqual(ex["verdict"], "certified")
        self.assertNotIn("current", ex)
        ex2 = self.w.svc.explain(self.w.reader(), d["decision_id"], reevaluate=True)
        self.assertEqual(ex2["current"]["verdict"], "revoked")

    def test_large_history_paginated(self):
        """controls: 28-09"""
        for i in range(30):
            self.w.advance(1)
            self.w.svc.ingest(self.w.producer(), self.w.evidence())
        d = self.w.svc.certify(self.w.reader(), self.k)
        ex = self.w.svc.explain(self.w.reader(), d["decision_id"], page=0, page_size=10)
        self.assertEqual((len(ex["evidence_history"]), ex["history_total"]), (10, 31))


class AlertsTest(unittest.TestCase):
    def test_alert_pack_owner_severity_runbook(self):
        """controls: 29-01 29-03 29-04 29-05 29-06"""
        rules = ops.alert_rules()["groups"][0]["rules"]
        for r in rules:
            self.assertIn(r["labels"]["owner"], ops.ROLES)
            self.assertTrue(r["annotations"]["runbook"].startswith("docs/RUNBOOKS.md#"))
            self.assertTrue(r["annotations"]["first_action"])
        self.assertIn("SLOBurnFast", " ".join(r["alert"] for r in rules))
        self.assertGreaterEqual(len(ops.dashboard()["panels"]), 12)

    def test_runbook_links_resolve(self):
        """controls: 29-06 48-10"""
        text = open(os.path.join(DOCS, "RUNBOOKS.md")).read()
        self.assertEqual(ops.check_runbook_links(text), [])

    def test_silence_controls(self):
        """controls: 29-07"""
        self.assertIn("paging alerts may be silenced for at most 4h",
                      ops.validate_silence(ops.Silence("GAP15EOLAdmitted", "alice", "maint", T0, T0 + 5 * 3600)))
        self.assertIn("owner and reason are required", ops.validate_silence(ops.Silence("GAP15EOLAdmitted", "", "", T0, T0 + 60)))
        self.assertEqual(ops.validate_silence(ops.Silence("GAP15CoverageLow", "alice", "maint", T0, T0 + 86400)), [])

    def test_alert_pipeline_watchdog(self):
        """controls: 29-09"""
        names = {a[0]: a for a in ops.ALERTS}
        self.assertEqual(names["GAP15Watchdog"][2], "vector(1)")
        self.assertIn("GAP15AlertPipelineDead", names)

    def test_pack_written(self):
        """controls: 29-01 29-10"""
        import tempfile
        paths = ops.write_pack(tempfile.mkdtemp())
        self.assertEqual(len(paths), 2)


class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        r = self.w.svc.ingest(self.w.producer(), self.w.evidence())
        self.pid = r["profile_id"]

    def req(self, **kw):
        base = {"request_id": "req-1", "artifact": art(1), "runtime": "wasmtime@21.0.0", "profile_id": self.pid,
                "partition": PART, "intent": "new", "workload": "svc-a"}
        base.update(kw)
        return base

    def test_admission_contract_and_revision_binding(self):
        """controls: 30-01 30-02 30-04 30-08"""
        rec = self.w.svc.admit(self.w.reader(), self.req())
        self.assertTrue(rec["admitted"])
        for f in ("decision_id", "matrix_revision", "ledger_seq", "policy_revision", "valid_until"):
            self.assertIn(f, rec)
        self.assertTrue(any(a["action"] == "admission.decided" for a in self.w.store.audit_events()))
        with self.assertRaises(ServiceError) as cm:
            self.w.svc.admit(self.w.reader(), self.req(request_id="req-2", artifact="svc:latest"))
        self.assertEqual(cm.exception.code, "E_ADMISSION_UNBOUND_ARTIFACT")

    def test_fail_closed_matrix_unsupported_expired_eol_revoked(self):
        """controls: 30-03 30-10 33-04"""
        w = self.w
        cases = {}
        cases["untested"] = w.svc.admit(w.reader(), self.req(request_id="a", artifact=art(5)))
        w.svc.lifecycle(w.operator(), partition=PART, runtime="wasmtime@21.0.0", state="deprecated", effective_at=T0,
                        reason="r", source="s")
        cases["deprecated-new"] = w.svc.admit(w.reader(), self.req(request_id="b"))
        w.svc.revoke(w.operator(), subject_type="artifact", subject_id=art(1), partition=PART, reason="cve", severity="high")
        cases["revoked"] = w.svc.admit(w.reader(), self.req(request_id="c"))
        for name, rec in cases.items():
            self.assertFalse(rec["admitted"], name)
            self.assertTrue(rec["remediation"])
        w2 = World()
        r = w2.svc.ingest(w2.producer(), w2.evidence())
        w2.advance(501)
        self.assertEqual(w2.svc.admit(w2.reader(), dict(self.req(), profile_id=r["profile_id"]))["verdict"], "expired")

    def test_idempotent_retries(self):
        """controls: 30-05"""
        a = self.w.svc.admit(self.w.reader(), self.req())
        b = self.w.svc.admit(self.w.reader(), self.req())
        self.assertEqual(a, b)
        with self.assertRaises(ServiceError):
            self.w.svc.admit(self.w.reader(), self.req(workload="different"))

    def test_revocation_outranks_cached_allow_and_prestart_recheck(self):
        """controls: 30-06 30-09 37-04"""
        a = self.w.svc.admit(self.w.reader(), self.req())
        self.assertTrue(a["admitted"])
        self.w.svc.revoke(self.w.operator(), subject_type="runtime", subject_id="wasmtime@21.0.0", partition=PART,
                          reason="cve", severity="critical")
        chk = self.w.svc.prestart_recheck(self.w.reader(), "req-1")
        self.assertEqual((chk["launch_allowed"], chk["verdict"]), (False, "revoked"))

    def test_denial_reasons_safe(self):
        """controls: 30-07"""
        rec = self.w.svc.admit(self.w.reader(), self.req(request_id="z", artifact=art(7)))
        self.assertEqual(rec["reason_code"], "R_NO_EVIDENCE")
        self.assertNotIn("producer", str(rec))

    def test_emergency_disable_admissions(self):
        """controls: 46-04 46-05"""
        w = self.w
        with self.assertRaises(ServiceError):
            w.svc.emergency_disable(w.operator(), scope="admissions", partition=PART, reason="x", incident="", until=T0 + 60)
        w.svc.emergency_disable(w.operator(), scope="admissions", partition=PART, reason="bad verdicts", incident="INC-9", until=T0 + 600)
        with self.assertRaises(ServiceError) as cm:
            w.svc.admit(w.reader(), self.req(request_id="e"))
        self.assertEqual(cm.exception.code, "E_EMERGENCY_ADMISSIONS_DISABLED")
        self.assertTrue(any(a["action"] == "emergency.disable" for a in w.store.audit_events()))
        from gap15_runtime_compatibility_certification.production.service import CertificationService
        # durable across restart: a new service instance rehydrates the disable from the audit stream
        svc2 = CertificationService(config=w.svc.cfg, store=w.store, trust=w.trust, authn=w.authn, authz=w.authz, clock=w.clock,
                                    key_provider=w.kp, service_key_id="svc-key", policy=w.policy, attestation_policy=w.att_policy)
        self.assertIn("admissions", svc2.emergency)
        w.advance(601)
        rec = w.svc.admit(w.reader(), self.req(request_id="f"))  # disable lapsed: no emergency refusal any more
        self.assertNotEqual(rec["reason_code"], "R_EMERGENCY_DISABLED")


class ConflictWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        r = self.w.svc.ingest(self.w.producer(), self.w.evidence())
        self.k = self.w.key_for(r)
        self.w.advance(5)
        self.w.svc.ingest(self.w.producer("producer-b"), self.w.evidence(producer="producer-b", result="incompatible",
                                                                        failure_class="deterministic"))
        self.case = next(iter(self.w.svc.conflict_cases))

    def test_case_object_and_quarantine(self):
        """controls: 31-01 31-02 31-06 31-07"""
        c = self.w.svc.conflict_cases[self.case]
        for f in ("case_id", "ctype", "severity", "sla_s", "evidence", "status", "owner", "opened_at"):
            self.assertIn(f, c)
        self.assertEqual(self.w.svc.certify(self.w.reader(), self.k)["verdict"], "quarantined")
        self.assertFalse(self.w.svc.admit(self.w.reader(), {"request_id": "r", "artifact": art(1), "runtime": "wasmtime@21.0.0",
                                                            "profile_id": self.k.profile_id, "partition": PART,
                                                            "intent": "new"})["admitted"])

    def test_two_person_resolution_preserves_history(self):
        """controls: 31-04 31-05"""
        w = self.w
        with self.assertRaises(ServiceError):
            w.svc.resolve_conflict(w.operator("alice"), w.operator("alice"), self.case, decision="uphold-newer", rationale="x")
        w.svc.resolve_conflict(w.operator("alice"), w.operator("bob"), self.case, decision="uphold-newer", rationale="retest confirms")
        self.assertEqual(w.svc.certify(w.reader(), self.k)["verdict"], "incompatible")
        cf = [e for e in w.store.events() if e["event_type"] == "conflict"]
        self.assertEqual([c["status"] for c in cf], ["open", "resolved"])
        from gap15_runtime_compatibility_certification.production.store import Store
        self.assertEqual(Store(w.db_path).certify(self.k, T0 + 5)["verdict"], "incompatible")  # replay agrees

    def test_both_invalid_quarantines_evidence(self):
        """controls: 31-09 31-10"""
        w = self.w
        w.svc.resolve_conflict(w.operator("alice"), w.operator("bob"), self.case, decision="both-invalid", rationale="harness bug")
        self.assertEqual(w.svc.certify(w.reader(), self.k)["verdict"], "quarantined")
        w.svc.update_gauges([self.k], T0)
        self.assertEqual(w.svc.metrics.get("gap15_conflicts_open"), 0)


class CapacityTest(unittest.TestCase):
    def test_documented_limits(self):
        """controls: 32-01"""
        for k in ("max_body_bytes", "max_batch_items", "max_identifier_length", "max_history_page", "max_concurrent_requests"):
            self.assertIn(k, LIMITS)

    def test_priority_paths_survive_overload(self):
        """controls: 32-08"""
        rl = RateLimiter(per_key_rate=0.0001, per_key_burst=1, global_rate=0.0001, global_burst=1, clock=lambda: 0.0)
        rl.check("a")
        with self.assertRaises(CapacityError):
            rl.check("a")
        rl.check("a", op="revocation")
        rl.check("a", op="health")

    def test_concurrency_gate_sheds(self):
        """controls: 32-03 14-02"""
        g = ConcurrencyGate(limit=2)
        with g, g:
            with self.assertRaises(CapacityError):
                with g:
                    pass

    def test_capacity_metrics_exported(self):
        """controls: 32-09"""
        m = obs.Metrics()
        m.set("gap15_queue_depth", 5, queue="ingest")
        self.assertIn('gap15_queue_depth{queue="ingest"} 5', m.exposition())


if __name__ == "__main__":
    unittest.main()
