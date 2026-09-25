"""Component 01: attestation policy engine (fixture trust root)."""
import unittest

from fixtures import SK_ROOT, PK_ROOT, seed
from gap09_unified_observability.components import ed25519
from gap09_unified_observability.components.attestation import AttestationPolicy, AttestationVerifier, make_evidence
from gap09_unified_observability.components.errors import DependencyUnavailable, Expired, Malformed, Revoked, Unverifiable

M = "a" * 64


def ev(**over):
    f = dict(device_id="dev-1", reporter="rep-a", tenant="t1", nonce="n" * 16 + over.pop("nsuffix", "0"),
             issued_at=990, measurements={"fw": M}, level="hardware", root_id="root-1")
    f.update(over)
    return make_evidence(over.pop("_sk", SK_ROOT), **f)


class TestAttestation(unittest.TestCase):
    def setUp(self):
        self.up = True
        self.v = AttestationVerifier(roots={"root-1": PK_ROOT},
                                     policy=AttestationPolicy(version="p1", approved_measurements={"fw": {M}}, freshness_window=60),
                                     available=lambda: self.up)

    def test_positive_and_decision_record(self):
        r = self.v.verify_evidence(ev(), reporter="rep-a", now=1000)
        self.assertEqual((r.level, r.device_id, r.policy_version), ("hardware", "dev-1", "p1"))
        d = self.v.decisions[-1]
        for k in ("evidence_sha256", "root_id", "policy_version", "outcome"):
            self.assertIn(k, d)

    def test_negative_matrix(self):
        cases = [
            (ev(nsuffix="1"), 1000, None),                      # first use OK
            (ev(nsuffix="1"), 1000, Unverifiable),              # replayed nonce
            (ev(issued_at=940, nsuffix="2"), 1000, Expired),    # stale (boundary: now-issued == window)
            (ev(issued_at=1001, nsuffix="3"), 1000, Expired),   # future
            (ev(measurements={"fw": "b" * 64}, nsuffix="4"), 1000, Unverifiable),  # altered measurement
            (ev(root_id="root-x", nsuffix="5"), 1000, Unverifiable),               # unknown root
            (ev(reporter="rep-b", nsuffix="6"), 1000, Unverifiable),               # wrong binding
        ]
        for e, now, exc in cases:
            if exc is None:
                self.v.verify_evidence(e, reporter="rep-a", now=now)
            else:
                with self.assertRaises(exc):
                    self.v.verify_evidence(e, reporter="rep-a", now=now)
        forged = ev(nsuffix="7")
        forged["level"] = "software"  # altered after endorsement
        with self.assertRaises(Unverifiable):
            self.v.verify_evidence(forged, reporter="rep-a", now=1000)
        other = make_evidence(seed("rogue"), device_id="dev-1", reporter="rep-a", tenant="t1", nonce="r" * 16,
                              issued_at=990, measurements={"fw": M}, level="hardware", root_id="root-1")
        with self.assertRaises(Unverifiable):
            self.v.verify_evidence(other, reporter="rep-a", now=1000)
        self.v.revoke_device("dev-1")
        with self.assertRaises(Revoked):
            self.v.verify_evidence(ev(nsuffix="8"), reporter="rep-a", now=1000)

    def test_malformed_and_partial(self):
        e = ev(nsuffix="9"); del e["nonce"]
        with self.assertRaises(Malformed):
            self.v.verify_evidence(e, reporter="rep-a", now=1000)
        with self.assertRaises(Malformed):
            self.v.verify_evidence("not-an-object", reporter="rep-a", now=1000)
        with self.assertRaises(Malformed):
            self.v.verify_evidence(ev(measurements={f"m{i}": M for i in range(40)}, nsuffix="a"), reporter="rep-a", now=1000)

    def test_dependency_outage_fails_closed(self):
        self.up = False
        with self.assertRaises(DependencyUnavailable):
            self.v.verify_evidence(ev(nsuffix="b"), reporter="rep-a", now=1000)

    def test_missing_required_measurement(self):
        v = AttestationVerifier(roots={"root-1": PK_ROOT}, policy=AttestationPolicy(
            version="p2", approved_measurements={"fw": {M}, "kernel": {M}}, freshness_window=60))
        with self.assertRaises(Unverifiable):
            v.verify_evidence(ev(nsuffix="c"), reporter="rep-a", now=1000)


if __name__ == "__main__":
    unittest.main()
