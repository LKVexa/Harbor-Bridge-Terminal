"""MC18-21 / MC29 / MC32 / MC49 / MC55 / MC77 — supply-chain trust and admission policy."""
import base64
import json
import unittest

from inv02_container_substrate import trust as t
from inv02_container_substrate.policy import PolicyEngine, Request, Waiver, WaiverRegistry
from inv02_container_substrate.registry import ValidationError
from inv02_container_substrate.tests.fixtures import sha

NOW = 1_700_000_000.0
RFC_SK = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
RFC_PK = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
RFC_SIG = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")


class Ed25519Tests(unittest.TestCase):
    def test_rfc8032_vector_1(self):
        self.assertEqual(t.ed25519_public_key(RFC_SK), RFC_PK)
        self.assertEqual(t.ed25519_sign(RFC_SK, b""), RFC_SIG)
        self.assertTrue(t.ed25519_verify(RFC_PK, b"", RFC_SIG))

    def test_rfc8032_vector_2(self):
        sk = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
        pk = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
        sig = bytes.fromhex("92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")
        self.assertEqual(t.ed25519_public_key(sk), pk)
        self.assertTrue(t.ed25519_verify(pk, b"\x72", sig))

    def test_rejects_tampering_and_malleability(self):
        self.assertFalse(t.ed25519_verify(RFC_PK, b"x", RFC_SIG))
        bad = bytearray(RFC_SIG)
        bad[5] ^= 1
        self.assertFalse(t.ed25519_verify(RFC_PK, b"", bytes(bad)))
        s = int.from_bytes(RFC_SIG[32:], "little") + t._q  # non-canonical S
        self.assertFalse(t.ed25519_verify(RFC_PK, b"", RFC_SIG[:32] + s.to_bytes(32, "little")))
        self.assertFalse(t.ed25519_verify(b"\x00" * 31, b"", RFC_SIG))


class KeyringTests(unittest.TestCase):
    def setUp(self):
        self.sk1, self.pk1 = t.generate_keypair(b"\x01" * 32)
        self.sk2, self.pk2 = t.generate_keypair(b"\x02" * 32)
        self.kr = t.Keyring()
        self.kr.add(t.TrustedKey("k1", self.pk1, NOW - 10, NOW + 1e6))

    def payload(self):
        return t.image_signature_payload(sha(b"m"), "reg.test/app")

    def test_verify_threshold_validity_and_revocation(self):
        p = self.payload()
        sig = t.ed25519_sign(self.sk1, p)
        self.assertEqual(t.verify_signatures(p, [("k1", sig)], self.kr, at=NOW), ["k1"])
        with self.assertRaises(t.SignatureInvalid):
            t.verify_signatures(p, [("k1", sig), ("k1", sig)], self.kr, at=NOW, threshold=2)  # same key twice
        with self.assertRaises(t.SignatureInvalid):
            t.verify_signatures(p, [("k1", sig)], self.kr, at=NOW + 2e6)  # expired
        self.kr.revoke("k1", "compromised")
        with self.assertRaises(t.SignatureInvalid):
            t.verify_signatures(p, [("k1", sig)], self.kr, at=NOW)
        with self.assertRaises(ValidationError):
            self.kr.add(t.TrustedKey("k1", self.pk1, NOW, NOW + 10))

    def test_signature_bound_to_repository(self):
        sig = t.ed25519_sign(self.sk1, self.payload())
        other = t.image_signature_payload(sha(b"m"), "reg.test/other")
        with self.assertRaises(t.SignatureInvalid):
            t.verify_signatures(other, [("k1", sig)], self.kr, at=NOW)

    def test_rotation_overlap(self):
        p = self.payload()
        self.kr.rotate("k1", t.TrustedKey("k2", self.pk2, NOW, NOW + 1e6), overlap_s=100, now=NOW)
        s1, s2 = t.ed25519_sign(self.sk1, p), t.ed25519_sign(self.sk2, p)
        t.verify_signatures(p, [("k1", s1)], self.kr, at=NOW + 50)
        t.verify_signatures(p, [("k2", s2)], self.kr, at=NOW + 50)
        with self.assertRaises(t.SignatureInvalid):
            t.verify_signatures(p, [("k1", s1)], self.kr, at=NOW + 200)
        self.assertEqual(self.kr.expiring(NOW, 200), ["k1"])


