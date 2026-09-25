"""Components 6 and 10: identity, capabilities, authorisation, tenant isolation."""
import unittest

try:
    from . import _path  # noqa: F401
except ImportError:
    import _path  # type: ignore # noqa: F401

from inv20_http_component_worlds.identity import (
    Authorizer, CapabilityInvalid, CapabilityStore, IdentityVerifier, KeyProvider, PolicyUnavailable,
    Principal, PrincipalKind, Quarantined, Unauthenticated,
)

A = [("api.example.com", 443)]


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def setup(env="prod"):
    keys = KeyProvider()
    keys.rotate()
    clock = Clock()
    return keys, clock, CapabilityStore(keys, env, clock)


W = Principal(PrincipalKind.WORKLOAD, "acme", "billing")


class IdentityTest(unittest.TestCase):
    def test_verify_and_forgery(self):
        keys, clock, _ = setup()
        v = IdentityVerifier(keys, clock)
        doc = v.issue(Principal(PrincipalKind.WORKLOAD, "acme", "billing", artifact_digest="sha256:aa"))
        self.assertEqual(v.verify(doc, expected_artifact="sha256:aa").tenant, "acme")
        body, mac = doc.split(".")
        import base64, json
        forged = json.loads(base64.urlsafe_b64decode(body + "==")); forged["tenant"] = "evil"
        fb = base64.urlsafe_b64encode(json.dumps(forged, sort_keys=True, separators=(",", ":")).encode()).rstrip(b"=").decode()
        for bad in (fb + "." + mac, "garbage", doc + "x"):
            with self.subTest(bad=bad[:10]), self.assertRaises(Unauthenticated):
                v.verify(bad)
        with self.assertRaises(Unauthenticated):
            v.verify(doc, expected_artifact="sha256:bb")
        clock.t += 301 + 31
        with self.assertRaises(Unauthenticated):
            v.verify(doc)
        v.available = False
        with self.assertRaises(PolicyUnavailable):
            v.verify(doc)

    def test_malformed_principal(self):
        with self.assertRaises(Unauthenticated):
            Principal(PrincipalKind.WORKLOAD, "ac me", "x")


class CapabilityTest(unittest.TestCase):
    def test_mint_resolve(self):
        _, _, store = setup()
        cap = store.mint(W, A, "sha256:pol")
        got = store.resolve(cap.token, W)
        self.assertEqual(got.authorities, frozenset(A))

    def test_only_workloads_hold_egress(self):
        _, _, store = setup()
        with self.assertRaises(CapabilityInvalid):
            store.mint(Principal(PrincipalKind.OPERATOR, "acme", "ops"), A, "p")

    def test_wrong_binding_and_replay(self):
        keys, clock, store = setup()
        cap = store.mint(W, A, "p")
        for holder in (Principal(PrincipalKind.WORKLOAD, "other", "billing"),
                       Principal(PrincipalKind.WORKLOAD, "acme", "search")):
            with self.subTest(holder=holder.id), self.assertRaises(CapabilityInvalid):
                store.resolve(cap.token, holder)
        other_env = CapabilityStore(keys, "staging", clock)
        with self.assertRaises(CapabilityInvalid):
            other_env.resolve(cap.token, W)           # replay into another environment

    def test_forged_and_tampered(self):
        _, _, store = setup()
        cap = store.mint(W, A, "p")
        k2 = KeyProvider(); k2.rotate("k1")
        rogue = CapabilityStore(k2, "prod", store.clock).mint(W, [("evil.com", 443)], "p")
        for tok in (rogue.token, cap.token[:-2] + "AA", "x.y", ""):
            with self.subTest(tok=tok[:8]), self.assertRaises(CapabilityInvalid):
                store.resolve(tok, W)

    def test_expiry_and_skew(self):
        _, clock, store = setup()
        cap = store.mint(W, A, "p", ttl=60)
        clock.t += 60
        store.resolve(cap.token, W)                   # boundary inclusive
        clock.t += 1
        with self.assertRaises(CapabilityInvalid):
            store.resolve(cap.token, W)
        clock.t -= 1000                               # clock stepped back beyond skew
        with self.assertRaises(CapabilityInvalid):
            store.resolve(cap.token, W)

    def test_revocation_and_emergency_disable(self):
        _, _, store = setup()
        cap = store.mint(W, A, "p")
        child = store.delegate(cap, Principal(PrincipalKind.WORKLOAD, "acme", "billing.worker"))
        store.revoke(cap.cap_id)
        for tok, holder in ((cap.token, W), (child.token, Principal(PrincipalKind.WORKLOAD, "acme", "billing.worker"))):
            with self.assertRaises(CapabilityInvalid):
                store.resolve(tok, holder)
        cap2 = store.mint(W, A, "p")
        store.revoke_all()
        with self.assertRaises(CapabilityInvalid):
            store.resolve(cap2.token, W)

    def test_delegation_attenuates_only(self):
        _, _, store = setup()
        cap = store.mint(W, A + [("b.example.com", 443)], "p", ttl=100)
        child_p = Principal(PrincipalKind.WORKLOAD, "acme", "billing.worker")
        child = store.delegate(cap, child_p, authorities=A, ttl=1000)
        self.assertEqual(child.authorities, frozenset(A))
        self.assertLessEqual(child.expires, cap.expires)
        with self.assertRaises(CapabilityInvalid):
            store.delegate(cap, child_p, authorities=[("evil.com", 443)])
        with self.assertRaises(CapabilityInvalid):
            store.delegate(cap, Principal(PrincipalKind.WORKLOAD, "other", "billing.worker"))
        with self.assertRaises(CapabilityInvalid):
            store.delegate(cap, Principal(PrincipalKind.WORKLOAD, "acme", "search"))

    def test_quarantine(self):
        _, _, store = setup()
        cap = store.mint(W, A, "p")
        other = Principal(PrincipalKind.WORKLOAD, "beta", "api")
        ocap = store.mint(other, A, "p")
        store.quarantine("acme")
        with self.assertRaises(Quarantined):
            store.resolve(cap.token, W)
        self.assertEqual(store.resolve(ocap.token, other).tenant, "beta")   # others continue
        store.release("acme")
        store.resolve(cap.token, W)

    def test_key_rotation_keeps_old_valid_until_retired(self):
        keys, _, store = setup()
        cap = store.mint(W, A, "p")
        keys.rotate()
        store.resolve(cap.token, W)
        keys.retire("k1")
        with self.assertRaises(CapabilityInvalid):
            store.resolve(cap.token, W)
        self.assertNotIn("\\x", repr(keys))


class AuthorizerTest(unittest.TestCase):
    def test_fail_closed_and_bounded_cache(self):
        clock = Clock(0)
        state = {"up": True}

        def pdp(p, a, t):
            if not state["up"]:
                raise ConnectionError
            return t == "ok"
        az = Authorizer(pdp, cache_seconds=5, clock=clock)
        self.assertTrue(az.check(W, "egress", "ok"))
        self.assertFalse(az.check(W, "egress", "no"))
        state["up"] = False
        self.assertTrue(az.check(W, "egress", "ok"))     # cached allow within window
        with self.assertRaises(PolicyUnavailable):
            az.check(W, "egress", "no")                   # cached deny never flips to allow
        clock.t = 6
        with self.assertRaises(PolicyUnavailable):
            az.check(W, "egress", "ok")                   # window expired
        az0 = Authorizer(pdp)
        with self.assertRaises(PolicyUnavailable):
            az0.check(W, "egress", "ok")


if __name__ == "__main__":
    unittest.main()
