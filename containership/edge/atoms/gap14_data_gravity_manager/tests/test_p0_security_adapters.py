"""P0-02..P0-08: estate adapters, authN/Z, tenant identity -- negative paths first."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fixtures.estate import Estate  # noqa: E402

from gap14_data_gravity_manager.engine import GravityDecisionError  # noqa: E402
from gap14_data_gravity_manager.errors import G14Error  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.e = Estate()

    def assertCode(self, code, fn, *a, **kw):
        with self.assertRaises(GravityDecisionError) as ctx:
            fn(*a, **kw)
        self.assertEqual(ctx.exception.code, code, ctx.exception)
        return ctx.exception


class PolicyAdapterTest(Base):  # G14-P0-02
    def test_signed_allow_and_deny_fixtures(self):
        d = self.e.decide(name="customers", size=1, cls="pii")
        self.assertEqual(d["recommendation"]["direction"], "move-compute")
        self.assertEqual(d["recommendation"]["elimination_details"][0]["code"], "RESIDENCY_FORBIDDEN")
        pol = d["provenance"]["inputs"]["policy"]
        self.assertTrue(pol["dub"]["allow"])
        self.assertFalse(pol["ams"]["allow"])
        self.assertEqual(d["provenance"]["obligations"], {"encryption_domain": "eu-kms"})

    def test_tampered_verdict_rejected(self):
        self.e.policy.tamper = True
        self.assertCode("G14_SIGNATURE_INVALID", self.e.decide)

    def test_verdict_bound_to_other_request_rejected(self):
        self.e.policy.rebind = True
        self.assertCode("G14_BINDING_MISMATCH", self.e.decide)

    def test_stale_verdict_refused(self):
        self.e.policy.stale_by = 301
        self.assertCode("G14_STALE_INPUT", self.e.decide)

    def test_future_dated_verdict_refused(self):
        self.e.policy.stale_by = -60
        self.assertCode("G14_CLOCK_SKEW", self.e.decide)

    def test_policy_version_rollback_refused(self):
        self.e.policy.version = 5
        self.e.decide()
        self.e.policy.version = 4
        self.assertCode("G14_VERSION_ROLLBACK", self.e.decide)

    def test_outage_is_fail_closed_no_decision_emitted(self):
        self.e.policy.outage = True
        before = len(self.e.audit.records)
        self.assertCode("G14_DEPENDENCY_UNAVAILABLE", self.e.decide)
        issued = [r for r in self.e.audit.records[before:] if r["event"] == "decision.issued"]
        self.assertEqual(issued, [])

    def test_unknown_issuer_key_rejected(self):
        self.e.policy.kid = "k-gap03"  # valid key, wrong issuer for GAP-13
        self.assertCode("G14_UNKNOWN_ISSUER", self.e.decide)

    def test_revoked_key_rejected(self):
        self.e.keys.revoke("k-gap13")
        self.assertCode("G14_UNKNOWN_ISSUER", self.e.decide)


class TopologyAdapterTest(Base):  # G14-P0-03
    def test_asymmetric_egress_used(self):
        self.e.topology.egress[("dub", "ams")] = 0.01
        d = self.e.decide(size=500)
        self.assertEqual(d["recommendation"]["direction"], "move-data")
        self.assertAlmostEqual(d["recommendation"]["cost"], 5.0)

    def test_missing_route_fails_closed(self):
        del self.e.topology.routes[("dub", "ams")]
        self.assertCode("PK_GRAVITY_COST_MODEL_ERROR", self.e.decide, size=2)

    def test_unavailable_route_eliminates_option(self):
        self.e.topology.unavailable.add(("dub", "ams"))
        d = self.e.decide(size=2)
        self.assertEqual(d["recommendation"]["direction"], "move-compute")
        self.assertIn("ROUTE_UNAVAILABLE", [x["code"] for x in d["recommendation"]["elimination_details"]])

    def test_stale_topology_refused_in_production(self):
        self.e.topology.stale_by = 601
        self.assertCode("G14_STALE_INPUT", self.e.decide)

    def test_snapshot_identity_in_provenance(self):
        self.e.topology.version = 7
        d = self.e.decide()
        ref = d["provenance"]["inputs"]["topology"]
        self.assertEqual({k: ref[k] for k in ("snapshot_id", "version", "age_s")}, {"snapshot_id": "topo-7", "version": 7, "age_s": 0.0})
        self.assertRegex(ref["body_digest"], "^sha256:[0-9a-f]{64}$")


class ReplicationAdapterTest(Base):  # G14-P0-04
    def test_unconverged_blocks_move_data(self):
        self.e.replication.unconverged.add("lake")
        self.e.placement.sites["dub"]["available"] = False
        self.assertCode("PK_GRAVITY_NO_LEGAL_OPTION", self.e.decide, size=2)

    def test_proof_for_other_dataset_rejected(self):
        self.e.replication.wrong_dataset = True
        self.assertCode("G14_BINDING_MISMATCH", self.e.decide)

    def test_proof_ttl_is_short(self):
        self.e.replication.stale_by = 61
        self.assertCode("G14_STALE_INPUT", self.e.decide)


class PlacementAdapterTest(Base):  # G14-P0-05 / P2-35 / P2-36
    def test_architecture_incompatibility_eliminates(self):
        d = self.e.decide(size=2, requirements={"architecture": "riscv64"})
        # neither site supports riscv64 for move-compute; move-data target ams also can't run it,
        # but move-data only moves data -- compute already sits at ams by request.
        codes = [x["code"] for x in d["recommendation"]["elimination_details"]]
        self.assertIn("COMPUTE_INCOMPATIBLE", codes)

    def test_quota_blocks_move_data(self):
        self.e.placement.sites["ams"]["quota_remaining_gb"] = 1
        d = self.e.decide(size=2)
        self.assertEqual(d["recommendation"]["direction"], "move-compute")
        self.assertIn("QUOTA_EXCEEDED", [x["code"] for x in d["recommendation"]["elimination_details"]])

    def test_gpu_requirement(self):
        d = self.e.decide(site="fra", size=5000, compute="ams", requirements={"gpu": 2})
        self.assertEqual(d["recommendation"]["direction"], "move-compute")
        self.assertEqual(d["recommendation"]["to"], "fra")


class AuthTest(Base):  # G14-P0-07
    def test_missing_token(self):
        self.assertCode("G14_UNAUTHENTICATED", self.e.service.decide, self.e.request(), None)

    def test_expired_token(self):
        tok = self.e.token(ttl=10)
        self.e.clock.advance(11)
        self.assertCode("G14_UNAUTHENTICATED", self.e.service.decide, self.e.request(), tok)

    def test_forged_claims(self):
        tok = self.e.token(tenants=("t-acme",))
        tok["claims"]["tenants"] = ["*"]
        self.assertCode("G14_SIGNATURE_INVALID", self.e.service.decide, self.e.request(tenant="t-other"), tok)

    def test_missing_scope(self):
        tok = self.e.token(scopes=("gravity:explain",))
        self.assertCode("G14_FORBIDDEN", self.e.service.decide, self.e.request(), tok)

    def test_wrong_tenant(self):
        self.assertCode("G14_FORBIDDEN", self.e.service.decide, self.e.request(tenant="t-other"), self.e.token())

    def test_wrong_audience_token(self):
        from gap14_data_gravity_manager.identity import Authenticator
        other = Authenticator(self.e.keys, audience="some.other.service")
        tok = other.mint(subject="svc", tenants=["t-acme"], scopes=["gravity:recommend"], kid="k-id", now=self.e.clock.now())
        self.assertCode("G14_UNAUTHENTICATED", self.e.service.decide, self.e.request(), tok)

    def test_unauthenticated_request_is_not_parsed(self):
        self.assertCode("G14_UNAUTHENTICATED", self.e.service.decide, {"garbage": True}, None)

    def test_revoked_audit_key_fails_closed(self):
        self.e.keys.revoke("k-audit")
        self.assertCode("G14_AUDIT_UNAVAILABLE", self.e.decide)

    def test_capacity_vs_compatibility_codes(self):
        self.e.placement.sites["dub"]["free_cpu"] = 0
        d = self.e.decide(size=2)
        self.assertIn("COMPUTE_UNAVAILABLE", [x["code"] for x in d["recommendation"]["elimination_details"]])

    def test_token_lifetime_bounded(self):
        tok = self.e.token(ttl=7200)
        self.assertCode("G14_UNAUTHENTICATED", self.e.service.decide, self.e.request(), tok)


class TenantIdentityTest(Base):  # G14-P0-08
    def test_cross_tenant_dataset_refused(self):
        tok = self.e.token(tenants=("t-acme", "t-other"))
        self.assertCode("G14_CROSS_TENANT", self.e.service.decide, self.e.request(dataset_tenant="t-other"), tok)

    def test_identity_carried_to_provenance_and_audit(self):
        d = self.e.decide()
        self.assertEqual(d["provenance"]["identity"]["tenant_id"], "t-acme")
        self.assertEqual(d["provenance"]["identity"]["workload_id"], "wl-etl")
        rec = [r for r in self.e.audit.records if r["event"] == "decision.issued"][-1]
        self.assertEqual(rec["payload"]["tenant_id"], "t-acme")

    def test_replayed_request_id_refused(self):
        r = self.e.request()
        self.e.service.decide(r, self.e.token())
        self.assertCode("G14_REPLAY", self.e.service.decide, r, self.e.token())

    def test_same_request_id_other_tenant_is_not_a_replay(self):
        tok = self.e.token(tenants=("t-acme", "t-b"))
        r = self.e.request()
        self.e.service.decide(r, tok)
        r2 = self.e.request(tenant="t-b")
        r2["request_id"] = r["request_id"]
        self.e.service.decide(r2, tok)



class TopologyDomainTest(Base):  # P0-03 A07 / E03
    def test_nan_zero_negative_multiplier_rejected(self):
        for bad in (float("nan"), 0.0, -1.0):
            with self.subTest(bad=bad):
                e = Estate()
                e.topology.routes[("dub", "ams")] = bad
                with self.assertRaises(GravityDecisionError) as ctx:
                    e.decide(size=2)
                self.assertEqual(ctx.exception.code, "G14_INVALID_REQUEST")

    def test_audit_records_carry_decision_id_and_key_metadata(self):  # P0-10 A07
        d = self.e.decide()
        rec = [r for r in self.e.audit.records if r["event"] == "decision.issued"][-1]
        self.assertEqual(rec["payload"]["decision_id"], d["provenance"]["decision_id"])
        self.assertEqual((rec["mac"]["alg"], rec["mac"]["kid"]), ("HS256", "k-audit"))
        self.assertEqual(rec["seq"], d["audit"]["seq"])


class SchemaVersionTest(Base):  # E05 for P0-02..06: current accepted (all other tests), incompatible rejected
    def _swap(self, fake, new_schema):
        orig = fake._sign

        def sign(body):
            body = {**body, "schema": new_schema}
            return orig(body)
        fake._sign = sign

    def test_incompatible_schema_versions_rejected(self):
        for dep, tag in (("policy", "PK_POLICY_VERDICT/2"), ("topology", "PK_TOPOLOGY_SNAPSHOT/2"),
                         ("replication", "PK_CONVERGENCE_PROOF/2"), ("placement", "PK_PLACEMENT_SNAPSHOT/2")):
            with self.subTest(dep=dep):
                e = Estate()
                self._swap(getattr(e, dep), tag)
                with self.assertRaises(GravityDecisionError) as ctx:
                    e.decide()
                self.assertEqual(ctx.exception.code, "G14_INVALID_REQUEST")

    def test_incompatible_ack_version_rejected(self):
        e = Estate()
        d = e.decide(size=2)
        self._swap(e.dataplane, "PK_DATA_MOVE_ACK/2")
        with self.assertRaises(GravityDecisionError) as ctx:
            e.service.handoff(d, e.token())
        self.assertEqual(ctx.exception.code, "G14_BINDING_MISMATCH")


if __name__ == "__main__":
    unittest.main()
