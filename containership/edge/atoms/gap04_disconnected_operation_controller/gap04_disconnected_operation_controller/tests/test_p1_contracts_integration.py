"""C36 schema contract tests + compatibility fixtures, C37 adjacent-layer integration,
C44 compatibility matrix consistency, C45/C46 packaging lock, SBOM, provenance, signing."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from _util import T, Tmp, node, code, Gap04Error
from gap04_disconnected_operation_controller.runtime import schema, canonical, trust as TR
from gap04_disconnected_operation_controller.runtime.adapters import CONTRACTS, ReferenceReplication, ReferenceSupervisor
from gap04_disconnected_operation_controller.runtime.errors import Gap04Error as E, REGISTRY
from gap04_disconnected_operation_controller.runtime.clock import sign_time_token

PKG = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"


class Contracts(unittest.TestCase):
    def test_T_C36_every_emitted_message_validates(self):
        seen = {"cmd": [], "batch": []}
        class S(ReferenceSupervisor):
            def execute(s, c): seen["cmd"].append(c); return super().execute(c)
        class R(ReferenceReplication):
            def submit(s, b): seen["batch"].append(b); return super().submit(b)
        with Tmp() as d:
            n, cp, m = node(d, supervisor=S(), replication=R())
            n.log.sink = []
            pol, lease = T.bring_up(n, cp, m); T.go_dark(n, m)
            schema.check(pol, "PK_POLICY_BUNDLE/1"); schema.check(lease, "PK_SIGNED_LEASE/1")
            schema.check(cp.trust_doc(), "PK_TRUST_BUNDLE/1")
            schema.check(cp.heartbeat(n.adapters.reachability, 1), "PK_HEARTBEAT/1")
            schema.check(sign_time_token(1, "a" * 32, cp.issuer, cp.key_id, cp.seed), "PK_TIME_TOKEN/1")
            schema.check(cp.grant("spiffe://example.org/x", ["gap04.decide.restart"], 100), "PK_CAPABILITY_GRANT/1")
            n.decide("restart", "ns/a", "req-00000001")
            try:
                n.decide("scale", "kube-system/x", "req-00000002")
            except E as e:
                schema.check(e.to_dict(), "PK_GAP04_ERROR/1")
            schema.check(n.controller.lease_view(n.clock.now()), "PK_AUTONOMY_LEASE/1")
            schema.check(n.controller.tier_view(n.clock.now()), "PK_DEGRADATION_TIER/1")
            T.come_back(n, cp, m)
            rec = n.reconnect()
            schema.check(rec, "PK_RECONCILIATION_RECORD/2")
            self.assertTrue(schema.validate(dict(rec, schema="PK_RECONCILIATION_RECORD/1"), schema.load("PK_RECONCILIATION_RECORD/1")))  # v1 consumers must not silently accept /2
            schema.check(n.health(), "PK_GAP04_HEALTH/1")
            for c in seen["cmd"]: schema.check(c, "PK_SUPERVISOR_COMMAND/1")
            for b in seen["batch"]: schema.check(b, "PK_REPLICATION_BATCH/1")
            for r in n.log.sink: schema.check(r, "PK_GAP04_LOG/1")
            self.assertTrue(n.log.sink)
            n.close()

    def test_T_C36_every_error_code_serializes(self):
        for c in REGISTRY:
            schema.check(E("m", code=c).to_dict(), "PK_GAP04_ERROR/1")

    def test_T_C36_schemas_reject_bad_payloads(self):
        cp = T.ControlPlane(); pol = cp.policy(); l = cp.lease(pol, 5)
        for bad in (dict(l, alg="none"), dict(l, extra=1), {k: v for k, v in l.items() if k != "sig"},
                    dict(l, authority_epoch=0), dict(l, capabilities=["root"])):
            self.assertTrue(schema.validate(bad, schema.load("PK_SIGNED_LEASE/1")))

    def test_T_C36_golden_fixtures_version_skew(self):
        """Frozen v1 fixtures must keep verifying (forward compat of the verifier), and a
        future /2 envelope must be refused with the explicit unsupported-version code."""
        g = json.loads((FIX / "golden_v1.json").read_text())
        ts = TR.TrustStore.from_doc(g["trust"])
        vl = TR.verify_lease(g["lease"], trust=ts, expected_scope=g["scope"], now=g["now"], min_authority_epoch=1,
                             expected_policy_digest=TR.policy_digest(g["policy"]))
        self.assertEqual(vl.fingerprint, g["expect"]["fingerprint"])
        self.assertEqual(TR.policy_digest(g["policy"]), g["expect"]["policy_digest"])
        v2 = dict(g["lease"], version="PK_SIGNED_LEASE/2")
        code(self, "GAP04-E0209", TR.verify_lease, v2, trust=ts, expected_scope=g["scope"], now=g["now"],
             min_authority_epoch=1, expected_policy_digest=None)
        for name in ("PK_AUTONOMY_LEASE/1", "PK_DEGRADATION_TIER/1", "PK_RECONCILIATION_RECORD/1"):
            for doc in g["v420_views"][name]:
                schema.check(doc, name)   # 4.2.0-emitted views still valid under shipped schemas


class Integration(unittest.TestCase):
    def test_T_C37_full_adjacent_stack(self):
        """GAP-12 (signed heartbeats) + GAP-13 (policy eval) + PLN-07 (grants) + GAP-01 (fenced,
        idempotent execution) + GAP-05 (batched, idempotent reconciliation) across a partition,
        a restart, a generation change and a reconnect."""
        with Tmp() as d:
            sup, rep = ReferenceSupervisor(), ReferenceReplication()
            n, cp, m = node(d, supervisor=sup, replication=rep, capabilities=True)
            T.bring_up(n, cp, m)
            now = n.clock.now()
            n.adapters.capabilities.install_grant(cp.grant(T.WORKLOAD.spiffe_id, ["gap04.decide.restart", "gap04.decide.admit-new"], now), now)
            T.go_dark(n, m)
            a = n.decide("admit-new", "ns/a", "req-00000001", principal=T.WORKLOAD)
            n.close()
            n2, _, _ = node(d, cp=cp, mono=m, supervisor=sup, replication=rep, capabilities=True)
            n2.clock.anchor_trusted(n2.clock.hwm)
            n2.adapters.capabilities.grants = n.adapters.capabilities.grants
            b = n2.decide("restart", "ns/b", "req-00000002", principal=T.WORKLOAD)
            self.assertGreater(b["generation"], a["generation"])
            # the old generation can no longer drive the supervisor
            with self.assertRaises(E):
                sup.execute({"contract": CONTRACTS["GAP-01"], "command_id": "d-" + "f" * 32, "kind": "restart",
                             "subject": "ns/z", "authority_epoch": a["authority_epoch"], "generation": a["generation"]})
            T.come_back(n2, cp, m)
            rec = n2.reconnect()
            self.assertEqual(rec["decision_count"], 2)
            self.assertEqual(set(rep.applied), {a["decision_id"], b["decision_id"]})
            n2.close()

    def test_T_C37_pk_core_conformance_adapter_still_loads(self):
        import importlib
        pkg = importlib.import_module("gap04_disconnected_operation_controller")
        self.assertEqual(pkg.__version__, "4.3.0")
        try:
            import pk_core  # noqa
        except ModuleNotFoundError:
            self.skipTest("pk_core not available in this environment (BLOCKED evidence, see CHECKLIST_STATUS)")
        pkg.build_contract()


class CompatAndRelease(unittest.TestCase):
    def test_T_C44_matrix_matches_code(self):
        mx = json.loads((PKG / "COMPATIBILITY_MATRIX.json").read_text())
        for layer, contract in CONTRACTS.items():
            self.assertEqual(mx["adjacent_contracts"][layer]["contract"], contract)
        self.assertEqual(mx["gap04_version"], (PKG / "VERSION").read_text().strip())
        from gap04_disconnected_operation_controller.runtime import crypto
        self.assertEqual(mx["crypto"]["cryptography"]["tested"], crypto.BACKEND_VERSION)
        lock = (PKG / "requirements.lock").read_text()
        self.assertIn(f"cryptography=={crypto.BACKEND_VERSION}", lock)
        self.assertTrue("--hash=sha256:" in lock or "HASHES_PENDING" in lock)

    def test_T_C45_C46_reproducible_signed_release(self):
        from gap04_disconnected_operation_controller.runtime import release, crypto
        out1, out2 = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        man = (PKG / "MANIFEST.sha256").read_bytes() if (PKG / "MANIFEST.sha256").exists() else None
        try:
            seed, pub = crypto.generate_signing_key()
            r1 = release.build(out1, seed); r2 = release.build(out2, seed)
            self.assertEqual(r1["sha256"], r2["sha256"], "build not reproducible")
            self.assertTrue(release.verify(out1, r1["pubkey"])["verified"])
            (out1 / "sbom.cdx.json").write_text((out1 / "sbom.cdx.json").read_text().replace("46.0.7", "46.0.6"))
            with self.assertRaises(SystemExit):
                release.verify(out1, r1["pubkey"])
            _, other = crypto.generate_signing_key()
            with self.assertRaises(SystemExit):
                release.verify(out2, other)
        finally:
            shutil.rmtree(out1); shutil.rmtree(out2)
            if man is not None:
                (PKG / "MANIFEST.sha256").write_bytes(man)


if __name__ == "__main__":
    unittest.main()
