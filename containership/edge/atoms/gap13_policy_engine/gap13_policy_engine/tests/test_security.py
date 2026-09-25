"""G13-MC-037 security suite derived from docs/THREAT_MODEL.md (IDs TM-xx)."""
import base64
import json
import unittest

import testkit as k
from gap13_policy_engine import errors as E
from gap13_policy_engine.canonical import canonical_bytes
from gap13_policy_engine.attributes import StaticContextProvider

g = k.g
TENANT_RULES = [
    {"name": "estate-deny-write", "effect": "deny", "scope": "estate", "match": {"action": "write"}},
    {"name": "t1-read", "effect": "allow", "scope": "tenant", "match": {"action": "read", "tenant": "t1"}},
    {"name": "admin-allow", "effect": "allow", "scope": "estate",
     "match": {"action": "read", "identity.kind": "human", "classification": "secret"}},
]


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.svc, self.c = k.service(require_separation_of_duties=False, context=StaticContextProvider({
            "svc-t1": {"tenant": "t1", "identity.kind": "service"},
            "svc-t2": {"tenant": "t2", "identity.kind": "service"},
        }))
        self.admin = k.principal("alice", clock=self.c)
        self.svc.load(self.admin, k.envelope(1, TENANT_RULES))
        self.t1 = k.principal("svc-t1", ("service",), kind="service", clock=self.c)
        self.t2 = k.principal("svc-t2", ("service",), kind="service", clock=self.c)

    def test_TM01_unsigned_permissive_bundle(self):
        doc = k.bundle_doc(2, [{"name": "allow-all", "effect": "allow", "scope": "estate", "match": {}}])
        payload = canonical_bytes(doc)
        forged = canonical_bytes({"schema": "PK_POLICY_SIGNED_BUNDLE/1", "payload_b64": base64.b64encode(payload).decode(),
                                  "digest": "sha256:" + __import__("hashlib").sha256(payload).hexdigest(),
                                  "signature": {"alg": "ed25519", "key_id": "k1", "value_b64": base64.b64encode(b"\0" * 64).decode()}})
        with self.assertRaises(E.VerificationFailed):
            self.svc.load(self.admin, forged)

    def test_TM02_attribute_injection_privilege(self):
        for attrs in ({"action": "read", "tenant": "t1"}, {"action": "read", "identity.kind": "human"},
                      {"action": "read", "classification": "secret"}):
            with self.subTest(attrs), self.assertRaises(E.AttributeRejected):
                self.svc.evaluate(self.t2, attrs)

    def test_TM03_cross_tenant_isolation(self):
        self.assertEqual(self.svc.evaluate(self.t1, {"action": "read"})["effect"], "allow")
        self.assertEqual(self.svc.evaluate(self.t2, {"action": "read"})["effect"], "deny")

    def test_TM04_tenant_widening(self):
        bad = TENANT_RULES + [{"name": "t1-write", "effect": "allow", "scope": "tenant",
                               "match": {"action": "write", "tenant": "t1"}}]
        with self.assertRaises(E.ScopeEscalation):
            self.svc.load(self.admin, k.envelope(2, bad))

    def test_TM05_replay_downgrade(self):
        self.svc.load(self.admin, k.envelope(2, TENANT_RULES))
        with self.assertRaises(E.ReplayRejected):
            self.svc.load(self.admin, k.envelope(1, TENANT_RULES))

    def test_TM06_tie_break_manipulation(self):
        # attacker-controlled allow at equal specificity can never beat a deny
        rules = [{"name": "aaaa-allow", "effect": "allow", "scope": "estate", "match": {"action": "write"}},
                 {"name": "zzzz-deny", "effect": "deny", "scope": "estate", "match": {"action": "write"}}]
        self.svc.load(self.admin, k.envelope(3, rules))
        v = self.svc.evaluate(self.t1, {"action": "write"})
        self.assertEqual((v["effect"], v["rule"], v["tie_break"]), ("deny", "zzzz-deny", True))

    def test_TM07_resource_exhaustion(self):
        with self.assertRaises(E.RequestTooLarge):
            self.svc.evaluate(self.t1, {f"x{i}": 1 for i in range(1000)})
        with self.assertRaises(E.VerificationFailed):
            self.svc.load(self.admin, b"{" * 3_000_000)
        big = [{"name": f"r{i}", "effect": "deny", "scope": "estate", "match": {"action": f"a{i}"}} for i in range(10_001)]
        with self.assertRaises(E.VerificationFailed):
            self.svc.load(self.admin, k.envelope(4, big))

    def test_TM08_type_confusion(self):
        rules = [{"name": "bool-allow", "effect": "allow", "scope": "estate", "match": {"operation_count": 1}}]
        self.svc.load(self.admin, k.envelope(5, rules))
        with self.assertRaises(E.AttributeRejected):
            self.svc.evaluate(self.t1, {"operation_count": True})

    def test_TM09_unicode_confusables_rejected(self):
        with self.assertRaises(E.AttributeRejected):
            self.svc.evaluate(self.t1, {"action": "re‍ad"})

    def test_TM10_spoofed_principal_and_privileged_ops(self):
        with self.assertRaises(E.Unauthorized):
            self.svc.load(self.t1, k.envelope(9))
        with self.assertRaises(E.Unauthorized):
            self.svc.set_control(self.t1, "NORMAL", reason="x", change_id="y")

    def test_TM11_information_disclosure_explain(self):
        x = self.svc.explain(self.t1, {"action": "read", "resource": "customer-4411"})
        self.assertEqual(x["matched"], [])
        self.assertNotIn("customer-4411", json.dumps(x))
        logs = json.dumps(self.svc.log.lines)
        self.assertNotIn("customer-4411", logs)
        self.assertNotIn('"t1"', logs)                   # tenant pseudonymised

    def test_TM12_algorithm_downgrade_via_bundle(self):
        env = json.loads(k.envelope(6))
        env["signature"]["alg"] = "none"
        r = self.svc.verifier.verify(canonical_bytes(env), now=k.T0)
        self.assertEqual(r.state.value, "UNSUPPORTED_ALGORITHM")


if __name__ == "__main__":
    unittest.main()
