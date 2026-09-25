"""End-to-end controller tests over the simulated fleet (components 2-15, 17, 18, 22, 23, 28-30)."""
from __future__ import annotations

import unittest

import _path  # noqa: F401
from gap08_ota_lifecycle_rollback.authz import Cap, Principal
from gap08_ota_lifecycle_rollback.errors import (Conflict, DependencyUnavailable, EvidenceRejected, Frozen,
                                                 IllegalTransition, Incompatible, Overloaded, PolicyDenied,
                                                 StaleFence, Unauthorized)
from gap08_ota_lifecycle_rollback.explain import explain, render_text
from gap08_ota_lifecycle_rollback.harness import (APPROVER, COMPAT, GATEKEEPER, OPERATOR, SECURITY, SRE,
                                                  build_world, spread_waves)
from gap08_ota_lifecycle_rollback.admission import AdmissionLimits
from gap08_ota_lifecycle_rollback.schema import validate
from gap08_ota_lifecycle_rollback.windows import MaintenancePolicy, Window


def start(w, sizes=(1, 2, 3, 6), **kw):
    c = w.controller()
    st = c.create(OPERATOR, bundle="v2", waves=spread_waves(w, sizes), environment="prod",
                  verification=w.verification(), compat_profile=COMPAT, lineage="edge-agent", **kw)
    return c, st["rollout_id"]


class HappyPathAndRollback(unittest.TestCase):
    def test_full_rollout_traceable_and_sealed(self):
        w = build_world()
        c, rid = start(w)
        for _ in range(4):
            c.step(OPERATOR, rid)
            w.pass_gate(c, rid)
        st = c.status(rid)
        self.assertEqual(st["phase"], "complete")
        self.assertTrue(all(v == "v2" for v in w.observed().values()))
        state = w.store.load(rid).state
        validate(state, "PK_CONTROLLER_STATE/1")
        # causal trace: created -> policy_admitted -> dispatch_intent -> dispatch_result -> wave_gate
        events = [e["event"] for e in state["core"]["audit_log"]]
        self.assertEqual(events[:3], ["rollback_target_pinned", "bundle_admitted", "rollout_created"])
        self.assertEqual(events[3:8], ["policy_admitted", "dispatch_intent", "dispatch_result", "wave_gate",
                                       "policy_admitted"][:5])
        w.sink.verify(w.ring)
        w.sink.verify_against(state["core"]["audit_log"])
        self.assertEqual(state["sealed_count"], len(state["core"]["audit_log"]))

    def test_failed_gate_rolls_back_at_canary(self):
        w = build_world()
        c, rid = start(w)
        c.step(OPERATOR, rid)
        r = w.pass_gate(c, rid, healthy=False)
        self.assertEqual(r["phase"], "rolled_back")
        self.assertTrue(all(v == "v1" for v in w.observed().values()))
        with self.assertRaises(IllegalTransition):
            c.step(OPERATOR, rid)

    def test_rollback_failure_quarantined_then_released_with_two_people(self):
        w = build_world()
        c, rid = start(w)
        c.step(OPERATOR, rid)
        w.pass_gate(c, rid)
        c.step(OPERATOR, rid)
        wave2 = c.status(rid)["pending"]["nodes"]
        w.nodes[wave2[0]].fail_ops.add("rollback")
        r = w.pass_gate(c, rid, healthy=False)
        self.assertEqual(r["phase"], "rollback_incomplete")
        self.assertEqual(r["quarantined"], [wave2[0]])
        node = wave2[0]
        # operator remediates the node out of band (reimage) -> now on v1
        w.nodes[node].fail_ops.clear()
        w.nodes[node].version = "v1"
        with self.assertRaises(Unauthorized):  # requester cannot self-approve
            a = w.approvals.request(SRE, Cap.QUARANTINE_RELEASE, f"release:{rid}:{node}", "reimaged")
            w.approvals.approve(Principal("carol", frozenset({"release-approver"})), a)
        a = w.approvals.request(SRE, Cap.QUARANTINE_RELEASE, f"release:{rid}:{node}", "reimaged")
        w.approvals.approve(APPROVER, a)
        r = c.release_quarantine(SRE, rid, node, approval_id=a, evidence_note="reimaged from golden image")
        self.assertEqual(r["quarantined"], [])
        self.assertEqual(r["phase"], "rolled_back")

    def test_release_refused_if_node_not_verifiably_recovered(self):
        w = build_world()
        c, rid = start(w)
        c.step(OPERATOR, rid)
        n = c.status(rid)["pending"]["nodes"][0]
        w.nodes[n].fail_ops.add("rollback")
        w.pass_gate(c, rid, healthy=False)
        a = w.approvals.request(SRE, Cap.QUARANTINE_RELEASE, f"release:{rid}:{n}", "trying")
        w.approvals.approve(APPROVER, a)
        with self.assertRaises(EvidenceRejected):
            c.release_quarantine(SRE, rid, n, approval_id=a, evidence_note="not actually fixed")


