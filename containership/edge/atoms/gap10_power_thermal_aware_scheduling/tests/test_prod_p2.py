"""P2 security/observability/resilience tests: components 19-28."""
import io
import json
import random
import unittest

from harness import SCOPE, Stack
from gap10_power_thermal_aware_scheduling.production.clock import ManualClock, TrustedClock
from gap10_power_thermal_aware_scheduling.production.coordination import (
    CircuitBreaker, PartitionManager, RetryPolicy, call_with_policy)
from gap10_power_thermal_aware_scheduling.production.errors import FAIL_CLOSED, ErrorCode, Gap10Error, category
from gap10_power_thermal_aware_scheduling.production.keys import KeyRing
from gap10_power_thermal_aware_scheduling.production.observability import (
    AuditSink, Metrics, StructuredLogger, new_metrics, parse_traceparent, traceparent)


class C19Errors(unittest.TestCase):
    def test_c19_codes_unique_stable_and_fail_closed(self):
        values = [c.value for c in ErrorCode]
        self.assertEqual(len(values), len(set(values)))
        for c in ErrorCode:
            self.assertRegex(c.value, r"^GAP10-E-[A-Z]{3}-\d{3}$")
            category(c)
        self.assertEqual(FAIL_CLOSED, frozenset(ErrorCode))
        d = Gap10Error(ErrorCode.STORE_UNAVAILABLE, "x", correlation_id="c1", secret=object()).to_dict()
        self.assertEqual(d["code"], "GAP10-E-STO-001")
        self.assertNotIn("secret", d["detail"])
        # frozen registry: codes pinned to prevent silent renumbering
        pinned = json.loads((__import__("harness").PKG_DIR / "docs" / "ERROR_CODES.json").read_text())
        self.assertEqual({c.name: c.value for c in ErrorCode}, pinned)


class C20Audit(unittest.TestCase):
    def test_c20_chain_detects_edit_delete_reorder_truncate(self):
        a = AuditSink()
        for i in range(5):
            a.append("policy.activated", "alice", float(i), revision=f"r{i}")
        ok, _ = AuditSink.verify(a.entries, a.head)
        self.assertTrue(ok)
        edited = [dict(e) for e in a.entries]
        edited[2] = dict(edited[2], actor="mallory")
        self.assertFalse(AuditSink.verify(edited)[0])
        self.assertFalse(AuditSink.verify(a.entries[:2] + a.entries[3:])[0])
        self.assertFalse(AuditSink.verify(list(reversed(a.entries)))[0])
        self.assertFalse(AuditSink.verify(a.entries[:-1], a.head)[0])
        with self.assertRaises(ValueError):
            a.append("made.up", "x", 0.0)

    def test_c20_persistent_sink_reloads_and_stack_events_recorded(self):
        s = Stack()
        s.send(temp=96.0)
        reloaded = AuditSink(s.audit.path)
        self.assertTrue(AuditSink.verify(reloaded.entries, s.audit.head)[0])
        types = {e["type"] for e in reloaded.entries}
        self.assertTrue({"policy.proposed", "policy.activated", "ownership.acquired", "node.excluded"} <= types)


class C21Metrics(unittest.TestCase):
    def test_c21_exposition_and_catalog(self):
        s = Stack()
        s.send(temp=80.0)
        text = s.ctl.metrics.render()
        for name in ("gap10_power_ceiling_slots", "gap10_node_temperature_celsius", "gap10_decision_latency_seconds_bucket",
                     "gap10_telemetry_samples_total", "gap10_telemetry_age_seconds"):
            self.assertIn(name, text)
        self.assertIn("# TYPE gap10_decision_latency_seconds histogram", text)

    def test_c21_cardinality_cap(self):
        m = Metrics()
        m.MAX_SERIES = 10
        for i in range(20):
            m.set("g", 1, {"node": str(i)})
        self.assertEqual(len(m.gauges), 10)
        self.assertEqual(m.dropped_series, 10)


