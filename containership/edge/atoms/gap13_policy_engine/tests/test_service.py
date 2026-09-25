"""PolicyService: MC-007 stale modes, MC-012 cache, MC-013 rollback, MC-014 swap, MC-016 errors,
MC-018/019 config, MC-020 controls, MC-021 health, MC-031 admission."""
import unittest

import testkit as k
from gap13_policy_engine import errors as E
from gap13_policy_engine.audit import verify_chain, read_log

g = k.g


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = k.tmpdir()
        self.svc, self.c = k.service(self.dir, config=getattr(self, "CONFIG", None))
        self.alice = k.principal("alice", ("policy_admin",), clock=self.c)
        self.bob = k.principal("bob", ("policy_admin",), clock=self.c)
        self.sec = k.principal("sec", ("security",), clock=self.c)
        self.ops = k.principal("ops", ("operator",), clock=self.c)
        self.app = k.principal("svc-a", ("service",), kind="service", clock=self.c)

    def push(self, gen, rules=None, svc=None):
        svc = svc or self.svc
        d = svc.stage(self.alice, k.envelope(gen, rules))["digest"]
        svc.activate(self.bob, d)
        return d

    def ev(self, **attrs):
        return self.svc.evaluate(self.app, attrs or {"action": "read"})


class LifecycleTests(Base):
    def test_no_policy_fails_closed(self):
        with self.assertRaises(E.NoActivePolicy):
            self.ev()
        self.assertFalse(self.svc.health()["ready"])

    def test_separation_of_duties(self):
        d = self.svc.stage(self.alice, k.envelope(1))["digest"]
        with self.assertRaises(E.Unauthorized):
            self.svc.activate(self.alice, d)
        with self.assertRaises(E.Unauthorized):
            self.svc.load(self.alice, k.envelope(1))
        self.svc.activate(self.bob, d)
        self.assertEqual(self.ev()["effect"], "allow")

    def test_downgrade_via_service_refused(self):
        self.push(2)
        with self.assertRaises(E.ReplayRejected):
            self.svc.stage(self.alice, k.envelope(1))

    def test_unverified_refused_and_audited(self):
        with self.assertRaises(E.VerificationFailed):
            self.svc.stage(self.alice, k.envelope(1, seed=k.ROGUE))
        acts = [r["action"] for r in self.svc.audit.records()]
        self.assertIn("bundle.verify", acts)

    def test_status_exposes_generation_floor_provenance(self):
        self.push(3)
        s = self.svc.status()
        self.assertEqual(s["active"]["generation"], 3)
        self.assertEqual(s["anti_rollback"]["gap07-publisher|estate|prod"]["generation"], 3)
        self.assertIn("config_digest", s["config_provenance"])
        self.assertEqual(s["engine_release"], g.__version__)
        self.assertNotIn("public_key", repr(s))