class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.sk, self.pk = t.generate_keypair(b"\x03" * 32)
        self.kr = t.Keyring()
        self.kr.add(t.TrustedKey("ci", self.pk, NOW - 1, NOW + 1e6, frozenset({"attestation"})))
        self.subject = sha(b"image")

    def env(self, subject=None, builder="https://ci.test/builder", pt=t.SLSA_PROVENANCE_V1):
        st = {"_type": t.INTOTO_STATEMENT_V1, "subject": [{"name": "app", "digest": {"sha256": (subject or self.subject)[7:]}}],
              "predicateType": pt, "predicate": {"runDetails": {"builder": {"id": builder}}}}
        return t.dsse_sign(t.DSSE_INTOTO, json.dumps(st).encode(), "ci", self.sk)

    def test_valid_provenance(self):
        v = t.verify_attestation(self.env(), self.subject, self.kr, at=NOW, allowed_builders=frozenset({"https://ci.test/builder"}))
        self.assertEqual(v.signers, ("ci",))

    def test_rejections(self):
        cases = {
            "subject": self.env(subject=sha(b"other")),
            "builder": self.env(builder="https://evil.test"),
            "ptype": self.env(pt="https://example.test/other"),
        }
        tampered = self.env()
        tampered["payload"] = base64.b64encode(base64.b64decode(tampered["payload"]).replace(b"app", b"apq")).decode()
        cases["tampered"] = tampered
        for name, env in cases.items():
            with self.subTest(name), self.assertRaises(t.SignatureInvalid):
                t.verify_attestation(env, self.subject, self.kr, at=NOW, allowed_builders=frozenset({"https://ci.test/builder"}))

    def test_image_key_cannot_sign_attestations(self):
        kr = t.Keyring()
        kr.add(t.TrustedKey("ci", self.pk, NOW - 1, NOW + 1e6, frozenset({"image"})))
        with self.assertRaises(t.SignatureInvalid):
            t.verify_attestation(self.env(), self.subject, kr, at=NOW)


class SBOMAndScanTests(unittest.TestCase):
    def test_cyclonedx_and_spdx(self):
        cdx = t.ingest_sbom({"bomFormat": "CycloneDX", "specVersion": "1.5",
                             "components": [{"name": "openssl", "version": "3.0.13", "purl": "pkg:deb/debian/openssl@3.0.13"}]}, sha(b"i"))
        self.assertEqual(cdx.components[0][0], "openssl")
        spdx = t.ingest_sbom({"spdxVersion": "SPDX-2.3", "packages": [{"name": "zlib", "versionInfo": "1.3",
                              "externalRefs": [{"referenceType": "purl", "referenceLocator": "pkg:generic/zlib@1.3"}]}]}, sha(b"i"))
        self.assertEqual(spdx.components, (("zlib", "1.3", "pkg:generic/zlib@1.3"),))
        with self.assertRaises(ValidationError):
            t.ingest_sbom({"foo": 1}, sha(b"i"))

    def test_scan_states_are_distinct(self):
        d = sha(b"i")
        S = t.ScanState
        self.assertEqual(t.scan_state(None, now=NOW, max_age_s=10)[0], S.UNSCANNED)
        self.assertEqual(t.scan_state(t.ScanResult(d, "s", "1", NOW, False), now=NOW, max_age_s=10)[0], S.SCAN_FAILED)
        self.assertEqual(t.scan_state(t.ScanResult(d, "s", "1", NOW - 100, True), now=NOW, max_age_s=10)[0], S.SCAN_STALE)
        r = t.ScanResult(d, "s", "1", NOW, True, (("CVE-1", "critical"), ("CVE-2", "low")))
        self.assertEqual(t.scan_state(r, now=NOW, max_age_s=10), (S.VULNERABLE, ["CVE-1"]))
        self.assertEqual(t.scan_state(r, now=NOW, max_age_s=10, waived=frozenset({"CVE-1"}))[0], S.EXCEPTION_APPROVED)
        self.assertEqual(t.scan_state(t.ScanResult(d, "s", "1", NOW, True, (("CVE-3", "low"),)), now=NOW, max_age_s=10)[0], S.CLEAN)