class C22Logging(unittest.TestCase):
    def test_c22_structured_redacted_and_traced(self):
        buf = io.StringIO()
        lg = StructuredLogger(sink=buf)
        tid = "a" * 32
        rec = lg.log("info", "decision", trace_id=tid, node="n1", workload="tenant-a/job-7", api_key="s3cret", note="x" * 2000)
        self.assertEqual(rec["api_key"], "[REDACTED]")
        self.assertTrue(rec["workload"].startswith("h:"))
        self.assertTrue(rec["note"].endswith("[truncated]"))
        self.assertEqual(json.loads(buf.getvalue())["trace_id"], tid)
        tp = traceparent(tid, "b" * 16)
        self.assertEqual(parse_traceparent(tp), (tid, "b" * 16))
        self.assertIsNone(parse_traceparent("garbage"))

    def test_c22_trace_id_propagates_through_ingest(self):
        s = Stack()
        tid = "c" * 32
        s.ctl.ingest(s.envelope(temp=40.0), trace_id=tid)
        self.assertEqual(s.ctl.logger.records[-1]["trace_id"], tid)
        self.assertEqual(s.ctl.logger.records[-1]["event"], "decision")


class C23Explain(unittest.TestCase):
    def test_c23_explain_has_all_evidence(self):
        s = Stack()
        s.send(temp=80.0)
        s.mc.advance(1)
        s.send(temp=74.0)  # held by hysteresis
        e = s.ctl.explain("edge-001", s.adapter)
        for k in ("decision", "source_sample", "policy_revision", "threshold_crossings", "hysteresis",
                  "precedence_trail", "controls", "downstream"):
            self.assertIn(k, e)
        self.assertTrue(e["hysteresis"]["held"])
        self.assertFalse(e["downstream"]["diverged"])
        self.assertIsNone(s.ctl.explain("edge-002")["decision"])


class C24Alerts(unittest.TestCase):
    def test_c24_alert_rules_reference_real_metrics(self):
        from harness import PKG_DIR
        rules = json.loads((PKG_DIR / "ops" / "alerts.json").read_text())
        catalog = set(new_metrics().help)
        classes = {r["class"] for r in rules["rules"]}
        self.assertTrue({"ordinary-derating", "stale-telemetry", "cooling-failure", "battery-emergency",
                         "forged-input", "software-defect", "fleet-wide"} <= classes)
        for r in rules["rules"]:
            self.assertTrue(any(m in r["expr"] for m in catalog), r["name"])
            self.assertIn(r["severity"], ("SEV1", "SEV2", "SEV3", "SEV4"))
            self.assertTrue(r["runbook"].startswith("docs/"))
        dash = json.loads((PKG_DIR / "ops" / "dashboard.json").read_text())
        for p in dash["panels"]:
            self.assertTrue(any(m in p["expr"] for m in catalog), p["title"])


class C25Retry(unittest.TestCase):
    def test_c25_bounded_retry_and_breaker(self):
        calls = []
        br = CircuitBreaker("store", failure_threshold=3, reset_after_s=10)
        t = [0.0]

        def boom():
            calls.append(1)
            raise OSError("down")
        with self.assertRaises(Gap10Error) as cm:
            call_with_policy(boom, breaker=br, policy=RetryPolicy(max_attempts=5), now=lambda: t[0], rng=random.Random(1))
        self.assertEqual(cm.exception.code, ErrorCode.DEPENDENCY_TIMEOUT)
        self.assertEqual(len(calls), 3)
        self.assertEqual(br.state, "open")
        with self.assertRaises(Gap10Error) as cm:
            call_with_policy(boom, breaker=br, policy=RetryPolicy(), now=lambda: t[0])
        self.assertEqual(cm.exception.code, ErrorCode.CIRCUIT_OPEN)
        t[0] = 11.0
        self.assertEqual(call_with_policy(lambda: 7, breaker=br, policy=RetryPolicy(), now=lambda: t[0]), 7)
        self.assertEqual(br.state, "closed")

    def test_c25_delays_bounded_by_deadline(self):
        d = list(RetryPolicy(max_attempts=50, base_delay_s=1, max_delay_s=2, deadline_s=5, jitter=0).delays())
        self.assertLessEqual(sum(d), 5)