class StaleTests(Base):
    def test_fail_closed_boundaries(self):
        self.push(1)
        self.c.advance(240)
        self.assertEqual(self.ev()["effect"], "allow")
        self.assertEqual(self.svc.status()["staleness"]["state"], "none")
        self.c.advance(1)
        self.ev()
        self.assertEqual(self.svc._stale_state, "warning")
        self.assertIn("policy staleness warning", self.svc.health()["degraded"])
        self.assertTrue(self.svc.health()["ready"])
        self.c.advance(59)                 # age == 300 exactly: still allowed
        self.assertEqual(self.ev()["effect"], "allow")
        self.c.advance(1)
        with self.assertRaises(E.StalePolicyRefused):
            self.ev()
        self.assertFalse(self.svc.health()["ready"])
        # step-up auth is only valid for 300 s, so admins re-authenticate
        self.alice = k.principal("alice", ("policy_admin",), clock=self.c)
        self.bob = k.principal("bob", ("policy_admin",), clock=self.c)
        self.push(2)                       # restored connectivity -> recovery
        self.assertEqual(self.ev()["effect"], "allow")
        acts = [r["action"] for r in self.svc.audit.records()]
        for a in ("stale.warning", "stale.hard"):
            self.assertIn(a, acts)

    def test_deny_only_mode(self):
        svc, c = k.service(config=g.EngineConfig(stale_mode="DENY_ONLY"))
        self.push(1, svc=svc)
        c.advance(400)
        v = svc.evaluate(self.app, {"action": "read"})
        self.assertEqual((v["effect"], v["mode"]), ("deny", "deny-only"))

    def test_freeze_lkg_mode(self):
        svc, c = k.service(config=g.EngineConfig(stale_mode="FREEZE_LAST_KNOWN_GOOD"))
        self.push(1, svc=svc)
        c.advance(400)
        v = svc.evaluate(self.app, {"action": "read"})
        self.assertEqual(v["effect"], "allow")
        self.assertTrue(v["stale"])
        self.assertEqual(v["mode"], "stale-freeze_last_known_good")

    def test_wall_clock_rollback_does_not_extend_trust(self):
        self.push(1)
        self.c.m += 400                    # monotonic time passes...
        self.c.t -= 1000                   # ...while the wall clock is wound back
        with self.assertRaises(E.StalePolicyRefused):
            self.ev()
        self.assertGreater(self.svc.clock_anomalies, 0)

    def test_wall_forward_jump_shortens_trust(self):
        self.push(1)
        self.c.t += 10_000
        with self.assertRaises(E.StalePolicyRefused):
            self.ev()

    def test_bundle_expiry(self):
        d = self.svc.stage(self.alice, k.envelope(1, expires_at=k.T0 + 100))["digest"]
        self.svc.activate(self.bob, d)
        self.c.advance(101)
        with self.assertRaises(E.StalePolicyRefused):
            self.ev()

    def test_request_cannot_weaken_staleness(self):
        self.push(1)
        self.c.advance(400)
        with self.assertRaises((E.AttributeRejected, E.StalePolicyRefused)):
            self.svc.evaluate(self.app, {"action": "read", "stale_mode": "FREEZE_LAST_KNOWN_GOOD"})

    def test_restart_does_not_reset_age(self):
        self.push(1)
        self.c.advance(200)
        svc2, _ = k.service(self.dir, clock=self.c)
        self.assertTrue(svc2.restore_from_cache())
        self.assertGreaterEqual(svc2.bundle_age(), 200)
        self.c.advance(101)
        with self.assertRaises(E.StalePolicyRefused):
            svc2.evaluate(self.app, {"action": "read"})


class RollbackAndControlTests(Base):
    def test_operator_rollback(self):
        d1 = self.push(1)
        self.push(2, [{"name": "deny-all", "effect": "deny", "scope": "estate", "match": {}}])
        self.assertEqual(self.ev()["effect"], "deny")
        with self.assertRaises(E.ConfigRejected):
            self.svc.rollback(self.bob, reason="")
        self.svc.rollback(self.bob, reason="INC-1 bad policy")
        self.assertEqual(self.svc.status()["active"]["digest"], d1)
        self.assertEqual(self.ev()["effect"], "allow")
        self.assertIn("bundle.rollback", [r["action"] for r in self.svc.audit.records()])
        with self.assertRaises(E.Unauthorized):
            self.svc.rollback(self.ops, reason="x")

    def test_freeze_blocks_updates_and_survives_restart_and_reconfig(self):
        self.push(1)
        self.svc.set_control(self.ops, "UPDATE_FROZEN", reason="incident", change_id="INC-2")
        d = self.svc.stage(self.alice, k.envelope(2))["digest"]
        with self.assertRaises(E.UpdateFrozen):
            self.svc.activate(self.bob, d)
        self.svc.reconfigure(self.bob, g.EngineConfig(site="default"), source="git:abc", version="c2")
        self.assertEqual(self.svc.status()["control"]["state"], "UPDATE_FROZEN")
        svc2, _ = k.service(self.dir, clock=self.c)
        self.assertEqual(svc2.status()["control"]["state"], "UPDATE_FROZEN")

    def test_control_transitions_need_capability_and_reason(self):
        with self.assertRaises(E.Unauthorized):
            self.svc.set_control(self.ops, "EVALUATION_DISABLED", reason="x", change_id="c")
        with self.assertRaises(E.ConfigRejected):
            self.svc.set_control(self.sec, "EVALUATION_DISABLED", reason="", change_id="c")
        with self.assertRaises(E.ConfigRejected):
            self.svc.set_control(self.sec, "EVALUATION_DISABLED", reason="x", change_id="c", expires_at=k.T0 + 5)
        with self.assertRaises(E.Unauthorized):
            self.svc.set_control(self.ops, "NORMAL", reason="x", change_id="c")

    def test_deny_only_and_disable(self):
        self.push(1)
        self.svc.set_control(self.ops, "DENY_ONLY", reason="r", change_id="c1")
        v = self.ev()
        self.assertEqual((v["effect"], v["mode"]), ("deny", "deny-only"))
        self.svc.set_control(self.sec, "EVALUATION_DISABLED", reason="r", change_id="c2")
        with self.assertRaises(E.EvaluationDisabled):
            self.ev()
        self.assertFalse(self.svc.health()["ready"])
        self.svc.set_control(self.sec, "NORMAL", reason="recovered", change_id="c3")
        self.assertEqual(self.ev()["effect"], "allow")

    def test_time_bounded_control_expires(self):
        self.push(1)
        self.svc.set_control(self.ops, "DENY_ONLY", reason="r", change_id="c", expires_at=int(self.c.t) + 10)
        self.c.advance(11)
        self.assertEqual(self.ev()["effect"], "allow")

    def test_quarantine_active_bundle_rolls_back(self):
        d1 = self.push(1)
        d2 = self.push(2)
        self.svc.quarantine(self.sec, digest=d2, reason="bad", change_id="INC-3")
        self.assertEqual(self.svc.status()["active"]["digest"], d1)
        with self.assertRaises((E.BundleQuarantined, E.ReplayRejected)):
            self.svc.stage(self.alice, k.envelope(2))

    def test_quarantine_only_bundle_forces_deny_only(self):
        d1 = self.push(1)
        self.svc.quarantine(self.sec, generation=1, reason="bad", change_id="INC-4")
        self.assertEqual(self.svc.status()["control"]["state"], "DENY_ONLY")
        self.assertEqual(self.ev()["effect"], "deny")

    def test_corrupt_control_state_is_conservative(self):
        self.push(1)
        self.svc.set_control(self.ops, "UPDATE_FROZEN", reason="r", change_id="c")
        import pathlib
        p = pathlib.Path(self.dir) / "control.json"
        p.write_text(p.read_text().replace("UPDATE_FROZEN", "NORMAL"))
        svc2, _ = k.service(self.dir, clock=self.c)
        self.assertEqual(svc2.status()["control"]["state"], "DENY_ONLY")


