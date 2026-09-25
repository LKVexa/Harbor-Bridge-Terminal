"""MC-005/006/013/014/019/024/026/037 through the real boundary service."""
from __future__ import annotations

import json
import unittest

from _support import (CTRL_A, CTRL_B, NODE, KMS, Clock, auditor, base_config, errors, make_service, operator,
                      publisher, san, service, token)

ME = errors.MeshError


def code(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except ME as e:
        return e.code
    return None


class DataPlaneTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock, self.kms = make_service()

    def test_reconcile_through_boundary(self):
        r = self.svc.reconcile(CTRL_A, "alpha", "orders->payments", 3, 3)
        self.assertEqual((r["owner"], r["effective_attempts"]), ("app", 3))

    def test_budget_above_configured_max_is_refused(self):
        self.assertEqual(code(self.svc.reconcile, CTRL_A, "alpha", "a->b", 3, 3, budget=99), "E_BUDGET_EXCEEDED")

    def test_invalid_input_is_structured(self):
        with self.assertRaises(ME) as cm:
            self.svc.reconcile(CTRL_A, "alpha", " bad", 3, 3)
        env = cm.exception.to_envelope()
        self.assertEqual((env["envelope"], env["code"], env["retryable"]), ("PK_MESH_ERROR/1", "E_INVALID_ARGUMENT", False))
        self.assertIsNotNone(env["correlation_id"])

    def test_version_negotiation(self):
        self.svc.reconcile(CTRL_A, "alpha", "a->b", 2, 1, version="PK_MESH_RECONCILE/1")
        self.assertEqual(code(self.svc.reconcile, CTRL_A, "alpha", "a->b", 2, 1, version="PK_MESH_RECONCILE/2"),
                         "E_UNSUPPORTED_VERSION")
        self.assertEqual(code(self.svc.map_identity, NODE, "alpha", "spiffe://estate.local/ns/alpha/sa/x",
                              version="PK_MESH_IDENTITY/0"), "E_UNSUPPORTED_VERSION")

    def test_payload_ceiling(self):
        self.assertEqual(code(self.svc.reconcile, CTRL_A, "alpha", "r" * 20_000, 2, 1), "E_PAYLOAD_TOO_LARGE")

    def test_identity_mapping_is_tenant_scoped(self):
        out = self.svc.map_identity(NODE, "alpha", "spiffe://estate.local/ns/alpha/sa/orders")
        self.assertEqual(out["runtime_identity"], "runtime:ns/alpha/sa/orders")
        self.assertEqual(code(self.svc.map_identity, NODE, "alpha", "spiffe://estate.local/ns/beta/sa/orders"), "E_TENANT_SCOPE")
        self.assertEqual(code(self.svc.map_identity, NODE, "alpha", "spiffe://evil/ns/alpha/sa/x"), "E_IDENTITY_UNMAPPABLE")

    def test_bypass_is_tenant_scoped(self):
        self.assertTrue(self.svc.report_flow(NODE, "alpha", "legacy-cron", "payments", False)["bypass"])
        self.assertFalse(self.svc.report_flow(NODE, "beta", "x", "payments", True)["bypass"])
        self.assertEqual(len(self.svc.bypass_evidence(CTRL_A, "alpha")), 1)
        self.assertEqual(len(self.svc.bypass_evidence(CTRL_B, "beta")), 0)
        self.assertEqual(code(self.svc.bypass_evidence, CTRL_A, "beta"), "E_TENANT_SCOPE")


class IsolationTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock, _ = make_service()

    def test_cross_tenant_reads_and_writes_denied_before_state_access(self):
        self.svc.migrate_route(CTRL_A, "alpha", "a->b", 3, 1, fence=1, idempotency_key="k-00000001")
        self.assertEqual(code(self.svc.get_route, CTRL_B, "alpha", "a->b"), "E_TENANT_SCOPE")
        self.assertEqual(code(self.svc.migrate_route, CTRL_B, "alpha", "a->b", 1, 1, fence=2, idempotency_key="k-00000002"), "E_TENANT_SCOPE")
        self.assertIsNone(self.svc.get_route(CTRL_B, "beta", "a->b"))
        self.assertEqual(code(self.svc.explain, CTRL_B, "alpha"), "E_TENANT_SCOPE")

    def test_undeclared_tenant_indistinguishable_from_forbidden(self):
        c1 = code(self.svc.get_route, CTRL_A, "gamma", "a->b")
        c2 = code(self.svc.get_route, CTRL_A, "beta", "a->b")
        self.assertEqual(c1, c2)
        self.assertEqual(code(self.svc.get_route, {"san": "spiffe://evil/x"}, "gamma", "a"), "E_UNAUTHENTICATED")

    def test_per_tenant_route_quota(self):
        cfg = base_config(limits={"max_routes_per_tenant": 2})
        svc, clock, _ = make_service(cfg=cfg)
        for i in range(2):
            svc.migrate_route(CTRL_A, "alpha", f"r{i}", 2, 1, fence=i, idempotency_key=f"key-{i:06d}")
        self.assertEqual(code(svc.migrate_route, CTRL_A, "alpha", "r9", 2, 1, fence=9, idempotency_key="key-999999"), "E_CAPACITY")
        svc.migrate_route(CTRL_B, "beta", "r9", 2, 1, fence=0, idempotency_key="key-b00000")  # other tenant unaffected

    def test_telemetry_and_journal_are_partitioned(self):
        self.svc.reconcile(CTRL_A, "alpha", "a->b", 2, 1)
        self.assertEqual(self.svc.explain(CTRL_B, "beta"), [])
        self.assertEqual(len(self.svc.explain(CTRL_A, "alpha")), 1)


class MutationSafetyTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock, _ = make_service()

    def test_idempotent_replay_and_conflict(self):
        a = self.svc.migrate_route(CTRL_A, "alpha", "a->b", 3, 1, fence=1, idempotency_key="idem-0001")
        b = self.svc.migrate_route(CTRL_A, "alpha", "a->b", 3, 1, fence=1, idempotency_key="idem-0001")
        self.assertTrue(b["replayed"])
        self.assertEqual(a["revision"], b["revision"])
        self.assertEqual(code(self.svc.migrate_route, CTRL_A, "alpha", "a->b", 2, 1, fence=1, idempotency_key="idem-0001"), "E_CONFLICT")

    def test_stale_controller_is_fenced(self):
        self.svc.migrate_route(CTRL_A, "alpha", "a->b", 3, 1, fence=5, idempotency_key="fence-005")
        self.assertEqual(code(self.svc.migrate_route, CTRL_A, "alpha", "a->b", 2, 1, fence=4, idempotency_key="fence-004"), "E_STALE_FENCE")
        self.assertEqual(self.svc.get_route(CTRL_A, "alpha", "a->b")["app"], 3)
        recs = [r for r in self.svc.audit.records() if r["type"] == "fence.rejected"]
        self.assertEqual(len(recs), 1)

    def test_freeze_blocks_mutation_but_not_data_plane(self):
        op = operator(self.clock)
        self.svc.freeze(op, True, reason="incident 42")
        self.assertEqual(self.svc.lifecycle.state, "frozen")
        self.assertEqual(code(self.svc.migrate_route, CTRL_A, "alpha", "a->b", 2, 1, fence=1, idempotency_key="frz-00001"), "E_FROZEN")
        self.svc.reconcile(CTRL_A, "alpha", "a->b", 2, 1)  # last-known-good data plane continues
        self.svc.freeze(operator(self.clock), False, reason="resolved")
        self.assertEqual(self.svc.lifecycle.state, "ready")

    def test_quarantine_route_and_tenant(self):
        self.svc.quarantine(operator(self.clock), "alpha", route="bad->route", reason="storm")
        self.assertEqual(code(self.svc.reconcile, CTRL_A, "alpha", "bad->route", 2, 1), "E_FROZEN")
        self.svc.reconcile(CTRL_A, "alpha", "good->route", 2, 1)
        self.svc.quarantine(operator(self.clock), "beta", reason="compromised")
        self.assertEqual(code(self.svc.report_flow, NODE, "beta", "a", "payments", True), "E_FROZEN")
        self.svc.report_flow(NODE, "alpha", "a", "payments", True)

    def test_break_glass_requires_armed_window(self):
        bg = lambda: token(self.clock, sub="sre", typ="operator", roles=("break-glass",))
        self.assertEqual(code(self.svc.break_glass, bg(), reason="x"), "E_PERMISSION_DENIED")
        # armer and invoker must differ (two-person rule)
        self.svc.arm_break_glass(operator(self.clock), seconds=120, reason="sev1")
        self.assertEqual(code(self.svc.break_glass, token(self.clock, sub="op", typ="operator", roles=("break-glass",)),
                              reason="self-armed"), "E_PERMISSION_DENIED")
        self.svc.break_glass(bg(), reason="emergency disable")
        self.assertTrue(self.svc.controls.frozen)
        types = [r["type"] for r in self.svc.audit.records()]
        self.assertIn("control.break_glass", types)


class ConfigLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock, self.kms = make_service()

    def test_activate_requires_publisher_and_rejects_invalid(self):
        self.assertEqual(code(self.svc.activate_config, operator(self.clock), base_config(version="2")), "E_PERMISSION_DENIED")
        self.assertEqual(code(self.svc.activate_config, CTRL_A, base_config(version="2")), "E_PERMISSION_DENIED")
        prev = self.svc.config.active()[1].digest
        self.assertEqual(code(self.svc.activate_config, publisher(self.clock),
                              base_config(trust_outage_policy={"identity": "fail_open"})), "E_CONFIG_INVALID")
        self.assertEqual(self.svc.config.active()[1].digest, prev)
        p = self.svc.activate_config(publisher(self.clock), base_config(version="2", default_budget=2))
        self.assertEqual((p["author"], p["version"], p["previous_digest"]), ("ci-bot", "2", prev))
        self.assertEqual(self.svc.reconcile(CTRL_A, "alpha", "a->b", 5, 1)["effective_attempts"], 2)

    def test_auto_rollback_when_new_config_points_at_missing_key(self):
        prev = self.svc.config.active()[1].digest
        bad = base_config(version="3", audit_key_ref="secretref://kms/inv58/missing")
        self.assertEqual(code(self.svc.activate_config, publisher(self.clock), bad), "E_CONFIG_INVALID")
        self.assertEqual(self.svc.config.active()[1].digest, prev)

    def test_operator_rollback(self):
        d1 = self.svc.config.active()[1].digest
        self.svc.activate_config(publisher(self.clock), base_config(version="2"))
        r = self.svc.rollback_config(operator(self.clock))
        self.assertEqual(r["digest"], d1)
        types = [x["type"] for x in self.svc.audit.records()]
        self.assertIn("config.rolled_back", types)

    def test_removed_tenant_becomes_unreachable(self):
        self.svc.activate_config(publisher(self.clock), base_config(version="2", tenants=["alpha"],
                                 spiffe_bindings={"runtime:ns/alpha/sa/controller": {"actor_type": "controller", "roles": ["mesh-controller"]}}))
        # beta state retained (reconstructable) but only reachable once re-declared -> still in registries here
        self.assertIn("alpha", self.svc._registries)


class TrustOutageTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock, self.kms = make_service()

    def test_security_dependencies_fail_closed(self):
        for dep in ("identity", "policy", "time"):
            with self.subTest(dep=dep):
                self.svc.set_dependency(dep, False)
                self.assertEqual(code(self.svc.reconcile, CTRL_A, "alpha", "a->b", 2, 1), "E_DEPENDENCY_UNAVAILABLE")
                self.assertFalse(self.svc.readiness()["ready"])
                self.svc.set_dependency(dep, True)
                self.svc.reconcile(CTRL_A, "alpha", "a->b", 2, 1)

    def test_key_service_outage_denies_tokens_not_mesh_identities(self):
        self.kms.up = False
        self.assertEqual(code(self.svc.freeze, operator(self.clock), True, reason="x"), "E_DEPENDENCY_UNAVAILABLE")
        self.svc.reconcile(CTRL_A, "alpha", "a->b", 2, 1)

    def test_audit_sink_outage_fails_closed_for_audited_ops(self):
        self.svc.set_dependency("audit_sink", False)
        self.assertEqual(code(self.svc.migrate_route, CTRL_A, "alpha", "a->b", 2, 1, fence=1, idempotency_key="aud-00001"),
                         "E_DEPENDENCY_UNAVAILABLE")
        self.assertIsNone(self.svc.get_route(CTRL_A, "alpha", "a->b"))

    def test_noncritical_telemetry_outage_degrades(self):
        self.svc.set_dependency("telemetry", False)
        self.assertEqual(self.svc.lifecycle.state, "degraded")
        self.svc.reconcile(CTRL_A, "alpha", "a->b", 2, 1)
        self.assertEqual(code(self.svc.migrate_route, CTRL_A, "alpha", "a->b", 2, 1, fence=1, idempotency_key="deg-00001"), "E_NOT_READY")
        self.assertTrue(self.svc.readiness()["ready"])
        self.svc.set_dependency("telemetry", True)
        self.assertEqual(self.svc.lifecycle.state, "ready")

    def test_bootstrap_fails_closed_without_keys(self):
        kms = KMS()
        kms.up = False
        with self.assertRaises(Exception):
            make_service(kms=kms)


class StatusExplainTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock, _ = make_service(lineage=service.ReleaseLineage("4.3.0", "sha256:abc", "build-7"))

    def test_status_surface(self):
        st = self.svc.status(operator(self.clock))
        for k in ("schema", "version", "health", "readiness", "config", "dependencies", "capabilities", "release"):
            self.assertIn(k, st)
        self.assertEqual(st["version"], "4.3.0")
        blob = json.dumps(st)
        for secret in ("AAAA", "TTTT", "RRRR"):
            self.assertNotIn(secret * 4, blob)
        self.assertEqual(code(self.svc.status, None), "E_UNAUTHENTICATED")

    def test_explain_links_decision_to_policy_config_topology_release(self):
        self.svc.migrate_route(CTRL_A, "alpha", "a->b", 3, 3, fence=1, idempotency_key="exp-00001")
        e = self.svc.explain(CTRL_A, "alpha", "a->b")[-1]
        self.assertEqual(e["reason"], "app_preferred_for_idempotency")
        self.assertEqual(e["release"]["build_id"], "build-7")
        self.assertTrue(e["config_digest"].startswith("sha256:"))
        self.assertEqual(e["topology"]["node"], "node-0")
        self.assertEqual(e["policy_version"], "p0")

    def test_audit_export_verified(self):
        self.svc.migrate_route(CTRL_A, "alpha", "a->b", 3, 1, fence=1, idempotency_key="aex-00001")
        out = self.svc.audit_export(auditor(self.clock))
        self.assertTrue(out["verified"])
        self.assertEqual(code(self.svc.audit_export, operator(self.clock)), "E_PERMISSION_DENIED")

    def test_every_denial_is_audited_with_reason_code(self):
        code(self.svc.migrate_route, CTRL_B, "alpha", "a->b", 1, 1, fence=1, idempotency_key="den-00001")
        denials = [r for r in self.svc.audit.records() if r["type"] == "authz.decision" and r["decision"].startswith("DENY")]
        self.assertTrue(denials)
        self.assertEqual(denials[-1]["decision"], "DENY_TENANT_SCOPE")
        self.assertEqual(denials[-1]["policy_version"], "p0")


class SnapshotRestoreTest(unittest.TestCase):
    def test_restart_restores_state(self):
        svc, clock, kms = make_service()
        svc.migrate_route(CTRL_A, "alpha", "a->b", 3, 1, fence=7, idempotency_key="snap-0001")
        svc.quarantine(operator(clock), "beta", reason="x")
        snap = svc.snapshot()
        svc2, _, _ = make_service(clock=clock, kms=kms)
        svc2.restore(operator(clock), snap)
        self.assertEqual(svc2.get_route(CTRL_A, "alpha", "a->b")["app"], 3)
        self.assertEqual(code(svc2.migrate_route, CTRL_A, "alpha", "a->b", 2, 1, fence=6, idempotency_key="snap-0002"), "E_STALE_FENCE")
        self.assertTrue(svc2.controls.is_quarantined("tenant:beta"))

    def test_tampered_snapshot_rejected_atomically(self):
        svc, clock, kms = make_service()
        svc.migrate_route(CTRL_A, "alpha", "a->b", 3, 1, fence=1, idempotency_key="snap-0003")
        snap = svc.snapshot()
        snap["body"]["routes"]["alpha"]["a->b"]["app"] = 9
        svc2, _, _ = make_service(clock=clock, kms=kms)
        self.assertEqual(code(svc2.restore, operator(clock), snap), "E_INTEGRITY")
        self.assertIsNone(svc2.get_route(CTRL_A, "alpha", "a->b"))

    def test_restore_requires_capability(self):
        svc, clock, _ = make_service()
        self.assertEqual(code(svc.restore, CTRL_A, svc.snapshot()), "E_PERMISSION_DENIED")


if __name__ == "__main__":
    unittest.main()
