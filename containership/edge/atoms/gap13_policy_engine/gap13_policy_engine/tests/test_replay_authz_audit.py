"""G13-MC-008 anti-replay, G13-MC-009 authorization, G13-MC-010 audit log, G13-MC-005/006 attributes."""
import json
import os
import pathlib
import unittest

import testkit as k
from gap13_policy_engine import errors as E
from gap13_policy_engine.attributes import AttributeSchema, build_request, StaticContextProvider
from gap13_policy_engine.audit import AuditLog, read_log, verify_chain
from gap13_policy_engine.authz import Authorizer, Capability as C, TokenAuthenticator, issue_token, Principal
from gap13_policy_engine.replay import AntiReplayState

g = k.g


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.path = pathlib.Path(k.tmpdir()) / "ar.json"
        self.st = AntiReplayState(self.path)

    def test_floor_replay_collision_rollback(self):
        b1, b2 = k.verified(1).bundle, k.verified(2).bundle
        self.assertEqual(self.st.check(b2), "new")
        self.st.commit(b2)
        self.assertEqual(self.st.check(b2), "benign-replay")
        with self.assertRaises(E.ReplayRejected):
            self.st.check(b1)                              # downgrade
        # same generation, different content
        other = k.verified(2, [{"name": "x", "effect": "allow", "scope": "estate", "match": {}}]).bundle
        with self.assertRaises(E.ReplayRejected):
            self.st.check(other)
        # generation gap is allowed (monotonic, not contiguous)
        self.assertEqual(self.st.check(k.verified(9).bundle), "new")

    def test_authorized_rollback_only_to_seen_digest(self):
        b1, b2 = k.verified(1).bundle, k.verified(2).bundle
        self.st.commit(b1)
        self.st.commit(b2)
        self.assertEqual(self.st.check(b1, rollback_authorized=True), "authorized-rollback")

    def test_durable_across_restart_and_corruption_not_reset(self):
        self.st.commit(k.verified(5).bundle)
        again = AntiReplayState(self.path)
        with self.assertRaises(E.ReplayRejected):
            again.check(k.verified(4).bundle)
        self.path.write_text(self.path.read_text().replace('"generation":5', '"generation":0'))
        with self.assertRaises(E.AntiReplayStateUnavailable):
            AntiReplayState(self.path)

    def test_partial_write_keeps_old_state(self):
        self.st.commit(k.verified(3).bundle)
        with self.assertRaises(OSError):
            self.st.commit(k.verified(4).bundle, fault="partial")
        self.assertEqual(AntiReplayState(self.path).status()["gap07-publisher|estate|prod"]["generation"], 3)


