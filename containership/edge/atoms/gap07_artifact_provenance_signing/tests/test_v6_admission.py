import hashlib
import io
import json
import os
import tempfile
import threading
import unittest

from gap07_artifact_provenance_signing import algorithms as algs
from gap07_artifact_provenance_signing.admission import make_bundle
from gap07_artifact_provenance_signing.audit_export import AppendOnlyFileSink, AuditExporter, verify_export
from gap07_artifact_provenance_signing.canonical import canonical_bytes
from gap07_artifact_provenance_signing.compromise import respond_to_compromise
from gap07_artifact_provenance_signing.controls import AdmissionLimiter
from gap07_artifact_provenance_signing.core import AuditLedger
from gap07_artifact_provenance_signing.errors import GapError
from gap07_artifact_provenance_signing.policy import evaluate
from gap07_artifact_provenance_signing.registry import (OCI_INDEX, OCI_MANIFEST, ContentStore, VerifiedContentStore, check_wasm,
                                                        discover_referrers, parse_reference, resolve_tag, verify_oci, verify_stream)
from gap07_artifact_provenance_signing.telemetry import Metrics, StructuredLogger, TraceContext, redact
from gap07_artifact_provenance_signing.tests.fixtures import NS, T0, Env, default_rules


class Admission(unittest.TestCase):
    def setUp(self):
        self.e = Env()

    def admit(self, **kw):
        return self.e.ctl.admit(self.e.full_request(**kw))

    def test_allow_records_complete_evidence(self):
        d = self.admit()
        self.assertEqual((d["outcome"], d["code"], d["runnable"]), ("allow", "ALLOW", True))
        self.assertEqual(d["trust_generation"], 1)
        self.assertEqual(d["policy"]["rule_id"], "prod-code")
        self.assertTrue(d["transparency"][0]["checkpoint_digest"])
        self.assertEqual(d["attestations"][0]["builder_id"], "https://ci.acme/builder@v1")
        self.assertIn("trusted_time", d["time"])
        self.assertTrue(self.e.audit.verify())

    def test_policy_driven_refusals(self):
        h = hashlib.sha256(b"artifact-bytes").hexdigest()
        cases = {
            "no transparency": (lambda e: dict(tlog=False), "TLOG_REQUIRED"),
            "no attestations": (lambda e: dict(attestations=[]), "ATTESTATION_PREDICATE"),
            "wrong builder": (lambda e: dict(attestations=[e.slsa(h, builder="https://rogue/ci"), e.sbom(h)]), "ATTESTATION_BUILDER"),
            "denied package": (lambda e: dict(attestations=[e.slsa(h), e.sbom(h, packages=("pkg:pypi/evil@1",))]), "SBOM_POLICY"),
            "critical vuln": (lambda e: dict(attestations=[e.slsa(h), e.sbom(h, vulns=("critical",))]), "SBOM_POLICY"),
            "no sbom": (lambda e: dict(attestations=[e.slsa(h)]), "SBOM_INVALID"),
        }
        for name, (kw, code) in cases.items():
            with self.subTest(name=name):
                e = Env()
                d = e.ctl.admit(e.full_request(**kw(e)))
                self.assertEqual((d["outcome"], d["code"]), ("deny", code))
                self.assertFalse(d["runnable"])

    def test_deny_rule_and_no_match(self):
        d = self.admit(kind="grant", attestations=[])
        self.assertEqual((d["outcome"], d["code"]), ("deny", "CERT_USAGE"))  # signer not certified for grants
        rules = default_rules() + [{"rule_id": "freeze", "priority": 500, "match": {"tenant": "acme", "environment": "prod", "kind": "oci-image"},
                                    "effect": "deny", "require": {}}]
        e = Env(rules=rules)
        self.assertEqual(e.ctl.admit(e.full_request(kind="oci-image", attestations=[]))["code"], "POLICY_DENY")
        d = self.admit(kind="bundle", attestations=[])
        self.assertEqual(d["code"], "POLICY_NO_MATCH")

    def test_conflicting_rules_deny(self):
        rules = default_rules()
        rules.append(dict(rules[1], rule_id="dup", require={"roles": ["release"], "threshold": 2}))
        e = Env(rules=rules)
        d = e.ctl.admit(e.full_request(kind="oci-image", attestations=[]))
        self.assertEqual(d["code"], "POLICY_CONFLICT")

    def test_threshold(self):
        rules = default_rules()
        rules[1]["require"]["threshold"] = 2
        e = Env(rules=rules)
        self.assertEqual(e.ctl.admit(e.full_request(kind="oci-image", attestations=[]))["code"], "THRESHOLD_UNMET")
        e.pki.add_signer("spiffe://acme/prod/reviewer", "k2", kinds=("oci-image",))
        e.state.swap(e.pki.trust(generation=2))
        req = e.full_request(kind="oci-image", attestations=[])
        req["bundle"]["signatures"].append(e.pki.signer("k2", "spiffe://acme/prod/reviewer").sign(b"artifact-bytes", "oci-image", now=T0))
        self.assertEqual(e.ctl.admit(req)["outcome"], "allow")

    def test_bad_signature_quarantines(self):
        req = self.e.full_request()
        req["bundle"]["signatures"][0]["sig"] = req["bundle"]["signatures"][0]["sig"][:-2] + ("AA" if not req["bundle"]["signatures"][0]["sig"].endswith("AA") else "BA")
        d = self.e.ctl.admit(req)
        self.assertEqual(d["outcome"], "deny")
        self.assertTrue(d.get("quarantined"))
        d2 = self.e.ctl.admit(self.e.full_request())
        self.assertEqual(d2["code"], "QUARANTINED")

    def test_tenant_confusion_and_mutable_reference(self):
        d = self.admit(site="site-b")
        self.assertEqual(d["code"], "TENANT_MISMATCH")
        req = self.e.full_request()
        req["digest"] = "registry.acme/app:latest"
        self.assertEqual(self.e.ctl.admit(req)["code"], "MUTABLE_REFERENCE")

    def test_dependency_loss_defers_never_allows(self):
        self.e.advance(8 * 86400)
        d = self.admit()
        self.assertEqual((d["outcome"], d["runnable"]), ("defer", False))
        self.assertIn(d["code"], {"TIME_UNTRUSTED", "TIME_STALE"})

    def test_internal_error_is_error_not_allow(self):
        self.e.ctl.policy.current = lambda now: (_ for _ in ()).throw(RuntimeError("boom"))
        d = self.admit()
        self.assertEqual((d["outcome"], d["code"], d["runnable"]), ("error", "INTERNAL_ERROR", False))

    def test_malformed_request(self):
        d = self.e.ctl.admit({"digest": 1})
        self.assertFalse(d["runnable"])
        d = self.e.ctl.admit("not a mapping")
        self.assertFalse(d["runnable"])

    def test_cache_invalidated_on_trust_change_and_revocation_applies(self):
        req = self.e.full_request()
        self.assertEqual(self.e.ctl.admit(req)["outcome"], "allow")
        self.assertTrue(self.e.ctl.admit(req).get("cache_hit"))
        self.e.state.swap(self.e.pki.trust(generation=2, revoked_kids=frozenset({self.e.pki.refs["k1"].kid})))
        d = self.e.ctl.admit(req)
        self.assertEqual(d["code"], "CERT_REVOKED")

    def test_overload_sheds_as_deny(self):
        self.e.ctl.limiter = AdmissionLimiter(max_concurrent=1, max_queue=0, rate_per_s=1000, burst=1000)
        d = self.admit()
        self.assertEqual((d["code"], d["runnable"]), ("OVERLOADED", False))
        self.e.ctl.limiter = AdmissionLimiter(rate_per_s=0.0, burst=1)
        self.assertEqual(self.admit()["outcome"], "allow")
        self.assertEqual(self.admit()["code"], "OVERLOADED")

    def test_break_glass_is_scoped_signed_single_use(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.e.ctl.cfg.replay_cache_path = os.path.join(tmp.name, "nonces.jsonl")
        from gap07_artifact_provenance_signing.controls import ReplayCache
        self.e.ctl._replay = ReplayCache(path=self.e.ctl.cfg.replay_cache_path)
        req = self.e.full_request(attestations=[], tlog=False)
        body = {"schema": "PK_BREAK_GLASS/1", "id": "bg-1", "digest": req["digest"], "kind": "code", "tenant": "acme", "site": "site-a",
                "environment": "prod", "approvers": ["alice", "bob"], "reason": "sev1 rollback", "issued_at": T0 - 5, "expires": T0 + 3600,
                "nonce": "n" * 32, "override_quarantine": False}
        # wrong kind / quarantined digest are refused even with a valid signed token
        wrong = dict(req, kind="grant", break_glass=self.e.cfg("break-glass", dict(body, nonce="w" * 32)))
        self.assertEqual(self.e.ctl.admit(wrong)["code"], "BREAK_GLASS_INVALID")
        self.e.ctl.quarantine.quarantine(req["digest"], "test", now=T0)
        req["break_glass"] = self.e.cfg("break-glass", dict(body, nonce="q" * 32))
        self.assertEqual(self.e.ctl.admit(req)["code"], "QUARANTINED")
        self.e.ctl.quarantine.release(req["digest"], approvers=["a", "b"], reason="test", now=T0)
        bg = self.e.cfg("break-glass", body)
        req["break_glass"] = bg
        d = self.e.ctl.admit(req)
        self.assertEqual((d["outcome"], d["code"], d["post_event_review_required"]), ("allow", "BREAK_GLASS", True))
        self.assertEqual(self.e.ctl.admit(req)["code"], "REPLAY")
        bad = dict(bg)
        bad["body"] = dict(bg["body"], approvers=["alice"])
        req["break_glass"] = bad
        self.assertEqual(self.e.ctl.admit(req)["code"], "TRUST_CORRUPT")

    def test_waiver_scoped_and_expiring(self):
        req = self.e.full_request(tlog=False)
        w = self.e.cfg("waiver", {"schema": "PK_WAIVER/1", "waiver_id": "w-1", "owner": "carol", "justification": "log outage", "controls": ["transparency"],
                                  "digest": req["digest"], "tenant": "acme", "environment": "prod", "issued_at": T0 - 5, "expires": T0 + 86400,
                                  "approvers": ["alice", "bob"], "compensating_controls": ["manual review"]})
        req["waivers"] = [w]
        d = self.e.ctl.admit(req)
        self.assertEqual(d["outcome"], "allow")
        self.assertEqual(d["policy"]["waivers_applied"], ["transparency"])
        w2 = self.e.cfg("waiver", dict(w["body"], controls=["signature"]))
        req["waivers"] = [w2]
        self.assertEqual(self.e.ctl.admit(req)["code"], "EXCEPTION_INVALID")

    def test_handoff_toctou(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = VerifiedContentStore(tmp)
            self.e.ctl.content = store
            payload = b"artifact-bytes"
            digest = "sha256:" + hashlib.sha256(payload).hexdigest()
            store.ingest(io.BytesIO(payload), digest)
            d = self.admit()
            self.assertEqual(self.e.ctl.handoff(d), payload)
            with open(os.path.join(tmp, digest.replace(":", "_")), "wb") as fh:
                fh.write(b"swapped!")
            with self.assertRaises(GapError) as cm:
                self.e.ctl.handoff(d)
            self.assertEqual(cm.exception.code, "TOCTOU")
            self.e.state.swap(self.e.pki.trust(generation=3))
            with self.assertRaises(GapError) as cm:
                self.e.ctl.handoff(d)
            self.assertEqual(cm.exception.code, "TRUST_STALE")

    def test_readiness(self):
        self.assertTrue(self.e.ctl.health.readiness()["ready"])
        self.e.advance(8 * 86400)
        self.assertFalse(self.e.ctl.health.readiness()["ready"])

    def test_metrics_and_decision_log(self):
        self.admit()
        self.admit(site="site-b")
        m = self.e.ctl.metrics
        self.assertEqual(m.get("gap07_admission_total", outcome="allow", code="ALLOW", kind="code"), 1)
        self.assertIn("gap07_admission_seconds_bucket", m.exposition())
        self.assertEqual(len(self.e.ctl.decisions), 2)


class ReviewRegressions(unittest.TestCase):
    """Regression tests for the adversarial review findings of this pass."""

    def test_forged_leaf_reusing_pooled_serial(self):
        e = Env()
        t = e.pki.trust()
        forged = dict(e.pki.certs[-1], subject="spiffe://acme/prod/ATTACKER")
        with self.assertRaises(GapError) as cm:
            t.validate_leaf(forged, T0, purpose="sign:code")
        self.assertEqual(cm.exception.code, "SIGNATURE_INVALID")

    def test_split_view_equal_or_smaller_checkpoint(self):
        from gap07_artifact_provenance_signing.tlog import LocalTransparencyLog, entry_bytes
        from gap07_artifact_provenance_signing.canonical import canonical_bytes as cb
        e = Env()
        self.assertEqual(e.ctl.admit(e.full_request())["outcome"], "allow")
        for i in range(3):
            e.log.append(b"filler-%d" % i)
        e.ctl._check_view(e.log.checkpoint(T0 + 1), e.log.prove_consistency(1, 4))
        fork = LocalTransparencyLog("log.acme", "log-k1", "ed25519", e.log._sign)
        payload = b"forked-artifact"
        h = hashlib.sha256(payload).hexdigest()
        sig = e.builder.sign(payload, "code", now=T0)
        ed = hashlib.sha256(cb(sig)).hexdigest()
        idx = fork.append(entry_bytes("code", h, ed))
        cp = fork.checkpoint(T0 + 2)
        tl = [{"envelope_digest": ed, "evidence": {"index": idx, "checkpoint": cp, "proof": fork.prove_inclusion(idx, cp["size"])}}]
        req = {"digest": "sha256:" + h, "kind": "code", "tenant": "acme", "site": "site-a", "environment": "prod",
               "bundle": make_bundle("sha256:" + h, "code", signatures=[sig], attestations=[e.slsa(h), e.sbom(h)], transparency=tl)}
        self.assertEqual(e.ctl.admit(req)["code"], "TLOG_ROLLBACK")

    def test_sbom_nested_and_qualified_purls(self):
        from gap07_artifact_provenance_signing.sbom import facts_from_predicate, normalize_purl
        bom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "components": [
            {"name": "app", "purl": "pkg:pypi/app@1", "components": [{"name": "evil", "purl": "pkg:PyPI/Evil@2?repository_url=x#sub"}]}]}
        self.assertIn("pkg:pypi/evil", facts_from_predicate("https://cyclonedx.org/bom", bom)["packages"])
        self.assertEqual(normalize_purl("pkg:npm/%40scope/Name@1.0?a=b"), "pkg:npm/%40scope/name")
        spdx = facts_from_predicate("https://spdx.dev/Document", {"spdxVersion": "SPDX-2.3", "packages": []})
        self.assertIsNone(spdx["open_vulnerability_severities"])

    def test_cache_respects_signature_age(self):
        e = Env()
        e.ctl.cfg.max_signature_age_s = 100
        req = e.full_request()
        self.assertEqual(e.ctl.admit(req)["outcome"], "allow")
        e.advance(250)
        self.assertEqual(e.ctl.admit(req)["code"], "SIGNATURE_EXPIRED")

    def test_name_constraints_segmentwise_and_dot_segments(self):
        from gap07_artifact_provenance_signing.trust import _within
        self.assertFalse(_within("spiffe://acme/prod-evil/x", "spiffe://acme/prod"))
        self.assertTrue(_within("spiffe://acme/prod/x", "spiffe://acme/prod"))
        e = Env()
        e.pki.add_signer("spiffe://acme/prod/../../evilcorp/x", "dots")
        with self.assertRaises(GapError) as cm:
            e.pki.trust()
        self.assertEqual(cm.exception.code, "ENVELOPE_MALFORMED")

    def test_dsse_subject_types(self):
        import json as _j
        from gap07_artifact_provenance_signing import dsse as D
        e = Env()
        st = D.statement([("app", "0" * 64)], D.SLSA_V1, {})
        st["subject"][0]["digest"]["sha256"] = 5
        env = D.make_envelope(canonical_bytes(st), [(e.pki.refs["k1"].kid, lambda m: e.pki.custody.sign(e.pki.refs["k1"], m, request_id="t"))])
        with self.assertRaises(GapError) as cm:
            D.verify_envelope(env, artifact_digest="0" * 64, trust=e.pki.trust(), now=T0, policy=D.AttestationPolicy())
        self.assertEqual(cm.exception.code, "ATTESTATION_SUBJECT")

    def test_policy_bundle_for_other_tenant_refused(self):
        rules = default_rules()
        e = Env()
        doc = e.cfg("policy-bundle", {"schema": "PK_POLICY_BUNDLE/1", "adapter_version": 1, "bundle_id": "other", "version": 2,
                                      "issued_at": T0 - 10, "expires": T0 + 10**6, "tenant": "globex", "rules": rules})
        e.policy.activate(doc, now=T0, actor="t")
        self.assertEqual(e.ctl.admit(e.full_request())["code"], "POLICY_INVALID")

    def test_break_glass_nonce_durable_across_controllers(self):
        from gap07_artifact_provenance_signing.admission import AdmissionConfig, AdmissionController
        e = Env()
        with tempfile.TemporaryDirectory() as tmp:
            cfg = AdmissionConfig(replay_cache_path=os.path.join(tmp, "nonces.jsonl"))
            mk = lambda: AdmissionController(trust_state=e.state, policy_store=e.policy, clock=e.clock, authorities=e.authorities, config=cfg)
            req = e.full_request(attestations=[], tlog=False)
            req["break_glass"] = e.cfg("break-glass", {"schema": "PK_BREAK_GLASS/1", "id": "bg", "digest": req["digest"], "kind": "code", "tenant": "acme",
                                                       "site": "site-a", "environment": "prod", "approvers": ["a", "b"], "reason": "r", "issued_at": T0 - 5,
                                                       "expires": T0 + 3600, "nonce": "z" * 32, "override_quarantine": False})
            self.assertEqual(mk().admit(req)["code"], "BREAK_GLASS")
            self.assertEqual(mk().admit(req)["code"], "REPLAY")

    def test_break_glass_refused_without_durable_nonce_store(self):
        e = Env()
        req = e.full_request(attestations=[], tlog=False)
        req["break_glass"] = e.cfg("break-glass", {"schema": "PK_BREAK_GLASS/1", "id": "bg", "digest": req["digest"], "kind": "code", "tenant": "acme",
                                                   "site": "site-a", "environment": "prod", "approvers": ["a", "b"], "reason": "r", "issued_at": T0 - 5,
                                                   "expires": T0 + 3600, "nonce": "y" * 32, "override_quarantine": False})
        self.assertEqual(e.ctl.admit(req)["code"], "BREAK_GLASS_INVALID")

    def test_custody_sign_enforces_key_policy_and_structures_defects(self):
        from gap07_artifact_provenance_signing.keys import KeyRef, ResilientCustody, SoftwareKeyCustody, CustodyPolicy
        sc = SoftwareKeyCustody()
        ref = KeyRef("software", "acme", "site-a", "prod", "dev", "1", "ed25519", protection_level="software")
        rc = ResilientCustody(sc, {ref.kid: sc.create(ref)})
        with self.assertRaises(GapError) as cm:
            rc.sign(ref, b"m")
        self.assertEqual(cm.exception.code, "KEY_POLICY_VIOLATION")

        class Broken:
            def metadata(self, ref):
                raise RuntimeError("sdk bug")
        rc2 = ResilientCustody(Broken(), {ref.kid: b"x"}, CustodyPolicy(breaker_threshold=1, backoff_s=0))
        with self.assertRaises(GapError) as cm:
            rc2.sign(ref, b"m")
        self.assertEqual(cm.exception.code, "KEY_UNAVAILABLE")
        with self.assertRaises(GapError) as cm:
            rc2.sign(ref, b"m")
        self.assertEqual(cm.exception.code, "CIRCUIT_OPEN")

    def test_handoff_missing_content_is_structured(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertRaises(GapError, VerifiedContentStore(tmp).open_verified, "sha256:" + "0" * 64)

    def test_audit_truncation_detectable_with_reference(self):
        led = AuditLedger()
        for i in range(5):
            led.append(f"e{i}")
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "a.jsonl")
            AppendOnlyFileSink(p).append_batch(led.events)
            lines = open(p, "rb").read().splitlines()[:2]
            open(p, "wb").write(b"\n".join(lines) + b"\n")
            self.assertEqual(verify_export(p)["unanchored_tail"], 2)
            self.assertRaises(GapError, verify_export, p, expected_head=led.head)
            self.assertRaises(GapError, verify_export, p, min_events=5)
            self.assertRaises(GapError, verify_export, p, require_anchored=True)

    def test_future_trust_generation_refused(self):
        e = Env()
        e.state.swap(e.pki.trust(generation=2, issued_at=T0 + 10**6))
        self.assertEqual(e.ctl.admit(e.full_request())["code"], "TRUST_CORRUPT")


class Compromise(unittest.TestCase):
    def test_blast_radius_quarantine_and_delta(self):
        e = Env()
        d = e.ctl.admit(e.full_request())
        self.assertEqual(d["outcome"], "allow")
        kid = e.pki.refs["k1"].kid
        res = respond_to_compromise(incident_id="inc-1", kid=kid, identity=None, compromised_since=T0 - 100, now=T0, namespace=NS,
                                    active_generation=1, decisions=e.ctl.decisions, quarantine=e.ctl.quarantine, audit=e.audit,
                                    authority=("cfg-1", "ed25519", e.auth_sign))
        self.assertEqual(len(res["evidence"]["affected"]), 1)
        self.assertTrue(res["delta"]["body"]["urgent"])
        self.assertEqual(e.ctl.admit(e.full_request())["code"], "QUARANTINED")


class Registry(unittest.TestCase):
    def setUp(self):
        self.s = ContentStore()
        self.layer = b"layer" * 1000
        self.cfg = b'{"architecture":"amd64"}'
        ld, cd = self.s.put(self.layer), self.s.put(self.cfg)
        self.man = canonical_bytes({"schemaVersion": 2, "mediaType": OCI_MANIFEST,
                                    "config": {"mediaType": "application/vnd.oci.image.config.v1+json", "digest": cd, "size": len(self.cfg)},
                                    "layers": [{"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip", "digest": ld, "size": len(self.layer)}]})
        self.md = self.s.put(self.man)
        self.idx = canonical_bytes({"schemaVersion": 2, "mediaType": OCI_INDEX, "manifests": [
            {"mediaType": OCI_MANIFEST, "digest": self.md, "size": len(self.man), "platform": {"os": "linux", "architecture": "amd64"}}]})
        self.id = self.s.put(self.idx)

    def test_manifest_and_index(self):
        self.assertEqual(verify_oci(self.s, self.md, OCI_MANIFEST, len(self.man)).blobs_verified, 3)
        v = verify_oci(self.s, self.id, OCI_INDEX, len(self.idx), platform="linux/amd64/")
        self.assertEqual((v.selected_digest, v.parent_index), (self.md, self.id))

    def test_substitution_partial_and_malformed(self):
        with self.assertRaises(GapError) as cm:
            verify_oci(self.s, self.md, OCI_MANIFEST, len(self.man) + 1)
        self.assertEqual(cm.exception.code, "REGISTRY_DIGEST_MISMATCH")
        with self.assertRaises(GapError):
            verify_oci(self.s, self.md, "application/x-unknown", len(self.man))
        self.s._blobs[self.md] = self.man.replace(b"amd64", b"arm64") if b"amd64" in self.man else self.man + b" "
        with self.assertRaises(GapError):
            verify_oci(self.s, self.md, OCI_MANIFEST, len(self.man))
        self.s.fail_reads = True
        with self.assertRaises(GapError) as cm:
            verify_oci(self.s, self.id, OCI_INDEX, len(self.idx))
        self.assertEqual(cm.exception.code, "REGISTRY_UNAVAILABLE")

    def test_tags_are_never_authoritative(self):
        with self.assertRaises(GapError) as cm:
            parse_reference("registry.acme/app:latest")
        self.assertEqual(cm.exception.code, "MUTABLE_REFERENCE")
        self.s.tag("registry.acme/app:latest", self.md)
        self.assertEqual(resolve_tag(self.s, "registry.acme/app:latest")["digest"], self.md)
        self.assertEqual(parse_reference(f"registry.acme/app@{self.md}")[2], self.md)

    def test_referrers_by_subject(self):
        sig_manifest = canonical_bytes({"schemaVersion": 2, "mediaType": OCI_MANIFEST, "artifactType": "application/vnd.gap07.signature.v3+json",
                                        "config": {"mediaType": "application/vnd.oci.empty.v1+json", "digest": self.s.put(b"{}"), "size": 2},
                                        "layers": [], "subject": {"mediaType": OCI_MANIFEST, "digest": self.md, "size": len(self.man)}})
        self.s.put(sig_manifest)
        refs = discover_referrers(self.s, self.md, "application/vnd.gap07.signature.v3+json")
        self.assertEqual(len(refs), 1)

    def test_stream_limits_and_wasm(self):
        data = b"x" * 5000
        d = "sha256:" + hashlib.sha256(data).hexdigest()
        self.assertEqual(verify_stream(io.BytesIO(data), d), 5000)
        with self.assertRaises(GapError):
            verify_stream(io.BytesIO(data), d, max_size=100)
        with self.assertRaises(GapError):
            verify_stream(io.BytesIO(data[:10]), d, expected_size=5000)
        self.assertEqual(check_wasm(b"\x00asm\x01\x00\x00\x00", "wasm-module"), "wasm-module:v1:l0")
        with self.assertRaises(GapError):
            check_wasm(b"\x00asm\x0d\x00\x01\x00", "wasm-module")
        self.assertTrue(check_wasm(b"\x00asm\x0d\x00\x01\x00", "wasm-component"))


class AuditExport(unittest.TestCase):
    def test_export_anchor_and_independent_verification(self):
        e = Env()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audit.jsonl")
            sink = AppendOnlyFileSink(path)
            ex = AuditExporter(e.audit, sink, anchor_log=e.log, anchor_every=1)
            e.ctl.admit(e.full_request())
            ex.export(now=T0)
            e.ctl.admit(e.full_request(site="site-b"))
            sink.available = False
            self.assertGreater(ex.export(now=T0)["spooled"], 0)
            self.assertFalse(ex.healthy)
            sink.available = True
            ex.export(now=T0)
            res = verify_export(path, log_keys=e.log_keys, now=T0)
            self.assertEqual(res["events"], len(e.audit.events))
            self.assertGreaterEqual(res["anchors"], 1)
            lines = open(path, "rb").read().splitlines()
            rec = json.loads(lines[1])
            rec["event"] = "tampered"
            lines[1] = canonical_bytes(rec)
            open(path, "wb").write(b"\n".join(lines) + b"\n")
            with self.assertRaises(GapError):
                verify_export(path)

    def test_sink_refuses_non_extending_batch(self):
        led = AuditLedger()
        led.append("a")
        led.append("b")
        with tempfile.TemporaryDirectory() as tmp:
            sink = AppendOnlyFileSink(os.path.join(tmp, "a.jsonl"))
            with self.assertRaises(GapError):
                sink.append_batch([led.events[1]])
            sink.append_batch(led.events)
            with self.assertRaises(GapError):
                sink.append_batch(led.events)  # duplicate batch

    def test_spool_exhaustion_is_reported(self):
        led = AuditLedger()
        for i in range(5):
            led.append(f"e{i}")
        with tempfile.TemporaryDirectory() as tmp:
            sink = AppendOnlyFileSink(os.path.join(tmp, "a.jsonl"))
            sink.available = False
            ex = AuditExporter(led, sink, spool_limit=3)
            with self.assertRaises(GapError) as cm:
                ex.export(now=0)
            self.assertEqual(cm.exception.code, "AUDIT_SPOOL_FULL")


class Telemetry(unittest.TestCase):
    def test_label_cardinality_and_redaction(self):
        m = Metrics()
        for i in range(100):
            m.inc("x", code=f"random-{i}")
        self.assertEqual(m.get("x", code="other"), 100)
        r = redact({"password": "p", "note": "-----BEGIN PRIVATE KEY-----abc", "digest": "abc", "blob": b"12345"})
        self.assertEqual(r, {"password": "[redacted]", "note": "[redacted]", "digest": "abc", "blob": "[bytes:5]"})
        buf = io.StringIO()
        StructuredLogger(buf).log("info", "x", TraceContext.from_traceparent("00-" + "a" * 32 + "-" + "b" * 16 + "-01"), token="t")
        rec = json.loads(buf.getvalue())
        self.assertEqual((rec["trace_id"], rec["token"]), ("a" * 32, "[redacted]"))


if __name__ == "__main__":
    unittest.main()
