"""MC-005 / MC-011 / MC-012: boundary authN, deny-by-default capability authZ, least privilege."""
from __future__ import annotations

import time
import unittest

from _support import KEYS, Clock, authz, token


def _authn(clock, key_ok=True, **kw):
    def key():
        if not key_ok:
            raise ConnectionError("kms down")
        return KEYS["inv58/token"]
    return authz.Authenticator(trust_domain="estate.local", token_key=key, clock=clock,
                               spiffe_bindings={"runtime:node/n1": ("node", {"mesh-node"}, {"alpha"}),
                                                "runtime:ns/alpha/sa/ctl": ("controller", {"mesh-controller"})}, **kw)


def _authz(clock, **kw):
    pol = authz.CapabilityPolicy("p1", {k: frozenset(v) for k, v in authz.DEFAULT_ROLES.items()}, issued_at=clock(), **kw)
    return authz.Authorizer(pol, clock=clock)


class BoundaryMatrixTest(unittest.TestCase):
    def test_every_operation_has_capability_actor_mechanism_scope(self):
        for op, (cap, actors, mechs, scoped) in authz.BOUNDARY_MATRIX.items():
            self.assertIn(cap, authz.CAPABILITIES, op)
            self.assertTrue(actors and set(actors) <= set(authz.ACTOR_TYPES), op)
            self.assertTrue(mechs and set(mechs) <= set(authz.AUTH_MECHANISMS), op)
            self.assertIsInstance(scoped, bool)

    def test_declared_interfaces_are_in_the_matrix(self):
        for op in ("reconcile", "identity", "bypass", "config.activate", "config.rollback", "status",
                   "control.freeze", "control.break_glass", "audit.export"):
            self.assertIn(op, authz.BOUNDARY_MATRIX)

    def test_read_and_mutation_capabilities_are_separated(self):
        for role, caps in authz.DEFAULT_ROLES.items():
            if "status.read" in caps and role == "mesh-observer":
                self.assertFalse(caps & {"route.migrate", "config.activate", "control.freeze", "audit.export"})
        self.assertNotIn("config.activate", authz.DEFAULT_ROLES["mesh-operator"])  # separation of duties
        only_bg = [r for r, c in authz.DEFAULT_ROLES.items() if "control.break_glass" in c]
        self.assertEqual(only_bg, ["break-glass"])

    def test_privilege_inventory_is_complete(self):
        inv = authz.privilege_inventory()
        self.assertEqual({r["role"] for r in inv}, set(authz.DEFAULT_ROLES))
        for row in inv:
            self.assertTrue(row["operations"], row["role"])


class AuthenticationTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.a = _authn(self.clock)

    def test_valid_token(self):
        p = self.a.from_token(token(self.clock)["token"])
        self.assertIsInstance(p, authz.Principal)
        self.assertEqual((p.subject, p.actor_type, p.mechanism), ("alice", "operator", "signed_token"))

    def test_expired_not_yet_valid_ttl_audience_signature(self):
        t0 = int(self.clock())
        self.assertEqual(self.a.from_token(token(self.clock, iat=t0 - 1000, ttl=300)["token"]), "DENY_EXPIRED")
        self.assertEqual(self.a.from_token(token(self.clock, iat=t0 + 1000)["token"]), "DENY_NOT_YET_VALID")
        self.assertEqual(self.a.from_token(token(self.clock, ttl=10_000)["token"]), "DENY_UNAUTHENTICATED")
        self.assertEqual(self.a.from_token(token(self.clock, aud="other")["token"]), "DENY_AUDIENCE")
        self.assertEqual(self.a.from_token(token(self.clock, key=b"X" * 32)["token"]), "DENY_BAD_SIGNATURE")

    def test_clock_skew_boundaries(self):
        t0 = int(self.clock())
        self.assertIsInstance(self.a.from_token(token(self.clock, iat=t0 + 29)["token"]), authz.Principal)
        self.assertEqual(self.a.from_token(token(self.clock, iat=t0 + 31)["token"]), "DENY_NOT_YET_VALID")
        self.assertIsInstance(self.a.from_token(token(self.clock, iat=t0 - 300 - 29, ttl=300)["token"]), authz.Principal)
        self.assertEqual(self.a.from_token(token(self.clock, iat=t0 - 300 - 30, ttl=300)["token"]), "DENY_EXPIRED")

    def test_replay_is_refused(self):
        t = token(self.clock, nonce="same-nonce")["token"]
        self.assertIsInstance(self.a.from_token(t), authz.Principal)
        self.assertEqual(self.a.from_token(t), "DENY_REPLAY")

    def test_replay_cache_saturation_fails_closed(self):
        a = _authn(self.clock, replay_cache_size=2)
        a.from_token(token(self.clock)["token"])
        a.from_token(token(self.clock)["token"])
        self.assertEqual(a.from_token(token(self.clock)["token"]), "DENY_TRUST_UNAVAILABLE")

    def test_key_service_outage_fails_closed(self):
        a = _authn(self.clock, key_ok=False)
        self.assertEqual(a.from_token(token(self.clock)["token"]), "DENY_TRUST_UNAVAILABLE")

    def test_malformed_tokens(self):
        for bad in (None, "", "abc", "a.b.c", "x" * 5000, "!!!.???", 12):
            self.assertIn(self.a.from_token(bad), ("DENY_UNAUTHENTICATED", "DENY_BAD_SIGNATURE"))

    def test_tokens_cannot_claim_mesh_actor_types(self):
        for typ in ("node", "workload", "root"):
            self.assertEqual(self.a.from_token(token(self.clock, typ=typ)["token"]), "DENY_UNAUTHENTICATED")

    def test_spiffe_principals(self):
        p = self.a.from_spiffe("spiffe://estate.local/node/n1")
        self.assertEqual((p.actor_type, p.tenants), ("node", frozenset({"alpha"})))
        w = self.a.from_spiffe("spiffe://estate.local/ns/beta/sa/app")
        self.assertEqual((w.actor_type, w.tenant, w.roles), ("workload", "beta", frozenset()))
        self.assertEqual(self.a.from_spiffe("spiffe://evil.example/node/n1"), "DENY_AMBIGUOUS_IDENTITY")
        self.assertEqual(self.a.from_spiffe("spiffe://estate.local/node/../n1"), "DENY_AMBIGUOUS_IDENTITY")


class AuthorizationTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.z = _authz(self.clock)
        self.op = authz.Principal("op", "operator", None, frozenset({"mesh-operator"}), "signed_token", frozenset({"alpha"}))
        self.ctl = authz.Principal("runtime:ns/alpha/sa/ctl", "controller", "alpha", frozenset({"mesh-controller"}), "mtls_spiffe")
        self.node = authz.Principal("runtime:node/n1", "node", None, frozenset({"mesh-node"}), "mtls_spiffe", frozenset({"alpha"}))

    def test_positive(self):
        self.assertTrue(self.z.authorize(self.ctl, "route.migrate", "alpha"))
        self.assertTrue(self.z.authorize(self.node, "identity", "alpha"))
        self.assertTrue(self.z.authorize(self.op, "control.freeze"))

    def test_deny_by_default(self):
        self.assertEqual(self.z.authorize(self.op, "drop_all_tables").code, "DENY_UNKNOWN_OPERATION")
        self.assertEqual(self.z.authorize(None, "status").code, "DENY_UNAUTHENTICATED")
        self.assertEqual(self.z.authorize("garbage", "status").code, "DENY_UNAUTHENTICATED")
        nobody = authz.Principal("w", "workload", "alpha", frozenset(), "mtls_spiffe")
        for op in authz.BOUNDARY_MATRIX:
            self.assertFalse(self.z.authorize(nobody, op, "alpha"), op)

    def test_confused_deputy_and_privilege_escalation(self):
        self.assertEqual(self.z.authorize(self.node, "route.migrate", "alpha").code, "DENY_ACTOR_TYPE")
        self.assertEqual(self.z.authorize(self.ctl, "config.activate").code, "DENY_MECHANISM")
        self.assertEqual(self.z.authorize(self.op, "config.activate").code, "DENY_NO_CAPABILITY")
        self.assertEqual(self.z.authorize(self.op, "audit.export").code, "DENY_ACTOR_TYPE")
        tok_node = authz.Principal("x", "node", None, frozenset({"mesh-node"}), "signed_token", frozenset({"alpha"}))
        self.assertEqual(self.z.authorize(tok_node, "identity", "alpha").code, "DENY_MECHANISM")

    def test_unknown_role_denies_even_if_other_role_grants(self):
        p = authz.Principal("op", "operator", None, frozenset({"mesh-operator", "god"}), "signed_token")
        self.assertEqual(self.z.authorize(p, "control.freeze").code, "DENY_UNKNOWN_ROLE")

    def test_cross_tenant(self):
        self.assertEqual(self.z.authorize(self.ctl, "route.migrate", "beta").code, "DENY_TENANT_SCOPE")
        self.assertEqual(self.z.authorize(self.ctl, "route.migrate", None).code, "DENY_TENANT_SCOPE")
        self.assertEqual(self.z.authorize(self.node, "bypass", "beta").code, "DENY_TENANT_SCOPE")

    def test_stale_policy(self):
        self.clock.advance(86_401)
        self.assertEqual(self.z.authorize(self.op, "control.freeze").code, "DENY_STALE_POLICY")

    def test_break_glass_requires_arming_and_expires(self):
        bg = authz.Principal("op", "operator", None, frozenset({"break-glass"}), "signed_token")
        self.assertEqual(self.z.authorize(bg, "control.break_glass").code, "DENY_BREAK_GLASS_NOT_ARMED")
        self.z.arm_break_glass(60)
        self.assertTrue(self.z.authorize(bg, "control.break_glass"))
        self.clock.advance(61)
        self.assertFalse(self.z.authorize(bg, "control.break_glass"))
        with self.assertRaises(ValueError):
            self.z.arm_break_glass(7200)

    def test_policy_rejects_wildcards_and_unknown_caps(self):
        with self.assertRaises(ValueError):
            authz.CapabilityPolicy("p", {"admin": frozenset({"*"})}, issued_at=0)
        with self.assertRaises(ValueError):
            authz.CapabilityPolicy("p", {"admin": frozenset({"everything"})}, issued_at=0)

    def test_decision_codes_are_stable(self):
        codes = {self.z.authorize(p, op, t).code for p, op, t in [
            (None, "status", None), (self.op, "nope", None), (self.ctl, "route.migrate", "beta")]}
        self.assertTrue(codes <= set(authz.DENY_CODES) | {authz.ALLOW})


if __name__ == "__main__":
    unittest.main()
