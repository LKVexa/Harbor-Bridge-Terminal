import json
import threading
import unittest

from gap03_topology_aware_scheduler import Topology
from gap03_topology_aware_scheduler.controlplane import alerts, logpipe, metrics, privacy, tracing
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.controlplane.explain import Explain, ExplainStore
from gap03_topology_aware_scheduler.controlplane.ledger_store import LedgerStore
from gap03_topology_aware_scheduler.controlplane.transactions import SCORING_VERSION, decision_inputs
from gap03_topology_aware_scheduler.tests.cp._util import TmpCase, covers

KEY = b"k"


class Metrics(unittest.TestCase):
    @covers("MC-019", 6, 7, 12, 15, 25)
    def test_mc019_catalog_and_prometheus_export(self):
        m = metrics.Metrics()
        m.observe("gap03_score_latency_ms", 3.2, result="ok")
        m.inc("gap03_requests_total", op="score", code="OK")
        m.set("gap03_starved_tenants", 2)
        text = m.export()
        self.assertIn("# TYPE gap03_score_latency_ms histogram", text)
        self.assertIn('gap03_score_latency_ms_bucket{result="ok",le="5"} 1', text)
        self.assertIn("gap03_starved_tenants 2", text)
        for name, spec in metrics.CATALOG.items():
            self.assertEqual(len(spec), 6, name)
            self.assertIn(spec[0], ("counter", "gauge", "histogram"))
        with self.assertRaises(TypeError):
            m.inc("gap03_starved_tenants")

    @covers("MC-019", 8)
    def test_mc019_required_signals_present_in_catalog(self):
        need = ["gap03_candidate_set_size", "gap03_feasible_candidates", "gap03_chosen_locality_cost",
                "gap03_fairness_denials_total", "gap03_reservation_utilization_ratio", "gap03_starved_tenants",
                "gap03_spread_failures_total", "gap03_stale_rejections_total", "gap03_idempotent_replays_total",
                "gap03_orphaned_reservations", "gap03_dependency_up", "gap03_breaker_state", "gap03_coordination_term",
                "gap03_cache_events_total", "gap03_admission_rejected_total"]
        for n in need:
            self.assertIn(n, metrics.CATALOG)

    @covers("MC-019", 11, 13, 20, 27)
    def test_mc019_cardinality_budget_and_forbidden_labels(self):
        """adversarial/fault: forbidden identifier labels are rejected, label-cardinality explosions collapse into an overflow series with a drop counter, and concurrent updates never block or lose counts."""
        m = metrics.Metrics()
        with self.assertRaises(ValueError):
            m.inc("gap03_requests_total", op="x", code="y", tenant="t1")
        for i in range(200):
            m.inc("gap03_admission_rejected_total", reason=f"r{i}")
        self.assertLessEqual(len(m.label_sets["gap03_admission_rejected_total"]), 33)
        self.assertGreater(m.get("gap03_metric_label_overflow_total", metric="gap03_admission_rejected_total"), 0)
        ts = [threading.Thread(target=lambda: [m.inc("gap03_requests_total", op="s", code="OK") for _ in range(500)]) for _ in range(4)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(m.get("gap03_requests_total", code="OK", op="s"), 2000)

    @covers("MC-019", 14)
    def test_mc019_recording_rules_reference_catalog(self):
        for r in metrics.RECORDING_RULES:
            self.assertTrue(any(n in r["expr"] for n in metrics.CATALOG), r)


class Logs(unittest.TestCase):
    @covers("MC-024", 26)
    @covers("MC-020", 6, 7, 8, 9, 15, 25)
    def test_mc020_schema_golden_events(self):
        out = []
        lg = logpipe.Logger(out.append, sample_rate=1.0, seed=1)
        lg.log("commit.ok", tenant="t1", txn="x1")
        lg.log("security.auth_failed", code="UNAUTHENTICATED", request_id="r1")
        lg.flush()
        recs = [logpipe.validate_record(l) for l in out]
        self.assertEqual(recs[1]["severity"], "SECURITY")
        self.assertEqual(recs[1]["request_id"], "r1")
        self.assertEqual(len(recs[0]["request_id"]), 32)  # generated at ingress
        self.assertTrue(recs[0]["tenant"].startswith("p:"))  # pseudonymised
        with self.assertRaises(ValueError):
            lg.log("made.up")
        with self.assertRaises(ValueError):
            logpipe.validate_record(json.dumps({"schema": "x"}))

    @covers("MC-020", 10, 11, 18, 20, 27)
    def test_mc020_injection_and_redaction(self):
        """untrusted-input validation: log-injection (newline/forged JSON) is escaped and nested secrets are redacted at the logging boundary."""
        out = []
        lg = logpipe.Logger(out.append, sample_rate=1.0)
        lg.log("dependency.failure", code="X\nFAKE {\"severity\":\"ERROR\"}", error="Bearer abc.def secret://kms/k",
               detail={"token": "t0p", "inner": {"message": "-----BEGIN PRIVATE KEY----- xyz"}})
        lg.flush()
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].count("\n"), 0)
        s = out[0]
        for leaked in ("abc.def", "secret://kms", "t0p", "BEGIN PRIVATE"):
            self.assertNotIn(leaked, s)

    @covers("MC-024", 12)

    @covers("MC-020", 12, 13, 27)
    def test_mc020_bounded_buffer_sampling_and_sink_outage(self):
        def broken(line):
            raise OSError("sink down")
        lg = logpipe.Logger(broken, capacity=5, sample_rate=0.0, seed=3)
        for _ in range(50):
            lg.log("score.ok")  # sampled out entirely
        self.assertEqual(len(lg.q), 0)
        for _ in range(8):
            lg.log("security.replay")  # never sampled; oldest evicted when full
        self.assertEqual(len(lg.q), 5)
        self.assertEqual(lg.flush(), 0)
        self.assertGreaterEqual(lg.dropped, 8)

    @covers("MC-020", 14)
    def test_mc020_retention_policy_declared(self):
        for k in ("hot_days", "total_days", "rotation_mb", "compression", "transport", "access", "security_events_days"):
            self.assertIn(k, logpipe.RETENTION)


