"""Identity, attestation, policy, replay and signature tests (MC043-MC056) plus
adversarial cases (MC035).  Every negative asserts a refusal, never an allow."""
import dataclasses
import unittest

import _fixtures as F
from inv29_hybrid_wasm_unikernel import admission as adm
from inv29_hybrid_wasm_unikernel.model import ImportUnsatisfied, LayerMissing


class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.kr = F.keyring()
        self.clock = F.Clock()
        self.a = F.admitter(self.kr, clock=self.clock)

    def refused(self, exc, req, admitter=None):
        with self.assertRaises(exc):
            (admitter or self.a).admit(req)

    def test_happy_path_signed_and_schema_valid(self):
        rec = self.a.admit(F.request(self.kr))
        self.assertEqual(rec["layer_count"], 2)
        self.assertEqual(rec["signature"]["alg"], "HMAC-SHA256")
        self.assertEqual({x["claim"] for x in rec["admission"]["attestations"]}, {"sealed", "hardened"})
        self.assertTrue(adm.verify_record(self.kr, rec, expected_key_id=F.SIGN_KEY, now=F.NOW)["verified"])

    # identity / tenant (MC043-MC046)
    def test_unknown_tenant_refused(self):
        self.refused(adm.PolicyDenied, F.request(self.kr, tenant="mallory"))

    def test_malformed_tenant_refused(self):
        for t in ("", "ACME", "a" * 64, "acme;drop", None):
            with self.subTest(t=t):
                self.refused(adm.IdentityInvalid, F.request(self.kr, tenant=t))

    # digest binding (MC047, MC048)
    def test_missing_or_non_sha256_digest_refused(self):
        req = F.request(self.kr)
        for field in ("module_digest", "host_digest"):
            for bad in ("", "md5:abcd", "sha256:XYZ", None):
                with self.subTest(field=field, bad=bad):
                    self.refused(adm.IdentityInvalid, dataclasses.replace(req, **{field: bad}, nonce=adm.new_nonce()))

    def test_attestation_for_other_artifact_refused(self):
        req = F.request(self.kr)
        other = adm.digest_bytes(b"tampered-module")
        self.refused(adm.AttestationInvalid, dataclasses.replace(req, module_digest=other))

    # sealed / hardened verification (MC049, MC050)
    def test_boolean_alone_is_not_trusted(self):
        self.refused(adm.AttestationInvalid, F.request(self.kr, atts=()))

    def test_forged_mac_refused(self):
        req = F.request(self.kr)
        forged = dict(req.attestations[0], mac="0" * 64)
        self.refused(adm.AttestationInvalid, dataclasses.replace(req, attestations=(forged, req.attestations[1])))

    def test_swapped_claims_refused(self):
        req = F.request(self.kr)
        relabelled = dict(req.attestations[0], claim="hardened")  # MAC no longer matches, and claim duplicates
        self.refused(adm.AttestationInvalid, dataclasses.replace(req, attestations=(relabelled, req.attestations[1])))

    def test_unknown_and_revoked_key_refused(self):
        kr2 = adm.Keyring({"rogue": b"R" * 32})
        md, hd = adm.digest_bytes(b"module-v1"), adm.digest_bytes(b"host-v1")
        rogue = (adm.issue_attestation(kr2, "rogue", "sealed", hd, now=F.NOW),
                 adm.issue_attestation(kr2, "rogue", "hardened", md, now=F.NOW))
        self.refused(adm.AttestationInvalid, F.request(self.kr, atts=rogue))
        pre_signed = F.request(self.kr)
        self.kr.revoke(F.ATTEST_KEY)
        self.refused(adm.AttestationInvalid, pre_signed)

    def test_stale_and_future_attestations_refused(self):
        self.refused(adm.AttestationInvalid, F.request(self.kr, now=F.NOW - 7200))
        self.refused(adm.AttestationInvalid, F.request(self.kr, now=F.NOW + 3600))

    def test_duplicate_claim_refused(self):
        req = F.request(self.kr)
        self.refused(adm.AttestationInvalid, dataclasses.replace(req, attestations=req.attestations + (req.attestations[0],)))

    def test_measured_boot_required_when_policy_says_so(self):
        a = F.admitter(self.kr, F.policy(require_measured_boot=True), clock=self.clock)
        self.refused(adm.AttestationInvalid, F.request(self.kr), a)
        req = F.request(self.kr)
        mb = adm.issue_attestation(self.kr, F.ATTEST_KEY, "measured-boot", req.host_digest, now=F.NOW)
        rec = a.admit(dataclasses.replace(req, attestations=req.attestations + (mb,)))
        self.assertEqual(len(rec["admission"]["attestations"]), 3)

    # capability policy (MC052-MC054)
    def test_denylisted_import_refused_even_if_exposed(self):
        self.refused(adm.PolicyDenied, F.request(self.kr, imports=("raw-socket",), exposes=("raw-socket",)))

    def test_host_exposing_denylisted_capability_refused(self):
        self.refused(adm.PolicyDenied, F.request(self.kr, imports=("clock",), exposes=("clock", "ptrace")))

    def test_cardinality_limit(self):
        a = F.admitter(self.kr, F.policy(max_imports_per_workload=2), clock=self.clock)
        caps = ("a", "b", "c")
        self.refused(adm.PolicyDenied, F.request(self.kr, imports=caps, exposes=caps), a)

    def test_capability_provenance(self):
        a = F.admitter(self.kr, F.policy(capability_issuers={"net-send": frozenset({"inv27"})}), clock=self.clock)
        self.refused(adm.PolicyDenied, F.request(self.kr), a)
        self.refused(adm.PolicyDenied, F.request(self.kr, capability_grants={"net-send": "someone-else"}), a)
        a.admit(F.request(self.kr, capability_grants={"net-send": "inv27"}))

    # existing invariants still hold through admission
    def test_layer_and_import_invariants_preserved(self):
        self.refused(LayerMissing, F.request(self.kr, sealed=False))
        self.refused(LayerMissing, F.request(self.kr, hardened=False))
        self.refused(ImportUnsatisfied, F.request(self.kr, imports=("fs-write",)))
        a = F.admitter(self.kr, F.policy(required_layers=3), clock=self.clock)
        self.refused(LayerMissing, F.request(self.kr), a)

    # replay / freshness / signature (MC055, MC056)
    def test_replay_refused(self):
        req = F.request(self.kr)
        self.a.admit(req)
        self.refused(adm.ReplayDetected, req)

    def test_bad_nonce_refused(self):
        for n in ("short", "x" * 200, "has space here!!"):
            with self.subTest(n=n):
                self.refused(adm.ReplayDetected, F.request(self.kr, nonce=n))

    def test_replay_cache_saturation_fails_closed(self):
        a = F.admitter(self.kr, clock=self.clock, replay=adm.ReplayGuard(capacity=2))
        a.admit(F.request(self.kr)); a.admit(F.request(self.kr))
        self.refused(adm.ReplayDetected, F.request(self.kr), a)

    def test_record_tamper_and_expiry_detected(self):
        rec = self.a.admit(F.request(self.kr))
        tampered = dict(rec, imports=rec["imports"] + ["net-recv"])
        with self.assertRaises(adm.AttestationInvalid):
            adm.verify_record(self.kr, tampered, expected_key_id=F.SIGN_KEY, now=F.NOW)
        with self.assertRaises(adm.ReplayDetected):
            adm.verify_record(self.kr, rec, expected_key_id=F.SIGN_KEY, now=F.NOW + 10_000)
        unsigned = {k: v for k, v in rec.items() if k != "signature"}
        with self.assertRaises(adm.AttestationInvalid):
            adm.verify_record(self.kr, unsigned, expected_key_id=F.SIGN_KEY, now=F.NOW)

    # operations
    def test_emergency_disable_and_policy_monotonicity(self):
        self.a.disable("incident-42")
        self.refused(adm.ComponentDisabled, F.request(self.kr))
        self.a.enable()
        self.a.admit(F.request(self.kr))
        self.a.set_policy(F.policy(generation=2))
        with self.assertRaises(adm.PolicyDenied):
            self.a.set_policy(F.policy(generation=1))
        self.a.rollback_policy(F.policy(generation=1))
        self.assertEqual(self.a.policy.generation, 1)

    def test_error_codes_stable(self):
        self.assertEqual(adm.error_code(LayerMissing("x")), "INV29-E-LAYER")
        self.assertEqual(adm.error_code(ImportUnsatisfied("x")), "INV29-E-IMPORT")
        self.assertEqual(adm.error_code(adm.ReplayDetected("x")), "INV29-E-REPLAY")
        self.assertEqual(adm.error_code(ValueError()), "INV29-E-INPUT")

    def test_keyring_never_leaks_material(self):
        self.assertNotIn("AAAA", repr(self.kr))
        with self.assertRaises(ValueError):
            adm.Keyring({"short": b"x" * 8})

    def test_decision_hook_failure_cannot_change_outcome(self):
        def boom(_):
            raise RuntimeError("telemetry down")
        a = F.admitter(self.kr, clock=self.clock, on_decision=boom)
        a.admit(F.request(self.kr))
        with self.assertRaises(adm.PolicyDenied):
            a.admit(F.request(self.kr, tenant="mallory"))


if __name__ == "__main__":
    unittest.main()
