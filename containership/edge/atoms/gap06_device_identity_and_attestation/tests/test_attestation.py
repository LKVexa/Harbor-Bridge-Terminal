"""Standalone security tests for GAP-06 attestation primitives (stdlib only)."""
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gap06_device_identity_and_attestation import (  # noqa: E402
    CHALLENGE_TTL,
    VERDICT_TTL,
    AttestationFailed,
    Attestor,
    ChallengeExpired,
    ClockRollback,
    Evidence,
    IdentityBindingFailed,
    InvalidEvidence,
    ReplayDetected,
    UnknownNode,
    UnissuedChallenge,
)


class AttestationSecurityTest(unittest.TestCase):
    def setUp(self):
        self.a = Attestor("prod", accepted={"m-fw-1", "m-kernel-1"}, measurement_set_version="set-v1")
        self.a.enrol("n1", hardware_identity="root:n1")
        self.a.enrol("n2", hardware_identity="root:n2")
        self.a.enrol("soft")

    def hardware_evidence(self, node="n1", now=0, measurements=("m-fw-1",), identity=None):
        if identity is None:
            identity = f"root:{node}"
        return Evidence(node, measurements, self.a.challenge(node, now), True, identity)

    def test_random_challenges_are_distinct_for_same_node_and_tick(self):
        values = {self.a.challenge("n1", 0) for _ in range(64)}
        self.assertEqual(len(values), 64)

    def test_unknown_node_cannot_receive_challenge(self):
        with self.assertRaises(UnknownNode):
            self.a.challenge("unknown", 0)

    def test_wrong_node_cannot_consume_challenge(self):
        nonce = self.a.challenge("n1", 0)
        with self.assertRaises(UnissuedChallenge):
            self.a.attest(Evidence("n2", ("m-fw-1",), nonce, True, "root:n2"), 0)
        verdict = self.a.attest(Evidence("n1", ("m-fw-1",), nonce, True, "root:n1"), 0)
        self.assertEqual(verdict.level, "hardware")

    def test_unissued_evidence_does_not_quarantine_or_replace_live_trust(self):
        self.a.attest(self.hardware_evidence(), 0)
        with self.assertRaises(UnissuedChallenge):
            self.a.attest(Evidence("n1", ("m-rootkit",), "not-issued", True, "root:n1"), 1)
        self.assertNotIn("n1", self.a.quarantined)
        self.assertEqual(self.a.level_of("n1", 1), "hardware")

    def test_valid_challenge_is_single_use(self):
        evidence = self.hardware_evidence()
        self.a.attest(evidence, 0)
        with self.assertRaises(ReplayDetected):
            self.a.attest(evidence, 1)

    def test_expired_challenge_is_rejected_and_not_reusable(self):
        nonce = self.a.challenge("n1", 0)
        ev = Evidence("n1", ("m-fw-1",), nonce, True, "root:n1")
        with self.assertRaises(ChallengeExpired):
            self.a.attest(ev, CHALLENGE_TTL)
        with self.assertRaises(ReplayDetected):
            self.a.attest(ev, CHALLENGE_TTL + 1)

    def test_unknown_measurement_quarantines_after_bound_challenge(self):
        nonce = self.a.challenge("n1", 0)
        with self.assertRaises(AttestationFailed):
            self.a.attest(Evidence("n1", ("m-rootkit",), nonce, True, "root:n1"), 0)
        self.assertEqual(self.a.level_of("n1", 0), "untrusted")
        self.assertIn("outside accepted set", self.a.quarantine_reasons["n1"])

    def test_empty_measurements_fail_closed(self):
        nonce = self.a.challenge("n1", 0)
        with self.assertRaises(AttestationFailed):
            self.a.attest(Evidence("n1", (), nonce, True, "root:n1"), 0)
        self.assertIn("n1", self.a.quarantined)

    def test_hardware_level_requires_matching_enrollment(self):
        nonce = self.a.challenge("n1", 0)
        with self.assertRaises(IdentityBindingFailed):
            self.a.attest(Evidence("n1", ("m-fw-1",), nonce, True, "root:other"), 0)
        self.assertIn("n1", self.a.quarantined)

    def test_software_node_cannot_self_assert_hardware(self):
        nonce = self.a.challenge("soft", 0)
        with self.assertRaises(IdentityBindingFailed):
            self.a.attest(Evidence("soft", ("m-fw-1",), nonce, True, "invented-root"), 0)

    def test_software_attestation_is_allowed_for_enrolled_node(self):
        nonce = self.a.challenge("soft", 0)
        verdict = self.a.attest(Evidence("soft", ("m-fw-1",), nonce, False), 0)
        self.assertEqual(verdict.level, "software")

    def test_verdict_expires_and_cannot_be_resurrected_by_time_rollback(self):
        self.a.attest(self.hardware_evidence(), 0)
        self.assertEqual(self.a.level_of("n1", VERDICT_TTL - 1), "hardware")
        self.assertEqual(self.a.level_of("n1", VERDICT_TTL), "untrusted")
        with self.assertRaises(ClockRollback):
            self.a.level_of("n1", 1)

    def test_verdict_carries_measurement_set_version_and_full_binding(self):
        verdict = self.a.attest(self.hardware_evidence(), 0)
        self.assertEqual(verdict.measurement_set_version, "set-v1")
        self.assertEqual(len(verdict.binding), 64)

    def test_canonical_measurements_required(self):
        nonce = self.a.challenge("n1", 0)
        with self.assertRaises(InvalidEvidence):
            self.a.attest(Evidence("n1", ("m-kernel-1", "m-fw-1"), nonce, True, "root:n1"), 0)
        # Structural rejection happens before challenge consumption; a corrected
        # canonical response can still use the challenge.
        verdict = self.a.attest(Evidence("n1", ("m-fw-1", "m-kernel-1"), nonce, True, "root:n1"), 0)
        self.assertEqual(verdict.level, "hardware")

    def test_duplicate_measurements_rejected(self):
        nonce = self.a.challenge("n1", 0)
        with self.assertRaises(InvalidEvidence):
            self.a.attest(Evidence("n1", ("m-fw-1", "m-fw-1"), nonce, True, "root:n1"), 0)

    def test_revoke_invalidates_verdict_and_outstanding_challenges(self):
        self.a.attest(self.hardware_evidence(), 0)
        nonce = self.a.challenge("n1", 1)
        self.a.revoke("n1", reason="compromise")
        self.assertEqual(self.a.level_of("n1", 1), "untrusted")
        with self.assertRaises(ReplayDetected):
            self.a.attest(Evidence("n1", ("m-fw-1",), nonce, True, "root:n1"), 1)

    def test_measurement_update_is_versioned(self):
        self.a.replace_accepted_measurements({"m-fw-2"}, version="set-v2")
        self.assertEqual(self.a.accepted, {"m-fw-2"})
        self.assertEqual(self.a.measurement_set_version, "set-v2")


if __name__ == "__main__":
    unittest.main()
