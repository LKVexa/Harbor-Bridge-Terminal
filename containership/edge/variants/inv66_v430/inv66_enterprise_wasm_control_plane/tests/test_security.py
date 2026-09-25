"""Adversarial, authentication and fuzz suite (MC-015/029/031/032/037)."""
from __future__ import annotations

import base64
import copy
import json
import random
import unittest

from support import Harness, component, config, request, token, IDP_HS_KEY
from inv66_enterprise_wasm_control_plane.errors import ControlPlaneError
from inv66_enterprise_wasm_control_plane.identity import b64e, mint_token
from inv66_enterprise_wasm_control_plane.rbac import Binding, RbacModel


class AuthnTest(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.a = self.h.svc.authn

    def tearDown(self):
        self.h.close()

    def code(self, tok, **kw):
        try:
            self.a.authenticate(tok, **kw)
            return "OK"
        except ControlPlaneError as exc:
            return exc.error.code

    def test_valid_hs_and_eddsa(self):
        self.assertEqual(self.code(self.h.tok()), "OK")
        self.assertEqual(self.code(token("user:ops", self.h.clock, iss="https://ed.acme")), "OK")

    def test_rejections(self):
        c = self.h.clock
        now = int(c())
        cases = {
            "wrong audience": token("user:ops", c, aud="other"),
            "expired": token("user:ops", c, iat=now - 1000, nbf=now - 1000, exp=now - 500),
            "not yet valid": token("user:ops", c, nbf=now + 1000, exp=now + 1200, iat=now),
            "too long lived": token("user:ops", c, exp=now + 86400),
            "untrusted issuer": mint_token("HS256", "k1", IDP_HS_KEY, {"iss": "https://evil", "sub": "user:ops",
                                           "aud": "inv66-control-plane", "iat": now, "exp": now + 60, "jti": "z"}),
            "bad subject": token("ops", c),
            "missing jti": token("user:ops", c, jti=""),
            "alg none": b64e(json.dumps({"alg": "none", "kid": "k1"}).encode()) + "." + b64e(json.dumps({"iss": "https://idp.acme"}).encode()) + ".",
            "alg confusion": mint_token("HS256", "e1", b"x" * 32, {"iss": "https://ed.acme", "sub": "user:ops",
                                        "aud": "inv66-control-plane", "iat": now, "exp": now + 60, "jti": "q"}),
            "oversize": "a" * 9000,
        }
        for name, tok in cases.items():
            self.assertEqual(self.code(tok), "AUTHN_INVALID", name)

    def test_replay_and_cert_binding(self):
        t = self.h.tok()
        self.assertEqual(self.code(t), "OK")
        self.assertEqual(self.code(t), "AUTHN_REPLAY")
        bound = token("service:ci", self.h.clock, cnf={"x5t#S256": "ab" * 32})
        self.assertEqual(self.code(bound, peer_thumbprint="cd" * 32), "AUTHN_INVALID")
        bound2 = token("service:ci", self.h.clock, cnf={"x5t#S256": "ab" * 32})
        self.assertEqual(self.code(bound2, peer_thumbprint="ab" * 32), "OK")


class RbacTest(unittest.TestCase):
    def test_hierarchy_deny_precedence_expiry(self):
        m = RbacModel([
            Binding("group:eng", "deployer", "org:a/tenant:t"),
            Binding("user:bob", "deployer", "org:a/tenant:t/lattice:prod", "deny"),
            Binding("user:tmp", "deployer", "org:a", expires_at=100),
        ], {"eng": ["user:bob", "user:amy"]})
        self.assertTrue(m.check("user:amy", "admit", "org:a/tenant:t/lattice:prod", 0).allowed)
        r = m.check("user:bob", "admit", "org:a/tenant:t/lattice:prod", 0)
        self.assertTrue(r.explicit_deny and not r.allowed)
        self.assertFalse(m.check("user:amy", "admit", "org:a/tenant:other", 0).allowed)
        self.assertFalse(m.check("user:amy", "admit", "org:a/tenant:tx", 0).allowed)   # prefix confusion
        self.assertTrue(m.check("user:tmp", "admit", "org:a/tenant:z", 99).allowed)
        self.assertFalse(m.check("user:tmp", "admit", "org:a/tenant:z", 100).allowed)
        self.assertFalse(m.check("user:amy", "config.activate", "org:a/tenant:t", 0).allowed)


class AdversarialTest(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.close()

    def test_signature_replay_onto_other_digest(self):
        good = component("api")
        other = dict(good, image=good["image"].replace("ab" * 32, "ef" * 32))
        r = self.h.svc.admit(self.h.tok(), request([other]))
        self.assertEqual([e["code"] for e in r["errors"]], ["SIGNATURE_INVALID"])

    def test_registry_confusion(self):
        for img in ("registry.estate.local.evil.example/a@sha256:" + "ab" * 32,
                    "REGISTRY.estate.local@evil/a@sha256:" + "ab" * 32):
            c = component("a", img=img) if "@evil" not in img else dict(component("a"), image=img)
            try:
                r = self.h.svc.admit(self.h.tok(), request([c]))
                self.assertFalse(r["admitted"])
            except ControlPlaneError as exc:
                self.assertEqual(exc.error.code, "SCHEMA_INVALID")

    def test_tenant_isolation(self):
        with self.assertRaises(ControlPlaneError) as cm:
            self.h.svc.admit(self.h.tok("user:ops"), request(tenant="other"))
        self.assertEqual(cm.exception.error.code, "AUTHZ_DENIED")
        self.h.svc.admit(self.h.tok(), request())
        with self.assertRaises(ControlPlaneError):
            self.h.svc.inventory(self.h.tok("user:ops"), tenant="other")

    def test_parser_bombs_and_non_json(self):
        deep = {}
        cur = deep
        for _ in range(5000):
            cur["x"] = {}
            cur = cur["x"]
        for bad in (deep, float("nan"), {"protocol": "PK_ECP_ADMIT/9"}, [], "x" * 10, {"manifest": {"components": [1] * 20000}}):
            with self.assertRaises(ControlPlaneError) as cm:
                self.h.svc.admit(self.h.tok(), bad if not isinstance(bad, float) else {"a": bad})
            self.assertIn(cm.exception.error.code, ("SCHEMA_INVALID", "PROTOCOL_UNSUPPORTED", "MANIFEST_TOO_LARGE"))

    def test_mutation_fuzz_never_admits_invalid_or_crashes(self):
        rng = random.Random(66)
        base = request()
        valid_sig = base["manifest"]["components"][0]["signature"]
        junk = [None, True, 0, -1, 2**70, "", " ", "\x00", "a" * 3000, [], {}, "../../x", "‮", 1.5]
        admitted = 0
        for i in range(1500):
            req = copy.deepcopy(base)
            req["request_id"] = f"f{i}"
            for _ in range(rng.randint(1, 3)):
                target = rng.choice(["top", "manifest", "comp"])
                try:
                    obj = req if target == "top" else req["manifest"] if target == "manifest" else req["manifest"]["components"][0]
                except (KeyError, TypeError, IndexError):
                    continue
                if not isinstance(obj, dict) or not obj:
                    continue
                k = rng.choice(list(obj.keys()) + ["extra"])
                if rng.random() < 0.2:
                    obj.pop(k, None)
                else:
                    obj[k] = rng.choice(junk)
            try:
                r = self.h.svc.admit(self.h.tok(), req)
            except ControlPlaneError:
                continue
            if r["admitted"]:
                c = req["manifest"]["components"][0]
                self.assertEqual(c["signature"], valid_sig)
                self.assertTrue(c["image"].startswith("registry.estate.local/"))
                admitted += 1
        self.assertLess(admitted, 1500)


if __name__ == "__main__":
    unittest.main()
