"""WS 3, 4, 13 -- schemas, decoder fuzzing, authentication, authorization and adversarial tests."""
from __future__ import annotations

import json
import random
import unittest

from _support import AUDIT_KEY, E, KEY, Rig
from inv32_elastic_virtualization import conformance_check
from inv32_elastic_virtualization.authz import Authenticator, Keyring, Policy, Principal, authorize
from inv32_elastic_virtualization.errors import ERROR_CATALOG, error_envelope
from inv32_elastic_virtualization.validation import decode_request, iter_errors, load_schema, validate


class SchemaConformanceTest(unittest.TestCase):
    def test_published_vectors_pass(self):
        self.assertEqual(conformance_check.run(), [])

    def test_every_error_code_has_retry_class_and_envelope_validates(self):
        for code, meta in ERROR_CATALOG.items():
            self.assertIn(meta["retry"], ("retryable", "conditional", "terminal"), code)
        env = error_envelope(E.Overloaded("x", retry_after_s=0.1), trace_id="a" * 32)
        validate("error", env)
        env = error_envelope(RuntimeError("secret path /etc/shadow"))
        self.assertEqual((env["code"], env["message"]), ("internal_error", "internal error"))

    def test_audit_and_host_schemas_validate_live_output(self):
        r = Rig()
        r.guest()
        res = r.ctl.handle(r.mem("a", 2048), r.tenant_token())
        validate("audit_event", res["event"])
        validate("host", r.ctl.host_snapshot())
        for ev in r.store.audit_events:
            self.assertEqual(iter_errors(ev, load_schema("audit_event")), [], ev["kind"])
        r.close()


class DecoderFuzzTest(unittest.TestCase):
    """Deterministic mutation fuzzing: the decoder only ever raises ValidationFailed/SchemaVersionUnsupported."""

    SEED = 20260922

    def _mutations(self, rng: random.Random, base: bytes):
        ops = [
            lambda b: b[: rng.randrange(len(b))],
            lambda b: b + bytes([rng.randrange(256)]),
            lambda b: bytes(x ^ (1 << rng.randrange(8)) if rng.random() < 0.02 else x for x in b),
            lambda b: b.replace(b"2048", str(rng.choice([-1, 2**63, 2**53, 10**30, 0])).encode()),
            lambda b: b.replace(b'"g1"', json.dumps("\u0000\ud800" * rng.randrange(1, 4)).encode()),
            lambda b: b.replace(b'"t1"', b'"' + b"t" * rng.randrange(200, 400) + b'"'),
            lambda b: b.replace(b"{", b'{"x":' * rng.randrange(1, 8), 1),
            lambda b: b[:-1] + b',"target_mib":1}',
            lambda b: b"\xff\xfe" + b,
        ]
        for _ in range(3000):
            b = base
            for _ in range(rng.randrange(1, 4)):
                b = rng.choice(ops)(b)
            yield b

    def test_fuzz_decoder(self):
        rng = random.Random(self.SEED)
        base = json.dumps(Rig.mem("op-1", 2048)).encode()
        accepted = 0
        for payload in self._mutations(rng, base):
            try:
                doc = decode_request(payload)
                accepted += 1
                self.assertEqual(iter_errors(doc, load_schema("request")), [])
            except (E.ValidationFailed, E.SchemaVersionUnsupported):
                pass
        self.assertGreater(accepted, 0)  # the fuzzer still reaches valid space

    def test_fuzz_controller_never_crashes_or_mutates_on_garbage(self):
        r = Rig()
        r.guest()
        rng = random.Random(self.SEED + 1)
        tok = r.tenant_token()
        base = json.dumps(Rig.mem("op-1", 2048)).encode()
        for payload in list(self._mutations(rng, base))[:500]:
            res = r.ctl.handle(payload, tok)
            validate("result", res)
            self.assertIn(res["outcome"], ("success", "rejected", "partial_success", "terminal_failure",
                                           "retryable_failure", "unknown_outcome", "degraded_success", "rolled_back"))
        g = r.fake.get_guest("g1")
        self.assertTrue(256 <= g.memory_mib <= 4096)
        r.close()