class DeferredAndIdempotency(unittest.TestCase):
    def test_offline_node_deferred_then_retried_behind_gate(self):
        # a deferred node counts as unavailable for blast radius, so use 4-node fault domains
        w = build_world(24, max_fraction_per_domain=0.75)
        c, rid = start(w, sizes=(2, 4, 8, 10))
        wave1 = spread_waves(w, (2, 4, 8, 10))[0]
        w.channel.offline.add(wave1[1])
        c.step(OPERATOR, rid)
        r = w.pass_gate(c, rid)
        self.assertEqual(r["deferred"], [wave1[1]])
        self.assertEqual(w.nodes[wave1[1]].version, "v1")
        for _ in range(3):
            c.step(OPERATOR, rid)
            w.pass_gate(c, rid)
        self.assertEqual(c.status(rid)["phase"], "deferred")  # never 'complete' with deferred nodes
        w.channel.offline.clear()
        w.clock.advance(3600)
        c.retry_deferred(OPERATOR, rid)
        r = w.pass_gate(c, rid)
        self.assertEqual(r["phase"], "complete")
        self.assertEqual(w.nodes[wave1[1]].version, "v2")

    def test_expired_verification_blocks_deferred_retry_until_reverified(self):
        w = build_world(24, max_fraction_per_domain=0.75)
        c, rid = start(w, sizes=(2, 4, 8, 10))
        n = spread_waves(w, (2, 4, 8, 10))[0][1]
        w.channel.offline.add(n)
        for _ in range(4):
            c.step(OPERATOR, rid)
            w.pass_gate(c, rid)
        w.channel.offline.clear()
        w.clock.advance(2 * 86400)                      # GAP-07 statement (24h) expired
        with self.assertRaises(EvidenceRejected):
            c.retry_deferred(OPERATOR, rid, force=True)
        with self.assertRaises(EvidenceRejected):       # a different artifact is never accepted
            c.reverify(OPERATOR, rid, w.verification(digest="sha256:" + "0" * 64))
        c.reverify(OPERATOR, rid, w.verification())
        c.retry_deferred(OPERATOR, rid, force=True)
        self.assertEqual(w.pass_gate(c, rid)["phase"], "complete")

    def test_lost_ack_and_duplicate_delivery_execute_once(self):
        w = build_world()
        c, rid = start(w)
        n = spread_waves(w, (1,))[0][0]
        w.channel.drop_ack[n] = 2
        w.channel.duplicate = True
        c.step(OPERATOR, rid)
        self.assertEqual(w.nodes[n].executions, 1)
        out = w.store.load(rid).state["pending"]["outcomes"][n]
        self.assertEqual(out["status"], "ok")

    def test_unknown_outcome_is_never_success(self):
        w = build_world()
        c, rid = start(w)
        n = spread_waves(w, (1,))[0][0]
        w.channel.drop_ack[n] = 99  # node installs but controller never gets an ack
        c.step(OPERATOR, rid)
        out = w.store.load(rid).state["pending"]["outcomes"][n]
        self.assertEqual(out["status"], "unknown")
        self.assertIn(n, c.status(rid)["needs_reconcile"])
        w.channel.drop_ack.clear()
        r = w.pass_gate(c, rid)
        self.assertEqual(r["deferred"], [n])
        rec = c.reconcile(OPERATOR, rid)
        self.assertEqual(rec["drift"][n]["class"], "installed_while_deferred")


