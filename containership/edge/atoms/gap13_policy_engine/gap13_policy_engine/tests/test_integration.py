"""G13-MC-038 integration tests against the adjacent-component adapter contracts
(docs/INTEGRATION_CONTRACTS.md).  These run against *reference* adapters that
implement each contract exactly; certification against the real GAP-07 / GAP-04 /
PLN-01 / PLN-06 / PLN-07 builds is tracked as BLOCKED in COMPONENT_STATUS.json
until those builds are available to the harness.
"""
import base64
import json
import pathlib
import unittest

import testkit as k
from gap13_policy_engine import errors as E
from gap13_policy_engine.distribution import DistributionController, FileFetcher

g = k.g


class Gap07TrustSource:
    """Reference GAP07_TRUST_SOURCE/1 adapter: serves a trust-store document, supports rotation/revocation."""
    def __init__(self):
        self.doc = json.loads((pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "trust_store.json").read_text())
        self.calls = 0

    def trust_store(self):
        self.calls += 1
        return g.TrustStore.from_dict(self.doc)

    def revoke(self, key_id):
        for kk in self.doc["keys"]:
            if kk["key_id"] == key_id:
                kk["revoked"] = True


class EnforcementPoint:
    """Reference EXT-02 enforcement point: anything but a well-formed allow is a deny."""
    def enforce(self, verdict_or_error):
        if not isinstance(verdict_or_error, dict) or verdict_or_error.get("schema") != "PK_POLICY_VERDICT/1":
            return "deny"
        return "allow" if verdict_or_error.get("effect") == "allow" else "deny"


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.src = Gap07TrustSource()
        self.svc, self.c = k.service(require_separation_of_duties=False,
                                     verifier=g.BundleVerifier(self.src, environment="prod"))
        self.admin = k.principal("alice", clock=self.c)
        self.app = k.principal("svc-a", ("service",), kind="service", clock=self.c)

    def test_gap07_signing_and_rotation(self):
        self.svc.load(self.admin, k.envelope(1))
        self.svc.load(self.admin, k.envelope(2, seed=k.SEED2, key_id="k2"))    # rotation overlap
        self.src.revoke("k1")
        with self.assertRaises(E.VerificationFailed):
            self.svc.load(self.admin, k.envelope(3))
        self.assertGreaterEqual(self.src.calls, 3)

    def test_gap04_disconnected_operation(self):
        d = k.tmpdir()
        svc, c = k.service(d, require_separation_of_duties=False, clock=self.c,
                           verifier=g.BundleVerifier(self.src, environment="prod"))
        p = pathlib.Path(d) / "published.json"
        p.write_bytes(k.envelope(1))
        dc = DistributionController(svc, FileFetcher(p), self.admin)
        self.assertEqual(dc.poll_once(), "applied")
        self.assertEqual(dc.poll_once(), "unchanged")        # idempotent
        p.unlink()                                           # disconnected
        self.assertEqual(dc.poll_once(), "unchanged")
        svc2, _ = k.service(d, clock=self.c, verifier=g.BundleVerifier(self.src, environment="prod"))
        self.assertTrue(svc2.restore_from_cache())           # offline restart from LKG cache
        self.assertEqual(svc2.evaluate(self.app, {"action": "read"})["effect"], "allow")

    def test_pln01_pln06_pln07_consume_verdicts_fail_safe(self):
        ep = EnforcementPoint()
        self.assertEqual(ep.enforce(None), "deny")
        try:
            self.svc.evaluate(self.app, {"action": "read"})
        except E.PolicyError as exc:
            self.assertEqual(ep.enforce(exc.to_dict()), "deny")    # outage/no policy -> deny
        self.svc.load(self.admin, k.envelope(1))
        v = self.svc.evaluate(self.app, {"action": "read"})
        self.assertEqual(ep.enforce(v), "allow")
        self.assertEqual(ep.enforce({**v, "effect": "ALLOW"}), "deny")
        self.assertEqual(ep.enforce({**v, "schema": "PK_POLICY_VERDICT/2"}), "deny")
        # PLN-06 residency is a protected attribute: must come from the trusted provider
        with self.assertRaises(E.AttributeRejected):
            self.svc.evaluate(self.app, {"action": "read", "residency": "eu"})

    def test_ext01_authoring_to_verdict_end_to_end(self):
        authored = [{"name": "ops-read", "effect": "allow", "scope": "estate", "match": {"action": "read", "resource_type": "log"}}]
        self.svc.load(self.admin, k.envelope(1, authored))
        v = self.svc.evaluate(self.app, {"action": "read", "resource_type": "log"})
        self.assertEqual((v["effect"], v["rule"], v["bundle"]["generation"]), ("allow", "ops-read", 1))


if __name__ == "__main__":
    unittest.main()
