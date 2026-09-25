"""M25 adversarial regression tests + a bounded fuzz smoke run."""
import unittest
from inv65_capability_providers.tests.helpers import World, ident, AUTHN_KEY
from inv65_capability_providers.authn.authenticator import Authenticator, TrustRoot, issue_token
from inv65_capability_providers.errors.mapping import ProviderFault
from inv65_capability_providers.fuzz.harness import run


class Adversarial(unittest.TestCase):
    def test_token_malleability_regression(self):
        """Fuzz finding 2026-09-22: junk chars in the signature segment were silently
        discarded by the stdlib base64 decoder, so altered token strings verified."""
        root = TrustRoot("pk-issuer", {"k1": AUTHN_KEY}, "inv65")
        t = issue_token(root, "k1", ident(), nonce="malleable-1")
        body, sig = t.split(".")
        for bad in (body + "." + sig + "\x00", body + "." + sig[:5] + "!" + sig[5:], body + "=." + sig, body + "." + sig + "=="):
            with self.subTest(bad=bad[-8:]), self.assertRaises(ProviderFault):
                Authenticator(root).authenticate(bad)

    def test_link_confusion_via_separator_injection(self):
        w = World(); w.svc.start()
        w.link("a|b", cfg={"bucket": "x", "user": "u"})
        with self.assertRaises(ProviderFault):
            w.call("a", component="orders")
        w.link("b", cfg={"bucket": "y", "user": "u"}, component="orders|a")
        self.assertEqual(w.call("a|b")["result"]["bucket"], "x")

    def test_decision_replay_across_links_refused(self):
        w = World(); w.svc.start(); w.link("a"); w.link("b")
        d = w.decision("call", "a", ["get"])
        with self.assertRaises(ProviderFault):
            w.svc.call(w.token(), d, link_name="b", op="get")

    def test_exhaustion_bounds(self):
        w = World(); w.svc.start()
        deep = {"bucket": "b", "user": "u"}; cur = deep
        for _ in range(20):
            cur["n"] = {}; cur = cur["n"]
        with self.assertRaises(ProviderFault):
            w.link("deep", cfg=deep)
        with self.assertRaises(ProviderFault):
            w.link("x" * 300)

    def test_fuzz_smoke_no_crashes(self):
        res = run(1200, seed=7, budget_s=20)
        self.assertEqual(res["crashes"], [])
        self.assertEqual(res["stats"]["authz"]["accepted"], 0)