class FencingRecovery(unittest.TestCase):
    def test_stale_controller_cannot_mutate(self):
        w = build_world()
        a, rid = start(w)
        a.step(OPERATOR, rid)
        w.clock.advance(31)                      # A's lease lapses
        b = w.controller("ctl-2")
        b.recover(rid)                           # B takes over with a higher fence
        with self.assertRaises((Conflict, StaleFence)):
            w.pass_gate(a, rid, settle=0)        # A cannot gate / commit
        w.pass_gate(b, rid)
        self.assertGreater(b.status(rid)["fence"], 1)

    def test_crash_after_write_ahead_intent_recovers_idempotently(self):
        w = build_world()
        a, rid = start(w)
        orig = a._send
        a._send = lambda *args, **kw: (_ for _ in ()).throw(SystemExit("crash"))  # die after intent commit
        with self.assertRaises(SystemExit):
            a.step(OPERATOR, rid)
        self.assertEqual(w.store.load(rid).state["pending"]["status"], "dispatching")
        a._send = orig
        w.clock.advance(31)
        b = w.controller("ctl-2")
        st = b.recover(rid)
        self.assertEqual(st["pending"]["status"], "awaiting_gate")
        n = st["pending"]["nodes"][0]
        self.assertEqual(w.nodes[n].executions, 1)
        w.pass_gate(b, rid)

    def test_nodes_reject_stale_fence_commands(self):
        w = build_world()
        a, rid = start(w)
        n = spread_waves(w, (1,))[0][0]
        a.executor.run(rollout_id=rid, fence=10, op="query", nodes=[n], target_version=None, digest=None,
                       attempt_group="x")
        out = a.executor.run(rollout_id=rid, fence=3, op="install", nodes=[n], target_version="v2",
                             digest=w.digest, attempt_group="y")[n]
        self.assertEqual(out.status, "failed")
        self.assertIn("stale_fence", out.reason)


class PolicyControls(unittest.TestCase):
    def test_conflicting_rollout_blocked(self):
        w = build_world()
        start(w)
        with self.assertRaises(Conflict):
            start(w)

    def test_freeze_blocks_forward_not_rollback_and_unfreeze_needs_second_person(self):
        w = build_world()
        c, rid = start(w)
        c.step(OPERATOR, rid)
        w.pass_gate(c, rid)
        w.freeze.freeze(SRE, "global", "*", "bad telemetry across fleet")
        with self.assertRaises(Frozen):
            c.step(OPERATOR, rid)
        a = w.approvals.request(SECURITY, Cap.UNFREEZE, "global:*", "resolved")
        with self.assertRaises(Unauthorized):
            w.freeze.unfreeze(SECURITY, "global", "*", a)       # not yet approved
        w.approvals.approve(APPROVER, a)
        w.freeze.unfreeze(SECURITY, "global", "*", a)
        w.freeze.freeze(SRE, "artifact", w.digest, "CVE in bundle")
        with self.assertRaises(Frozen):
            c.step(OPERATOR, rid)
        r = c.rollback(SRE, rid, reason="artifact disabled")
        self.assertEqual(r["phase"], "rolled_back")

    def test_authorization_enforced(self):
        w = build_world()
        viewer = Principal("eve", frozenset({"viewer"}))
        tenant = Principal("t1", frozenset({"release-operator"}), tenant="acme")
        c = w.controller()
        for who in (viewer, tenant):
            with self.assertRaises(Unauthorized):
                c.create(who, bundle="v2", waves=spread_waves(w, (1,)), environment="prod",
                         verification=w.verification(), compat_profile=COMPAT)
        c, rid = start(w)
        c.step(OPERATOR, rid)
        with self.assertRaises(Unauthorized):  # operators cannot submit gate evidence as the controller
            c.gate(viewer, rid, {})

    def test_topology_blast_radius_denies_whole_domain(self):
        w = build_world()
        bad = sorted(w.nodes)[:12:3]  # n001,n004,n007,n010 = all of site0
        c = w.controller()
        waves = [bad[:1], bad[1:]] + [[n for n in sorted(w.nodes) if n not in bad]]
        st = c.create(OPERATOR, bundle="v2", waves=waves, environment="prod", verification=w.verification(),
                      compat_profile=COMPAT)
        c.step(OPERATOR, st["rollout_id"])
        w.pass_gate(c, st["rollout_id"])
        with self.assertRaises(PolicyDenied):
            c.step(OPERATOR, st["rollout_id"])

    def test_maintenance_window(self):
        w = build_world()
        c, rid = start(w)
        c.windows = MaintenancePolicy(site_offsets_min={f"site{i}": 0 for i in range(3)},
                                      default_windows=[Window(frozenset(range(7)), 0, 1)])
        with self.assertRaises(PolicyDenied):
            c.step(OPERATOR, rid)

    def test_backpressure_limits(self):
        w = build_world(limits=AdmissionLimits(max_active_rollouts=1, api_rate_per_s=1000, api_burst=1000,
                                               max_wave_fanout=3))
        with self.assertRaises(Overloaded):
            start(w, sizes=(1, 2, 3, 6))   # wave of 6 > fan-out 3

    def test_incompatible_profile_fails_closed(self):
        w = build_world()
        c = w.controller()
        with self.assertRaises(Incompatible):
            c.create(OPERATOR, bundle="v2", waves=spread_waves(w, (1,)), environment="prod",
                     verification=w.verification(), compat_profile={**COMPAT, "arch": "mips"})


