"""P1 operations: C21 config model, C22 activation/rollback, C23 tier schedule, C24 overrides,
C25 health API, C26 metrics, C27 logging, C28 tracing, C29 alerts/dashboards, C30 backpressure,
C41 backup/restore/migration, C42 quarantine, C43 rollout."""
import copy, io, json, re, threading, time, unittest, urllib.request
from pathlib import Path
from _util import T, Tmp, node, code, Gap04Error
from gap04_disconnected_operation_controller.runtime import schema
from gap04_disconnected_operation_controller.runtime.config import ConfigManager, default_config, validate_config
from gap04_disconnected_operation_controller.runtime.observability import StructuredLogger, TraceContext, standard_metrics
from gap04_disconnected_operation_controller.runtime.resilience import Admission, CircuitBreaker, RetryBudget
from gap04_disconnected_operation_controller.runtime import backup as B
from gap04_disconnected_operation_controller.runtime.rollout import Rollout, compatible
from gap04_disconnected_operation_controller.runtime.node import migrate_state, MIGRATIONS
from gap04_disconnected_operation_controller.controller import AutonomyController, validate_tier_schedule

PKG = Path(__file__).resolve().parents[1]


class Config(unittest.TestCase):
    def test_T_C21_validation(self):
        validate_config(default_config())
        schema.check(default_config(), "PK_GAP04_CONFIG/1")
        bads = []
        c = default_config(); c["extra"] = 1; bads.append(c)
        c = default_config(); c["lease"]["max_lifetime_s"] = 10; bads.append(c)
        c = default_config(); c["journal"]["reserve_bytes"] = c["journal"]["max_bytes"]; bads.append(c)
        c = default_config(); c["overrides"]["two_person_required"] = False; bads.append(c)
        c = default_config(); c["tier_schedule"] = [[0, "full"], [99999999, "freeze"]]; bads.append(c)
        c = default_config(); c["max_policy_staleness_s"] = True; bads.append(c)
        for b in bads:
            e = code(self, "GAP04-E0800", validate_config, b)
            self.assertTrue(e.details["problems"])

    def test_T_C22_activation_provenance_rollback(self):
        with Tmp() as d:
            cm = ConfigManager(d)
            c1 = default_config(); cm.activate(c1, author="a", approver="b", reason="initial", now=1)
            c2 = copy.deepcopy(c1); c2["config_version"] = 2; c2["max_policy_staleness_s"] = 3600
            code(self, "GAP04-E0802", cm.activate, c2, author="a", approver="a", reason="x", now=2)
            rec = cm.activate(c2, author="a", approver="b", reason="tighten", now=2)
            self.assertEqual(rec["provenance"]["previous"], 1)
            code(self, "GAP04-E0801", cm.activate, c1, author="a", approver="b", reason="downgrade", now=3)
            rb = cm.rollback(author="c", approver="d", reason="bad canary", now=4)
            self.assertEqual(rb["config"]["config_version"], 1); self.assertEqual(cm.history(), [1, 2])

    def test_T_C22_signed_config(self):
        from gap04_disconnected_operation_controller.runtime import canonical, crypto
        cp = T.ControlPlane()
        with Tmp() as d:
            cm = ConfigManager(d, trust=cp.trust(), require_signature=True)
            c = default_config()
            code(self, "GAP04-E0800", cm.activate, c, author="a", approver="b", reason="r", now=1)
            sig = {"key_id": cp.key_id, "issuer": cp.issuer, "alg": "Ed25519", "sig": crypto.sign(cp.seed, canonical.dumps(c))}
            cm.activate(c, author="a", approver="b", reason="r", now=1, signature=sig)

    def test_T_C23_tier_schedule(self):
        ctl = AutonomyController("s", tier_schedule=((0, "full"), (10, "sustain"), (20, "freeze")))
        ctl.partition(0)
        self.assertEqual([ctl.tier(t) for t in (0, 9, 10, 19, 20)], ["full", "full", "sustain", "sustain", "freeze"])
        for bad in ([], [[1, "full"]], [[0, "full"], [5, "full"]], [[0, "full"], [10, "freeze"], [20, "sustain"]],
                    [[0, "full"], [0, "sustain"]], [[0, "full"], [5, "expired"]]):
            with self.assertRaises(ValueError):
                validate_tier_schedule(bad)
        self.assertEqual(ctl.to_snapshot()["tier_schedule"], [[0, "full"], [10, "sustain"], [20, "freeze"]])