class ConfigAdmissionErrorTests(Base):
    def test_config_validation(self):
        for bad in ({"stale_mode": "OPEN"}, {"staleness_warning_seconds": 500}, {"zzz": 1},
                    {"limits": {"max_rules": 0}}, {"environment": ""}, {"staleness_hard_seconds": 10**7}):
            with self.subTest(bad), self.assertRaises(E.ConfigRejected):
                g.EngineConfig.from_mapping(bad)
        self.assertEqual(g.EngineConfig.from_mapping({"site": "edge-1", "limits": {"max_rules": 5}}).limits.max_rules, 5)

    def test_config_provenance_chain(self):
        p1 = self.svc.provenance
        p2 = self.svc.reconfigure(self.bob, g.EngineConfig(site="default", staleness_hard_seconds=600),
                                  source="git:1", version="c1")
        self.assertEqual(p2.previous_digest, p1.record_digest)
        with self.assertRaises(E.Unauthorized):
            self.svc.reconfigure(self.ops, g.EngineConfig(), source="x", version="y")

    def test_admission_control_sheds(self):
        self.push(1)
        self.svc._inflight = self.svc.config.limits.max_concurrency
        with self.assertRaises(E.Overloaded) as cm:
            self.ev()
        self.assertTrue(cm.exception.retryable)
        self.svc._inflight = 0
        self.assertEqual(self.ev()["effect"], "allow")

    def test_deadline(self):
        self.push(1)
        with self.assertRaises(E.DeadlineExceeded):
            self.svc.evaluate(self.app, {"action": "read"}, deadline=self.c.m - 1)

    def test_error_codes_unique_and_stable(self):
        reg = E.registry()
        self.assertEqual(len(reg), len(set(reg)))
        self.assertEqual(reg["G13-E100"], E.BundleRejected)
        self.assertTrue(issubclass(E.BundleRejected, PermissionError))   # 4.x compatibility

    def test_audit_chain_intact_after_workflow(self):
        self.push(1)
        self.svc.set_control(self.ops, "DENY_ONLY", reason="r", change_id="c")
        import pathlib
        recs = list(read_log(pathlib.Path(self.dir) / "audit.jsonl"))
        self.assertTrue(verify_chain(recs, expected_head=self.svc.audit.head)[0])

    def test_explain_detail_requires_capability(self):
        self.push(1)
        summary = self.svc.explain(self.app, {"action": "read"})
        self.assertEqual(summary["matched"], [])
        detailed = self.svc.explain(self.ops, {"action": "read"})
        self.assertEqual(detailed["matched"][0]["rule"], "allow-read")
        self.assertIn("explain.detailed", [r["action"] for r in self.svc.audit.records()])


if __name__ == "__main__":
    unittest.main()
