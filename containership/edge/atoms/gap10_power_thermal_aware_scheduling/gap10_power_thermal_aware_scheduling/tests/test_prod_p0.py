"""P0 production-enforcement tests: components 01-08.
Each test id carries its component tag (cNN) for the evidence matrix."""
import json
import os
import unittest

from harness import SCOPE, Stack
from gap10_power_thermal_aware_scheduling.model import PowerThermalPolicy
from gap10_power_thermal_aware_scheduling.production.enforcement import CeilingView, FailClosedContract
from gap10_power_thermal_aware_scheduling.production.errors import ErrorCode, Gap10Error
from gap10_power_thermal_aware_scheduling.production.policy_service import policy_to_dict, sign_bundle
from gap10_power_thermal_aware_scheduling.production.store import FileStateStore, NodeRecord


class C01TelemetryAdapter(unittest.TestCase):
    def setUp(self):
        self.s = Stack()

    def code(self, env):
        with self.assertRaises(Gap10Error) as cm:
            self.s.ctl.ingest(env)
        return cm.exception.code

    def test_c01_accepts_authenticated_sample_with_provenance(self):
        d = self.s.send(temp=40.0)
        self.assertEqual(d["band"], "nominal")
        prov = self.s.ctl.nodes["edge-001"].last_sample
        for k in ("source_identity", "key_id", "attestation", "signature_status", "seq", "observed_at",
                  "received_at", "correlation_id", "schema_version"):
            self.assertIn(k, prov)
        self.assertEqual(prov["source_identity"], "gap09-reporter")
        self.assertEqual(prov["signature_status"], "verified")

    def test_c01_bad_signature_rejected_before_parse(self):
        self.assertEqual(self.code(self.s.envelope(temp=99.0, tamper=True)), ErrorCode.TELEMETRY_BAD_SIGNATURE)
        self.assertEqual(self.s.ctl.telemetry.counters["bad_signature"], 1)

    def test_c01_unauthorized_scope_rejected(self):
        self.assertEqual(self.code(self.s.envelope(key="rogue-k1")), ErrorCode.TELEMETRY_UNAUTHORIZED)

    def test_c01_unknown_key_and_unsigned_rejected(self):
        env = self.s.envelope()
        env["key_id"] = "nope"
        self.assertEqual(self.code(env), ErrorCode.TELEMETRY_UNAUTHENTICATED)
        env = self.s.envelope()
        del env["signature"]
        self.assertEqual(self.code(env), ErrorCode.TELEMETRY_UNAUTHENTICATED)

    def test_c01_insufficient_attestation_rejected(self):
        self.assertEqual(self.code(self.s.envelope(attestation="software")), ErrorCode.TELEMETRY_UNAUTHENTICATED)

    def test_c01_stale_and_future_rejected_never_refreshed(self):
        now = self.s.clock.now()
        self.assertEqual(self.code(self.s.envelope(observed_at=now - 31)), ErrorCode.TELEMETRY_STALE)
        self.assertEqual(self.code(self.s.envelope(observed_at=now + 6)), ErrorCode.TELEMETRY_FUTURE)

    def test_c01_replay_and_duplicate_rejected(self):
        self.s.send(seq=5)
        self.assertEqual(self.code(self.s.envelope(seq=5)), ErrorCode.TELEMETRY_REPLAYED)
        self.assertEqual(self.code(self.s.envelope(seq=4)), ErrorCode.TELEMETRY_REPLAYED)
        self.assertEqual(self.s.ctl.telemetry.counters["duplicate"], 1)
        self.assertEqual(self.s.ctl.telemetry.counters["replayed"], 1)

    def test_c01_unsupported_major_and_malformed(self):
        env = self.s.envelope()
        env["schema"] = "PK_TELEMETRY_ENVELOPE/2"
        self.assertEqual(self.code(env), ErrorCode.TELEMETRY_UNSUPPORTED_VERSION)
        self.assertEqual(self.code(b"{not json"), ErrorCode.TELEMETRY_MALFORMED)
        self.assertEqual(self.code(b"x" * 70000), ErrorCode.TELEMETRY_OVERSIZE)
        self.assertEqual(self.code([1, 2]), ErrorCode.TELEMETRY_MALFORMED)

    def test_c01_key_rotation_overlap_and_revocation(self):
        kr = self.s.kr
        now = self.s.clock.now()
        kr.rotate("gap09-k1", "gap09-k2", b"z" * 40, overlap_until=now + 60)
        # old key is verify-only: signatures made before rotation still verify within overlap
        self.s.send(key="gap09-k2")
        kr.revoke("gap09-k2")
        self.assertEqual(self.code(self.s.envelope(key="gap09-k2")), ErrorCode.TELEMETRY_UNAUTHENTICATED)

    def test_c01_partial_trust_node_fails_closed_to_critical(self):
        sensors = [{"sensor_id": "cpu0", "kind": "cpu", "temperature_c": 40.0},
                   {"sensor_id": "gpu0", "kind": "gpu", "temperature_c": float("nan")}]
        d = self.s.send(sensors=sensors)
        self.assertEqual(d["band"], "critical")
        self.assertIn("partial sensor trust", d["reason"])