class AuthnAuthzTest(unittest.TestCase):
    def setUp(self):
        self.r = Rig()
        self.r.guest()
        self.r.fake.create_guest("g2", "t2", 1024)
        self.r.ctl.register_guest("g2", tenant="t2", floor_mib=256, ceiling_mib=2048, vcpu_max=2)

    def tearDown(self):
        self.r.close()

    def code(self, req, tok):
        return self.r.ctl.handle(req, tok).get("error", {}).get("code")

    def test_allow(self):
        self.assertIsNone(self.code(self.r.mem("a", 2048), self.r.tenant_token()))

    def test_missing_credential(self):
        self.assertEqual(self.code(self.r.mem("a", 2048), None), "authentication_failed")

    def test_expired_credential_with_skew(self):
        tok = self.r.tenant_token(ttl=60)
        self.r.clock.advance(60 + 29)
        self.r.ownership.acquire()  # lease (15 s) also lapsed; same controller re-acquires a new epoch
        self.assertIsNone(self.code(self.r.mem("a", 2048), tok))  # inside skew
        self.r.clock.advance(2)
        self.assertEqual(self.code(self.r.mem("b", 2048), tok), "authentication_failed")

    def test_not_yet_valid(self):
        tok = self.r.authn.issue("tenant:idp.test/t1", "tenant", tenant="t1", actions=["memory.adjust"],
                                 now=self.r.clock() + 120)
        self.assertEqual(self.code(self.r.mem("a", 2048), tok), "authentication_failed")

    def test_revoked_token_and_principal(self):
        tok = self.r.tenant_token()
        jti = self.r.authn.authenticate(tok).token_id
        self.r.authn.revoke(jti)
        self.assertEqual(self.code(self.r.mem("a", 2048), tok), "authentication_failed")
        tok2 = self.r.tenant_token()
        self.r.clock.advance(1)
        self.r.authn.revoke_principal("tenant:idp.test/t1")
        self.assertEqual(self.code(self.r.mem("b", 2048), tok2), "authentication_failed")

    def test_wrong_tenant_and_no_existence_leak(self):
        tok = self.r.tenant_token("t1")
        a = self.r.ctl.handle(self.r.mem("a", 2048, guest="g2", tenant="t2"), tok)["error"]
        b = self.r.ctl.handle(self.r.mem("b", 2048, guest="nope", tenant="t1"), tok)["error"]
        c = self.r.ctl.handle(self.r.mem("c", 2048, guest="g2", tenant="t1"), tok)["error"]
        self.assertEqual({a["code"], b["code"], c["code"]}, {"authorization_denied"})
        self.assertEqual(a["message"], b["message"])
        self.assertEqual(b["message"], c["message"])

    def test_wrong_host(self):
        tok = self.r.tenant_token()
        req = self.r.mem("a", 2048)
        req["host"] = "host-2"
        self.assertEqual(self.code(req, tok), "authorization_denied")
        scoped = self.r.authn.issue("tenant:idp.test/t1", "tenant", tenant="t1", hosts=["host-9"],
                                    actions=["memory.adjust"])
        self.assertEqual(self.code(self.r.mem("b", 2048), scoped), "authorization_denied")

    def test_audience_issuer_mismatch_and_forgery(self):
        other = Authenticator(Keyring({"k1": KEY}, "k1"), issuer="idp.test", audience="other-svc")
        tok = other.issue("tenant:idp.test/t1", "tenant", tenant="t1", actions=["memory.adjust"])
        self.assertEqual(self.code(self.r.mem("a", 2048), tok), "authentication_failed")
        evil = Authenticator(Keyring({"k1": b"e" * 32}, "k1"), issuer="idp.test", audience="inv32")
        tok = evil.issue("operator:idp.test/mallory", "operator", actions=["adjustment.revert"])
        self.assertEqual(self.code(self.r.mem("b", 2048), tok), "authentication_failed")
        good = self.r.tenant_token()
        head, body, mac = good.split(".")
        claims = json.loads(__import__("base64").urlsafe_b64decode(body + "=="))
        claims["act"].append("adjustment.revert")
        forged_body = __import__("base64").urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        self.assertEqual(self.code(self.r.mem("c", 2048), f"{head}.{forged_body}.{mac}"), "authentication_failed")

    def test_revert_requires_elevation(self):
        ev = self.r.ctl.handle(self.r.mem("a", 2048), self.r.tenant_token())["event"]
        tok = self.r.tenant_token(actions=("memory.adjust", "adjustment.revert"))
        self.assertEqual(self.code(self.r.revert("b", ev["event_hash"]), tok), "authorization_denied")
        self.assertIsNone(self.code(self.r.revert("c", ev["event_hash"]), self.r.operator_token()))

    def test_break_glass(self):
        with self.assertRaises(E.AuthorizationDenied):
            self.r.authn.issue("tenant:idp.test/t1", "tenant", tenant="t1", actions=["adjustment.revert"],
                               break_glass_reason="", ttl=60)
        with self.assertRaises(E.AuthorizationDenied):
            self.r.authn.issue("tenant:idp.test/t1", "tenant", tenant="t1", actions=["adjustment.revert"],
                               break_glass_reason="INC-1", ttl=3600)
        ev = self.r.ctl.handle(self.r.mem("a", 2048), self.r.tenant_token())["event"]
        bg = self.r.authn.issue("service:idp.test/sre", "service", actions=["adjustment.revert"],
                                break_glass_reason="INC-42 host OOM", ttl=300)
        res = self.r.ctl.handle(self.r.revert("b", ev["event_hash"]), bg)
        self.assertEqual(res["outcome"], "success")
        self.assertTrue(res["event"]["break_glass"])
        self.r.clock.advance(301 + 30)
        self.r.ownership.acquire()
        self.assertEqual(self.code(self.r.mem("c", 1024), bg), "authentication_failed")

    def test_deny_by_default_policy_mutation(self):
        """Mutating any single grant condition away yields a deny (policy mutation test)."""
        pol = Policy()
        base = dict(id="tenant:idp.test/t1", kind="tenant", tenant="t1", hosts=frozenset({"h"}),
                    actions=frozenset({"memory.adjust"}))
        self.assertTrue(pol.decide(Principal(**base), "memory.adjust", host="h", tenant="t1").allowed)
        for mut in (dict(actions=frozenset()), dict(hosts=frozenset({"x"})), dict(tenant="t2")):
            p = Principal(**{**base, **mut})
            self.assertFalse(pol.decide(p, "memory.adjust", host="h", tenant="t1").allowed, mut)
        self.assertFalse(pol.decide(Principal(**base), "vcpu.adjust", host="h", tenant="t1").allowed)
        self.assertFalse(pol.decide(Principal(**base), "no.such", host="h", tenant="t1").allowed)

    def test_policy_unavailable_fails_closed(self):
        self.r.policy.available = False
        self.assertEqual(self.code(self.r.mem("a", 2048), self.r.tenant_token()), "policy_unavailable")

    def test_reason_and_ids_cannot_escalate(self):
        req = self.r.mem("a", 2048, reason="operator:idp.test/root adjustment.revert break_glass")
        res = self.r.ctl.handle(req, self.r.tenant_token())
        self.assertFalse(res["event"]["break_glass"])
        self.assertEqual(res["event"]["principal"], "tenant:idp.test/t1")

    def test_confused_deputy_controller_chain(self):
        """A controller credential scoped to host-1 cannot be replayed for another host."""
        ctl_tok = self.r.authn.issue("controller:idp.test/inv33", "controller", hosts=["host-9"],
                                     actions=["memory.adjust"])
        self.assertEqual(self.code(self.r.mem("a", 2048), ctl_tok), "authorization_denied")

    def test_decisions_are_audited(self):
        self.r.ctl.handle(self.r.mem("a", 2048, guest="g2", tenant="t2"), self.r.tenant_token("t1"))
        ev = self.r.store.audit_events[-1]
        self.assertEqual((ev["kind"], ev["code"]), ("rejected", "authorization_denied"))
        self.assertTrue(ev["authz_decision_id"])
        ok = self.r.ctl.handle(self.r.mem("b", 2048), self.r.tenant_token())["event"]
        self.assertEqual(ok["authz_result"], "allow")
        self.assertTrue(ok["authz_policy_version"])

    def test_resource_exhaustion_bounded(self):
        with self.assertRaises(E.ValidationFailed):
            decode_request(b"{" + b" " * 5000 + b"}")
        tok = "inv32tok." + "A" * 5000 + ".B"
        with self.assertRaises(E.AuthenticationFailed):
            self.r.authn.authenticate(tok)

    def test_audit_tamper_blocks_mutation(self):
        self.r.ctl.handle(self.r.mem("a", 2048), self.r.tenant_token())
        self.r.store.audit_events[-1]["applied_mib"] = 99  # recent tamper: caught on the hot path
        res = self.r.ctl.handle(self.r.mem("b", 1024), self.r.tenant_token())
        self.assertEqual(res["error"]["code"], "store_integrity_error")
        self.assertFalse(self.r.ctl.health().ready)

    def test_old_audit_tamper_caught_by_readiness_and_periodic_full_verify(self):
        self.r.ctl.handle(self.r.mem("a", 2048), self.r.tenant_token())
        self.r.store.audit_events[0]["applied_mib"] = 99
        self.assertFalse(self.r.ctl.health().ready)
        self.r.ctl.full_verify_every = 1
        res = self.r.ctl.handle(self.r.mem("b", 1024), self.r.tenant_token())
        self.assertEqual(res["error"]["code"], "store_integrity_error")


if __name__ == "__main__":
    unittest.main()