BUNDLE = {"version": "2026.09.1", "protected_environments": ["prod"], "trusted_signers": ["k1"],
          "require_signature": {"prod": True}, "allowed_builders": ["https://ci.test/builder"],
          "unwaivable": ["not-quarantined"],
          "tenants": {"team-a": {"workload_classes": ["web", "batch"]}},
          "workload_classes": {"web": {"grants": []}, "batch": {"grants": ["cap:NET_ADMIN"]}}}


def req(**kw):
    base = dict(tenant="team-a", workload_class="web", environment="prod", reference="r.test/a@" + sha(b"m"),
                digest=sha(b"m"), signed_by=("k1",), provenance_builder="https://ci.test/builder",
                scan_state=t.ScanState.CLEAN)
    base.update(kw)
    return Request(**base)


class PolicyTests(unittest.TestCase):
    def test_allow_and_explain(self):
        d = PolicyEngine(BUNDLE).evaluate(req(), NOW)
        self.assertTrue(d.allow)
        ex = d.explain()
        self.assertEqual(ex["policy_version"], "2026.09.1")
        self.assertTrue(ex["policy_digest"].startswith("sha256:"))
        self.assertEqual(ex["denied_by"], [])

    def test_each_rule_denies(self):
        eng = PolicyEngine(BUNDLE)
        cases = {"digest-pinned": req(digest=None), "signed": req(signed_by=("other",)),
                 "provenance": req(provenance_builder="x"), "vulnerabilities": req(scan_state=t.ScanState.UNSCANNED),
                 "not-quarantined": req(quarantined=True), "tenant-isolation": req(tenant="team-z")}
        for rule, r in cases.items():
            with self.subTest(rule):
                d = eng.evaluate(r, NOW)
                self.assertFalse(d.allow)
                self.assertIn(rule, d.explain()["denied_by"])

    def test_tenant_grants(self):
        eng = PolicyEngine(BUNDLE)
        self.assertFalse(eng.evaluate(req(runtime={"capabilities": ["NET_ADMIN"]}), NOW).allow)
        self.assertTrue(eng.evaluate(req(workload_class="batch", runtime={"capabilities": ["NET_ADMIN"]}), NOW).allow)
        self.assertFalse(eng.evaluate(req(runtime={"privileged": True}), NOW).allow)

    def test_rule_exception_fails_closed(self):
        eng = PolicyEngine(BUNDLE, rules={"boom": lambda r, b: 1 / 0})
        d = eng.evaluate(req(), NOW)
        self.assertFalse(d.allow)
        self.assertIn("ZeroDivisionError", d.outcomes[0].reason)

    def test_waivers_scoped_expiring_and_unwaivable(self):
        w = Waiver("W-1", "vulnerabilities", "team-a", sha(b"m"), "alice", "bob", "vendor fix pending",
                   "network-isolated", NOW + 100, "SEC-42")
        eng = PolicyEngine(BUNDLE, waivers=WaiverRegistry([w]))
        d = eng.evaluate(req(scan_state=t.ScanState.VULNERABLE), NOW)
        self.assertTrue(d.allow)
        self.assertEqual([o.waiver for o in d.outcomes if o.rule == "vulnerabilities"], ["W-1"])
        self.assertFalse(eng.evaluate(req(scan_state=t.ScanState.VULNERABLE), NOW + 200).allow)
        self.assertFalse(eng.evaluate(req(scan_state=t.ScanState.VULNERABLE, digest=sha(b"other")), NOW).allow)
        wq = Waiver("W-2", "not-quarantined", "team-a", None, "alice", "bob", "x", "y", NOW + 100, "SEC-1")
        eng2 = PolicyEngine(BUNDLE, waivers=WaiverRegistry([wq]))
        self.assertFalse(eng2.evaluate(req(quarantined=True), NOW).allow)
        with self.assertRaises(ValidationError):
            Waiver("W-3", "signed", "team-a", None, "alice", "alice", "x", "y", NOW, "SEC-2")


if __name__ == "__main__":
    unittest.main()