class C02SchedulerEnforcement(unittest.TestCase):
    def setUp(self):
        self.s = Stack()

    def test_c02_ceiling_is_hard_admission_limit(self):
        self.s.send(temp=80.0)  # elevated -> 60
        self.s.adapter.admit("edge-001", "w1", 60, self.s.clock.now())
        with self.assertRaises(Gap10Error) as cm:
            self.s.adapter.admit("edge-001", "w2", 1, self.s.clock.now())
        self.assertEqual(cm.exception.code, ErrorCode.ADMISSION_DENIED)

    def test_c02_emergency_node_accepts_nothing_even_manual(self):
        self.s.send(temp=96.0)
        for path in (lambda: self.s.adapter.admit("edge-001", "w", 1, self.s.clock.now()),
                     lambda: self.s.sched.manual_place("edge-001", "w", 1)):
            with self.assertRaises(Gap10Error):
                path()

    def test_c02_decision_binding_and_toctou_revalidation(self):
        d1 = self.s.send(temp=40.0)
        self.s.mc.advance(1)
        self.s.send(temp=80.0)
        with self.assertRaises(Gap10Error) as cm:
            self.s.adapter.admit("edge-001", "w", 1, self.s.clock.now(), consulted_decision_id=d1["decision_id"])
        self.assertEqual(cm.exception.code, ErrorCode.CEILING_REVISION_MISMATCH)

    def test_c02_capacity_drop_below_allocation_drains(self):
        self.s.send(temp=40.0)
        for i in range(10):
            self.s.adapter.admit("edge-001", f"w{i}", 10, self.s.clock.now())
        self.s.mc.advance(1)
        self.s.send(temp=86.0)  # critical -> 25
        self.assertLessEqual(self.s.sched.allocated("edge-001"), 25)

    def test_c02_fractional_ceiling_floors(self):
        from gap10_power_thermal_aware_scheduling.production.enforcement import SchedulerEnforcementAdapter
        self.assertEqual(SchedulerEnforcementAdapter.to_units(0.6, 7), 4)
        self.assertEqual(SchedulerEnforcementAdapter.to_units(0.25, 3), 0)

    def test_c02_divergence_detected(self):
        self.s.send(temp=40.0)
        self.assertIsNone(self.s.adapter.divergence("edge-001", self.s.clock.now()))
        self.s.sched.limits["edge-001"] = (100, "forged")
        self.s.mc.advance(1)
        self.s.view.publish(self.s.ctl.ingest(self.s.envelope(temp=86.0)))
        self.assertIsNotNone(self.s.adapter.divergence("edge-001", self.s.clock.now()))
        self.assertEqual(self.s.ctl.metrics.get("gap10_enforcement_divergence", {"node": "edge-001", "consumer": "scheduler"}), 1)


class C03Elasticity(unittest.TestCase):
    def test_c03_autoscaler_cannot_refill_constrained_capacity(self):
        s = Stack()
        s.send("edge-001", 40.0)
        s.send("edge-002", 40.0)
        self.assertEqual(s.elastic_adapter.apply("pool", s.clock.now()), 200)
        s.mc.advance(1)
        s.send("edge-001", 96.0)
        self.assertEqual(s.elastic_adapter.apply("pool", s.clock.now()), 100)
        self.assertEqual(s.elastic.request_scale("pool", 200), 100)
        # recovery: ceiling rises but cooldown holds the cap
        s.mc.advance(1)
        s.send("edge-001", 40.0)  # hysteresis keeps emergency until margin; 40 clears margin
        s.elastic_adapter.apply("pool", s.clock.now())
        self.assertEqual(s.elastic.request_scale("pool", 200), 100)
        for _ in range(5):
            s.mc.advance(29)
            s.send("edge-001", 40.0)
            s.send("edge-002", 40.0)
            s.elastic_adapter.apply("pool", s.clock.now())
        self.assertEqual(s.elastic.request_scale("pool", 200), 200)


