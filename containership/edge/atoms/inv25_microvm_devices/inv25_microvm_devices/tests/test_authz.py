"""Items 9 and 10: authentication boundary and capability authorization (C023/C024)."""
import unittest

from _support import AUD, Clock, authz, token, verifier


class AuthnTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.v = verifier(self.clock)

    def test_valid(self):
        p = self.v.verify(token(self.v, "alice", ["catalogue.read"]))
        self.assertEqual(p.subject, "alice")

    def test_rejections(self):
        v = self.v
        cases = {
            "missing": None,
            "garbage": "not-a-token",
            "bad signature": token(v, "a", [], key=b"wrong"),
            "unknown key": token(v, "a", [], kid="k9"),
            "wrong issuer": token(v, "a", [], iss="evil"),
            "wrong audience": token(v, "a", [], aud="other"),
            "expired": token(v, "a", [], now=self.clock.t - 1000, ttl=10),
            "not yet valid": token(v, "a", [], now=self.clock.t + 1000),
        }
        for name, t in cases.items():
            with self.subTest(name), self.assertRaises(authz.Unauthenticated):
                v.verify(t)

    def test_revoked_subject_and_key(self):
        t = token(self.v, "mallory", [])
        self.v.revoked_subjects.add("mallory")
        self.assertRaises(authz.Unauthenticated, self.v.verify, t)
        t2 = token(self.v, "bob", [])
        self.v.revoked_keys.add("k1")
        self.assertRaises(authz.Unauthenticated, self.v.verify, t2)

    def test_replay(self):
        t = token(self.v, "a", [])
        self.v.verify(t)
        self.assertRaises(authz.ReplayDetected, self.v.verify, t)

    def test_clock_failure_fails_closed(self):
        def broken():
            raise OSError("ntp down")
        v = authz.Verifier(audience=AUD, keys=self.v.keys, clock=broken)
        self.assertRaises(authz.Unauthenticated, v.verify, token(self.v, "a", []))


class AuthorizationTest(unittest.TestCase):
    def P(self, caps, envs=("prod",), bg=False):
        return authz.Principal("s", "i", frozenset(caps), frozenset(envs), bg)

    def test_positive_per_capability(self):
        for cap in sorted(authz.CAPABILITIES - {"catalogue.emergency_disable"}):
            with self.subTest(cap):
                self.assertTrue(authz.authorize(self.P([cap]), cap, "prod").allowed)
        self.assertTrue(authz.authorize(self.P(["catalogue.emergency_disable"], bg=True),
                                        "catalogue.emergency_disable", "prod").allowed)

    def test_cross_role_negative(self):
        for cap in authz.CAPABILITIES:
            others = authz.CAPABILITIES - {cap}
            with self.subTest(cap), self.assertRaises(authz.Unauthorized):
                authz.authorize(self.P(others, bg=True), cap, "prod")

    def test_environment_boundary(self):
        self.assertRaises(authz.Unauthorized, authz.authorize, self.P(["catalogue.read"], ["dev"]),
                          "catalogue.read", "prod")

    def test_unknown_capability_denied(self):
        self.assertRaises(authz.Unauthorized, authz.authorize, self.P(authz.CAPABILITIES), "catalogue.root", "prod")

    def test_break_glass_required(self):
        self.assertRaises(authz.Unauthorized, authz.authorize, self.P(["catalogue.emergency_disable"]),
                          "catalogue.emergency_disable", "prod")

    def test_token_cannot_grant_unknown_capabilities(self):
        v = verifier()
        p = v.verify(token(v, "a", ["catalogue.read", "admin.*"]))
        self.assertEqual(p.capabilities, frozenset({"catalogue.read"}))

    def test_decision_is_recorded(self):
        d = authz.authorize(self.P(["catalogue.read"]), "catalogue.read", "prod")
        self.assertEqual(d.policy_revision, authz.POLICY_REVISION)


if __name__ == "__main__":
    unittest.main()