class C26Partition(unittest.TestCase):
    def test_c26_local_authority_capped_and_no_bump_on_reconnect(self):
        pm = PartitionManager(partition_cap=0.6, max_autonomy_s=100)
        pm.confirm("n", 1.0)
        pm.on_disconnect(0.0)
        self.assertEqual(pm.bound("n", 1.0, 10.0)[0], 0.6)
        self.assertEqual(pm.bound("n", 0.25, 10.0)[0], 0.25)
        self.assertEqual(pm.bound("n", 1.0, 200.0)[0], 0.25)
        pm.on_reconnect(["n"])
        pm.last_confirmed_fraction["n"] = 0.25
        self.assertEqual(pm.bound("n", 1.0, 201.0)[0], 0.25)
        pm.confirm("n", 1.0)
        self.assertEqual(pm.bound("n", 1.0, 202.0)[0], 1.0)


class C27Clock(unittest.TestCase):
    def test_c27_unsynced_jump_and_expiry_untrusted(self):
        mc = ManualClock()
        c = TrustedClock(wall=mc.wall, mono=mc.mono, max_sync_age=60, max_jump=2)
        self.assertFalse(c.trusted())
        c.sync()
        self.assertTrue(c.trusted())
        mc.jump_wall(-3600)  # wall jumps back an hour; monotonic-derived now() unaffected
        self.assertAlmostEqual(c.now(), 1000.0)
        self.assertFalse(c.trusted())
        c.sync()
        mc.advance(61)
        self.assertFalse(c.trusted())
        c.sync(authenticated=False)
        self.assertFalse(c.trusted())

    def test_c27_untrusted_clock_fails_closed_in_controller(self):
        s = Stack()
        s.mc.jump_wall(100)
        d = s.send(temp=30.0)
        self.assertEqual(d["band"], "critical")
        self.assertIn("clock untrusted", d["reason"])


class C28Keys(unittest.TestCase):
    def test_c28_scope_capability_and_no_secret_exposure(self):
        kr = KeyRing()
        kr.add("k", "svc", b"x" * 32, {"telemetry.publish"}, scopes=("edge-*",))
        with self.assertRaises(Gap10Error):
            kr.sign("k", "policy.author", "edge-1", {})
        with self.assertRaises(Gap10Error):
            kr.sign("k", "telemetry.publish", "core-1", {})
        with self.assertRaises(ValueError):
            kr.add("w", "svc", b"short", {"telemetry.publish"})
        with self.assertRaises(ValueError):
            kr.add("u", "svc", b"x" * 32, {"root"})
        self.assertNotIn("x" * 32, json.dumps(kr.describe()))

    def test_c28_expired_verify_only_key_rejected(self):
        kr = KeyRing()
        kr.add("k1", "svc", b"a" * 32, {"telemetry.publish"})
        sig = kr.sign("k1", "telemetry.publish", "n", {"v": 1})
        kr.rotate("k1", "k2", b"b" * 32, overlap_until=100.0)
        self.assertEqual(kr.verify("k1", "telemetry.publish", "n", {"v": 1}, sig, now=50.0), "svc")
        with self.assertRaises(Gap10Error):
            kr.verify("k1", "telemetry.publish", "n", {"v": 1}, sig, now=150.0)
        with self.assertRaises(Gap10Error):
            kr.sign("k1", "telemetry.publish", "n", {"v": 1})


class C01RateLimit(unittest.TestCase):
    def test_c01_per_identity_rate_limit(self):
        s = Stack()
        s.ctl.telemetry.burst_per_identity = 3
        s.ctl.telemetry.rate_per_identity_s = 0.0
        s.ctl.telemetry._buckets.clear()
        for _ in range(3):
            s.ctl.ingest(s.envelope(temp=40.0))
        with self.assertRaises(Gap10Error) as cm:
            s.ctl.ingest(s.envelope(temp=40.0))
        self.assertEqual(cm.exception.code, ErrorCode.TELEMETRY_RATE_LIMITED)


class C20TransitionAudit(unittest.TestCase):
    def test_c20_every_band_transition_audited_with_before_after(self):
        s = Stack()
        for t in (40.0, 80.0, 86.0, 96.0):
            s.mc.advance(1)
            s.send(temp=t)
        ch = [e for e in s.audit.entries if e["type"] == "node.band_changed" and e["detail"]["node"] == "edge-001"]
        self.assertEqual([e["detail"]["after_band"] for e in ch], ["nominal", "elevated", "critical", "emergency"])
        self.assertEqual(ch[1]["detail"]["before_band"], "nominal")
        self.assertTrue(all(e["detail"]["policy_revision"].startswith("rev-") for e in ch))


if __name__ == "__main__":
    unittest.main()