class C04StateStore(unittest.TestCase):
    def test_c04_restart_resumes_restrictive_state(self):
        s = Stack()
        s.send(temp=96.0)
        s.leases.release("shard-0", "ctl-a")
        ctl2 = s.controller("ctl-b")
        ctl2.acquire()
        ctx = ctl2.register("edge-001", scope=SCOPE)
        self.assertEqual(ctx.state.band, "emergency")
        self.assertTrue(ctx.restored)

    def test_c04_restart_never_starts_nominal(self):
        s = Stack()
        s.send(temp=30.0)
        ctl2 = s.controller("ctl-a")
        ctl2.fencing_token = s.ctl.fencing_token
        self.assertEqual(ctl2.register("edge-001", scope=SCOPE).state.band, "critical")

    def test_c04_corrupt_record_fails_closed(self):
        s = Stack()
        s.send(temp=30.0)
        path = s.store._path("edge-001")
        with open(path, "r+", encoding="utf-8") as fh:
            doc = json.load(fh)
            doc["record"]["last_trusted_seq"] = 0  # tampered: would re-open replay window
            fh.seek(0); fh.truncate(); json.dump(doc, fh)
        with self.assertRaises(Gap10Error) as cm:
            s.store.load("edge-001")
        self.assertEqual(cm.exception.code, ErrorCode.STORE_CORRUPT)
        ctx = s.ctl.register("edge-001", scope=SCOPE)
        self.assertEqual(ctx.state.band, "critical")

    def test_c04_persisted_replay_rejected_after_restart(self):
        s = Stack()
        s.send(seq=10)
        ctl2 = s.controller("ctl-a")
        ctl2.fencing_token = s.ctl.fencing_token
        ctl2.register("edge-001", scope=SCOPE)
        with self.assertRaises(Gap10Error):
            ctl2.ingest(s.envelope(seq=9))

    def test_c04_store_outage_restricts_and_reports_unsafe(self):
        s = Stack()
        s.send(temp=30.0)
        s.store.available = False
        s.mc.advance(1)
        d = s.ctl.ingest(s.envelope(temp=30.0))
        self.assertLessEqual(d["ceiling_fraction"], 0.25)
        self.assertFalse(s.ctl.health()["safe_to_enforce"])


class C05C06PolicyService(unittest.TestCase):
    def setUp(self):
        self.s = Stack()
        self.p = self.s.policies
        self.base = policy_to_dict(PowerThermalPolicy())

    def active(self):
        return self.p.active[SCOPE]

    def test_c05_tightening_by_author_activates_with_immutable_revision(self):
        tighter = dict(self.base, elevated_c=70.0)
        rev = self.p.submit(sign_bundle(self.s.kr, SCOPE, tighter, self.active(), "author-k1"), now=1)
        self.assertTrue(rev.revision_id.startswith("rev-"))
        again = self.p.submit(sign_bundle(self.s.kr, SCOPE, tighter, self.active(), "author-k1"), now=2)
        self.assertEqual(rev.revision_id, again.revision_id)
        old = self.active()
        self.p.activate(SCOPE, rev.revision_id, actor="alice", now=3)
        self.assertEqual(self.p.rollback(SCOPE, actor="alice", now=4), old)

    def test_c05_staged_activation_only_hits_cohort(self):
        tighter = dict(self.base, elevated_c=70.0)
        rev = self.p.submit(sign_bundle(self.s.kr, SCOPE, tighter, self.active(), "author-k1"), now=1)
        self.p.stage(SCOPE, rev.revision_id, {"edge-001"}, actor="alice", now=2)
        self.assertEqual(self.p.effective(SCOPE, "edge-001").revision_id, rev.revision_id)
        self.assertNotEqual(self.p.effective(SCOPE, "edge-002").revision_id, rev.revision_id)

    def test_c05_parent_conflict_rejected(self):
        b = sign_bundle(self.s.kr, SCOPE, dict(self.base, elevated_c=70.0), "rev-stale", "author-k1")
        with self.assertRaises(Gap10Error) as cm:
            self.p.submit(b, now=1)
        self.assertEqual(cm.exception.code, ErrorCode.POLICY_REVISION_CONFLICT)

    def test_c05_invalid_policy_rejected(self):
        b = sign_bundle(self.s.kr, SCOPE, dict(self.base, elevated_c=99.0), self.active(), "author-k1")
        with self.assertRaises(Gap10Error) as cm:
            self.p.submit(b, now=1)
        self.assertEqual(cm.exception.code, ErrorCode.POLICY_INVALID)

    def test_c06_relaxation_requires_distinct_second_party(self):
        looser = dict(self.base, emergency_c=98.0)
        with self.assertRaises(Gap10Error) as cm:
            self.p.submit(sign_bundle(self.s.kr, SCOPE, looser, self.active(), "author-k1"), now=1)
        self.assertEqual(cm.exception.code, ErrorCode.POLICY_UNAUTHORIZED)
        with self.assertRaises(Gap10Error):
            self.p.submit(sign_bundle(self.s.kr, SCOPE, looser, self.active(), "author-k1", "self-approver"), now=1)
        rev = self.p.submit(sign_bundle(self.s.kr, SCOPE, looser, self.active(), "author-k1", "approver-k1"), now=1)
        self.assertEqual(rev.approver, "bob")
        self.assertIn("emergency_c", rev.provenance["relaxed"])

    def test_c06_forged_or_out_of_scope_bundle_rejected(self):
        b = sign_bundle(self.s.kr, SCOPE, dict(self.base, elevated_c=70.0), self.active(), "author-k1")
        b["policy"]["emergency_c"] = 120.0
        with self.assertRaises(Gap10Error) as cm:
            self.p.submit(b, now=1)
        self.assertEqual(cm.exception.code, ErrorCode.POLICY_UNSIGNED)
        types = [e["type"] for e in self.s.audit.entries]
        self.assertIn("security.failure", types)
        with self.assertRaises(Gap10Error):  # author key is scoped to dub/* only
            self.p.submit(sign_bundle(self.s.kr, "dub/prod", self.base, self.active(), "ops-k1"), now=1)


