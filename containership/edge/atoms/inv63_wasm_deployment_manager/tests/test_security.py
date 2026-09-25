"""Threat-model-derived security tests (INV-63-C041..C050, C087)."""
import json
import os
import unittest

from _support import covers, desired, make_env, mod, req

security = mod("security")
errors = mod("errors")
E = errors.ErrorCode


class AuthNTest(unittest.TestCase):
    def setUp(self):
        self.env = make_env()

    @covers(23, 44, 87, 50)
    def test_spoofed_expired_and_foreign_tokens_rejected(self):
        p = security.Principal("mallory", "acme", frozenset({"tenant-deployer"}))
        forged = security.TokenAuthority({"k1": b"x" * 32}, clock=self.env.clock).issue(p)
        self.assertEqual(req(self.env, "set_desired", desired(self.env), token=forged)["error"]["code"], "INV63-E-UNAUTHENTICATED")
        tok = self.env.tokens.issue(p, ttl_s=10)
        self.env.clock.advance(100)
        self.assertEqual(req(self.env, "set_desired", desired(self.env), token=tok)["error"]["code"], "INV63-E-UNAUTHENTICATED")
        body, sig = self.env.tokens.issue(p).split(".")
        claims = json.loads(security._unb64(body)); claims["ten"] = "*"
        tampered = security._b64(json.dumps(claims).encode()) + "." + sig
        self.assertEqual(req(self.env, "set_desired", desired(self.env), token=tampered)["error"]["code"], "INV63-E-UNAUTHENTICATED")
        for junk in ["", "a.b.c", "x" * 3000, "..", "e30.AAAA"]:
            self.assertIn(req(self.env, "explain", {"component": "api"}, token=junk)["error"]["code"],
                          ("INV63-E-UNAUTHENTICATED", "INV63-E-SCHEMA"))

    @covers(23, 50, 87)
    def test_token_replay_detected(self):
        tok = self.env.tokens.issue(security.Principal("alice", "acme", frozenset({"tenant-deployer"})))
        self.assertEqual(req(self.env, "set_desired", desired(self.env), token=tok)["outcome"], "SUCCESS")
        self.assertEqual(req(self.env, "set_desired", desired(self.env), token=tok)["error"]["code"], "INV63-E-REPLAY")

    @covers(47, 23)
    def test_key_rotation(self):
        p = security.Principal("alice", "acme", frozenset({"tenant-viewer"}))
        old = self.env.tokens.issue(p)
        self.env.tokens.rotate("k2", b"z" * 32)
        new = self.env.tokens.issue(p)
        self.env.tokens.verify(old)
        self.env.tokens.verify(new)
        self.env.tokens.retire("k1")
        with self.assertRaises(errors.DeploymentError):
            self.env.tokens.verify(self.env.tokens.issue(p).replace(".", ".x", 1) if False else old)


class AuthZTest(unittest.TestCase):
    def setUp(self):
        self.env = make_env()

    @covers(24, 42, 50, 87)
    def test_privilege_escalation_blocked(self):
        r = req(self.env, "set_desired", desired(self.env), roles=("tenant-viewer",))
        self.assertEqual(r["error"]["code"], "INV63-E-FORBIDDEN")
        r = req(self.env, "freeze", {"tenant": "acme", "component": "api"}, roles=("tenant-deployer",))
        self.assertEqual(r["error"]["code"], "INV63-E-FORBIDDEN")
        r = req(self.env, "set_desired", desired(self.env), roles=("sre-operator",), tenant="*")
        self.assertEqual(r["error"]["code"], "INV63-E-FORBIDDEN")   # separation of duties
        r = req(self.env, "set_desired", desired(self.env), roles=("no-such-role",))
        self.assertEqual(r["error"]["code"], "INV63-E-FORBIDDEN")

    @covers(42)
    def test_roles_are_minimal(self):
        for role, caps in security.ROLES.items():
            self.assertTrue(caps <= security.CAPABILITIES, role)
        self.assertNotIn("control:quarantine", security.ROLES["tenant-deployer"])
        self.assertNotIn("desired:write", security.ROLES["sre-operator"])
        self.assertEqual(security.ROLES["reconciler"], frozenset({"reconcile:run", "desired:read"}))

    @covers(46, 24, 87, 50)
    def test_cross_tenant_access_blocked(self):
        req(self.env, "set_desired", desired(self.env, tenant="acme"))
        r = req(self.env, "set_desired", desired(self.env, tenant="acme"), tenant="evil")
        self.assertEqual(r["error"]["code"], "INV63-E-TENANT-ISOLATION")
        r = req(self.env, "explain", {"tenant": "acme", "component": "api"}, tenant="evil", roles=("tenant-viewer",))
        self.assertEqual(r["error"]["code"], "INV63-E-TENANT-ISOLATION")
        with self.assertRaises(errors.DeploymentError):
            security.namespace("acme", "../other/api")
        with self.assertRaises(errors.DeploymentError):
            security.namespace("ACME", "api")

    @covers(46)
    def test_tenants_with_same_component_name_do_not_collide(self):
        req(self.env, "set_desired", desired(self.env, tenant="acme", count=1))
        req(self.env, "set_desired", desired(self.env, tenant="globex", count=2), tenant="globex")
        req(self.env, "reconcile", {"tenant": "acme", "component": "api"})
        req(self.env, "reconcile", {"tenant": "globex", "component": "api"}, tenant="globex")
        comps = sorted(c for c, _, _ in self.env.lattice.running)
        self.assertEqual(comps, ["acme/api", "globex/api", "globex/api"])


