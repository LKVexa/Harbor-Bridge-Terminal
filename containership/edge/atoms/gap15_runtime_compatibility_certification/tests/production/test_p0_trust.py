"""P0 trust foundation: signing (03), provenance (04), attestation (05), trusted time (06),
authentication (07), authorization (08), adversarial (36)."""
import json
import unittest

from fixtures import ENV, PART, PART2, T0, World, art
from gap15_runtime_compatibility_certification.production import (attestation, authn, authz, ed25519, provenance,
                                                                   signing, timepolicy)
from gap15_runtime_compatibility_certification.production.canonical import canonical_bytes
from gap15_runtime_compatibility_certification.production.service import ServiceError


class SigningTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.payload = {"a": 1, "b": "x"}
        self.sig = signing.sign_payload(self.w.kp, "producer-a-key", message_type="evidence", environment=ENV,
                                        payload=self.payload, signed_at=T0)

    def v(self, sig=None, **kw):
        args = dict(message_type="evidence", environment=ENV, payload=self.payload, required_scope=f"evidence:submit:{ENV}")
        args.update(kw)
        return signing.verify_payload(self.w.trust, sig or self.sig, **args)

    def test_rfc8032_vector_and_strict_s(self):
        """controls: 03-02 03-09 35-06"""
        sk = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        self.assertEqual(ed25519.public_key(sk).hex(), "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        s = ed25519.sign(sk, b"")
        self.assertTrue(s.hex().startswith("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"))
        pk = ed25519.public_key(sk)
        S = int.from_bytes(s[32:], "little") + ed25519.L  # malleated S
        self.assertFalse(ed25519.verify(pk, b"", s[:32] + S.to_bytes(32, "little")))

    def test_domain_separation_prevents_cross_type_and_env_replay(self):
        """controls: 03-01 36-01 25-02"""
        self.assertTrue(self.v().ok)
        self.assertEqual(self.v(message_type="quote").code, "E_SIG_INVALID")
        self.assertEqual(self.v(environment="staging").code, "E_SIG_INVALID")

    def test_binding_fields_and_stable_reason_codes(self):
        """controls: 03-03 03-04 03-10"""
        r = self.v()
        self.assertEqual((r.signer, r.key_id, r.trust_store_revision), ("producer-a", "producer-a-key", self.w.trust.revision))
        self.assertTrue({"algorithm", "key_id", "signed_at", "payload_digest", "value"} <= set(self.sig))
        cases = {
            "E_SIG_ALG_UNAPPROVED": dict(self.sig, algorithm="rsa-pss"),
            "E_SIG_ALG_DEPRECATED": dict(self.sig, algorithm="hmac-sha256"),
            "E_SIG_UNKNOWN_KEY": dict(self.sig, key_id="nope"),
            "E_SIG_DIGEST_MISMATCH": dict(self.sig, payload_digest="sha256:" + "0" * 64),
            "E_SIG_MALFORMED": dict(self.sig, value=self.sig["value"][:40]),
        }
        for code, sig in cases.items():
            self.assertEqual(self.v(sig).code, code)
        self.assertEqual(self.v(payload={"a": 2, "b": "x"}).code, "E_SIG_DIGEST_MISMATCH")

    def test_key_id_confusion_and_signer_authorization(self):
        """controls: 03-06 36-02"""
        forged = dict(self.sig, key_id="producer-b-key")
        self.assertEqual(self.v(forged).code, "E_SIG_INVALID")
        builder_sig = signing.sign_payload(self.w.kp, "builder-key", message_type="evidence", environment=ENV,
                                           payload=self.payload, signed_at=T0)
        self.assertEqual(self.v(builder_sig).code, "E_SIG_SIGNER_UNAUTHORIZED")

    def test_rotation_overlap_and_compromise(self):
        """controls: 03-05 13-07 36-03"""
        ts = signing.TrustStore()
        kp = signing.DevelopmentKeyProvider()
        ts.add(signing.TrustedKey("k1", "p", kp.generate("k1"), not_before=0, not_after=T0 + 100, scopes=frozenset({"s"})))
        ts.add(signing.TrustedKey("k2", "p", kp.generate("k2"), not_before=T0 + 50, scopes=frozenset({"s"})))
        old = signing.sign_payload(kp, "k1", message_type="m", environment="e", payload={}, signed_at=T0 + 10)
        new = signing.sign_payload(kp, "k2", message_type="m", environment="e", payload={}, signed_at=T0 + 60)
        late = signing.sign_payload(kp, "k1", message_type="m", environment="e", payload={}, signed_at=T0 + 200)
        chk = lambda s: signing.verify_payload(ts, s, message_type="m", environment="e", payload={}, required_scope="s").code
        self.assertEqual((chk(old), chk(new), chk(late)), ("OK", "OK", "E_SIG_KEY_EXPIRED"))
        with self.assertRaises(signing.SignatureError):
            ts.add(signing.TrustedKey("k1", "p", kp.generate("k1b")))  # key ids are never reused
        ts.mark_compromised("k2", T0 + 70)
        self.assertEqual(chk(new), "E_SIG_KEY_REVOKED")

    def test_development_key_provider_refuses_production(self):
        """controls: 03-07 44-05"""
        with self.assertRaises(signing.SignatureError):
            signing.DevelopmentKeyProvider(production=True)
        self.assertNotIn("seed", repr(self.w.kp))
        with self.assertRaises(ServiceError):
            World(production=True)

    def test_offline_trust_bundle_roundtrip(self):
        """controls: 03-08"""
        b = self.w.trust.export_bundle()
        ts2 = signing.TrustStore.from_bundle(json.loads(json.dumps(b)))
        self.assertTrue(signing.verify_payload(ts2, self.sig, message_type="evidence", environment=ENV,
                                               payload=self.payload).ok)


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.a = provenance.ArtifactId(art(1), "application/wasm")

    def check(self, prov, **kw):
        return provenance.verify_provenance(self.w.trust, self.a, prov["statement"], prov["signature"], sbom=prov.get("sbom"),
                                            environment=ENV, **kw)

    def test_digest_identity_required(self):
        """controls: 04-01 36-02"""
        for bad in ("svc:latest", "sha256:ABC", "sha1:" + "a" * 40):
            with self.assertRaises(provenance.ProvenanceError):
                provenance.ArtifactId(bad, "application/wasm")
        with self.assertRaises(provenance.ProvenanceError):
            provenance.ArtifactId(art(1), "text/html")

    def test_valid_and_forged_provenance(self):
        """controls: 04-02 04-05 04-10 33-03"""
        good = self.w.provenance(art(1))
        r = self.check(good)
        self.assertTrue(r.ok)
        self.assertTrue(r.statement_digest.startswith("sha256:"))
        forged = self.w.provenance(art(1))
        forged["statement"]["predicate"]["runDetails"]["builder"]["id"] = "https://evil"
        self.assertEqual(self.check(forged).code, "E_PROV_SIG_DIGEST_MISMATCH")
        other = self.w.provenance(art(2))
        self.assertEqual(self.check(other).code, "E_PROV_DIGEST_MISMATCH")

    def test_sbom_subject_and_unknown_fields(self):
        """controls: 04-03 04-04"""
        p = self.w.provenance(art(1), sbom_subject=art(3))
        self.assertEqual(self.check(p).code, "E_PROV_SBOM_SUBJECT")
        p = self.w.provenance(art(1))
        p.pop("sbom")
        self.assertEqual(self.check(p).code, "E_PROV_SBOM_MISSING")
        p = self.w.provenance(art(1))
        p["statement"]["extra"] = 1
        self.assertEqual(self.check(p).code, "E_PROV_SHAPE")

    def test_revoked_builder_and_source(self):
        """controls: 04-07"""
        p = self.w.provenance(art(1))
        self.assertEqual(self.check(p, revoked_builders=frozenset({"https://builder.example/gap07"})).code, "E_PROV_BUILDER_REVOKED")
        self.assertEqual(self.check(p, revoked_sources=frozenset({"git+https://src.example/svc@abc"})).code, "E_PROV_SOURCE_REVOKED")

    def test_multi_artifact_index_children(self):
        """controls: 04-06"""
        idx = provenance.ArtifactId(art(10), "application/vnd.oci.image.index.v1+json")
        st = {"_type": provenance.STATEMENT_TYPE, "predicateType": "https://slsa.dev/provenance/v1",
              "subject": [{"digest": {"sha256": art(i)[7:]}} for i in (10, 11, 12)],
              "predicate": {"runDetails": {"builder": {"id": "b"}}, "gap15_children": [art(11), art(12)]}}
        sig = signing.sign_payload(self.w.kp, "builder-key", message_type="provenance", environment=ENV, payload=st, signed_at=T0)
        ok = provenance.verify_provenance(self.w.trust, idx, st, sig, sbom={"subject": art(10)}, environment=ENV)
        self.assertTrue(ok.ok)
        self.assertEqual(ok.children, tuple(sorted([art(11), art(12)])))
        st["predicate"]["gap15_children"] = [art(11)]
        sig = signing.sign_payload(self.w.kp, "builder-key", message_type="provenance", environment=ENV, payload=st, signed_at=T0)
        self.assertEqual(provenance.verify_provenance(self.w.trust, idx, st, sig, sbom={"subject": art(10)}, environment=ENV).code,
                         "E_PROV_INDEX_MISMATCH")

    def test_tag_resolution_and_toctou(self):
        """controls: 04-08 30-09"""
        tr = provenance.TagResolver({"svc:prod": (art(1), 1)})
        resolved = tr.resolve("svc:prod")
        self.assertEqual(tr.confirm("svc:prod", resolved), art(1))
        tr.tags["svc:prod"] = (art(2), 2)
        with self.assertRaises(provenance.ProvenanceError) as cm:
            tr.confirm("svc:prod", resolved)
        self.assertEqual(cm.exception.code, "E_TAG_MOVED")


class AttestationTest(unittest.TestCase):
    def setUp(self):
        self.w = World()

    def vq(self, q, s, nonce, **kw):
        pol = kw.pop("policy", self.w.att_policy)
        return attestation.verify_quote(self.w.trust, q, s, nonce=nonce, now=kw.pop("now", T0), policy=pol, environment=ENV)

    def test_valid_quote_derives_profile(self):
        """controls: 05-01 05-02 05-03 17-04 33-02"""
        q, s = self.w.quote("ab" * 16)
        r = self.vq(q, s, "ab" * 16)
        self.assertTrue(r.ok, r.code)
        self.assertEqual(r.trust_class, "hardware-attested")
        self.assertTrue(r.profile.identity().startswith("profile:"))
        self.assertEqual(r.profile.get("cpu.arch"), "aarch64")  # normalised alias from 'arm64'
        self.assertNotIn("node-1", json.dumps(r.summary()))  # privacy: hashed node reference only

    def test_replay_nonce_stale_measurements_firmware(self):
        """controls: 05-04 05-05 05-10 36-01"""
        q, s = self.w.quote("ab" * 16)
        self.assertEqual(self.vq(q, s, "cd" * 16).code, "E_ATT_NONCE")
        self.assertEqual(self.vq(q, s, "ab" * 16, now=T0 + 301).code, "E_ATT_STALE")
        q2, s2 = self.w.quote("ab" * 16, measurements={"pcr0": "c" * 64, "pcr7": "b" * 64})
        self.assertEqual(self.vq(q2, s2, "ab" * 16).code, "E_ATT_MEASUREMENT")
        q3, s3 = self.w.quote("ab" * 16, firmware="1.9.9")
        self.assertEqual(self.vq(q3, s3, "ab" * 16).code, "E_ATT_FIRMWARE_DOWNGRADE")
        q4, s4 = self.w.quote("ab" * 16, secure_boot=False)
        self.assertEqual(self.vq(q4, s4, "ab" * 16).code, "E_ATT_SECURE_BOOT")

    def test_cloned_identity_and_untrusted_root(self):
        """controls: 05-10 36-02"""
        q, s = self.w.quote("ab" * 16)
        q["node_id"] = "node-2"  # cloned/substituted identity invalidates the signature
        self.assertEqual(self.vq(q, s, "ab" * 16).code, "E_ATT_SIG_DIGEST_MISMATCH")
        q, s = self.w.quote("ab" * 16, ak="producer-a-key")  # a key not authorised to quote
        self.assertEqual(self.vq(q, s, "ab" * 16).code, "E_ATT_SIG_SIGNER_UNAUTHORIZED")

    def test_reduced_trust_policy_explicit(self):
        """controls: 05-06"""
        q, s = self.w.quote("ab" * 16, root="software")
        self.assertEqual(self.vq(q, s, "ab" * 16).code, "E_ATT_NO_HW_ROOT")
        pol = attestation.AttestationPolicy(baselines=self.w.att_policy.baselines, min_firmware="2.0.0", allow_reduced_trust=True)
        r = self.vq(q, s, "ab" * 16, policy=pol)
        self.assertEqual(r.trust_class, "reduced-trust")
        self.assertEqual(r.profile.get("runtime.name", min_provenance="attested"), "__unknown__")
        self.assertNotEqual(r.profile.identity(), self.vq(*self.w.quote("ab" * 16), "ab" * 16).profile.identity())

    def test_nested_layers_and_revoked_firmware(self):
        """controls: 05-07 05-08"""
        q, s = self.w.quote("ab" * 16)
        self.assertTrue(self.vq(q, s, "ab" * 16).ok)
        pol = attestation.AttestationPolicy(baselines=self.w.att_policy.baselines, min_firmware="2.0.0",
                                            revoked_firmware={"2.1.0"})
        self.assertEqual(self.vq(q, s, "ab" * 16, policy=pol).code, "E_ATT_FIRMWARE_REVOKED")
        pol = attestation.AttestationPolicy(baselines=self.w.att_policy.baselines, min_firmware="2.0.0",
                                            revoked_attestation_keys={"ak-node-1"})
        self.assertEqual(self.vq(q, s, "ab" * 16, policy=pol).code, "E_ATT_KEY_REVOKED")

    def test_node_ids_hashed_in_logs(self):
        """controls: 05-09 27-09"""
        self.w.svc.log.log("info", "x", node="node-1", artifact=art(1))
        self.assertNotIn("node-1", self.w.svc.log.sink[-1])


class TimeTest(unittest.TestCase):
    def test_sources_confidence_and_skew(self):
        """controls: 06-01 06-02 06-04 06-09"""
        a, b = [T0], [T0 + 2]
        c = timepolicy.TrustedClock([timepolicy.fixed_source(a, "nts-a"), timepolicy.fixed_source(b, "ptp", timepolicy.MEDIUM, "ptp")],
                                    monotonic=lambda: 0.0)
        r = c.now()
        self.assertEqual((r.confidence, r.source), ("high", "nts-a"))
        b[0] = T0 + 100
        self.assertEqual(c.now().confidence, "low")
        with self.assertRaises(timepolicy.TimeError_):
            c.require()
        self.assertEqual(c.metrics["freshness_rejections"], 1)

    def test_rollback_and_forward_jump_detection(self):
        """controls: 06-05 06-10"""
        v, mono = [T0], [0.0]
        c = timepolicy.TrustedClock([timepolicy.fixed_source(v)], monotonic=lambda: mono[0])
        c.now()
        mono[0] = 10.0
        v[0] = T0 - 100
        with self.assertRaises(timepolicy.TimeError_) as cm:
            c.now()
        self.assertEqual(cm.exception.code, "E_TIME_ROLLBACK")
        c2 = timepolicy.TrustedClock([timepolicy.fixed_source([T0])], monotonic=lambda: 0.0)
        c2.now()
        c2.sources[0] = timepolicy.fixed_source([T0 + 10_000])
        with self.assertRaises(timepolicy.TimeError_):
            c2.now()

    def test_monotonic_holdover_and_offline_grace(self):
        """controls: 06-03 06-06 06-08"""
        v, mono = [T0], [0.0]
        src = timepolicy.TimeSource("n", "nts", lambda: v[0], "high", 1)
        c = timepolicy.TrustedClock([src], monotonic=lambda: mono[0])
        c.now()
        v[0] = None
        mono[0] = 120.0
        r = c.now()
        self.assertEqual((r.source, r.wall, r.confidence), ("holdover", T0 + 120, "low"))
        mono[0] = 120.0 + 7200
        self.assertEqual(c.now().confidence, "none")
        self.assertEqual(timepolicy.effective_expiry(T0, 500, offline_grace_s=10_000), T0 + 500)
        self.assertEqual(timepolicy.effective_expiry(T0, 500, eol_at=T0 + 100), T0 + 100)

    def test_times_persisted_separately(self):
        """controls: 06-07"""
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence(observed_at=T0 - 30))
        e = w.store.events()[-1]
        self.assertTrue({"observed_at", "signed_at", "ingested_at"} <= set(e))
        self.assertEqual((e["observed_at"], e["ingested_at"]), (T0 - 30, T0))
        d = w.svc.certify(w.reader(), w.key_for(r))
        self.assertEqual(d["evaluated_at"], T0)

    def test_untrusted_time_blocks_decisions(self):
        """controls: 06-04 15-07 38-05"""
        w = World()
        w.clock.sources[0] = timepolicy.TimeSource("dead", "nts", lambda: None, "high", 1)
        w.clock._last = None
        with self.assertRaises(ServiceError) as cm:
            w.svc.certify(w.reader(), w.key_for({"profile_id": "profile:x"}))
        self.assertEqual(cm.exception.category, "dependency")
        self.assertFalse(w.svc.readiness()["ready"])


class AuthnTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.a = self.w.authn

    def test_valid_token_and_typed_principal(self):
        """controls: 07-01 07-02 07-03"""
        p = self.a.authenticate(self.w.producer(), now=T0)
        self.assertEqual((p.subject, p.ptype, p.issuer), ("producer-a", "producer", "idp"))

    def test_expired_wrong_audience_replay_revoked(self):
        """controls: 07-03 07-04 07-10 36-01"""
        t = self.w.producer()
        with self.assertRaises(authn.AuthError) as cm:
            self.a.authenticate(t, now=T0 + 10_000)
        self.assertEqual(cm.exception.code, "E_AUTH_EXPIRED")
        self.a.authenticate(t, now=T0)
        with self.assertRaises(authn.AuthError) as cm:
            self.a.authenticate(t, now=T0)
        self.assertEqual(cm.exception.code, "E_AUTH_REPLAY")
        other = authn.Authenticator(self.w.trust, audience="staging", issuers={"idp": set(authn.PRINCIPAL_TYPES)})
        other.update_revocations(set(), set(), T0)
        with self.assertRaises(authn.AuthError) as cm:
            other.authenticate(self.w.producer(), now=T0)
        self.assertEqual(cm.exception.code, "E_AUTH_AUDIENCE")
        t2 = self.w.producer("producer-b")
        self.a.update_revocations(set(), {"producer-b"}, T0)
        with self.assertRaises(authn.AuthError) as cm:
            self.a.authenticate(t2, now=T0)
        self.assertEqual(cm.exception.code, "E_AUTH_REVOKED")

    def test_stale_revocation_list_fails_closed(self):
        """controls: 07-04 36-08"""
        self.a.revocation_list_at = T0 - 10_000
        with self.assertRaises(authn.AuthError) as cm:
            self.a.authenticate(self.w.producer(), now=T0)
        self.assertEqual(cm.exception.code, "E_AUTH_REVOCATION_STALE")

    def test_throttle_and_no_enumeration_detail(self):
        """controls: 07-05"""
        t = self.w.producer()
        for _ in range(5):
            with self.assertRaises(authn.AuthError) as cm:
                self.a.authenticate(t, now=T0 + 10_000)
            self.assertEqual(str(cm.exception), cm.exception.code)
        with self.assertRaises(authn.AuthError) as cm:
            self.a.authenticate(self.w.producer(), now=T0)
        self.assertEqual(cm.exception.code, "E_AUTH_THROTTLED")

    def test_channel_binding_and_node_attestation(self):
        """controls: 07-06 14-07 36-02"""
        t = self.w.token("svc", "service", ["certify"], cnf="f" * 64)
        with self.assertRaises(authn.AuthError) as cm:
            self.a.authenticate(t, now=T0, channel_binding="e" * 64)
        self.assertEqual(cm.exception.code, "E_AUTH_BINDING")
        n = self.w.token("node-1", "node", ["certify"], attestation_digest="sha256:" + "1" * 64)
        with self.assertRaises(authn.AuthError) as cm:
            self.a.authenticate(n, now=T0)
        self.assertEqual(cm.exception.code, "E_AUTH_ATTESTATION_REQUIRED")
        n = self.w.token("node-1", "node", ["certify"], attestation_digest="sha256:" + "1" * 64)
        self.assertEqual(self.a.authenticate(n, now=T0, attestation_verified="sha256:" + "1" * 64).ptype, "node")

    def test_breakglass_requires_incident_and_other_approver(self):
        """controls: 07-07 08-08"""
        bad = self.w.token("bob", "breakglass", [], breakglass={"incident": "INC-1", "approver": "bob"})
        with self.assertRaises(authn.AuthError):
            self.a.authenticate(bad, now=T0)
        ok = self.w.token("bob", "breakglass", [], breakglass={"incident": "INC-1", "approver": "carol"})
        p = self.a.authenticate(ok, now=T0)
        z = self.w.authz
        self.assertTrue(z.decide(p, "revocation.create", PART).allowed)
        self.assertEqual(z.decide(p, "policy.update", PART).code, "E_AUTHZ_BREAKGLASS_SCOPE")
        self.assertTrue(p.as_audit()["breakglass"])

    def test_delegation_chain_propagates(self):
        """controls: 07-08"""
        t = self.w.token("scheduler", "service", ["certify"], delegated_by=("alice",))
        p = self.a.authenticate(t, now=T0)
        self.assertEqual(p.as_audit()["delegated_by"], ["alice"])

    def test_forged_token_signature_and_lifetime(self):
        """controls: 07-10 36-03"""
        t = self.w.producer()
        head, sig = t.split(".")
        claims = json.loads(signing.b64d(head) if len(head) < 256 else authn.b64d_long(head))
        claims["sub"] = "admin"
        forged = signing.b64e(canonical_bytes(claims)) + "." + sig
        with self.assertRaises(authn.AuthError) as cm:
            self.a.authenticate(forged, now=T0)
        self.assertEqual(cm.exception.code, "E_AUTH_SIGNATURE")
        with self.assertRaises(authn.AuthError):
            self.a.authenticate("x" * 5000, now=T0)

    def test_secrets_not_in_logs(self):
        """controls: 07-09 27-05"""
        rec = self.w.svc.log.log("info", "auth", token="eyJsecret", authorization="Bearer x", value="ok")
        line = self.w.svc.log.sink[-1]
        self.assertNotIn("eyJsecret", line)
        self.assertNotIn("Bearer x", line)
        self.assertEqual(rec["fields"]["value"], "ok")


