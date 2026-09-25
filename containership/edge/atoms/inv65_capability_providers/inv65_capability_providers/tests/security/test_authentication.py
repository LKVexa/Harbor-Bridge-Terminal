import secrets, time, unittest
from inv65_capability_providers.tests.helpers import World, ident, AUTHN_KEY
from inv65_capability_providers.authn.authenticator import Authenticator, TrustRoot, issue_token
from inv65_capability_providers.errors.mapping import ProviderFault


class Authn(unittest.TestCase):
    def setUp(self):
        self.root = TrustRoot("pk-issuer", {"k1": AUTHN_KEY}, "inv65")
        self.a = Authenticator(self.root)

    def tok(self, **kw):
        return issue_token(self.root, "k1", ident(), nonce=kw.pop("nonce", secrets.token_hex(8)), **kw)

    def refuse(self, t, **kw):
        with self.assertRaises(ProviderFault) as c:
            self.a.authenticate(t, **kw)
        self.assertEqual(c.exception.code, "PK_PROVIDER_UNAUTHENTICATED")

    def test_valid(self):
        i = self.a.authenticate(self.tok())
        self.assertTrue(i.authenticated); self.assertEqual(i.tenant, "acme")

    def test_malformed(self):
        for t in (None, "", "a.b.c", "x" * 5000, "abc.def", 42):
            with self.subTest(t=str(t)[:10]):
                self.refuse(t)

    def test_bad_signature_and_tamper(self):
        t = self.tok(); body, sig = t.split(".")
        self.refuse(body + "." + sig[::-1])
        forged = issue_token(TrustRoot("pk-issuer", {"k1": b"x" * 32}, "inv65"), "k1", ident(), nonce="n" * 16)
        self.refuse(forged)

    def test_expired_and_future(self):
        self.refuse(self.tok(now=time.time() - 4000))
        self.refuse(self.tok(now=time.time() + 4000))

    def test_replay_refused(self):
        t = self.tok(nonce="fixed-nonce-1")
        self.a.authenticate(t)
        self.refuse(t)

    def test_wrong_audience_or_issuer(self):
        other = TrustRoot("evil", {"k1": AUTHN_KEY}, "inv65")
        self.refuse(issue_token(other, "k1", ident(), nonce="n" * 12))
        other = TrustRoot("pk-issuer", {"k1": AUTHN_KEY}, "other")
        self.refuse(issue_token(other, "k1", ident(), nonce="n" * 13))

    def test_key_rotation_and_revocation(self):
        self.root.keys["k2"] = b"z" * 32
        self.a.authenticate(issue_token(self.root, "k2", ident(), nonce="rot-nonce-1"))
        self.root.revoked_kids.add("k1")
        self.refuse(self.tok())

    def test_service_refuses_unauthenticated_calls(self):
        w = World(); w.svc.start(); w.link()
        with self.assertRaises(ProviderFault) as c:
            w.svc.call("garbage", w.decision("call", "primary", ["get"]), link_name="primary", op="get")
        self.assertEqual(c.exception.code, "PK_PROVIDER_UNAUTHENTICATED")
