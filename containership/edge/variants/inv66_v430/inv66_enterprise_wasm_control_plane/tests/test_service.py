"""End-to-end behaviour of the production service (MC-008/009/015/016/017/019/024/032/033/042/053/069/070)."""
from __future__ import annotations

import unittest

from support import Harness, component, config, image, request, ROGUE_PRIV
from inv66_enterprise_wasm_control_plane.errors import ControlPlaneError
from inv66_enterprise_wasm_control_plane.schema import validate


def codes(resp):
    return sorted(e["code"] for e in resp["errors"])


class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.svc = self.h.svc

    def tearDown(self):
        self.h.close()

    def test_happy_path_is_delivered_and_matches_response_schema(self):
        r = self.svc.admit(self.h.tok(), request())
        self.assertTrue(r["admitted"], r)
        self.assertEqual(validate(r, "urn:inv66:schema:PK_ECP_ADMIT:1:response"), [])
        self.assertEqual(r["lifecycle_state"], "deployed")
        self.assertEqual(self.svc.state["decisions"][r["decision_id"]]["state"], "deployed")
        self.assertIn(r["decision_id"], self.h.deployer.received)
        self.assertEqual(r["policy_version"], "gap13-bundle-7")

    def test_unauthenticated_and_forged_callers_rejected(self):
        for tok in (None, "a.b.c", self.h.tok()[:-4] + "AAAA"):
            with self.assertRaises(ControlPlaneError) as cm:
                self.svc.admit(tok, request())
            self.assertIn(cm.exception.error.code, ("AUTHN_MISSING", "AUTHN_INVALID"))
        self.assertEqual(self.h.deployer.received, {})

    def test_rbac_scope_and_explicit_deny(self):
        with self.assertRaises(ControlPlaneError) as cm:
            self.svc.admit(self.h.tok("user:dev"), request())
        self.assertEqual(cm.exception.error.code, "AUTHZ_DENIED")
        self.assertTrue(self.svc.admit(self.h.tok("user:dev"), request(lattice="staging"))["admitted"])
        with self.assertRaises(ControlPlaneError) as cm:
            self.svc.admit(self.h.tok("user:ops"), request(lattice="restricted"))
        self.assertEqual(cm.exception.error.code, "AUTHZ_EXPLICIT_DENY")
        # group membership via configuration and via IdP claim
        self.assertTrue(self.svc.admit(self.h.tok("user:root"), request(rid="g1"))["admitted"])
        self.assertTrue(self.svc.admit(self.h.tok("user:x", groups=["sre"]), request(rid="g2"))["admitted"])

    def test_supply_chain_rejections_are_typed_and_not_forwarded(self):
        bad = [
            component("a", img="registry.estate.local/a:latest"),          # tag, not digest -> schema
        ]
        with self.assertRaises(ControlPlaneError) as cm:
            self.svc.admit(self.h.tok(), request(bad))
        self.assertEqual(cm.exception.error.code, "SCHEMA_INVALID")
        r = self.svc.admit(self.h.tok(), request([
            component("a", img=image("a", reg="ghcr.evil.example")),
            component("b", priv=ROGUE_PRIV),
            component("c", signer="someone"),
            component("d", attest=False),
        ]))
        self.assertFalse(r["admitted"])
        self.assertEqual(codes(r), ["ATTESTATION_MISSING", "REGISTRY_NOT_APPROVED", "SIGNATURE_INVALID", "SIGNER_NOT_APPROVED"])
        self.assertEqual(self.h.deployer.received, {})
        self.assertNotIn(r["decision_id"], self.svc.state["outbox"])

    def test_duplicate_and_limits(self):
        r = self.svc.admit(self.h.tok(), request([component("a"), component("a")]))
        self.assertEqual(codes(r), ["COMPONENT_DUPLICATE"])
        many = [component(f"c{i}") for i in range(65)]
        r = self.svc.admit(self.h.tok(), request(many, rid="big"))
        self.assertIn("MANIFEST_TOO_MANY_COMPONENTS", codes(r))

    def test_policy_engine_denial_and_unavailability_fail_closed(self):
        h = Harness(rules=[{"id": "no-debug", "deny_if": {"image_contains": "debug"}, "message": "no debug images"}])
        r = h.svc.admit(h.tok(), request([component("debug")]))
        self.assertEqual(codes(r), ["POLICY_DENIED"])
        self.assertEqual(r["errors"][0]["details"]["rule"], "no-debug")

        class Down:
            def evaluate(self, *a):
                raise ConnectionError("down")
        h.svc.policy_engine = Down()
        r = h.svc.admit(h.tok(), request(rid="x"))
        self.assertFalse(r["admitted"])
        self.assertEqual(codes(r), ["POLICY_UNAVAILABLE"])
        self.assertEqual(h.svc.readiness()["dependencies"]["policy-engine"], "degraded")
        h.close()

    def test_idempotency(self):
        req = request(idempotency_key="k-1")
        a = self.svc.admit(self.h.tok(), req)
        b = self.svc.admit(self.h.tok(), dict(req, request_id="r2"))
        self.assertEqual(a["decision_id"], b["decision_id"])
        self.assertTrue(b["replayed"])
        self.assertEqual(len(self.h.deployer.received), 1)
        with self.assertRaises(ControlPlaneError) as cm:
            self.svc.admit(self.h.tok(), request([component("other")], idempotency_key="k-1"))
        self.assertEqual(cm.exception.error.code, "IDEMPOTENCY_CONFLICT")

    def test_quota(self):
        h = Harness(cfg=config(quotas={"payments/prod-eu": {"admissions_per_minute": 2}}))
        h.svc.admit(h.tok(), request(rid="1"))
        h.svc.admit(h.tok(), request(rid="2"))
        with self.assertRaises(ControlPlaneError) as cm:
            h.svc.admit(h.tok(), request(rid="3"))
        self.assertEqual(cm.exception.error.code, "QUOTA_EXCEEDED")
        self.assertTrue(cm.exception.error.retryable)
        h.mono.t += 60
        self.assertTrue(h.svc.admit(h.tok(), request(rid="4"))["admitted"])
        h.close()

    def test_freeze_quarantine_and_lifecycle(self):
        root = self.h.tok("user:root")
        self.svc.set_freeze(root, "org:acme/tenant:payments", True, "incident 42")
        with self.assertRaises(ControlPlaneError) as cm:
            self.svc.admit(self.h.tok(), request())
        self.assertEqual(cm.exception.error.code, "FROZEN")
        self.svc.set_freeze(self.h.tok("user:root"), "org:acme/tenant:payments", False, "resolved")
        r = self.svc.admit(self.h.tok(), request())
        did = r["decision_id"]
        with self.assertRaises(ControlPlaneError) as cm:
            self.svc.transition(self.h.tok("user:root"), did, "proposed", "x")
        self.assertEqual(cm.exception.error.code, "ILLEGAL_TRANSITION")
        self.svc.transition(self.h.tok("user:root"), did, "quarantined", "suspicious")
        self.svc.transition(self.h.tok("user:root"), did, "rolled_back", "confirmed bad")
        self.assertEqual(self.svc.inventory(self.h.tok("user:auditor"))["lattices"]["payments/prod-eu"], {})
        states = [s["state"] for s in self.svc.state["decisions"][did]["history"]]
        self.assertEqual(states, ["proposed", "admitted", "delivering", "deployed", "quarantined", "rolled_back"])
        with self.assertRaises(ControlPlaneError):
            self.svc.set_freeze(self.h.tok("user:ops"), "org:acme", True, "not allowed")

    def test_frozen_scope_blocks_delivery_of_already_admitted(self):
        self.h.deployer.fail_next = 99
        r = self.svc.admit(self.h.tok(), request())
        self.assertEqual(self.svc.state["decisions"][r["decision_id"]]["state"], "delivery_failed")
        self.svc.set_freeze(self.h.tok("user:root"), "org:acme", True, "kill switch")
        self.h.deployer.fail_next = 0
        self.assertEqual(self.svc.drain_outbox(), {r["decision_id"]: "frozen"})
        self.assertEqual(self.h.deployer.received, {})

    def test_deploy_outage_is_retried_from_outbox(self):
        self.h.deployer.fail_next = 3
        r = self.svc.admit(self.h.tok(), request())
        self.assertTrue(r["admitted"])
        self.assertEqual(self.svc.state["decisions"][r["decision_id"]]["state"], "delivery_failed")
        self.assertEqual(self.svc.drain_outbox(), {r["decision_id"]: "deployed"})

    def test_config_activation_rollback_and_two_person_rule(self):
        root = self.h.tok("user:root")
        with self.assertRaises(ControlPlaneError) as cm:
            self.svc.apply_config(root, config(revision=2, approved_by=["alice"]))
        self.assertEqual(cm.exception.error.code, "CONFIG_INVALID")
        with self.assertRaises(ControlPlaneError):
            self.svc.apply_config(self.h.tok("user:ops"), config(revision=2))
        bad = config(revision=2)
        bad["limits"]["max_components"] = 0
        with self.assertRaises(ControlPlaneError):
            self.svc.apply_config(self.h.tok("user:root"), bad)
        self.assertEqual(self.svc.policy.revision, 1)              # nothing partially applied
        self.svc.apply_config(self.h.tok("user:root"), config(revision=2, registries=["other.local"]))
        r = self.svc.admit(self.h.tok(), request())
        self.assertEqual(codes(r), ["REGISTRY_NOT_APPROVED"])
        self.svc.rollback_config(self.h.tok("user:root"), 1)
        self.assertTrue(self.svc.admit(self.h.tok(), request(rid="after"))["admitted"])
        hist = [(h["revision"], h["action"]) for h in self.svc.state["config"]["history"]]
        self.assertEqual(hist, [(1, "bootstrap"), (2, "activate"), (1, "rollback")])
        with self.assertRaises(ControlPlaneError):
            self.svc.apply_config(self.h.tok("user:root"), config(revision=2))  # revision must increase

    def test_explain_inventory_audit_export(self):
        r = self.svc.admit(self.h.tok(), request())
        ex = self.svc.explain(self.h.tok("user:auditor"), r["decision_id"])
        self.assertEqual(ex["decision"]["principal"], "user:ops")
        self.assertEqual(ex["config"]["digest"], r["config_digest"])
        inv = self.svc.inventory(self.h.tok("user:auditor"), tenant="payments")
        self.assertEqual(inv["lattices"]["payments/prod-eu"]["api"]["decision_id"], r["decision_id"])
        q = self.svc.audit_query(self.h.tok("user:auditor"), kind="admission")
        self.assertEqual(len(q["records"]), 1)
        for rec in q["records"]:
            self.assertEqual(validate(rec, "urn:inv66:schema:PK_ECP_AUDIT:1:event"), [])
        exp = self.svc.audit_export(self.h.tok("user:auditor"))
        self.assertEqual(exp["manifest"]["count"], len(exp["records"]))
        with self.assertRaises(ControlPlaneError):
            self.svc.audit_query(self.h.tok("user:ops"))

    def test_logs_are_structured_and_redacted(self):
        tok = self.h.tok()
        self.svc.admit(tok, request())
        self.svc.log.log("info", "probe", authorization=tok, note=f"bearer {tok}")
        text = self.h.logs.getvalue()
        self.assertNotIn(tok, text)
        import json
        for line in text.splitlines():
            rec = json.loads(line)
            self.assertEqual(rec["schema"], "PK_ECP_LOG/1")

    def test_trace_context_propagates(self):
        tp = "00-" + "1" * 32 + "-" + "2" * 16 + "-01"
        r = self.svc.admit(self.h.tok(), request(), traceparent=tp)
        self.assertEqual(r["trace_id"], "1" * 32)

    def test_metrics_exposition(self):
        self.svc.admit(self.h.tok(), request())
        self.svc.refresh_gauges()
        text = self.svc.metrics.exposition()
        for name in ("inv66_admissions_total", "inv66_admission_latency_ms_bucket", "inv66_audit_entries_total",
                     "inv66_outbox_depth", "inv66_leader"):
            self.assertIn(name, text)


