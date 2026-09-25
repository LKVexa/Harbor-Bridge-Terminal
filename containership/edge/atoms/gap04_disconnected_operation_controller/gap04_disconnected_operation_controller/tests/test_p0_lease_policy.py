"""C01 signed lease envelope, C05 policy provenance, C06 revocation epochs,
C19 error model, canonical encoding. Test IDs: T-C01-*, T-C05-*, T-C06-*, T-C19-*."""
import json, unittest
from _util import T, Tmp, node, code, Gap04Error
from gap04_disconnected_operation_controller.runtime import canonical, crypto, trust as TR
from gap04_disconnected_operation_controller.runtime.errors import REGISTRY, to_error, ERROR_MODEL_VERSION
from gap04_disconnected_operation_controller.controller import LeaseExpired

NOW = 1_800_000_000


def verify(env, cp, **kw):
    pol = kw.pop("pol")
    args = dict(trust=cp.trust(), expected_scope=T.SCOPE, now=NOW + 5, min_authority_epoch=1,
                expected_policy_digest=TR.policy_digest(pol))
    args.update(kw)
    return TR.verify_lease(env, **args)


class LeaseEnvelope(unittest.TestCase):
    def setUp(self):
        self.cp = T.ControlPlane()
        self.pol = self.cp.policy()
        self.env = self.cp.lease(self.pol, NOW)

    def test_T_C01_positive(self):
        vl = verify(self.env, self.cp, pol=self.pol)
        self.assertEqual(vl.scope["site"], "site-a")
        av = vl.audit_view()
        self.assertNotIn("sig", json.dumps(av)); self.assertNotIn("nonce", av)

    def test_T_C01_canonical_bytes_roundtrip(self):
        raw = canonical.dumps(self.env)
        verify(raw, self.cp, pol=self.pol)
        noncanon = json.dumps(self.env, indent=1).encode()
        code(self, "GAP04-E0200", verify, noncanon, self.cp, pol=self.pol)

    def test_T_C01_duplicate_keys_rejected(self):
        raw = canonical.dumps(self.env).decode()
        dup = raw[:-1] + ',"alg":"Ed25519"}'
        code(self, "GAP04-E0200", verify, dup, self.cp, pol=self.pol)

    def test_T_C01_non_nfc_rejected(self):
        with self.assertRaises(canonical.CanonicalError):
            canonical.dumps({"a": "é"})

    def test_T_C01_forged_signature(self):
        e = dict(self.env); e["sig"] = crypto.b64e(b"\x00" * 64)
        code(self, "GAP04-E0201", verify, e, self.cp, pol=self.pol)

    def test_T_C01_modified_capabilities(self):
        e = dict(self.env); e["capabilities"] = ["restart"]
        code(self, "GAP04-E0201", verify, e, self.cp, pol=self.pol)

    def test_T_C01_wrong_site(self):
        e = self.cp.lease(self.pol, NOW, scope=dict(T.SCOPE, site="site-b"))
        code(self, "GAP04-E0204", verify, e, self.cp, pol=self.pol)

    def test_T_C01_every_scope_field_bound(self):
        for k in TR.SCOPE_KEYS:
            e = self.cp.lease(self.pol, NOW, scope=dict(T.SCOPE, **{k: "other"}))
            code(self, "GAP04-E0204", verify, e, self.cp, pol=self.pol)

    def test_T_C01_wrong_policy_hash(self):
        other = self.cp.policy()
        code(self, "GAP04-E0207", verify, self.env, self.cp, pol=other)

    def test_T_C01_expired_and_future(self):
        code(self, "GAP04-E0205", verify, self.cp.lease(self.pol, NOW - 100, ttl=50), self.cp, pol=self.pol)
        code(self, "GAP04-E0205", verify, self.cp.lease(self.pol, NOW + 3600), self.cp, pol=self.pol)
        code(self, "GAP04-E0205", verify, self.cp.lease(self.pol, NOW, ttl=TR.MAX_LEASE_LIFETIME_S + 1), self.cp, pol=self.pol)
        bad = self.cp.lease(self.pol, NOW, not_before=NOW - 10)
        code(self, "GAP04-E0205", verify, bad, self.cp, pol=self.pol)

    def test_T_C01_stale_epoch(self):
        e = self.cp.lease(self.pol, NOW, epoch=0)
        code(self, "GAP04-E0206", verify, e, self.cp, pol=self.pol)

    def test_T_C01_unknown_issuer_and_key(self):
        code(self, "GAP04-E0202", verify, self.cp.lease(self.pol, NOW, key_id="nope"), self.cp, pol=self.pol)
        code(self, "GAP04-E0202", verify, self.cp.lease(self.pol, NOW, issuer="evil"), self.cp, pol=self.pol)

    def test_T_C01_revoked_key(self):
        ts = TR.TrustStore.from_doc(self.cp.trust_doc(revoked=True))
        code(self, "GAP04-E0202", verify, self.env, self.cp, pol=self.pol, trust=ts)

    def test_T_C01_alg_downgrade(self):
        for alg in ("none", "HS256", "RS256", "ES256", "ed25519"):
            e = self.cp.lease(self.pol, NOW, alg=alg)
            code(self, "GAP04-E0203", verify, e, self.cp, pol=self.pol)

    def test_T_C01_truncated_and_extra_fields(self):
        raw = canonical.dumps(self.env)
        code(self, "GAP04-E0200", verify, raw[: len(raw) // 2], self.cp, pol=self.pol)
        e = dict(self.env); e["extra"] = 1
        code(self, "GAP04-E0200", verify, e, self.cp, pol=self.pol)
        e = dict(self.env); del e["nonce"]
        code(self, "GAP04-E0200", verify, e, self.cp, pol=self.pol)

    def test_T_C01_version_skew(self):
        e = self.cp.lease(self.pol, NOW, version="PK_SIGNED_LEASE/2")
        code(self, "GAP04-E0209", verify, e, self.cp, pol=self.pol)

    def test_T_C01_trust_unavailable(self):
        code(self, "GAP04-E0208", verify, self.env, self.cp, pol=self.pol, trust=None)

    def test_T_C01_trust_domain(self):
        e = self.cp.lease(self.pol, NOW, trust_domain="evil.org")
        code(self, "GAP04-E0204", verify, e, self.cp, pol=self.pol)

    def test_T_C01_nonce_and_caps_syntax(self):
        code(self, "GAP04-E0200", verify, self.cp.lease(self.pol, NOW, nonce="short"), self.cp, pol=self.pol)
        code(self, "GAP04-E0200", verify, self.cp.lease(self.pol, NOW, capabilities=["root"]), self.cp, pol=self.pol)

    def test_T_C01_key_rotation(self):
        seed2, pub2 = crypto.generate_signing_key()
        k2 = {"key_id": "cp-1-k2", "issuer": "cp-1", "alg": "Ed25519", "public_key": pub2, "not_before": 0,
              "not_after": 2**40, "purposes": ["lease"], "revoked": False}
        self.cp.extra_keys = [k2]; self.cp.bundle_version = 2
        ts = self.cp.trust()
        new = TR.sign_lease(dict(TR.lease_payload(self.env), key_id="cp-1-k2", lease_id="L-new"), seed2)
        verify(new, self.cp, pol=self.pol, trust=ts)          # overlap: both valid
        verify(self.env, self.cp, pol=self.pol, trust=ts)
        doc = self.cp.trust_doc(revoked=True); doc["bundle_version"] = 3
        ts3 = TR.TrustStore.from_doc(doc)                       # forced rollover: old revoked
        code(self, "GAP04-E0202", verify, self.env, self.cp, pol=self.pol, trust=ts3)
        verify(new, self.cp, pol=self.pol, trust=ts3)
        code(self, "GAP04-E0208", TR.TrustStore.from_doc, self.cp.trust_doc(), min_version=3)  # stale bundle refused

    def test_T_C01_production_gate_node(self):
        """No unsigned/stale/cross-site/downgraded/policy-mismatched lease can authorize an action."""
        with Tmp() as d:
            n, cp, m = node(d, cp=self.cp)
            n.clock.anchor_trusted(cp.t0)
            T.come_back(n, cp, m)
            pol = cp.policy(); n.install_policy(pol)
            now = n.clock.now()
            bads = [dict(cp.lease(pol, now), sig="AAAA"), cp.lease(pol, now, scope=dict(T.SCOPE, site="x")),
                    cp.lease(pol, now, alg="none"), cp.lease(self.pol, now), cp.lease(pol, now, epoch=0)]
            for b in bads:
                with self.assertRaises(Gap04Error):
                    n.install_lease(b)
            T.go_dark(n, m)
            code(self, "GAP04-E0100", n.decide, "restart", "ns/a", "req-00000001")
            self.assertEqual(n.metrics.get("verification_failures_total", code="GAP04-E0201"), 1)
            n.close()


class PolicyProvenance(unittest.TestCase):
    def test_T_C05_verify_and_rollback(self):
        cp = T.ControlPlane(); ts = cp.trust()
        p2 = cp.policy(version=2)
        vp = TR.verify_policy(p2, trust=ts, now=NOW, min_policy_version=1)
        self.assertEqual(vp.policy_version, 2)
        code(self, "GAP04-E0221", TR.verify_policy, cp.policy(version=1), trust=ts, now=NOW, min_policy_version=2)
        tampered = dict(p2); tampered["rules"] = {"allow_kinds": ["scale"]}
        code(self, "GAP04-E0220", TR.verify_policy, tampered, trust=ts, now=NOW, min_policy_version=0)
        same = dict(p2); same["approver"] = same["author"]
        same = TR.sign_policy({k: v for k, v in same.items() if k != "sig"}, cp.seed)
        code(self, "GAP04-E0220", TR.verify_policy, same, trust=ts, now=NOW, min_policy_version=0)

    def test_T_C05_node_pins_version(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m)
            code(self, "GAP04-E0221", n.install_policy, cp.policy(version=1, rules={"allow_kinds": ["scale"]}))
            code(self, "GAP04-E0221", n.install_policy, cp.policy(version=0))
            n.close()


class RevocationEpoch(unittest.TestCase):
    def test_T_C06_watermark_survives_restart(self):
        with Tmp() as d:
            n, cp, m = node(d)
            pol, lease = T.bring_up(n, cp, m)
            cp.epoch = 5
            n.apply_revocations(5)
            self.assertFalse(n.health()["ready"])
            code(self, "GAP04-E0206", n.install_lease, cp.lease(pol, n.clock.now(), epoch=4))
            code(self, "GAP04-E0206", n.install_lease, lease)  # old lease cannot become valid again
            n.close()
            n2, _, _ = node(d, cp=cp, mono=m)
            n2.clock.anchor_trusted(n2.clock.hwm)
            self.assertEqual(n2.state["authority_watermark"], 5)
            T.come_back(n2, cp, m)
            code(self, "GAP04-E0206", n2.install_lease, cp.lease(pol, n2.clock.now(), epoch=4, lease_id="L-zz"))
            n2.install_lease(cp.lease(pol, n2.clock.now(), epoch=5))
            code(self, "GAP04-E0206", n2.apply_revocations, 4)
            n2.close()

    def test_T_C06_revoked_lease_id(self):
        with Tmp() as d:
            n, cp, m = node(d)
            pol, lease = T.bring_up(n, cp, m)
            r = n.apply_revocations(1, revoked_lease_ids=[lease["lease_id"]])
            self.assertTrue(r["lease_dropped"])
            T.go_dark(n, m)
            code(self, "GAP04-E0100", n.decide, "restart", "ns/a", "req-00000001")
            n.close()


class ErrorModel(unittest.TestCase):
    def test_T_C19_registry_and_mapping(self):
        for c, (cat, retry, status, desc) in REGISTRY.items():
            self.assertRegex(c, r"^GAP04-E\d{4}$"); self.assertIsInstance(retry, bool)
            self.assertTrue(100 <= status < 600); self.assertTrue(desc)
        e = to_error(LeaseExpired("x"))
        self.assertEqual((e["schema"], e["code"]), (ERROR_MODEL_VERSION, "GAP04-E0100"))
        self.assertEqual(to_error(ValueError("t predates the last"))["code"], "GAP04-E0003")
        with self.assertRaises(ValueError):
            Gap04Error("x", code="GAP04-E9999")

    def test_T_C19_registry_snapshot_is_append_only(self):
        import pathlib
        snap = json.loads((pathlib.Path(__file__).parent / "fixtures" / "error_registry.v1.json").read_text())
        for c, v in snap.items():
            self.assertIn(c, REGISTRY, f"code {c} removed")
            self.assertEqual(list(REGISTRY[c][:3]), v[:3], f"code {c} semantics changed")


if __name__ == "__main__":
    unittest.main()