class AuthTests(unittest.TestCase):
    KEY = b"k" * 32

    def setUp(self):
        self.clock = k.Clock()
        self.auth = TokenAuthenticator({"i1": self.KEY}, issuer="idp", audience="gap13", clock=self.clock.wall)

    def tok(self, **over):
        c = {"kid": "i1", "iss": "idp", "aud": "gap13", "sub": "alice", "iat": k.T0, "exp": k.T0 + 600,
             "jti": os.urandom(8).hex(), "roles": ["policy_admin"], "env": ["prod"], "mfa": True,
             "auth_time": k.T0}
        c.update(over)
        return issue_token(self.KEY, c)

    def test_valid_and_negative_tokens(self):
        self.assertEqual(self.auth.authenticate(self.tok()).subject, "alice")
        bad = {"wrong-aud": self.tok(aud="other"), "wrong-iss": self.tok(iss="x"),
               "expired": self.tok(exp=k.T0 - 1), "nbf": self.tok(nbf=k.T0 + 100),
               "overlong": self.tok(exp=k.T0 + 99999), "unknown-kid": self.tok(kid="zz"),
               "forged": self.tok()[:-3] + "AAA", "no-jti": self.tok(jti=""), "garbage": "a.b.c"}
        for name, t in bad.items():
            with self.subTest(name), self.assertRaises(E.Unauthenticated):
                self.auth.authenticate(t)
        wrong_key = issue_token(b"z" * 32, {"kid": "i1", "iss": "idp", "aud": "gap13", "iat": k.T0,
                                            "exp": k.T0 + 60, "jti": "q"})
        with self.assertRaises(E.Unauthenticated):
            self.auth.authenticate(wrong_key)

    def test_replay_and_revocation(self):
        t = self.tok(jti="once")
        self.auth.authenticate(t)
        with self.assertRaises(E.Unauthenticated):
            self.auth.authenticate(t)
        self.auth.revoked.add("r1")
        with self.assertRaises(E.Unauthenticated):
            self.auth.authenticate(self.tok(jti="r1"))

    def test_dependency_outage_denies(self):
        self.auth.available = False
        with self.assertRaises(E.DependencyUnavailable):
            self.auth.authenticate(self.tok())

    def test_capabilities_scope_and_privilege_confusion(self):
        az = Authorizer("prod", clock=self.clock.wall)
        admin = k.principal("alice", ("policy_admin",), clock=self.clock)
        az.require(admin, C.BUNDLE_ACTIVATE)
        for p, cap in [(k.principal("v", ("viewer",)), C.BUNDLE_ACTIVATE),
                       (k.principal("s", ("policy_admin",), kind="service"), C.BUNDLE_ACTIVATE),  # service escalation
                       (k.principal("o", ("operator",)), C.CONTROL_DISABLE),
                       (k.principal("t", ("policy_admin",)), C.TRUST_ADMIN),
                       (None, C.STATUS)]:
            with self.subTest(p and p.subject), self.assertRaises(E.Unauthorized):
                az.require(p, cap)
        wrong_env = Principal("a", "human", frozenset({"policy_admin"}), frozenset({"dev"}), mfa=True, auth_time=k.T0)
        with self.assertRaises(E.Unauthorized):
            az.require(wrong_env, C.BUNDLE_STAGE)
        tenant_scoped = Principal("a", "human", frozenset({"viewer"}), frozenset({"prod"}), tenants=frozenset({"t1"}))
        with self.assertRaises(E.Unauthorized):
            az.require(tenant_scoped, C.STATUS, tenant="t2")

    def test_step_up_required(self):
        az = Authorizer("prod", clock=self.clock.wall)
        stale_auth = Principal("a", "human", frozenset({"policy_admin"}), frozenset({"prod"}), mfa=True,
                               auth_time=k.T0 - 3600)
        with self.assertRaises(E.Unauthorized):
            az.require(stale_auth, C.BUNDLE_ACTIVATE)
        no_mfa = Principal("a", "human", frozenset({"policy_admin"}), frozenset({"prod"}), auth_time=k.T0)
        with self.assertRaises(E.Unauthorized):
            az.require(no_mfa, C.BUNDLE_ACTIVATE)

    def test_rate_limit(self):
        from gap13_policy_engine.authz import RateLimiter
        az = Authorizer("prod", clock=self.clock.wall, limiter=RateLimiter(3, clock=self.clock.wall))
        p = k.principal("alice", ("policy_admin",), clock=self.clock)
        for _ in range(3):
            az.require(p, C.BUNDLE_STAGE)
        with self.assertRaises(E.Unauthorized):
            az.require(p, C.BUNDLE_STAGE)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.path = pathlib.Path(k.tmpdir()) / "audit.jsonl"
        self.log = AuditLog(self.path)
        for i in range(5):
            self.log.emit("bundle.activate", actor="a", target=str(i), token="SECRET-TOKEN")

    def recs(self):
        return list(read_log(self.path))

    def test_chain_valid_and_redacted(self):
        ok, _ = verify_chain(self.recs(), expected_head=self.log.head, expected_count=5)
        self.assertTrue(ok)
        self.assertNotIn("SECRET-TOKEN", self.path.read_text())

    def test_tamper_detection(self):
        r = self.recs()
        mods = {
            "modified": r[:2] + [{**r[2], "target": "evil"}] + r[3:],
            "deleted": r[:2] + r[3:],
            "reordered": [r[1], r[0]] + r[2:],
            "duplicate-seq": r[:3] + [r[2]] + r[3:],
        }
        for name, recs in mods.items():
            with self.subTest(name):
                self.assertFalse(verify_chain(recs)[0])
        self.assertFalse(verify_chain(r[:4], expected_head=self.log.head)[0])      # truncated
        self.assertFalse(verify_chain(r[:4], expected_count=5)[0])

    def test_reopen_refuses_tampered_file(self):
        txt = self.path.read_text().replace('"target":"3"', '"target":"X"')
        self.path.write_text(txt)
        with self.assertRaises(E.AuditSinkUnavailable):
            AuditLog(self.path)

    def test_sink_outage_buffer_and_recovery(self):
        self.log.sink_down = True
        self.log.buffer_limit = 2
        self.log.emit("a")
        self.log.emit("b")
        with self.assertRaises(E.AuditSinkUnavailable):
            self.log.emit("c")
        with self.assertRaises(E.AuditSinkUnavailable):
            self.log.require_capacity()
        self.assertEqual(self.log.recover(), 2)
        self.assertTrue(verify_chain(self.recs(), expected_head=self.log.head)[0])

    def test_tenant_scoped_retrieval_and_export(self):
        self.log.emit("x", tenant="t1")
        self.assertEqual(len(self.log.records(tenant="t1")), 1)
        ex = self.log.export()
        self.assertEqual(ex["manifest"]["count"], 6)


class AttributeTests(unittest.TestCase):
    def setUp(self):
        self.schema = AttributeSchema()
        self.lim = g.Limits()

    def test_protected_cannot_be_self_asserted(self):
        for name in ("tenant", "identity.subject", "attestation.level", "classification", "identity.anything"):
            with self.subTest(name), self.assertRaises(E.AttributeRejected):
                build_request({name: "x"}, {}, self.schema, self.lim)

    def test_types_normalisation_unknown(self):
        req = build_request({"action": "READ", "labels": ["a"]}, {"tenant": "t1"}, self.schema, self.lim)
        self.assertEqual(req, {"action": "read", "labels": ["a"], "tenant": "t1"})
        for bad in ({"action": 1}, {"operation_count": True}, {"labels": "a"}, {"nope": 1},
                    {"action": "re​ad"}, {"Action": "x"}, {"action": "x" * 100}):
            with self.subTest(bad), self.assertRaises(E.AttributeRejected):
                build_request(bad, {}, self.schema, self.lim)
        with self.assertRaises(E.AttributeRejected):
            build_request({}, {"classification": "top-secret"}, self.schema, self.lim)
        ignore = AttributeSchema(unknown="ignore")
        self.assertEqual(build_request({"nope": 1}, {}, ignore, self.lim), {})

    def test_size_limits(self):
        with self.assertRaises(E.RequestTooLarge):
            build_request({f"a{i}": 1 for i in range(100)}, {}, self.schema, self.lim)

    def test_provider_outage_and_unknown_subject(self):
        p = StaticContextProvider({"a": {"tenant": "t"}}, available=False)
        with self.assertRaises(E.ContextUnavailable):
            p.context("a")
        with self.assertRaises(E.ContextUnavailable):
            StaticContextProvider({}).context("zz")
        with self.assertRaises(E.AttributeRejected):
            build_request({}, {"action": "read"}, self.schema, self.lim)   # provider may only give protected


if __name__ == "__main__":
    unittest.main()
