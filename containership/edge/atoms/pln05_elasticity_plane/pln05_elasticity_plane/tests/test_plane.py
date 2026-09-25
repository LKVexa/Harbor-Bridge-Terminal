"""Integration tests for the PLN-05 service boundary (plane.py) through real bytes and credentials."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import World  # noqa: E402

from pln05_elasticity_plane.audit import AuditLog  # noqa: E402
from pln05_elasticity_plane.errors import PlaneError  # noqa: E402


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.declare(floor=0, ceiling=8)

    def codes(self, fn):
        try:
            fn()
        except PlaneError as exc:
            return exc.code
        return "OK"

    def test_decisions_carry_contract_fields(self):
        d = self.w.observe(0.9, correlation_id="corr-0001")
        self.assertEqual((d["outcome"], d["target"], d["reason_code"]), ("scale-up", 1, "R_SCALE_UP"))
        self.assertTrue(d["published"])
        self.assertEqual(d["fencing_token"], d["epoch"])
        self.assertEqual(len(d["config_checksum"]), 64)
        self.assertEqual(self.w.sink.applied[-1]["decision_id"], d["decision_id"])

    def test_every_outcome_class_reachable(self):
        seen = set()
        w = self.w
        for u in (0.9, 0.9, 0.9, 0.9, 0.9):
            seen.add(w.observe(u)["outcome"])  # scale-up then constrained-hold at ceiling
        seen.add(w.observe(0.5)["outcome"])  # hold
        for _ in range(3):
            seen.add(w.observe(0.1)["outcome"])  # grace holds then scale-down
        w.clock.advance(31)
        w.plane.tick()  # stale-input-hold
        w.clock.advance(300)
        w.plane.tick()  # degraded
        seen.add(w.observe(0.5)["outcome"])  # recovery
        seen |= {d["outcome"] for d in w.sink.applied}
        self.assertTrue({"scale-up", "scale-down", "hold", "constrained-hold", "stale-input-hold",
                         "degraded", "recovery"} <= seen, seen)

    def test_limits_require_authority_and_increasing_revision(self):
        w = self.w
        rep = w.token()
        with self.assertRaises(PlaneError) as cm:
            w.plane.submit_limits(w.limits(ceiling=100, revision=2), rep)
        self.assertEqual(cm.exception.code, "E_AUTHZ_DENIED")
        with self.assertRaises(PlaneError) as cm:
            w.declare(revision=1, ceiling=4)
        self.assertEqual(cm.exception.code, "E_OUT_OF_ORDER")
        with self.assertRaises(PlaneError) as cm:  # issuer spoofing
            w.plane.submit_limits(w.limits(revision=2, issuer="someone-else"), w.token("intent_plane"))
        self.assertEqual(cm.exception.code, "E_AUTHZ_SCOPE")

    def test_envelope_change_clamps_and_resets_grace(self):
        w = self.w
        for _ in range(4):
            w.observe(0.9)
        self.assertEqual(w.plane.scopes["t1/dub/w1"].controller.current, 8)
        w.observe(0.1)
        w.declare(revision=2, floor=0, ceiling=4)
        s = w.plane.scopes["t1/dub/w1"]
        self.assertEqual((s.controller.current, s.controller._below), (4, 0))

    def test_lower_ceiling_via_boundary(self):
        w = self.w
        pt = w.token("power_thermal")
        w.plane.lower_ceiling(pt, tenant="t1", site="dub", workload="w1", ceiling=3)
        for _ in range(4):
            d = w.observe(0.99)
        self.assertEqual(d["target"], 3)
        with self.assertRaises(PlaneError) as cm:
            w.plane.lower_ceiling(w.token("power_thermal"), tenant="t1", site="dub", workload="w1", ceiling=6)
        self.assertEqual(cm.exception.code, "E_AUTHORITY_ESCALATION")
        with self.assertRaises(PlaneError) as cm:  # single-use token
            w.plane.lower_ceiling(pt, tenant="t1", site="dub", workload="w1", ceiling=2)
        self.assertEqual(cm.exception.code, "E_AUTHN_REPLAY")

    def test_low_confidence_holds(self):
        w = self.w
        tok = w.token("platform_operator", tenant="*")
        w.plane.activate_config(tok, {"site": {"revision": 2, "min_confidence": 0.5}})
        d = w.observe(0.95, confidence=0.2)
        self.assertEqual((d["outcome"], d["reason_code"], d["target"]), ("hold", "R_LOW_CONFIDENCE", 0))

    def test_config_change_needs_platform_operator_and_is_audited(self):
        w = self.w
        with self.assertRaises(PlaneError):
            w.plane.activate_config(w.token("operator"), {"site": {"revision": 2}})
        desc = w.plane.activate_config(w.token("platform_operator", tenant="*"), {"site": {"revision": 2, "stale_after_s": 20}})
        self.assertEqual(desc["revision"], 2)
        back = w.plane.rollback_config(w.token("platform_operator", tenant="*"))
        self.assertEqual(back["revision"], 1)
        actions = [r["action"] for r in w.plane.audit.records]
        self.assertIn("config.change", actions)
        self.assertIn("config.rollback", actions)


class ControlsTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.declare()
        self.w.observe(0.9)

    def test_freeze_holds_and_does_not_publish(self):
        w = self.w
        w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1",
                        reason="incident", ticket="INC-7")
        n = len(w.sink.applied)
        d = w.observe(0.99)
        self.assertEqual((d["outcome"], d["published"], d["target"]), ("frozen", False, 1))
        self.assertEqual(len(w.sink.applied), n)

    def test_disable_and_quarantine(self):
        w = self.w
        w.plane.control(w.token("operator"), "quarantine", tenant="t1", site="dub", workload="w1",
                        reason="bad reporter", ticket="INC-8", source="r1")
        with self.assertRaises(PlaneError) as cm:
            w.observe(0.5)
        self.assertEqual(cm.exception.code, "E_QUARANTINED")
        w.observe(0.5, source="r2", token=w.token(source="r2"))  # other sources unaffected
        w.plane.control(w.token("operator", sites=("*",)), "disable", tenant="t1", site="*", workload=None,
                        reason="maintenance", ticket="CHG-1")
        with self.assertRaises(PlaneError) as cm:
            w.observe(0.5, source="r2", token=w.token(source="r2"))
        self.assertEqual(cm.exception.code, "E_DISABLED")

    def test_controls_need_reason_ticket_and_capability(self):
        w = self.w
        with self.assertRaises(PlaneError):
            w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="", ticket="x")
        with self.assertRaises(PlaneError) as cm:
            w.plane.control(w.token("sibling_plane"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")
        self.assertEqual(cm.exception.code, "E_AUTHZ_DENIED")

    def test_limits_update_cannot_clear_freeze(self):
        w = self.w
        w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")
        w.declare(revision=2, ceiling=16)
        self.assertEqual(w.observe(0.99)["outcome"], "frozen")

    def test_two_person_resume(self):
        w = self.w
        w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")
        w.plane.resume(w.admin("admin-a"), tenant="t1", site="dub", workload="w1", ticket="INC-1")
        with self.assertRaises(PlaneError):
            w.plane.resume(w.admin("admin-a"), tenant="t1", site="dub", workload="w1", ticket="INC-1")
        self.assertEqual(w.observe(0.99)["outcome"], "frozen")
        out = w.plane.resume(w.admin("admin-b"), tenant="t1", site="dub", workload="w1", ticket="INC-1")
        self.assertEqual(out["state"], "resumed")
        self.assertEqual(w.observe(0.99)["outcome"], "scale-up")

    def test_expiring_freeze(self):
        w = self.w
        w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="r",
                        ticket="t", expires=w.clock() + 5)
        self.assertEqual(w.observe(0.99)["outcome"], "frozen")
        w.clock.advance(6)
        self.assertEqual(w.observe(0.99)["outcome"], "scale-up")

    def test_drain(self):
        w = self.w
        w.plane.enqueue_demand(w.demand(0.9), w.token())
        self.assertEqual(w.plane.drain(), 1)
        with self.assertRaises(PlaneError) as cm:
            w.observe(0.9)
        self.assertEqual(cm.exception.code, "E_DISABLED")
        self.assertFalse(w.plane.health()["ready"])


class PersistenceAndFailoverTest(unittest.TestCase):
    def test_restart_preserves_hysteresis_and_controls(self):
        with tempfile.TemporaryDirectory() as d:
            w = World(d)
            w.declare()
            for u in (0.9, 0.9, 0.1, 0.1):  # two grace holds pending
                w.observe(u)
            w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")
            ring, leases, sink, clock = w.ring, w.leases, w.sink, w.clock
            w2 = World(d, ring=ring, leases=leases, sink=sink, clock=clock)
            w2.seq = w.seq
            self.assertEqual(w2.observe(0.1)["outcome"], "frozen")  # freeze survived restart
            s = w2.plane.scopes["t1/dub/w1"]
            self.assertEqual((s.controller.current, s.controller._below), (2, 2))

    def test_tenant_wide_freeze_survives_restart(self):
        with tempfile.TemporaryDirectory() as d:
            w = World(d)
            w.declare()
            w.observe(0.5)
            w.plane.control(w.token("operator", sites=("*",)), "freeze", tenant="t1", site="*", workload=None, reason="r", ticket="t")
            w2 = World(d, ring=w.ring, leases=w.leases, sink=w.sink, clock=w.clock)
            w2.seq = w.seq
            self.assertEqual(w2.observe(0.9)["outcome"], "frozen")

    def test_restart_without_freeze_continues_grace_exactly(self):
        with tempfile.TemporaryDirectory() as d:
            w = World(d)
            w.declare()
            for u in (0.9, 0.9, 0.1, 0.1):
                w.observe(u)
            w2 = World(d, ring=w.ring, leases=w.leases, sink=w.sink, clock=w.clock)
            w2.seq = w.seq
            self.assertEqual(w2.observe(0.1)["outcome"], "scale-down")  # 3rd sample, not a reset

    def test_replayed_message_after_restart_is_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            w = World(d)
            w.declare()
            raw = w.demand(0.9, message_id="fixed-0000001")
            w.plane.submit_demand(raw, w.token())
            w2 = World(d, ring=w.ring, leases=w.leases, sink=w.sink, clock=w.clock)
            with self.assertRaises(PlaneError) as cm:
                w2.plane.submit_demand(raw, w2.token())
            self.assertEqual(cm.exception.code, "E_DUPLICATE")

    def test_corrupt_state_fails_safe_and_is_visible(self):
        with tempfile.TemporaryDirectory() as d:
            w = World(d)
            w.declare()
            w.observe(0.9)
            f = next((pathlib.Path(d) / "state").glob("*.state.json"))
            f.write_bytes(f.read_bytes()[:-10])
            w2 = World(d, ring=w.ring, leases=w.leases, sink=w.sink, clock=w.clock)
            with self.assertRaises(PlaneError) as cm:
                w2.observe(0.9)
            self.assertEqual(cm.exception.code, "E_STATE_CORRUPT")
            h = w2.plane.health()
            self.assertFalse(h["ready"])
            self.assertIn("R_STATE_CORRUPT", h["blockers"])

    def test_failover_fences_the_old_leader(self):
        w = World()
        w.declare()
        w.observe(0.9)
        b = World(instance="ctl-b", ring=w.ring, leases=w.leases, sink=w.sink, clock=w.clock)
        with self.assertRaises(PlaneError) as cm:  # non-leader may not change the envelope
            b.plane.submit_limits(w.limits(), w.token("intent_plane"))
        self.assertEqual(cm.exception.code, "E_NOT_LEADER")  # A still holds the lease
        w.clock.advance(16)  # A's lease lapses (no renewals)
        b.plane.submit_limits(w.limits(), w.token("intent_plane"))
        d = b.observe(0.9, source="r2", token=b.token(source="r2"))
        self.assertTrue(d["published"])
        # A comes back believing it is leader: re-acquire fails, nothing published
        with self.assertRaises(PlaneError) as cm:
            w.observe(0.9)
        self.assertEqual(cm.exception.code, "E_NOT_LEADER")
        # a resurrected stale decision with the old epoch is fenced downstream
        stale = dict(w.sink.applied[0], decision_id="stale-x")
        with self.assertRaises(PlaneError) as cm:
            w.sink.apply(stale)
        self.assertEqual(cm.exception.code, "E_FENCED")

    def test_coordination_outage_never_publishes_without_lease(self):
        w = World()
        w.declare()
        w.observe(0.9)
        w.leases.available = False
        w.clock.advance(5)
        self.assertTrue(w.observe(0.9)["published"])  # still inside granted lease
        w.clock.advance(20)
        with self.assertRaises(PlaneError) as cm:
            w.observe(0.9)
        self.assertEqual(cm.exception.code, "E_NOT_LEADER")
        self.assertIn("coordination", w.plane.health()["dependencies"])


class ObservabilityTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.w.declare()

    def test_explain_by_decision_and_correlation(self):
        w = self.w
        d = w.observe(0.9, correlation_id="corr-abc123")
        op = w.token("operator")
        ex = w.plane.explain(op, decision_id=d["decision_id"], tenant="t1", site="dub")
        self.assertEqual(ex["reason_code"], "R_SCALE_UP")
        self.assertEqual(ex["config"]["checksum"], d["config_checksum"])
        self.assertEqual(ex["ownership"]["fencing_token"], d["fencing_token"])
        self.assertEqual(ex["authorization"]["policy_version"], "1.0.0")
        self.assertEqual(w.plane.explain(op, correlation_id="corr-abc123", tenant="t1", site="dub")["decision_id"],
                         d["decision_id"])
        with self.assertRaises(PlaneError):  # other tenant cannot read it
            w.plane.explain(w.token("operator", tenant="t2"), decision_id=d["decision_id"], tenant="t2", site="dub")
        rows = w.plane.explain_query(op, tenant="t1", site="dub", workload="w1")
        self.assertEqual(len(rows), 1)

    def test_explain_ceiling_constrained_alternative(self):
        w = self.w
        w.declare(revision=2, floor=0, ceiling=3)
        for _ in range(3):  # 0 -> 1 -> 2 -> 3 (a full step would be 4)
            d = w.observe(0.9)
        ex = w.plane.explain(w.token("operator"), decision_id=d["decision_id"], tenant="t1", site="dub")
        self.assertIn("ceiling constrained", ex["rejected_alternative"])

    def test_explain_retention_bounded(self):
        w = self.w
        w.plane.activate_config(w.token("platform_operator", tenant="*"), {"site": {"revision": 2, "explain": {"retention": 10}}})
        for _ in range(30):
            w.observe(0.5)
        self.assertEqual(len(w.plane.explain_store), 10)

    def test_status_public_vs_admin(self):
        w = self.w
        w.observe(0.9)
        pub = w.plane.status()
        self.assertNotIn("scopes", pub)
        self.assertTrue(pub["ready"])
        self.assertEqual(pub["config"]["revision"], 1)
        with self.assertRaises(PlaneError):
            w.plane.status(w.token("telemetry_collector"), tenant="t1", site="dub")
        adm = w.plane.status(w.token("operator"), tenant="t1", site="dub")
        self.assertEqual(adm["scopes"][0]["target"], 1)
        self.assertNotIn("secret", json.dumps(adm))

    def test_metrics_logs_and_traces_emitted(self):
        w = self.w
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        d = w.observe(0.9, traceparent=tp)
        self.assertTrue(d["traceparent"].startswith("00-4bf92f3577b34da6a3ce929d0e0e4736-"))
        self.assertEqual(w.plane.metrics.value("decisions", outcome="scale-up", reason_code="R_SCALE_UP"), 1.0)
        self.assertTrue(any(r["event"] == "decision" for r in w.plane.log.records))
        tok = w.token()
        try:
            w.plane.submit_demand(b"{bad", tok)
        except PlaneError:
            pass
        self.assertNotIn(tok, json.dumps(list(w.plane.log.records)))

    def test_audit_chain_of_plane_actions_verifies(self):
        w = self.w
        w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")
        try:
            w.plane.control(w.token("operator", tenant="t2"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")
        except PlaneError:
            pass
        log = w.plane.audit
        self.assertTrue(AuditLog.verify(log.records, log.anchor(w.clock()), w.ring, w.clock(), log.window_start)["ok"])
        self.assertEqual([r["result"] for r in log.records][-2:], ["applied", "denied"])


class ReviewFindingsTest(unittest.TestCase):
    """Regression tests for defects found by the independent adversarial review of 4.2.0."""

    def test_stale_leader_reloads_shared_state_on_new_term(self):
        with tempfile.TemporaryDirectory() as d:
            a = World(d, instance="ctl-a")
            b = World(d, instance="ctl-b", ring=a.ring, leases=a.leases, sink=a.sink, clock=a.clock, mono=a.mono)
            a.declare(floor=0, ceiling=16)
            for _ in range(4):
                a.observe(0.9)
            a.clock.advance(100)
            b.plane.submit_limits(b.limits(floor=0, ceiling=2, revision=2), b.token("intent_plane"))
            b.observe(0.5, seq=100)
            a.clock.advance(100)
            d2 = a.observe(0.9, seq=200)
            self.assertEqual((d2["ceiling"], d2["target"]), (2, 2))  # A adopted B's envelope
            c = World(d, instance="ctl-c", ring=a.ring, leases=a.leases, sink=a.sink, clock=a.clock)
            s = c.plane._load_scope("t1/dub/w1")
            self.assertEqual((s.limits_revision, s.controller.limits.ceiling), (2, 2))

    def test_takeover_inherits_idempotency_state(self):
        with tempfile.TemporaryDirectory() as d:
            a = World(d)
            b = World(d, instance="ctl-b", ring=a.ring, leases=a.leases, sink=a.sink, clock=a.clock)
            a.declare()
            raw = a.demand(0.9, message_id="once-0000001")
            a.plane.submit_demand(raw, a.token())
            a.clock.advance(20)
            with self.assertRaises(PlaneError) as cm:
                b.plane.submit_demand(raw, b.token())
            self.assertEqual(cm.exception.code, "E_DUPLICATE")

    def test_persist_failure_on_authority_changes_rolls_back(self):
        with tempfile.TemporaryDirectory() as d:
            w = World(d)
            w.declare(ceiling=8)
            orig = w.plane.store.save

            def full(*a, **k):
                raise OSError(28, "No space left on device")
            w.plane.store.save = full
            for fn in (lambda: w.plane.submit_limits(w.limits(ceiling=1, revision=2), w.token("intent_plane")),
                       lambda: w.plane.lower_ceiling(w.token("power_thermal"), tenant="t1", site="dub", workload="w1", ceiling=2),
                       lambda: w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")):
                with self.assertRaises(PlaneError) as cm:
                    fn()
                self.assertEqual(cm.exception.code, "E_STATE_UNAVAILABLE")
            s = w.plane.scopes["t1/dub/w1"]
            self.assertEqual((s.limits_revision, s.controller.limits.ceiling, s.controls), (1, 8, {}))
            w.plane.store.save = orig
            w.plane.submit_limits(w.limits(ceiling=1, revision=2), w.token("intent_plane"))  # retry works

    def test_site_scope_enforced_for_reads_and_tenant_controls(self):
        w = World()
        w.plane.submit_limits(w.limits(site="ams"), w.token("intent_plane", sites=("ams",)))
        w.declare()
        d = w.observe(0.9, site="ams", token=w.token(sites=("ams",)))
        dub_op = w.token("operator")  # sites=("dub",)
        with self.assertRaises(PlaneError):
            w.plane.explain(dub_op, decision_id=d["decision_id"], tenant="t1", site="dub")
        st = w.plane.status(w.token("operator"), tenant="t1", site="dub")
        self.assertTrue(all("/dub/" in x["scope"] for x in st["scopes"]))
        with self.assertRaises(PlaneError):  # tenant-wide needs a credential for every site
            w.plane.control(w.token("operator"), "disable", tenant="t1", site="*", workload=None, reason="r", ticket="t")
        with self.assertRaises(PlaneError):  # and cannot be smuggled through a site-scoped call
            w.plane.control(w.token("operator"), "disable", tenant="t1", site="dub", workload=None, reason="r", ticket="t")

    def test_resume_proposal_expires_and_binds_to_controls(self):
        w = World()
        w.declare()
        w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")
        w.plane.resume(w.admin("a1"), tenant="t1", site="dub", workload="w1", ticket="t")
        w.clock.advance(5 * 86400 - 3600)
        out = w.plane.resume(w.admin("a2"), tenant="t1", site="dub", workload="w1", ticket="t")
        self.assertEqual(out["state"], "resume-proposed")  # stale proposal expired; this is a new one
        # a proposal made before another control was added cannot release the new control
        w.plane.control(w.token("operator"), "quarantine", tenant="t1", site="dub", workload="w1", reason="r", ticket="t2")
        out = w.plane.resume(w.admin("a1"), tenant="t1", site="dub", workload="w1", ticket="t")
        self.assertEqual(out["state"], "resume-proposed")

    def test_authority_expansion_refused_during_time_fault(self):
        w = World()
        w.declare()
        w.observe(0.5)
        w.clock.advance(-100)
        with self.assertRaises(PlaneError) as cm:
            w.plane.submit_limits(w.limits(revision=2, ceiling=100), w.token("intent_plane"))
        self.assertEqual(cm.exception.code, "E_SECURITY_DEPENDENCY")
        # safety-reducing controls still work
        w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub", workload="w1", reason="r", ticket="t")

    def test_envelope_change_publishes_the_clamp(self):
        w = World()
        w.declare(ceiling=8)
        for _ in range(4):
            w.observe(0.9)
        w.plane.lower_ceiling(w.token("power_thermal"), tenant="t1", site="dub", workload="w1", ceiling=2)
        last = w.sink.applied[-1]
        self.assertEqual((last["target"], last["ceiling"], last["reason_code"]), (2, 2, "R_ENVELOPE_CHANGED"))

    def test_quarantine_list_is_deduplicated_and_bounded(self):
        w = World()
        w.declare()
        for i in range(3):
            w.plane.control(w.token("operator"), "quarantine", tenant="t1", site="dub", workload="w1", reason="r",
                            ticket="t", source="rx")
        self.assertEqual(w.plane.scopes["t1/dub/w1"].controls["quarantined_sources"], ["rx"])


if __name__ == "__main__":
    unittest.main()