class DependencyFailClosed(unittest.TestCase):
    def test_required_dependency_down_blocks_forward(self):
        w = build_world()
        c, rid = start(w)
        w.deps.report("health", False)
        with self.assertRaises(DependencyUnavailable):
            c.step(OPERATOR, rid)

    def test_audit_sink_outage_blocks_forward_buffers_rollback(self):
        w = build_world()
        c, rid = start(w)
        c.step(OPERATOR, rid)
        w.pass_gate(c, rid)
        w.sink.available = False
        w.deps.report("audit_sink", False)
        with self.assertRaises(DependencyUnavailable):
            c.step(OPERATOR, rid)
        r = c.rollback(SRE, rid, reason="sink down, abort")
        self.assertEqual(r["phase"], "rolled_back")
        self.assertLess(r["sealed"], r["audit_events"])      # buffered, not lost
        w.sink.available = True
        w.deps.report("audit_sink", True)
        state, core, rev = c._load(rid)
        c._seal(state, core, rev, c._lease(rid).token, strict=True)
        self.assertEqual(c.status(rid)["sealed"], c.status(rid)["audit_events"])
        w.sink.verify(w.ring)


class Cancellation(unittest.TestCase):
    def test_cancel_before_touch(self):
        w = build_world()
        c, rid = start(w)
        self.assertEqual(c.cancel(OPERATOR, rid, reason="wrong bundle")["phase"], "cancelled")
        start(w)  # reservation released

    def test_pause_blocks_then_resume(self):
        w = build_world()
        c, rid = start(w)
        c.pause(SRE, rid, "investigating")
        with self.assertRaises(IllegalTransition):
            c.step(OPERATOR, rid)
        c.resume(OPERATOR, rid, "clear")
        c.step(OPERATOR, rid)

    def test_cancel_after_partial_rolls_back_or_abandons_with_approval(self):
        w = build_world()
        c, rid = start(w)
        c.step(OPERATOR, rid)
        w.pass_gate(c, rid)
        with self.assertRaises(Unauthorized):
            c.cancel(OPERATOR, rid, mode="abandon", reason="x")  # operator lacks OVERRIDE
        a = w.approvals.request(SRE, Cap.OVERRIDE, f"abandon:{rid}", "hardware refresh supersedes")
        w.approvals.approve(APPROVER, a)
        r = c.cancel(SRE, rid, mode="abandon", reason="superseded", approval_id=a)
        self.assertEqual(r["phase"], "abandoned")
        self.assertTrue(r["needs_reconcile"])


class ExplainTelemetry(unittest.TestCase):
    def test_explain_and_metrics(self):
        w = build_world()
        c, rid = start(w)
        c.step(OPERATOR, rid)
        w.pass_gate(c, rid, healthy=False)
        view = explain(w.store.load(rid).state)
        self.assertFalse(view["gates"][0]["healthy"])
        self.assertTrue(view["audit"]["fully_sealed"])
        self.assertIn("FAIL", render_text(view))
        prom = w.telemetry.prometheus()
        self.assertIn('gap08_rollbacks_total{complete="true",trigger="gate"} 1.0', prom)
        with self.assertRaises(ValueError):
            w.telemetry.inc("gap08_commands_total", node="n001")  # node ids never become labels


if __name__ == "__main__":
    unittest.main()
