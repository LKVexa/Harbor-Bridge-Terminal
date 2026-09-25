"""Components 10 (authn/authz), 11 (secrets/keys), 12 (audit), 21 (tenancy),
22 (residency), 23 (policy), 24 (parsers), 26 (network), 43 (adversarial)."""
from __future__ import annotations

import json
import os
import shutil
import socket
import ssl
import stat
import tempfile
import unittest

import fixtures as F
from inv07_gitops_transition_layer.components import errors as E, manifests as M
from inv07_gitops_transition_layer.components.audit import AuditLedger
from inv07_gitops_transition_layer.components.authz import Authorizer, TokenAuthority
from inv07_gitops_transition_layer.components.keys import KeyRing, SecretBytes, SecretResolver
from inv07_gitops_transition_layer.components.netsec import EgressPolicy, tls_context
from inv07_gitops_transition_layer.components.policy import PolicyEngine, sign_bundle
from inv07_gitops_transition_layer.components.redact import scrub
from inv07_gitops_transition_layer.components.signing import TrustRoots
from inv07_gitops_transition_layer.components.tenancy import ResidencyPolicy, TenantScope

NOW = 1_800_000_000


def _rd(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _wr(p, lines):
    with open(p, "w", encoding="utf-8") as fh:
        fh.writelines(lines)


def tok(sub="alice", tenant="acme", roles=("operator",), iat=NOW - 10, exp=NOW + 600, aud="inv07", kid="k1",
        secret=None, jti="j1"):
    return TokenAuthority.issue(secret or F.KEYS["token"][0], kid, {"sub": sub, "tenant": tenant, "roles": list(roles),
                                                                  "iat": iat, "exp": exp, "aud": aud, "jti": jti})


class TestAuthz(unittest.TestCase):
    def setUp(self):
        self.ta = TokenAuthority({"k1": F.KEYS["token"][1]}, audience="inv07", max_ttl=3600, clock=lambda: NOW)
        self.az = Authorizer(tenant="acme", audit=AuditLedger())

    def test_authentication_failures(self):
        bad = {"missing": None, "garbage": "x.y.z", "forged": tok(secret=F.KEYS["rogue"][0]),
               "expired": tok(exp=NOW - 1, iat=NOW - 100), "future": tok(iat=NOW + 1000, exp=NOW + 2000),
               "aud": tok(aud="other"), "ttl": tok(exp=NOW + 10_000), "kid": tok(kid="k9"),
               "oversize": "PKT1." + "a" * 5000 + ".b"}
        for name, t in bad.items():
            with self.subTest(name), self.assertRaises(E.Unauthenticated):
                self.ta.verify(t)
        self.ta.revoked.add("j1")
        with self.assertRaises(E.Unauthenticated):
            self.ta.verify(tok())

    def test_rbac_abac_and_two_person_rule(self):
        op = self.ta.verify(tok())
        self.assertEqual(self.az.require(op, "sync.trigger")["decision"], "allow")
        with self.assertRaises(E.Unauthorized):
            self.az.require(op, "config.reload")
        other = self.ta.verify(tok(tenant="globex", jti="j2"))
        with self.assertRaises(E.Unauthorized):
            self.az.require(other, "status.read")          # tenant scope
        adm = self.ta.verify(tok(sub="root", roles=("admin",), jti="j3"))
        adm2 = self.ta.verify(tok(sub="sec", roles=("admin",), jti="j4"))
        with self.assertRaises(E.Unauthorized):
            self.az.require(adm, "freeze.override")          # no approver
        with self.assertRaises(E.Unauthorized):
            self.az.require(adm, "freeze.override", approver=adm)   # self-approval
        with self.assertRaises(E.Unauthorized):
            self.az.require(adm, "freeze.override", approver=op)    # approver lacks capability
        self.assertEqual(self.az.require(adm, "freeze.override", approver=adm2)["approver"], "sec")
        kinds = [e["payload"]["decision"] for e in self.az.audit.entries()]
        self.assertIn("deny", kinds)
        self.assertIn("allow", kinds)

    def test_unknown_roles_grant_nothing(self):
        p = self.ta.verify(tok(roles=("superuser",)))
        self.assertEqual(p.capabilities(), set())


class TestKeys(unittest.TestCase):
    def test_secret_refs_and_hygiene(self):
        r = SecretResolver(environ={"INV07_ACME_TOKEN": "s3cret"})
        s = r.resolve("env:INV07_ACME_TOKEN")
        self.assertEqual(s.reveal(), b"s3cret")
        self.assertNotIn("s3cret", repr(s) + str(s))
        s.wipe()
        with self.assertRaises(E.SecretUnavailable):
            s.reveal()
        with self.assertRaises(E.SecretUnavailable):
            r.resolve("env:MISSING")
        with self.assertRaises(E.SecretUnavailable):
            r.resolve("kms:key/1")
        self.assertEqual(SecretResolver(provider=lambda n: b"k").resolve("kms:x").reveal(), b"k")
        with self.assertRaises(E.ConfigRejected):
            r.resolve("inline:abc")

    @unittest.skipUnless(os.name == "posix", "POSIX permission semantics")
    def test_file_secret_permissions(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "t")
            with open(p, "w") as fh:
                fh.write("tok\n")
            os.chmod(p, 0o644)
            with self.assertRaises(E.ConfigRejected):
                SecretResolver().resolve("file:" + p)
            os.chmod(p, 0o600)
            self.assertEqual(SecretResolver().resolve("file:" + p).reveal(), b"tok")
        finally:
            shutil.rmtree(d)

    def test_keyring_rotation_and_revocation(self):
        kr = KeyRing()
        kr.add("a", F.KEYS["dev"][1], activated_at=0, purpose="commit")
        kr.rotate("a", "b", F.KEYS["dev2"][1], at=100, overlap=50)
        self.assertEqual(kr.public("a", now=120), F.KEYS["dev"][1])       # overlap window
        with self.assertRaises(E.Revoked):
            kr.public("a", now=150)
        self.assertEqual(kr.public("b", now=150), F.KEYS["dev2"][1])
        self.assertTrue(all("public" not in r for r in kr.listing()))
        with self.assertRaises(E.ConfigRejected):
            kr.add("b", F.KEYS["dev"][1], activated_at=0, purpose="commit")

    def test_controller_holds_no_private_keys(self):
        roots = TrustRoots.from_doc(F.trust_doc())
        for k in roots.keys.values():
            self.assertIn(len(k.public_key), (0, 32))


class TestAudit(unittest.TestCase):
    def test_chain_seal_truncation_and_redaction(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "a.jsonl")
            a = AuditLedger(p)
            a.append("x", {"password": "hunter2", "note": "token abcdefghijklmnop"}, actor="op")
            a.append("y", {"k": 1}, actor="op")
            a.seal(F.KEYS["audit"][0], "audit")
            head = a.head()
            info = a.verify(expected_head=head, seal_keys={"audit": F.KEYS["audit"][1]})
            self.assertEqual(info["seals"], 1)
            self.assertNotIn("hunter2", _rd(p))
            self.assertNotIn("abcdefghijklmnop", _rd(p))
            with self.assertRaises(E.Corrupted):
                a.verify(seal_keys={"audit": F.KEYS["rogue"][1]})
            lines = _rd(p).splitlines(True)
            _wr(p, lines[:-1])                   # truncation
            with self.assertRaises(E.Corrupted):
                AuditLedger.verify_entries([json.loads(x) for x in lines[:-1]], expected_head=head)
            tampered = lines[:]
            tampered[0] = tampered[0].replace('"x"', '"z"')
            _wr(p, tampered)
            with self.assertRaises(E.Corrupted):
                AuditLedger(p)
            AuditLedger().export(os.path.join(d, "exp.json"))
        finally:
            shutil.rmtree(d)


class TestTenancy(unittest.TestCase):
    def test_paths_secrets_namespaces(self):
        d = tempfile.mkdtemp()
        try:
            t = TenantScope("acme", "edge-1", root=d, namespaces=("team-a",))
            t.path("state")
            with self.assertRaises(E.TenantViolation):
                t.path("..", "..", "globex")
            os.symlink(d, os.path.join(t.root, "escape"))
            with self.assertRaises(E.TenantViolation):
                t.path("escape", "x")
            t.check_secret_ref("env:INV07_ACME_GIT")
            for bad in ("env:INV07_GLOBEX_GIT", "file:/run/secrets/inv07/globex/t", "file:/run/secrets/inv07/acme/../x"):
                with self.subTest(bad), self.assertRaises(E.TenantViolation):
                    t.check_secret_ref(bad)
            t.check_resources({("", "ConfigMap", "team-a", "x"): {}})
            for bad in ({("", "ConfigMap", "kube-system", "x"): {}}, {("", "ConfigMap", "", "x"): {}},
                        {("rbac.authorization.k8s.io", "ClusterRoleBinding", "", "x"): {}}):
                with self.subTest(bad), self.assertRaises(E.TenantViolation):
                    t.check_resources(bad)
            self.assertEqual(t.stamp({"a": 1})["tenant"], "acme")
            with self.assertRaises(E.TenantViolation):
                TenantScope("Acme!", "s", root=d, namespaces=())
        finally:
            shutil.rmtree(d)

    def test_cross_tenant_manifest_refused_end_to_end(self):
        e = F.Env()
        try:
            e.commit({"a.yaml": F.deployment(ns="kube-system")})
            r = e.controller().reconcile("refs/heads/main")
            self.assertEqual((r["outcome"], r["error"]["code"]), ("failed", "PKG-TENANT-001"))
        finally:
            e.cleanup()


class TestResidency(unittest.TestCase):
    def test_allowlist_failover_exceptions_credentials(self):
        r = ResidencyPolicy(region="eu-west", allowed_regions=("eu-west", "eu-central"), site="s1",
                            failover_regions=("eu-central",),
                            exceptions=[{"kind": "telemetry", "region": "us-east", "approved_by": "dpo", "expires": 200}])
        self.assertEqual(r.check("backup", "eu-central", now=0)["basis"], "allowlist")
        with self.assertRaises(E.ResidencyViolation):
            r.check("backup", "us-east", now=0)
        with self.assertRaises(E.ResidencyViolation):
            r.check("failover", "eu-west", now=0)
        self.assertEqual(r.check("telemetry", "us-east", now=100)["basis"], "exception")
        with self.assertRaises(E.ResidencyViolation):
            r.check("telemetry", "us-east", now=300)               # expired exception
        with self.assertRaises(E.ResidencyViolation):
            r.check_credential_site("s2")
        with self.assertRaises(E.ResidencyViolation):
            ResidencyPolicy(region="us-east", allowed_regions=("eu-west",), site="s")


class TestPolicy(unittest.TestCase):
    def setUp(self):
        self.pe = PolicyEngine(TrustRoots.from_doc(F.trust_doc()))

    def res(self, replicas=2, image="r/x:1"):
        return {("apps", "Deployment", "team-a", "w"): {"spec": {"replicas": replicas, "template": {"spec": {
            "containers": [{"image": image}]}}}}}

    def test_bundle_trust_and_version(self):
        with self.assertRaises(E.PolicyUnavailable):
            self.pe.evaluate(self.res(), context={}, now=0)
        with self.assertRaises(E.Untrusted):
            self.pe.load(sign_bundle({"schema": "PK_GITOPS_POLICY/1", "version": 1, "rules": []}, "dev",
                                     F.KEYS["dev"][0]), now=0)
        self.pe.load(F.policy_bundle(version=2), now=0)
        with self.assertRaises(E.Untrusted):
            self.pe.load(F.policy_bundle(version=1), now=0)    # regression
        self.assertEqual(self.pe.bundle["version"], 2)

    def test_deny_reasons_waivers_and_bounds(self):
        self.pe.load(F.policy_bundle(waivers=[{"rule": "no-latest", "resource": "apps/Deployment/team-a/w",
                                               "approved_by": "sec", "expires": 100}]), now=0)
        self.assertTrue(self.pe.evaluate(self.res(), context={}, now=0)["allow"])
        r = self.pe.evaluate(self.res(replicas=99), context={}, now=0)
        self.assertEqual([d["rule"] for d in r["deny"]], ["max-replicas"])
        w = self.pe.evaluate(self.res(image="r/x:latest"), context={}, now=50)
        self.assertTrue(w["allow"])
        self.assertEqual(w["waived"][0]["waiver_by"], "sec")
        self.assertFalse(self.pe.evaluate(self.res(image="r/x:latest"), context={}, now=150)["allow"])
        with self.assertRaises(E.PolicyDenied):
            self.pe.enforce(self.res(replicas=99), context={}, now=0)
        small = PolicyEngine(TrustRoots.from_doc(F.trust_doc()), max_evals=1)
        small.load(F.policy_bundle(), now=0)
        with self.assertRaises(E.PolicyUnavailable):
            small.evaluate(self.res(), context={}, now=0)

    def test_policy_denial_end_to_end(self):
        e = F.Env()
        try:
            e.commit({"a.yaml": F.deployment(image="r/web:latest")})
            c = e.controller()
            r = c.reconcile("refs/heads/main")
            self.assertEqual((r["outcome"], r["error"]["code"]), ("refused", "PKG-POLICY-001"))
            self.assertEqual(c.target.list(), {})
        finally:
            e.cleanup()


class TestParsers(unittest.TestCase):
    def test_yaml_refusals(self):
        bad = {"anchor": b"a: &x 1\nb: *x\n", "alias": b"a: *x\n", "tag": b"a: !!python/object 1\n",
               "merge": b"<<: {}\n", "flow": b"a: [1, 2]\n", "block scalar": b"a: |\n  x\n", "dup": b"a: 1\na: 2\n",
               "tabs": b"a:\n\tb: 1\n", "directive": b"%YAML 1.1\n---\na: 1\n", "nan": b"a: .nan\n",
               "bad indent": b"a:\n  b: 1\n c: 2\n", "not utf8": b"a: \xff\n"}
        for name, data in bad.items():
            with self.subTest(name), self.assertRaises((E.Malformed, E.LimitExceeded)):
                M.parse_yaml(data)

    def test_yaml_norway_and_types(self):
        d = M.parse_yaml(b"a: no\nb: yes\nc: on\nd: 1\ne: 1.5\nf: null\ng: 'q'\nh: \"x\\ny\"\n")[0]
        self.assertEqual(d, {"a": "no", "b": "yes", "c": "on", "d": 1, "e": 1.5, "f": None, "g": "q", "h": "x\ny"})

    def test_json_refusals_and_limits(self):
        with self.assertRaises(E.Malformed):
            M.parse_json(b'{"a":1,"a":2}')
        with self.assertRaises(E.Malformed):
            M.parse_json(b'{"a":NaN}')
        with self.assertRaises(E.LimitExceeded):
            M.parse_json(b"[" * 1000 + b"]" * 1000)
        with self.assertRaises(E.LimitExceeded):
            M.parse_json(b" " * 2000, max_bytes=1000)
        with self.assertRaises(E.LimitExceeded):
            M.parse_yaml(("a:\n" + "".join("  " * i + f"k{i}:\n" for i in range(1, 60)) + "  " * 60 + "v: 1\n")
                         .encode())

    def test_resource_validation(self):
        with self.assertRaises(E.Malformed):
            M.load_tree([("a.json", b'{"kind":"X"}')])
        with self.assertRaises(E.Malformed):
            M.load_tree([("a.json", b'{"apiVersion":"v1","kind":"X","metadata":{"name":"Bad_Name"}}')])
        with self.assertRaises(E.Malformed):
            M.load_tree([("a.json", F.configmap().encode()), ("b.json", F.configmap().encode())])
        with self.assertRaises(E.LimitExceeded):
            M.load_tree([(f"{i}.json", F.configmap(name=f"c{i}").encode()) for i in range(5)], max_resources=3)
        self.assertEqual(len(M.load_tree([("x.txt", b"ignored"), ("a.yaml", F.deployment().encode())])), 1)


class TestNetsec(unittest.TestCase):
    def test_tls_context_defaults(self):
        c = tls_context()
        self.assertEqual(c.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(c.check_hostname)
        self.assertGreaterEqual(c.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertEqual(tls_context(min_version="TLSv1.3").minimum_version, ssl.TLSVersion.TLSv1_3)

    def test_egress_allowlist_and_ssrf(self):
        p = EgressPolicy(["https://git.example", "https://10.0.0.5:8443"])
        p.check("https://git.example/org/repo")
        for bad in ("https://evil.example/", "http://git.example/", "https://u:p@git.example/",
                    "https://169.254.169.254/latest"):
            with self.subTest(bad), self.assertRaises(E.NetworkPolicy):
                p.check(bad)
        fake = lambda h, port, proto=0: [(socket.AF_INET, 1, 6, "", ("127.0.0.1", port))]  # noqa: E731
        with self.assertRaises(E.NetworkPolicy):                    # DNS rebinding to loopback
            p.resolve_pinned("git.example", 443, resolver=fake)
        ok = lambda h, port, proto=0: [(socket.AF_INET, 1, 6, "", ("93.184.216.34", port))]  # noqa: E731
        self.assertEqual(p.resolve_pinned("git.example", 443, resolver=ok), ["93.184.216.34"])
        with self.assertRaises(E.NetworkPolicy):
            EgressPolicy(["git.example"])


class TestAdversarial(unittest.TestCase):
    def test_redaction_everywhere(self):
        s = scrub({"api_key": "x", "nested": {"Authorization": "Bearer abc"}, "url": "https://u:tok@h/x",
                   "text": "password=hunter2 and -----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----",
                   "key_id": "dev", "b": b"\x00" * 10})
        blob = json.dumps(s)
        for leak in ("hunter2", "tok@", "AAAA", "Bearer abc"):
            self.assertNotIn(leak, blob)
        self.assertEqual(s["key_id"], "dev")
        err = E.Unauthorized("denied token abcdefghijk", secret="zzz").envelope()
        self.assertNotIn("zzz", json.dumps(err))
        self.assertNotIn("abcdefghijk", json.dumps(err))

    def test_unknown_exception_never_leaks_text(self):
        env = E.from_exception(RuntimeError("/etc/shadow contents"), "cid")
        self.assertEqual(env["code"], "PKG-INTERNAL-001")
        self.assertNotIn("shadow", json.dumps(env))

    def test_unsigned_injection_via_manifest_does_not_reach_target(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            c.reconcile("refs/heads/main")
            e.commit({"a.json": F.configmap(mode="evil")}, key=None)          # unsigned head
            r = c.reconcile("refs/heads/main")
            self.assertEqual((r["outcome"], r["error"]["code"]), ("refused", "PKG-TRUST-001"))
            live = list(c.target.list().values())[0][0]
            self.assertEqual(live["data"], {"mode": "prod"})
            self.assertEqual(c.m.value("inv07_unsigned_refusals_total", reason="PKG-TRUST-001"), 1)
        finally:
            e.cleanup()

    def test_resource_exhaustion_bounds(self):
        from inv07_gitops_transition_layer.components.telemetry import Registry
        r = Registry(max_series=5)
        r.counter("c")
        for i in range(50):
            r.inc("c", tenant=f"t{i}")
        self.assertLessEqual(len(r._m["c"]["series"]), 6)
        self.assertGreater(r.value("inv07_metric_label_overflow_total"), 0)


if __name__ == "__main__":
    unittest.main()