class AuthzTest(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.z = self.w.authz

    def p(self, sub, ptype, scopes, parts=(PART,)):
        return authn.Principal(sub, ptype, "idp", frozenset(scopes), frozenset(parts), "t")

    def test_default_deny_and_explicit_permissions(self):
        """controls: 08-01 08-02 08-03 08-04"""
        prod = self.p("pa", "producer", ["evidence.submit"])
        self.assertTrue(self.z.decide(prod, "evidence.submit", PART).allowed)
        self.assertEqual(self.z.decide(prod, "lifecycle.mutate", PART).code, "E_AUTHZ_SCOPE")
        weird = self.p("pa", "producer", ["lifecycle.mutate"])
        self.assertEqual(self.z.decide(weird, "lifecycle.mutate", PART).code, "E_AUTHZ_DEFAULT_DENY")
        self.assertEqual(self.z.decide(prod, "made.up", PART).code, "E_AUTHZ_UNKNOWN_ACTION")

    def test_horizontal_site_escape(self):
        """controls: 08-10 25-09 36-07"""
        prod = self.p("pa", "producer", ["evidence.submit"], parts=(PART,))
        self.assertEqual(self.z.decide(prod, "evidence.submit", PART2).code, "E_AUTHZ_PARTITION")
        self.assertEqual(self.z.decide(prod, "evidence.submit", "acme/prod/edge-10").code, "E_AUTHZ_PARTITION")

    def test_separation_of_duties(self):
        """controls: 08-05 20-05"""
        alice = self.p("alice", "user", ["lifecycle.reactivate"], ("acme/prod/*",))
        bob = self.p("bob", "user", ["lifecycle.reactivate"], ("acme/prod/*",))
        self.assertEqual(self.z.decide(alice, "lifecycle.reactivate", PART).code, "E_AUTHZ_SOD")
        self.assertEqual(self.z.decide(alice, "lifecycle.reactivate", PART, second_approver=alice).code, "E_AUTHZ_SOD")
        self.assertTrue(self.z.decide(alice, "lifecycle.reactivate", PART, second_approver=bob).allowed)

    def test_policy_versioning_validation_and_rollback(self):
        """controls: 08-07 08-09"""
        bad = authz.PolicyBundle("authz:bad", [authz.Rule("w", "allow", frozenset({"*"}), frozenset({"user"})),
                                               authz.Rule("sod", "allow", frozenset({"policy.update"}), frozenset({"user"}))])
        probs = bad.validate()
        self.assertTrue(any("wildcard" in p for p in probs) and any("separation" in p for p in probs))
        with self.assertRaises(authz.AuthzError):
            self.z.activate(bad)
        good2 = authz.PolicyBundle("authz:2", list(self.z.bundle.rules) + [authz.Rule("deny-pa", "deny", frozenset({"evidence.submit"}), frozenset({"producer"}), subjects=frozenset({"pa"}))])
        self.z.activate(good2)
        prod = self.p("pa", "producer", ["evidence.submit"])
        d = self.z.decide(prod, "evidence.submit", PART)
        self.assertEqual((d.code, d.policy_revision), ("E_AUTHZ_DENIED", "authz:2"))  # deny overrides
        self.z.rollback()
        self.assertTrue(self.z.decide(prod, "evidence.submit", PART).allowed)
        cov = authz.coverage_report(self.z.bundle)
        self.assertIn("policy.update", cov["never_allowed"])

    def test_entry_points_enforce_authorization(self):
        """controls: 08-04 08-06 36-04"""
        w = self.w
        with self.assertRaises(ServiceError) as cm:
            w.svc.revoke(w.producer(), subject_type="artifact", subject_id=art(1), partition=PART, reason="x", severity="low")
        self.assertEqual(cm.exception.category, "authz")
        with self.assertRaises(ServiceError):
            w.svc.lifecycle(w.reader(), partition=PART, runtime="wasmtime@21.0.0", state="end-of-life", effective_at=T0,
                            reason="x", source="y")


if __name__ == "__main__":
    unittest.main()
