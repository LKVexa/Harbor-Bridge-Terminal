"""Regression tests for the adversarial review findings on 4.3.0 (R1-R3)."""
from __future__ import annotations

import unittest

from tests.support import EcpError, Estate


class ReviewFindingsTest(unittest.TestCase):
    def test_R1_new_generation_cannot_lower_its_own_approval_bar(self):
        e = Estate(approvals=2)
        s = e.service
        weak = e.config(dual_authorization={"config_activate": 1, "quarantine_release": 1})
        admin = e.principal("root", groups=["platform-admins"])
        gen = s.stage_config(weak, admin, source_repo="g", source_rev="r")
        s.approve_config(gen, e.principal("sec1"))
        with self.assertRaises(EcpError) as cm:
            s.activate_config(gen, admin, expected_active=s.config.active.generation)
        self.assertEqual(cm.exception.code, "ECP_DUAL_AUTH_REQUIRED")
        s.approve_config(gen, e.principal("sec2"))
        s.activate_config(gen, admin, expected_active=s.config.active.generation)  # 2 approvals: allowed

    def test_R1_rollback_to_weaker_generation_needs_approvals(self):
        e = Estate(approvals=1)
        s = e.service
        cm_ = s.config
        weak_gen = cm_.active.generation
        strong = cm_.stage(e.config(dual_authorization={"config_activate": 2, "quarantine_release": 2}, site="s"),
                           author="a", source_repo="g", source_rev="r")
        cm_.approve(strong, "b")
        cm_.approve(strong, "c")
        cm_.activate(strong, activated_by="b", expected_active=weak_gen)
        with self.assertRaises(EcpError):
            cm_.rollback(weak_gen, activated_by="b", reason="undo")

    def test_R2_tenant_admin_cannot_remove_org_admin_deny(self):
        e = Estate()
        s = e.service
        org = e.principal("root", groups=["platform-admins"])
        deny = {"subject": "dev", "role": "deployer", "scope": "acme/payments/staging", "effect": "deny"}
        s.rbac({"protocol": "PK_ECP_RBAC/1", "op": "bind", "request_id": "1", "binding": deny}, org)
        with self.assertRaises(EcpError):
            s.admit(e.request("api", lattice="staging"), e.token("dev"))
        with self.assertRaises(EcpError) as cm:
            s.rbac({"protocol": "PK_ECP_RBAC/1", "op": "unbind", "request_id": "2", "binding": deny}, e.principal("tadmin"))
        self.assertEqual(cm.exception.code, "ECP_FORBIDDEN")
        self.assertEqual(e.open().overlay_authority, s.overlay_authority)  # authority survives replay
        s.rbac({"protocol": "PK_ECP_RBAC/1", "op": "unbind", "request_id": "3", "binding": deny}, org)
        self.assertTrue(s.admit(e.request("api", lattice="staging"), e.token("dev"))["admitted"])

    def test_R2_config_bindings_cannot_be_unbound_via_overlay_api(self):
        e = Estate()
        with self.assertRaises(EcpError) as cm:
            e.service.rbac({"protocol": "PK_ECP_RBAC/1", "op": "unbind", "request_id": "x",
                            "binding": {"subject": "contractor", "role": "deployer", "scope": "acme/payments/prod",
                                        "effect": "deny"}}, e.principal("tadmin"))
        self.assertEqual(cm.exception.code, "ECP_NOT_FOUND")

    def test_R3_idempotency_keys_are_scoped_to_the_principal(self):
        e = Estate()
        s = e.service
        r = e.request("api", lattice="staging", key="shared-key")
        d1 = s.admit(r, e.token("contractor"))
        d2 = s.admit(dict(r), e.token("payments-bot", kind="service", groups=["platform-admins"]))
        self.assertNotEqual(d1["decision_id"], d2["decision_id"])
        self.assertFalse(d2["idempotent_replay"])
        self.assertEqual(d2["principal"]["subject"], "payments-bot")


if __name__ == "__main__":
    unittest.main()