class GovernanceTest(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.svc = self.h.svc

    def tearDown(self):
        self.h.close()

    def test_optimistic_concurrency_on_config(self):
        stale = self.svc.policy.digest
        self.svc.apply_config(self.h.tok("user:root"), config(revision=2), if_match=stale)
        with self.assertRaises(ControlPlaneError) as cm:
            self.svc.apply_config(self.h.tok("user:root"), config(revision=3), if_match=stale)
        self.assertEqual(cm.exception.error.code, "STALE_REVISION")

    def test_no_privilege_escalation_through_config(self):
        # a tenant-scoped policy-admin cannot mint an org-admin binding
        cfg = config(revision=2)
        cfg["bindings"].append({"subject": "user:pa", "role": "policy-admin", "scope": "org:acme", "effect": "allow"})
        self.svc.apply_config(self.h.tok("user:root"), cfg)
        esc = config(revision=3)
        esc["bindings"] = cfg["bindings"] + [{"subject": "user:pa", "role": "org-admin", "scope": "org:acme", "effect": "allow"}]
        with self.assertRaises(ControlPlaneError) as cm:
            self.svc.apply_config(self.h.tok("user:pa"), esc)
        self.assertEqual(cm.exception.error.code, "PRIVILEGE_ESCALATION")

    def test_freeze_ttl_ticket_and_readiness(self):
        self.svc.set_freeze(self.h.tok("user:root"), "org:acme/tenant:payments", True, "drill", ticket="INC-1", ttl_s=60)
        self.assertEqual(self.svc.readiness()["freezes"]["org:acme/tenant:payments"]["ticket"], "INC-1")
        with self.assertRaises(ControlPlaneError):
            self.svc.admit(self.h.tok(), request())
        self.h.clock.t += 61
        self.assertTrue(self.svc.heartbeat())          # ops loop renews the lease
        self.assertTrue(self.svc.admit(self.h.tok(), request(rid="later"))["admitted"])
        with self.assertRaises(ControlPlaneError):
            self.svc.set_freeze(self.h.tok("user:root"), "org:acme", True, "")

    def test_access_review(self):
        rv = self.svc.access_review(self.h.tok("user:auditor"), "user:ops", "org:acme/tenant:payments/lattice:restricted")
        self.assertFalse(rv["capabilities"]["admit"]["allowed"])
        self.assertTrue(rv["capabilities"]["admit"]["explicit_deny"])

    def test_layered_config(self):
        from inv66_enterprise_wasm_control_plane.config import DEFAULTS, build_policy, merge_layers
        site = {k: v for k, v in config().items() if k != "limits"}
        pol = build_policy(merge_layers(DEFAULTS, site, {"limits": {"max_components": 8}}))
        self.assertEqual((pol.max_components, pol.max_manifest_bytes), (8, 1_000_000))


if __name__ == "__main__":
    unittest.main()