class Overrides(unittest.TestCase):
    def test_T_C24_two_person_time_bounded(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            code(self, "GAP04-E0004", n.request_override, "tier_cap", value="full", reason="widen authority", ttl_s=60, requester=T.OPERATOR)
            code(self, "GAP04-E0004", n.request_override, "freeze", value=None, reason="x", ttl_s=60, requester=T.OPERATOR)
            oid = n.request_override("tier_cap", value="freeze", reason="suspicious workload churn", ttl_s=600, requester=T.OPERATOR)
            n.decide("admit-new", "ns/a", "req-00000001")          # not active until approved
            code(self, "GAP04-E0802", n.approve_override, oid, T.OPERATOR)
            n.approve_override(oid, T.OPERATOR2)
            code(self, "GAP04-E0101", n.decide, "admit-new", "ns/b", "req-00000002")
            self.assertEqual(n.health()["overrides_active"], [oid])
            m.t += 601
            n.decide("admit-new", "ns/c", "req-00000003")          # expired -> authority restored
            o2 = n.request_override("freeze", value=None, reason="second containment", ttl_s=600, requester=T.OPERATOR)
            n.approve_override(o2, T.OPERATOR2)
            code(self, "GAP04-E0101", n.decide, "admit-new", "ns/d", "req-00000004")
            self.assertIsNone(n.cancel_override(o2, T.OPERATOR)["effective_tier_cap"])
            n.decide("admit-new", "ns/d", "req-00000004")
            n.close()

    def test_T_C24_disable_override(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            oid = n.request_override("disable", value=None, reason="maintenance window", ttl_s=300, requester=T.OPERATOR)
            n.approve_override(oid, T.OPERATOR2)
            code(self, "GAP04-E0103", n.decide, "restart", "ns/a", "req-00000001")
            n.close()


class HealthMetricsLogs(unittest.TestCase):
    def test_T_C25_health_schema_and_http(self):
        from gap04_disconnected_operation_controller.runtime.opsapi import make_server
        with Tmp() as d:
            n, cp, m = node(d)
            h = n.health(); schema.check(h, "PK_GAP04_HEALTH/1")
            self.assertFalse(h["ready"]); self.assertIn("clock_unanchored", h["not_ready_reasons"])
            T.bring_up(n, cp, m)
            h = n.health(); schema.check(h); self.assertTrue(h["ready"])
            code(self, "GAP04-E0104", make_server, n)
            srv = make_server(n, allow_insecure_loopback=True)
            port = srv.server_address[1]
            body = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz").read())
            self.assertTrue(body["ready"])
            txt = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics").read().decode()
            self.assertIn("gap04_lease_remaining_seconds", txt)
            n.quarantine("test", None)
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz")
            self.assertEqual(cm.exception.code, 503)
            srv.shutdown(); n.close()

    def test_T_C26_metrics_exposition_and_cardinality(self):
        m = standard_metrics()
        for i in range(1000):
            m.inc("denials_total", code=f"attacker-{i}")
        m.inc("decisions_total", kind="restart", tier="full")
        txt = m.render()
        self.assertEqual(len([l for l in txt.splitlines() if l.startswith("gap04_denials_total{")]), 1)
        self.assertIn('gap04_denials_total{code="other"} 1000', txt)
        for line in txt.splitlines():
            if line and not line.startswith("#"):
                self.assertRegex(line, r'^[a-z_0-9]+(\{[^}]*\})? [0-9.e+-]+$')

    def test_T_C27_logging_redaction_and_schema(self):
        s = io.StringIO(); lg = StructuredLogger("site-a", "n1", stream=s)
        tc = TraceContext.new()
        lg.info("x", op="decide", trace=tc, sig="AAAA", nonce="abc", subject="tenant/secret", nested={"private_key": "k"})
        rec = json.loads(s.getvalue())
        schema.check(rec, "PK_GAP04_LOG/1")
        self.assertEqual(rec["fields"]["sig"], "<redacted>"); self.assertEqual(rec["fields"]["nonce"], "<redacted>")
        self.assertTrue(rec["fields"]["subject"].startswith("h:")); self.assertEqual(rec["fields"]["nested"]["private_key"], "<redacted>")
        self.assertEqual(rec["trace_id"], tc.trace_id)
        lg2 = StructuredLogger("s", "n", stream=io.StringIO(), debug_sample_rate=0.0)
        self.assertIsNone(lg2.log("debug", "noisy"))

    def test_T_C28_trace_propagation(self):
        tc = TraceContext.parse("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual(tc.trace_id, "a" * 32)
        self.assertNotEqual(TraceContext.parse("garbage").trace_id, "a" * 32)
        self.assertNotEqual(TraceContext.parse("00-" + "0" * 32 + "-" + "b" * 16 + "-01").trace_id, "0" * 32)
        with Tmp() as d:
            seen = []
            from gap04_disconnected_operation_controller.runtime.adapters import ReferenceSupervisor, ReferenceReplication
            class S(ReferenceSupervisor):
                def execute(s, c): seen.append(c["traceparent"]); return super().execute(c)
            class R(ReferenceReplication):
                def submit(s, b): seen.append(b["traceparent"]); return super().submit(b)
            n, cp, m = node(d, supervisor=S(), replication=R())
            T.bring_up(n, cp, m); T.go_dark(n, m)
            tp = "00-" + "c" * 32 + "-" + "d" * 16 + "-01"
            r = n.decide("restart", "ns/a", "req-00000001", traceparent=tp)
            self.assertEqual(r["trace_id"], "c" * 32)
            T.come_back(n, cp, m); n.reconnect(traceparent=tp)
            self.assertTrue(all(s.split("-")[1] == "c" * 32 for s in seen)); self.assertEqual(len(seen), 2)
            n.close()

    def test_T_C29_alerts_reference_real_metrics_and_runbooks(self):
        rules = (PKG / "ops" / "alerts.rules.yml").read_text()
        rendered = standard_metrics().render()
        defined = set(re.findall(r"# TYPE (gap04_[a-z_]+)", rendered))
        used = set(re.findall(r"(gap04_[a-z_]+?)(?:_bucket)?\b", rules))
        self.assertTrue(used); self.assertTrue(used <= defined | {"gap04_decision_latency_seconds"}, used - defined)
        runbook = (PKG / "docs" / "RUNBOOK.md").read_text()
        for anchor in set(re.findall(r"RUNBOOK.md#(rb-[0-9a-z-]+)", rules)):
            self.assertIn(f'id="{anchor}"', runbook, anchor)
        classes = set(re.findall(r"class: ([a-z_]+)", rules))
        for c in ("partition", "prolonged_degradation", "stale_policy", "lease_expiry", "storage_pressure",
                  "reconciliation_conflict", "attack", "software_fault"):
            self.assertIn(c, classes)
        dash = json.loads((PKG / "ops" / "dashboard.grafana.json").read_text())
        for p in dash["panels"]:
            for mname in re.findall(r"gap04_[a-z_]+", p["targets"][0]["expr"]):
                self.assertIn(mname.replace("_bucket", ""), defined)


class Backpressure(unittest.TestCase):
    def test_T_C30_admission_sheds(self):
        a = Admission(2, 1, wait_s=0.05)
        hold = threading.Event(); results = []
        def w():
            try:
                with a.slot():
                    hold.wait(1)
                results.append("ok")
            except Gap04Error as e:
                results.append(e.code)
        ts = [threading.Thread(target=w) for _ in range(6)]
        [t.start() for t in ts]; time.sleep(0.2); hold.set(); [t.join() for t in ts]
        self.assertEqual(results.count("ok"), 2); self.assertEqual(results.count("GAP04-E0700"), 4)

    def test_T_C30_retry_budget_and_breaker(self):
        clk = [0.0]
        rb = RetryBudget(percent=10, min_retries=2, clock=lambda: clk[0])
        for _ in range(10):
            rb.record_attempt()
        self.assertEqual([rb.try_retry() for _ in range(4)], [True, True, False, False])
        cb = CircuitBreaker("x", failure_threshold=2, reset_after_s=5, clock=lambda: clk[0])
        def boom(): raise RuntimeError()
        for _ in range(2):
            with self.assertRaises(RuntimeError): cb.call(boom)
        code(self, "GAP04-E0701", cb.call, lambda: 1)
        clk[0] = 6; self.assertEqual(cb.call(lambda: 1), 1); self.assertEqual(cb.state, "closed")


class BackupRestore(unittest.TestCase):
    def test_T_C41_backup_restore_roundtrip(self):
        with Tmp() as d:
            src = d / "src"; dst = d / "dst"
            n, cp, m = node(src)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            n.decide("restart", "ns/a", "req-00000001")
            gen = n.generation
            n.close()
            B.backup(src, d / "b.bak", "correct horse battery")
            raw = (d / "b.bak").read_bytes(); self.assertNotIn(b"journal", raw[40:])
            code(self, "GAP04-E0403", B.restore, d / "b.bak", d / "x", "wrong passphrase!")
            r = B.restore(d / "b.bak", dst, "correct horse battery")
            self.assertEqual(r["generation"], gen + 1)
            code(self, "GAP04-E0004", B.restore, d / "b.bak", dst, "correct horse battery")  # non-empty target
            n2, _, _ = node(dst, cp=cp, mono=m)
            self.assertEqual(len(n2.controller.decisions), 1); self.assertGreater(n2.generation, gen + 1)
            n2.close()

    def test_T_C41_state_migration_guards(self):
        st = {"schema": "PK_GAP04_STATE/1", "schema_version": 0}
        code(self, "GAP04-E0404", migrate_state, dict(st))
        MIGRATIONS[0] = lambda s: dict(s, schema_version=1)
        try:
            self.assertEqual(migrate_state(dict(st))["schema_version"], 1)
        finally:
            MIGRATIONS.pop(0)
        code(self, "GAP04-E0404", migrate_state, {"schema": "PK_GAP04_STATE/1", "schema_version": 2})


class Quarantine(unittest.TestCase):
    def test_T_C42_local_and_remote_quarantine_and_recovery(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m); T.go_dark(n, m)
            q = n.quarantine("operator suspects compromise", T.OPERATOR)
            code(self, "GAP04-E0103", n.decide, "restart", "ns/a", "req-00000001")
            n.close()
            n, _, _ = node(d, cp=cp, mono=m)                      # survives restart
            n.clock.anchor_trusted(n.clock.hwm)
            code(self, "GAP04-E0103", n.decide, "restart", "ns/a", "req-00000001")
            T.come_back(n, cp, m); n.reconnect()
            tok = cp.release_token(q["nonce"])
            code(self, "GAP04-E0802", n.release_quarantine, tok, T.OPERATOR)
            code(self, "GAP04-E0104", n.release_quarantine, cp.release_token("wrong"), T.OPERATOR2)
            n.release_quarantine(tok, T.OPERATOR2)
            self.assertFalse(n.health()["quarantine"])
            n.quarantine("x", command=cp.quarantine_cmd())       # signed remote command
            self.assertTrue(n.state["quarantine"]["source"].startswith("remote:"))
            code(self, "GAP04-E0104", n.quarantine, "x", command=dict(cp.quarantine_cmd(), reason="forged"))
            n.close()


class Rollouts(unittest.TestCase):
    def test_T_C43_staged_rollout(self):
        self.assertTrue(compatible("4.2.0", "4.3.0")[0])
        self.assertFalse(compatible("4.3.0", "9.9.9")[0])
        r = Rollout("4.2.0", "4.3.0")
        good = [{"site": "s1", "code_version": "4.3.0", "ready": True, "quarantine": False}]
        self.assertEqual(r.evaluate(0, good)["action"], "HOLD")
        self.assertEqual(r.evaluate(1800, good)["action"], "PROMOTE")
        bad = [dict(good[0], ready=False, not_ready_reasons=["clock_unanchored"])]
        d = r.evaluate(1900, bad)
        self.assertEqual((d["action"], d["to"]), ("ROLLBACK", "4.2.0"))
        self.assertEqual(r.evaluate(5000, good, denials=1, decisions=2)["action"], "ROLLBACK")
        r2 = Rollout("4.2.0", "4.3.0"); t = 0
        for _ in range(4):
            t += 1800; d = r2.evaluate(t, good)
        self.assertEqual(d["action"], "COMPLETE")


if __name__ == "__main__":
    unittest.main()