class ArtifactTest(unittest.TestCase):
    def setUp(self):
        self.env = make_env()

    @covers(45, 44, 87, 50)
    def test_unsigned_tampered_untrusted_unapproved_revoked(self):
        b = desired(self.env)
        b1 = {k: v for k, v in b.items() if k != "artifact"}; b1["schema"] = "PK_DEPLOY_DESIRED/1"
        self.assertEqual(req(self.env, "set_desired", b1)["error"]["code"], "INV63-E-ARTIFACT-UNTRUSTED")
        bad = dict(b, version="v9")
        self.assertEqual(req(self.env, "set_desired", bad)["error"]["code"], "INV63-E-ARTIFACT-UNTRUSTED")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        rogue = security.sign_artifact(Ed25519PrivateKey.generate(), "rel-1", "api", "v1", b"api-v1")
        self.assertEqual(req(self.env, "set_desired", dict(b, artifact=rogue))["error"]["code"], "INV63-E-ARTIFACT-UNTRUSTED")
        v = self.env.verifier
        v.approved_versions = {"api": {"v0"}}
        with self.assertRaises(errors.DeploymentError):
            v.verify("api", "v1", b["artifact"])
        v.approved_versions = None
        v.revoked_digests.add(b["artifact"]["digest"])
        with self.assertRaises(errors.DeploymentError):
            v.verify("api", "v1", b["artifact"])
        with self.assertRaises(errors.DeploymentError):
            security.ArtifactVerifier({"rel-1": self.env.priv.public_key()}).verify("api", "v1", b["artifact"], blob=b"other")

    @covers(48, 45)
    def test_verifier_unavailable_fails_closed(self):
        self.env.svc.verifier = None
        self.assertEqual(req(self.env, "set_desired", desired(self.env))["error"]["code"], "INV63-E-DEPENDENCY-UNAVAILABLE")


class SecretsAndCryptoTest(unittest.TestCase):
    @covers(39, 75)
    def test_redaction(self):
        rec = security.redact({"password": "hunter2", "note": "key -----BEGIN RSA PRIVATE KEY----- x",
                               "nested": {"api_key": "AKIAABCDEFGHIJKLMNOP"}, "ok": "fine"})
        self.assertEqual(rec["password"], security.REDACTED)
        self.assertNotIn("BEGIN RSA", rec["note"])
        self.assertEqual(rec["nested"]["api_key"], security.REDACTED)
        self.assertEqual(rec["ok"], "fine")

    @covers(39)
    def test_secret_refs(self):
        self.assertEqual(security.resolve_secret_ref("env:X", {"X": "v"}), b"v")
        for bad in ("plain", "http://x", 5):
            with self.assertRaises(errors.DeploymentError):
                security.resolve_secret_ref(bad, {})
        with self.assertRaises(errors.DeploymentError) as cm:
            security.resolve_secret_ref("env:MISSING", {})
        self.assertEqual(cm.exception.code, E.DEPENDENCY_UNAVAILABLE)

    @covers(47, 49)
    def test_encryption_at_rest_and_rotation(self):
        s = security.Sealer({"d1": os.urandom(32)})
        tok = s.seal(b"state")
        self.assertEqual(s.open(tok), b"state")
        s.rotate("d2", os.urandom(32))
        self.assertEqual(s.open(tok), b"state")
        new = s.reseal(tok)
        self.assertTrue(new.startswith("v1.d2."))
        with self.assertRaises(errors.DeploymentError):
            s.open(tok[:-2] + ("A" if tok[-2] != "A" else "B") + tok[-1])

    @covers(47, 57)
    def test_encrypted_journal_roundtrip(self):
        import tempfile
        store = mod("store")
        s = security.Sealer({"d1": os.urandom(32)})
        d = tempfile.mkdtemp()
        j = store.Journal(d, sealer=s); j.acquire()
        j.append("desired_set", {"ns": "t/c", "secretish": "tenant data"})
        self.assertNotIn(b"tenant data", (j.path).read_bytes())
        self.assertEqual(store.Journal(d, sealer=s).records[0].data["secretish"], "tenant data")
        with self.assertRaises(errors.DeploymentError):
            store.Journal(d, sealer=security.Sealer({"d1": os.urandom(32)}))


class InjectionTest(unittest.TestCase):
    @covers(50, 85, 87)
    def test_injection_and_resource_exhaustion_inputs(self):
        env = make_env()
        vectors = [
            desired(env, component="api\nX-Injected: 1"),
            desired(env, component="a" * 300),
            desired(env, count=10**9),
            desired(env, tenant="acme; rm -rf /"),
            dict(desired(env), extra_field=1),
        ]
        for v in vectors:
            r = req(env, "set_desired", v)
            self.assertEqual(r["outcome"], "TERMINAL", v)
        huge = json.dumps({"schema": "PK_DEPLOY_REQUEST/1", "op": "explain", "token": "t",
                           "idempotency_key": "k" * 10, "body": {"x": "y" * 70000}}).encode()
        self.assertEqual(env.svc.handle(huge)["error"]["code"], "INV63-E-PAYLOAD-TOO-LARGE")
        deep = b'{"a":' * 50 + b"1" + b"}" * 50
        self.assertEqual(env.svc.handle(deep)["outcome"], "TERMINAL")


if __name__ == "__main__":
    unittest.main()
