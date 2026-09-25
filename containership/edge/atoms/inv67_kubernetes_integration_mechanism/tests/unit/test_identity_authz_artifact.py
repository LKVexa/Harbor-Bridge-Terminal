"""Identity mapping, authn/authz, artifact verification, compat, precedence (items 5, 8, 15, 16, 24-26)."""
import unittest

import _support as S

PE = S.lifecycle.PlaneError


class Identity(unittest.TestCase):
    def test_stable_and_uid_scoped(self):
        m = S.identity.IdentityMapper("c1", {"ns": "t"})
        a = m.map("ns", "web", "1234abcd-0000")
        self.assertEqual(a.app_id, m.map("ns", "web", "1234abcd-0000").app_id)
        self.assertNotEqual(a.app_id, m.map("ns", "web", "1234abcd-0001").app_id)
        self.assertRegex(a.app_id, r"^app-[0-9a-f]{24}$")

    def test_fail_closed(self):
        m = S.identity.IdentityMapper("c1", {"ns": "t"})
        for args in [("other", "web", "1234abcd"), ("ns", "Web", "1234abcd"), ("ns", "web", "x"), ("ns", "web", None)]:
            with self.assertRaises(PE):
                m.map(*args)
        with self.assertRaises(ValueError):
            S.identity.IdentityMapper("Bad_Cluster", {})


class Authz(unittest.TestCase):
    def test_default_policy_least_privilege(self):
        pol = S.authz.default_policy()
        ctl = S.authz.Principal(S.authz.CONTROLLER_SA, (), "tokenreview")
        pol.check(ctl, "update", "wasmworkloads/status", "any")
        for verb, res, ns in [("delete", "wasmworkloads", "x"), ("get", "secrets", "x"), ("update", "leases", "kube-system"),
                              ("create", "pods", "x")]:
            with self.assertRaises(PE):
                pol.check(ctl, verb, res, ns)
        with self.assertRaises(PE):
            pol.check(S.authz.Principal(S.authz.CONTROLLER_SA), "get", "wasmworkloads", "x")  # unauthenticated
        with self.assertRaises(PE):
            pol.check(S.authz.Principal("mallory", (), "mtls"), "get", "wasmworkloads", "x")

    def test_rbac_yaml_matches_policy_verbs(self):
        rules = S.mod("manifests").rbac()[1]["rules"]
        verbs = {(r["resources"][0], v) for r in rules for v in r["verbs"]}
        self.assertNotIn(("wasmworkloads", "delete"), verbs)
        self.assertNotIn(("wasmworkloads", "create"), verbs)
        self.assertFalse(any("*" in r["verbs"] or "*" in r["resources"] for r in rules))
        self.assertFalse(any(r["resources"][0] in ("secrets", "pods") for r in rules))

    def test_tokens(self):
        c = S.Clock()
        v = S.authz.TokenVerifier(S.KEY, c)
        t = v.issue("svc", ttl=10)
        self.assertEqual(v.verify(t).subject, "svc")
        for bad in (t[:-1] + ("0" if t[-1] != "0" else "1"), "garbage", "a|b|c", t.replace("svc", "adm")):
            with self.assertRaises(PE):
                v.verify(bad)
        c.tick(11)
        with self.assertRaises(PE):
            v.verify(t)
        with self.assertRaises(ValueError):
            S.authz.TokenVerifier(b"short")

    def test_mtls_trust_domain(self):
        p = S.authz.principal_from_mtls(["spiffe://prod.example/ns/x/sa/y"], "spiffe://prod.example/")
        self.assertEqual(p.method, "mtls")
        with self.assertRaises(PE):
            S.authz.principal_from_mtls(["spiffe://evil.example/ns/x"], "spiffe://prod.example/")


class Artifact(unittest.TestCase):
    def kw(self, **o):
        k = dict(allowed_registries=["registry.example.org"], require_digest=True, require_signature=True,
                 verifier=S.artifact.HmacAttestationVerifier(S.KEY, {S.IMAGE: S.artifact.HmacAttestationVerifier.sign(S.KEY, S.IMAGE)}))
        k.update(o)
        return k

    def test_accepts_pinned_signed(self):
        S.artifact.verify_image(S.IMAGE, **self.kw())

    def test_refusals(self):
        cases = [("registry.example.org/web:latest", {}), ("evil.io/web" + S.DIGEST, {}), ("web" + S.DIGEST, {}),
                 ("registry.example.org/other" + S.DIGEST, {}), (S.IMAGE, {"verifier": None}),
                 (S.IMAGE, {"allowed_registries": []}), ("registry.example.org/a b", {}), ("", {})]
        for img, over in cases:
            with self.subTest(img=img, over=over):
                with self.assertRaises(PE) as e:
                    S.artifact.verify_image(img, **self.kw(**over))
                self.assertEqual(e.exception.code, "INV67_ARTIFACT_UNVERIFIED")


class Compat(unittest.TestCase):
    def test_certify(self):
        req = S.translator.translate({"metadata": {"name": "a"}, "spec": {"containers": [
            {"name": "c", "image": "i", "resources": {"requests": {"cpu": "1"}}}]}})
        S.compat.certify(req, ["cpu"])
        with self.assertRaises(PE):
            S.compat.certify(req, ["memory"])

    def test_peer_matrix(self):
        S.compat.check_peer("kubernetes", "v1.31.2")
        for k, v in [("kubernetes", "1.20"), ("crd", "x/v9"), ("martian", "1")]:
            with self.assertRaises(PE):
                S.compat.check_peer(k, v)


class Precedence(unittest.TestCase):
    def test_order(self):
        r = S.policy.resolve
        self.assertEqual(r({"security": "deny", "preference": "allow"}), ("deny", "security"))
        self.assertEqual(r({"cost": "deny", "slo": "allow"}), ("deny", "cost"))
        self.assertEqual(r({"capacity": "defer", "cost": "deny"}), ("deny", "cost"))
        self.assertEqual(r({"capacity": "defer"}), ("defer", "capacity"))
        self.assertEqual(r({}), ("allow", "all"))
        self.assertEqual(r({"vibes": "allow"})[0], "deny")
        self.assertEqual(r({"security": "maybe"})[0], "deny")


if __name__ == "__main__":
    unittest.main()
