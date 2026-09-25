import time, unittest
from inv65_capability_providers.tests.helpers import World, ident, POLICY_KEY
from inv65_capability_providers.authz.decision import sign_decision
from inv65_capability_providers.errors.mapping import ProviderFault


class Authz(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.w.svc.start(); self.w.link()

    def forbid(self, decision, op="get", name="primary"):
        with self.assertRaises(ProviderFault) as c:
            self.w.svc.call(self.w.token(), decision, link_name=name, op=op)
        self.assertEqual(c.exception.code, "PK_PROVIDER_FORBIDDEN")

    def test_absent_decision(self):
        self.forbid(None)

    def test_deny_effect(self):
        self.forbid(self.w.decision("call", "primary", ["get"], effect="deny"))

    def test_expired(self):
        d = self.w.decision("call", "primary", ["get"])
        d = sign_decision(POLICY_KEY, {**d, "issued_at": time.time() - 100, "expires_at": time.time() - 50})
        self.forbid(d)

    def test_overlong_validity(self):
        self.forbid(self.w.decision("call", "primary", ["get"], ttl=5000))

    def test_forged_signature(self):
        d = self.w.decision("call", "primary", ["get"]); d["signature"] = "a" * 64
        self.forbid(d)

    def test_tampered_after_signing(self):
        d = self.w.decision("call", "primary", ["get"]); d["resource"]["operations"] = ["get", "delete"]
        self.forbid(d, op="delete")

    def test_wrong_subject_scope(self):
        self.forbid(self.w.decision("call", "primary", ["get"], subject=ident(tenant="globex")))

    def test_wrong_action_link_contract_or_op(self):
        self.forbid(self.w.decision("link.create", "primary"))
        self.forbid(self.w.decision("call", "archive", ["get"]))
        self.forbid(self.w.decision("call", "primary", ["get"], contract="wasi:http"))
        self.forbid(self.w.decision("call", "primary", ["set"]))

    def test_link_creation_needs_link_create_decision(self):
        with self.assertRaises(ProviderFault) as c:
            self.w.svc.link(self.w.token(), self.w.decision("call", "x", ["get"]), link_name="x", config={"bucket": "b", "user": "u"})
        self.assertEqual(c.exception.code, "PK_PROVIDER_FORBIDDEN")