class Traces(unittest.TestCase):
    @covers("MC-021", 6, 7, 8, 13, 25)
    def test_mc021_w3c_propagation_and_attributes(self):
        tr = tracing.Tracer(sample_rate=1.0)
        hdr = {"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"}
        root = tr.start("admission", headers=hdr, txn="tx1")
        child = tr.start("locality_score")
        tr.attr(child, "candidate_count", 10)
        with self.assertRaises(ValueError):
            tr.attr(child, "tenant", "t1")
        tr.end(child)
        out = tr.inject(root)
        tr.end(root)
        self.assertEqual(root["trace_id"], "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertEqual(child["parent_id"], root["span_id"])
        self.assertEqual(child["txn"], "tx1")
        self.assertTrue(out["traceparent"].startswith("00-4bf92f3577b34da6a3ce929d0e0e4736-"))

    @covers("MC-021", 10, 18, 27)
    def test_mc021_invalid_headers_and_baggage_limits(self):
        """adversarial: malformed/zero/uppercase traceparent headers and oversize baggage are rejected with resource limits."""
        for bad in ["", "00-" + "0" * 32 + "-00f067aa0ba902b7-01", "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                    "00-4BF92F3577B34DA6A3CE929D0E0E4736-00f067aa0ba902b7-01", "x" * 55, "00-abc"]:
            self.assertIsNone(tracing.parse_traceparent(bad), bad)
        self.assertEqual(tracing.parse_baggage("a=" + "x" * 2000), {})
        self.assertLessEqual(len(tracing.parse_baggage(",".join(f"k{i}=v" for i in range(50)))), 16)
        tr = tracing.Tracer()
        s = tr.start("admission", headers={"traceparent": "garbage"})
        self.assertEqual(len(s["trace_id"]), 32)  # fresh trace, header not trusted
        tr.end(s)

    @covers("MC-021", 9, 11, 12, 14, 15)
    def test_mc021_sampling_async_propagation_exporter_outage(self):
        def dead(span):
            raise ConnectionError()
        tr = tracing.Tracer(exporter=dead, sample_rate=0.0, seed=1)
        s = tr.start("admission")
        seen = []
        t = threading.Thread(target=tr.wrap(lambda: seen.append(tracing._current.get()["trace_id"])))
        t.start()
        t.join()
        self.assertEqual(seen, [s["trace_id"]])
        tr.end(s)  # ok + sampled out -> not exported
        e = tr.start("durable_claim")
        tr.end(e, error_code="STALE_STATE")  # errors always kept -> exporter fails -> counted
        self.assertEqual(tr.dropped, 1)
        tr2 = tracing.Tracer(sample_rate=0.0)
        x = tr2.start("fairness")
        tr2.end(x, security=True)
        self.assertEqual(len(tr2.finished), 1)
        self.assertEqual(x["attrs"], {})


class ExplainT(TmpCase):
    def mk(self, audit=None):
        return Explain(ExplainStore(self.d("ex"), clock=self.clock), audit=audit, clock=self.clock)

    def rec(self, ex, txn="t1", tenant="a"):
        from gap03_topology_aware_scheduler.scheduler import _score_snapshot
        topo = Topology()
        for n, p in {"a": ("eu", "d", "r1"), "b": ("eu", "d", "r2"), "c": ("us", "i", "r1")}.items():
            topo.place(n, *p)
        snap = topo.snapshot()
        led = LedgerStore(self.d("l" + txn))
        led.submit({"type": "set_capacity", "capacity": 2})
        v, _, g = led.verdict(tenant)
        scored = _score_snapshot(snap, "a", ["c", "b"])
        inputs = decision_inputs(workload={"id": "w"}, candidates=["c", "b"], snapshot=snap, ledger_token=v.state_token,
                                 entitlement_generation=g, config_generation=1)
        return ex.record(txn=txn, tenant=tenant, workload={"id": "w"}, inputs=inputs, scored=scored, fairness=v,
                         snapshot_nodes={k: list(p) for k, p in snap.nodes.items()}, infeasible={"x": "isa"},
                         components={"b": {"locality": 20}}, sources={"anchor": "a", "spread_from": []})

    @covers("MC-022", 6, 7, 9, 10, 11, 25)
    def test_mc022_record_contents(self):
        r = self.rec(self.mk())
        for k in ("txn", "workload_ref", "inputs", "candidates", "tie_break", "hard_filter", "soft_components", "fairness",
                  "snapshot_ref"):
            self.assertIn(k, r)
        self.assertEqual(r["hard_filter"], {"x": "isa"})
        self.assertEqual(r["inputs"]["scoring_version"], SCORING_VERSION)
        for k in ("reserved", "held", "capacity", "surplus", "state_token"):
            self.assertIn(k, r["fairness"])

    @covers("MC-022", 8, 14, 15, 17, 27)
    def test_mc022_query_authz_scoping_pagination_audit(self):
        """authorization + adversarial access: unauthorised queries, cross-tenant reads, over-wide ranges and query floods are refused; access is audited."""
        audit = self.audit()
        ex = self.mk(audit)
        for i in range(6):
            self.rec(ex, txn=f"t{i}", tenant="ab"[i % 2])
        with self.assertRaises(SchedulerError):
            ex.query({"sub": "x", "perms": set()})
        own = ex.query({"sub": "w", "tenant": "a", "perms": set()})
        self.assertTrue(all(r["tenant"] == "a" for r in own["records"]))
        p1 = ex.query({"sub": "op", "perms": {"explain.read"}}, page_size=4)
        self.assertEqual(len(p1["records"]), 4)
        p2 = ex.query({"sub": "op", "perms": {"explain.read"}}, page_token=p1["next_page_token"])
        self.assertEqual(len(p2["records"]), 2)
        with self.assertRaises(SchedulerError):
            ex.query({"sub": "op", "perms": {"explain.read"}}, since=0, until=10**9)
        self.assertIn("explain.query", [e["action"] for e in audit.export(principal_roles={"audit.export"})["events"]])
        ex2 = Explain(ex.store, clock=self.clock, rate=1)
        ex2.query({"sub": "z", "perms": {"explain.read"}})
        with self.assertRaises(SchedulerError):
            ex2.query({"sub": "z", "perms": {"explain.read"}})

    @covers("MC-022", 12, 13, 26)
    def test_mc022_replay_determinism_and_divergence_flag(self):
        ex = self.mk()
        self.rec(ex)
        r = ex.replay("t1", scoring_version=SCORING_VERSION)
        self.assertTrue(r["identical"])
        self.assertFalse(r["version_changed"])
        self.assertTrue(ex.replay("t1", scoring_version="gap03-score/3")["version_changed"])
        again = self.rec(ex)  # immutable: second write ignored
        self.assertEqual(len(ex.store.state["order"]), 1)
        self.assertTrue(again)
        self.assertEqual(ExplainStore(self.d("ex")).state["order"], ["t1"])  # durable


class AlertsT(unittest.TestCase):
    @covers("MC-023", 26)
    @covers("MC-023", 6, 7, 8, 10, 11, 14)
    def test_mc023_definitions_valid(self):
        """definitions carry runbook links, owning team, severity, escalation target and first diagnostics for every alert."""
        self.assertEqual(alerts.validate_definitions(), [])
        classes = {a["class"] for a in alerts.ALERTS}
        self.assertTrue({"overload", "policy", "dependency", "stale_state", "security", "software_defect"} <= classes)
        names = {a["alert"] for a in alerts.ALERTS}
        for n in ("GAP03FencingRejections", "GAP03AuditWriteFailure", "GAP03ReconciliationDrift", "GAP03OrphanTransactions",
                  "GAP03StaleTopology"):
            self.assertIn(n, names)

    @covers("MC-023", 9, 12, 13, 15)
    def test_mc023_synthetic_incident_fire_and_clear(self):
        quiet = [{"t": i * 60, "error_ratio": 0.0} for i in range(70)]
        self.assertNotIn("GAP03SLOBurnFast", alerts.evaluate(quiet))
        incident = [{"t": i * 60, "error_ratio": 0.5 if 5 <= i < 65 else 0.0, "fenced_writes": 1 if i == 30 else 0}
                    for i in range(70)]
        f = alerts.evaluate(incident)
        self.assertIn("GAP03SLOBurnFast", f)
        self.assertIn("GAP03FencingRejections", f)
        self.assertEqual(f["GAP03FencingRejections"], [1800])
        dep = [{"t": i * 60, "dependency_down": 1} for i in range(3)]
        self.assertIn("GAP03DependencyDown", alerts.evaluate(dep))
        self.assertNotIn("GAP03DependencyDown", alerts.evaluate(dep, maintenance=True))
        sec = [{"t": i * 60, "audit_write_failures": 1} for i in range(2)]
        self.assertIn("GAP03AuditWriteFailure", alerts.evaluate(sec, maintenance=True))  # never suppressed
        p = alerts.precision(f, {"GAP03SLOBurnFast", "GAP03FencingRejections"})
        self.assertIn("retire_candidates", p)


class Privacy(unittest.TestCase):
    @covers("MC-024", 6, 7, 8, 25)
    def test_mc024_classification_and_sanitize(self):
        for f, c in privacy.FIELD_CLASS.items():
            self.assertIn(c, privacy.CLASSES)
        self.assertEqual(privacy.classify("unknown_field"), "confidential")
        rec = {"tenant": "acme", "node": "n1", "dataset": "orders", "token": "t", "message": "Bearer abc.def",
               "nested": {"workload": "w", "detail": {"secret": "s"}}}
        m = privacy.sanitize(rec, signal="metrics", key=KEY)
        self.assertNotIn("tenant", m)
        tr = privacy.sanitize(rec, signal="traces", key=KEY)
        self.assertNotIn("tenant", tr)
        lg = privacy.sanitize(rec, signal="logs", key=KEY)
        self.assertEqual(lg["tenant"], privacy.pseudonym("acme", KEY))
        self.assertNotIn("dataset", lg)
        self.assertNotIn("token", lg)
        self.assertEqual(lg["message"], "<redacted>")
        self.assertNotIn("secret", json.dumps(lg))

    @covers("MC-024", 9, 14, 15, 27)
    def test_mc024_retention_security_exception_and_offboarding(self):
        """fault/adversarial: retention expiry and tenant offboarding delete operational telemetry but never security evidence."""
        recs = [{"day": 0, "class": "confidential"}, {"day": 0, "class": "confidential", "security_evidence": True},
                {"day": 95, "class": "internal"}]
        kept = privacy.expire(recs, now_days=100)
        self.assertEqual(len(kept), 2)
        p = privacy.pseudonym("t1", KEY)
        rows = [{"tenant": p}, {"tenant": p, "security_evidence": True}, {"tenant": "other"}]
        kept, n = privacy.offboard_tenant(rows, p)
        self.assertEqual(n, 1)
        self.assertEqual(len(kept), 2)

    @covers("MC-024", 10, 11, 13, 17, 27)
    def test_mc024_export_allowlist(self):
        """authorization/adversarial: exports to non-allow-listed or unencrypted destinations are refused (least privilege on telemetry export)."""
        privacy.check_export("otlp://collector.observability.internal:4317")
        for bad in ("http://evil.example/ingest", "otlp://other:4317"):
            with self.assertRaises(SchedulerError):
                privacy.check_export(bad)