class C07FailClosedConsumer(unittest.TestCase):
    def test_c07_missing_stale_unhealthy_never_unlimited(self):
        v = CeilingView(FailClosedContract(max_decision_age_s=15))
        self.assertEqual(v.effective("x", 100, 0)["ceiling"], 0)
        s = Stack()
        d = s.send(temp=30.0)
        self.assertEqual(s.view.effective("edge-001", 100, d["issued_at"])["ceiling"], 100)
        self.assertEqual(s.view.effective("edge-001", 100, d["issued_at"] + 16)["ceiling"], 0)
        s.view.gap10_healthy = False
        self.assertTrue(s.view.effective("edge-001", 100, d["issued_at"])["fail_closed"])

    def test_c07_contract_rejects_permissive_absent_fraction(self):
        with self.assertRaises(ValueError):
            FailClosedContract(absent_fraction=1.0)

    def test_c07_scheduler_without_decision_admits_nothing(self):
        s = Stack()
        with self.assertRaises(Gap10Error):
            s.adapter.admit("edge-002", "w", 1, s.clock.now())


class C08Fencing(unittest.TestCase):
    def test_c08_second_controller_cannot_acquire_live_lease(self):
        s = Stack()
        ctl2 = s.controller("ctl-b")
        with self.assertRaises(Gap10Error) as cm:
            ctl2.acquire()
        self.assertEqual(cm.exception.code, ErrorCode.OWNERSHIP_CONFLICT)

    def test_c08_expired_leader_is_fenced_out_everywhere(self):
        s = Stack()
        s.send(temp=40.0)
        s.mc.advance(31)  # lease expired
        ctl2 = s.controller("ctl-b")
        ctl2.acquire()
        ctl2.register("edge-001", scope=SCOPE)
        d2 = ctl2.ingest(s.envelope(temp=90.0))
        s.view.publish(d2)
        # old leader cannot decide ...
        with self.assertRaises(Gap10Error):
            s.ctl.decide("edge-001")
        # ... cannot persist with an older token ...
        with self.assertRaises(Gap10Error) as cm:
            s.store.save(NodeRecord("edge-001", "nominal", None, None, "r", "nominal", fencing_token=1))
        self.assertEqual(cm.exception.code, ErrorCode.FENCING_TOKEN_STALE)
        # ... and consumers reject its stale-token decisions
        old = dict(d2, fencing_token=1, band="nominal", ceiling=100, ceiling_fraction=1.0, excluded=False)
        with self.assertRaises(Gap10Error):
            s.view.publish(old)


if __name__ == "__main__":
    unittest.main()
