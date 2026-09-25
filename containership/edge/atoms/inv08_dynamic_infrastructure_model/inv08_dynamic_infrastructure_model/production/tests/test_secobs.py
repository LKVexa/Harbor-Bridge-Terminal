"""secobs group: components 34-40, 47-55 (security + observability)."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import tempfile
import time
import unittest
from pathlib import Path

from ...model import Pool, PoolInvariantError
from .. import (artifact_verify as av, attestation as at, audit, bench, capacity, dashboards, explain,
                isolation as iso, keys, logging_trace as lt, metrics, power, telemetry_gov as tg, threat_model as tm)
from ..core import Inv08Error, TrustRoot, canonical, redact

K1, K2, K3 = b"k" * 32, b"j" * 32, b"m" * 32


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


class TmpDir(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.dir = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()


# ======================================================================= 34
class ThreatModelTests(unittest.TestCase):
    def test_model_validates(self):
        ids = tm.validate_model()
        self.assertGreaterEqual(len(ids), 10)
        self.assertEqual({t["stride"] for t in tm.MODEL["threats"]}, set(tm.STRIDE))

    def test_every_mitigation_resolves(self):
        resolved = tm.resolve_mitigations()
        self.assertTrue(resolved)
        for ref, obj in resolved.items():
            self.assertTrue(callable(obj) or isinstance(obj, type), ref)

    def test_unresolvable_mitigation_rejected(self):
        with self.assertRaises(Inv08Error):
            tm.resolve_ref("production/keys.py::DoesNotExist")
        with self.assertRaises(Inv08Error):
            tm.resolve_ref("../etc/passwd.py::x")
        with self.assertRaises(Inv08Error):
            tm.resolve_ref("nocolons")

    def test_dangling_references_rejected(self):
        for mut in (lambda m: m["flows"][0].update(src="A.nope"),
                    lambda m: m["flows"][0]["crosses"].append("B.nope"),
                    lambda m: m["threats"][0].update(stride="X"),
                    lambda m: m["threats"][0].update(target="A.nope"),
                    lambda m: m["threats"][0].update(mitigations=[]),
                    lambda m: m["attack_trees"][0]["children"].append("T99"),
                    lambda m: m.update(schema="PK_DYN_THREAT/2"),
                    lambda m: m["assets"].append(dict(m["assets"][0]))):
            m = copy.deepcopy(tm.MODEL)
            mut(m)
            with self.assertRaises(Inv08Error):
                tm.validate_model(m)

    def test_abuse_cases_tenant_and_compromised_node(self):
        self.assertTrue(tm.abuse_cases("tenant"))
        self.assertTrue(tm.abuse_cases("compromised_node"))
        with self.assertRaises(Inv08Error):
            tm.abuse_cases("aliens")

    def test_attack_trees_and_or(self):
        tree = tm.MODEL["attack_trees"][0]
        self.assertFalse(tm.tree_achievable(tree, set()))
        self.assertFalse(tm.tree_achievable(tree, {"T03"}))          # AND needs T05 too
        self.assertTrue(tm.tree_achievable(tree, {"T03", "T05"}))
        self.assertTrue(tm.tree_achievable(tree, {"T14"}))           # OR leaf
        kinds = {t["abuse_case"] for t in tm.MODEL["threats"]}
        self.assertTrue({"supply_chain", "replay", "spoofing"} <= kinds)

    def test_residual_risk_unaccepted_and_owner_required(self):
        reg = tm.residual_risk_register()
        self.assertTrue(all(r["acceptance"] == "UNACCEPTED" and r["owner"] == "UNASSIGNED" for r in reg))
        m = copy.deepcopy(tm.MODEL)
        m["threats"][0]["residual_risk"]["acceptance"] = "ACCEPTED"
        with self.assertRaises(Inv08Error):
            tm.validate_model(m)
        self.assertTrue(tm.model_digest().startswith("sha256:"))


# ======================================================================= 35
class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock(1000.0)
        self.trust = TrustRoot()
        self.nonces = at.NonceIssuer(self.clock, random.Random(1), ttl=30)
        self.dev = at.SimulatedDevice("node-1", "dev-1", K1, self.trust)
        for i, blob in enumerate([b"firmware", b"bootloader", b"kernel"]):
            self.dev.measure(i, blob, f"stage{i}")
        golden = at.replay_event_log(self.dev.events)
        self.v = at.AttestationVerifier(self.trust, self.nonces, at.AttestationPolicy(golden_pcrs=golden), self.clock)

    def fresh(self, **kw):
        return self.dev.quote(self.nonces.issue(), self.clock(), **kw)

    def test_rot_evidence_valid_admitted(self):
        ev = self.fresh()
        self.assertEqual(ev["rot"]["type"], "sim")
        vd = self.v.evaluate(ev)
        self.assertTrue(vd.admitted, vd.reasons)
        self.assertTrue(self.v.schedulable("node-1"))

    def test_rot_unsupported_hardware_types_denied(self):
        ev = self.fresh()
        ev["rot"]["type"] = "tpm2"   # real TPM path is BLOCKED -> must deny, not pass
        self.assertEqual(self.v.evaluate(ev).action, at.Action.DENY)
        with self.assertRaises(ValueError):
            at.AttestationPolicy(allowed_rot=("quantum",))

    def test_rot_forged_quote_quarantined(self):
        ev = self.fresh()
        ev["quote"]["mac"] = "0" * 64
        vd = self.v.evaluate(ev)
        self.assertEqual(vd.action, at.Action.QUARANTINE)
        self.assertIn("bad_quote", vd.reasons)

    def test_boot_measurement_replay_and_mismatch(self):
        self.assertEqual(at.extend(at.ZERO_PCR, "00" * 32),
                         hashlib.sha256(bytes(64)).hexdigest())
        # event log inconsistent with PCRs
        ev = self.fresh(pcr_override={"0": "11" * 32})
        vd = self.v.evaluate(ev)
        self.assertIn("event_log_mismatch", vd.reasons)
        self.assertEqual(vd.action, at.Action.QUARANTINE)

    def test_boot_measurement_unexpected_kernel(self):
        self.dev.events[2]["digest"] = hashlib.sha256(b"evil-kernel").hexdigest()
        vd = self.v.evaluate(self.fresh())
        self.assertIn("pcr_mismatch", vd.reasons)
        self.assertFalse(self.v.schedulable("node-1"))

    def test_nonce_replay_unknown_and_stale(self):
        ev = self.fresh()
        self.assertTrue(self.v.evaluate(ev).admitted)
        self.assertIn("nonce_replay", self.v.evaluate(ev).reasons)
        ev2 = self.dev.quote("ab" * 16, self.clock())
        self.assertEqual(self.v.evaluate(ev2).action, at.Action.DENY)
        n = self.nonces.issue()
        self.clock.t += 31
        vd = self.v.evaluate(self.dev.quote(n, self.clock()))
        self.assertEqual(vd.reasons, ["stale_nonce"])
        self.assertEqual(vd.action, at.Action.DEGRADE)

    def test_nonce_issuer_bounded(self):
        ni = at.NonceIssuer(self.clock, random.Random(2), ttl=5, max_outstanding=3)
        for _ in range(3):
            ni.issue()
        with self.assertRaises(Inv08Error):
            ni.issue()
        self.clock.t += 6
        ni.issue()  # expired ones pruned

    def test_policy_evaluation_malformed_evidence(self):
        for bad in (None, {}, {"schema": at.SCHEMA}, "x", [1]):
            self.assertEqual(self.v.evaluate(bad).action, at.Action.DENY)
        ev = self.fresh()
        ev["ts"] = float("nan")
        self.assertEqual(self.v.evaluate(ev).reasons, ["malformed"])
        ev = self.fresh()
        ev["event_log"][0]["digest"] = "zz"
        self.assertEqual(self.v.evaluate(ev).reasons, ["malformed"])

    def test_policy_evidence_too_old(self):
        ev = self.dev.quote(self.nonces.issue(), self.clock() - 120)
        self.assertIn("evidence_too_old", self.v.evaluate(ev).reasons)

    def test_actions_severity_and_audit(self):
        with tempfile.TemporaryDirectory() as d:
            log = audit.AuditLog(Path(d) / "a.jsonl", clock=self.clock)
            self.v.audit = log
            ev = self.fresh()
            ev["quote"]["mac"] = "0" * 64
            ev["rot"]["type"] = "tdx"
            vd = self.v.evaluate(ev)
            self.assertEqual(vd.action, at.Action.DENY)  # worst action wins
            ok, _, entries = audit.verify_file(Path(d) / "a.jsonl")
            self.assertTrue(ok)
            self.assertEqual(entries[-1]["outcome"], "DENY")
            self.assertEqual(self.v._finish("n", ["mystery"]).action, at.Action.DENY)
        self.assertFalse(self.v.schedulable("never-seen"))


# ======================================================================= 36
class ArtifactVerifyTests(TmpDir):
    def setUp(self):
        super().setUp()
        self.clock = Clock(100.0)
        self.trust = TrustRoot()
        self.trust.add("root", K1)
        self.trust.add("release", K2)
        self.log = audit.AuditLog(self.dir / "audit.jsonl", clock=self.clock)
        self.gate = av.ArtifactGate(self.trust, {"root"}, {"builder://ci"}, self.log, self.clock)

    def manifest(self, data: bytes, name="pkg.whl", scope="artifact", **over):
        dg = "sha256:" + hashlib.sha256(data).hexdigest()
        chain = [av.make_delegation(self.trust, "root", "release", [scope], 0, 1000)]
        m = {"schema": av.SCHEMA, "name": name, "digest": dg, "scope": scope, "chain": chain,
             "signature": self.trust.sign("release", av.envelope(name, dg, scope)),
             "provenance": {"schema": av.PROVENANCE, "subject": [{"name": name, "digest": dg}],
                            "builder": {"id": "builder://ci"}, "materials": [{"uri": "src", "digest": "sha256:" + "a" * 64}]}}
        m.update(over)
        return m

    def test_digest_ok_and_mismatch(self):
        av.verify_digest(b"abc", "sha256:" + hashlib.sha256(b"abc").hexdigest())
        with self.assertRaises(av.VerificationError):
            av.verify_digest(b"abd", "sha256:" + hashlib.sha256(b"abc").hexdigest())
        for bad in ("md5:00", "sha256:XYZ", None, "sha256:" + "a" * 63):
            with self.assertRaises(av.VerificationError):
                av.verify_digest(b"abc", bad)

    def test_chain_valid(self):
        r = self.gate.verify_release(b"wheel", self.manifest(b"wheel"))
        self.assertEqual(r["scope"], "artifact")

    def test_chain_revoked_expired_scope_and_untrusted(self):
        m = self.manifest(b"w")
        self.trust.revoke("release")
        with self.assertRaises(av.VerificationError):
            self.gate.verify_release(b"w", m)
        self.trust.add("release2", K3)
        dg = m["digest"]
        cases = [
            [av.make_delegation(self.trust, "root", "release2", ["artifact"], 0, 50)],         # expired
            [av.make_delegation(self.trust, "root", "release2", ["policy"], 0, 1000)],         # scope
            [av.make_delegation(self.trust, "release2", "release2", ["artifact"], 0, 1000)],   # untrusted issuer
            [{"statement": "junk", "signature": {}}],
            [av.make_delegation(self.trust, "root", "release2", ["artifact"], 0, 1000)] * 5,  # too long
        ]
        for chain in cases:
            m2 = dict(m, chain=chain, signature=self.trust.sign("release2", av.envelope("pkg.whl", dg, "artifact")))
            with self.assertRaises(av.VerificationError):
                self.gate.verify_release(b"w", m2)

    def test_chain_signer_mismatch_and_tampered_delegation(self):
        m = self.manifest(b"w", signature=self.trust.sign("root", av.envelope("pkg.whl", "sha256:" + hashlib.sha256(b"w").hexdigest(), "artifact")))
        with self.assertRaises(av.VerificationError) as cm:
            self.gate.verify_release(b"w", m)
        self.assertEqual(cm.exception.code, "INV08.ARTIFACT.SIGNER_MISMATCH")
        m = self.manifest(b"w")
        m["chain"][0]["statement"]["scopes"] = ["artifact", "policy"]
        with self.assertRaises(av.VerificationError):
            self.gate.verify_release(b"w", m)

    def test_provenance_checks(self):
        dg = "sha256:" + hashlib.sha256(b"w").hexdigest()
        good = self.manifest(b"w")["provenance"]
        av.verify_provenance(good, dg, "pkg.whl", {"builder://ci"})
        with self.assertRaises(av.VerificationError):
            av.verify_provenance(good, dg, "pkg.whl", {"builder://other"})
        with self.assertRaises(av.VerificationError):
            av.verify_provenance(good, "sha256:" + "b" * 64, "pkg.whl", {"builder://ci"})
        for bad in (None, {}, dict(good, schema="x"), dict(good, materials=[{"digest": "md5"}])):
            with self.assertRaises(av.VerificationError):
                av.verify_provenance(bad, dg, "pkg.whl", {"builder://ci"})

    def policy(self, version=1, **pool):
        p = {"min_nodes": 1, "max_nodes": 10, "per_node": 4, "lease_ttl": 10}
        p.update(pool)
        return {"schema": av.POLICY, "version": version, "pool": p}

    def test_policy_bundle_validation(self):
        self.assertEqual(av.validate_policy_bundle(self.policy())["max_nodes"], 10)
        bad = [self.policy(min_nodes=11), self.policy(max_nodes=10 ** 6), self.policy(per_node=0),
               self.policy(version=0), self.policy(version=True), dict(self.policy(), extra=1),
               {"schema": "x", "version": 1, "pool": {}}, self.policy(lease_ttl=1.5), None]
        for b in bad:
            with self.assertRaises(av.VerificationError):
                av.validate_policy_bundle(b)

    def test_policy_bundle_through_gate_anti_rollback(self):
        b = self.policy(version=3)
        data = canonical(b)
        r = self.gate.verify_release(data, self.manifest(data, name="policy", scope="policy", policy_bundle=b))
        self.assertEqual(r["pool"]["max_nodes"], 10)
        b2 = self.policy(version=2)
        d2 = canonical(b2)
        with self.assertRaises(av.VerificationError):
            self.gate.verify_release(d2, self.manifest(d2, name="policy", scope="policy", policy_bundle=b2))

    def test_fail_closed_and_audited(self):
        with self.assertRaises(av.VerificationError):
            self.gate.verify_release(b"w", self.manifest(b"other"))
        with self.assertRaises(av.VerificationError) as cm:
            self.gate.verify_release(b"w", {"schema": av.SCHEMA, "name": "x"})  # KeyError -> internal
        self.assertEqual(cm.exception.code, "INV08.ARTIFACT.INTERNAL")
        with self.assertRaises(av.VerificationError):
            self.gate.verify_release(b"w", "not a manifest")
        ok, problems, entries = audit.verify_file(self.dir / "audit.jsonl")
        self.assertTrue(ok, problems)
        self.assertEqual([e["outcome"] for e in entries], ["DENY"] * 3)


# ======================================================================= 37
class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.pol = {"alpha": iso.TenantPolicy("alpha", mem_limit_mib=2048, cpu_millis=2000),
                    "beta": iso.TenantPolicy("beta", allowed_peers=frozenset({"alpha"}))}
        self.nodes = {"node-1": iso.NodeCapacity(4096, 4000), "node-2": iso.NodeCapacity(4096, 4000)}

    def P(self, t, w, node, mem=512, cpu=500, **kw):
        kw.setdefault("identity", f"spiffe://inv08/{t}/{w}")
        return iso.Placement(t, w, node, mem_mib=mem, cpu_millis=cpu, **kw)

    def test_compute_compliant_and_shared_node(self):
        self.assertEqual(iso.check_isolation(self.pol, [self.P("alpha", "a", "node-1"), self.P("beta", "b", "node-2")], self.nodes), [])
        v = iso.check_isolation(self.pol, [self.P("alpha", "a", "node-1"), self.P("beta", "b", "node-1")], self.nodes)
        self.assertEqual({x["boundary"] for x in v}, {"compute"})
        v = iso.check_isolation(self.pol, [self.P("gamma", "g", "node-1"), self.P("alpha", "a", "node-9")], self.nodes)
        self.assertEqual(len(v), 2)

    def test_memory_limits(self):
        v = iso.check_isolation(self.pol, [self.P("alpha", "a", "node-1", mem=4000, cpu=100), self.P("alpha", "b", "node-1", mem=200)], self.nodes)
        self.assertTrue(any(x["detail"] == "node node-1 overcommitted" for x in v))
        self.assertTrue(any(x["detail"] == "tenant resource limit exceeded" for x in v))
        with self.assertRaises(Inv08Error):
            iso.TenantPolicy("alpha", mem_limit_mib=0)

    def test_network_identity(self):
        v = iso.check_isolation(self.pol, [self.P("alpha", "a", "node-1", identity="spiffe://inv08/beta/a"),
                                           self.P("alpha", "c", "node-1", peers=("beta",)),
                                           self.P("beta", "b", "node-2", peers=("alpha",))], self.nodes)
        self.assertEqual([x["tenant"] for x in v if x["boundary"] == "network"], ["alpha", "alpha"])

    def test_state_namespacing(self):
        back = {}
        a, b = iso.NamespacedState(back, "alpha"), iso.NamespacedState(back, "beta")
        a["k"] = 1
        self.assertNotIn("k", b)
        with self.assertRaises(KeyError):
            b["k"]
        b["k"] = 2
        self.assertEqual((a["k"], b["k"]), (1, 2))
        self.assertEqual(list(a.keys()), ["k"])
        for bad in ("", "x\x00beta", 5, "y" * 600):
            with self.assertRaises(Inv08Error):
                a[bad] = 1
        with self.assertRaises(Inv08Error):
            iso.NamespacedState(back, "Alpha\x00")
        # prefix confusion: tenant 'a' vs 'alpha'
        c = iso.NamespacedState(back, "a")
        self.assertEqual(len(c), 0)

    def test_device_exclusive(self):
        v = iso.check_isolation(self.pol, [self.P("alpha", "a", "node-1", devices=("gpu0",)),
                                           self.P("beta", "b", "node-2", devices=("gpu0",))], self.nodes)
        self.assertEqual({x["boundary"] for x in v}, {"device"})
        shared = {"alpha": iso.TenantPolicy("alpha", exclusive_devices=False),
                  "beta": iso.TenantPolicy("beta", exclusive_devices=False)}
        self.assertEqual(iso.check_isolation(shared, [self.P("alpha", "a", "node-1", devices=("gpu0",)),
                                                      self.P("beta", "b", "node-2", devices=("gpu0",))], self.nodes), [])


# ======================================================================= 38
class KeyTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock(0.0)
        self.kh = keys.KeyHierarchy(K1, self.clock, overlap=100)

    def test_transport_and_at_rest_are_blocked_not_faked(self):
        self.assertEqual(keys.TRANSPORT_POLICY["status"], "BLOCKED")
        self.assertTrue(all(b["status"] in ("BLOCKED", "N/A") for b in keys.AT_REST_BOUNDARIES))
        self.assertFalse(hasattr(keys, "encrypt"))

    def test_hkdf_rfc5869_vector(self):
        ikm = bytes.fromhex("0b" * 22)
        okm = keys.hkdf_sha256(ikm, salt=bytes(range(13)), info=bytes(range(0xf0, 0xfa)), length=42)
        self.assertEqual(okm.hex(), "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865")
        with self.assertRaises(ValueError):
            keys.hkdf_sha256(ikm, length=0)

    def test_hierarchy_derivation(self):
        kek = self.kh.create_kek("state")
        dek = self.kh.create_dek("journal", "state")
        self.assertEqual(dek.parent, ("state", 1))
        m1 = self.kh.material_for("DEK", "journal", 1, purpose="encrypt")
        self.assertEqual(len(m1), 32)
        self.assertNotEqual(m1, kek._material)
        self.assertNotIn(m1.hex(), repr(self.kh) + json.dumps(dek.describe()))
        with self.assertRaises(ValueError):
            keys.KeyHierarchy(b"short", self.clock)
        with self.assertRaises(Inv08Error):
            self.kh.create_dek("x", "nokek")

    def test_rotation_overlap(self):
        self.kh.create_kek("state")
        self.kh.create_dek("journal", "state")
        self.kh.rotate_dek("journal")
        self.assertEqual(self.kh.active("DEK", "journal").version, 2)
        with self.assertRaises(Inv08Error):
            self.kh.material_for("DEK", "journal", 1, purpose="encrypt")
        self.assertTrue(self.kh.usable_for_decrypt("DEK", "journal", 1))
        self.clock.t = 100
        self.assertFalse(self.kh.usable_for_decrypt("DEK", "journal", 1))
        self.assertEqual(self.kh.keys[("DEK", "journal", 1)].state, "RETIRED")
        with self.assertRaises(Inv08Error):
            self.kh.rotate_dek("unknown")

    def test_revocation_cascades(self):
        self.kh.create_kek("state")
        self.kh.create_dek("a", "state")
        ids = self.kh.revoke("KEK", "state", 1, "test")
        self.assertEqual(set(ids), {"KEK:state:v1", "DEK:a:v1"})
        with self.assertRaises(Inv08Error):
            self.kh.material_for("DEK", "a", 1, purpose="decrypt")
        with self.assertRaises(Inv08Error):
            self.kh.revoke("KEK", "nope", 1, "x")

    def test_compromise_procedure(self):
        with tempfile.TemporaryDirectory() as d:
            self.kh.audit = audit.AuditLog(Path(d) / "a.jsonl", clock=self.clock)
            self.kh.create_kek("state")
            self.kh.create_dek("a", "state")
            self.kh.create_dek("b", "state")
            rep = self.kh.compromise("state")
            self.assertEqual(sorted(rep["rewrap_required"]), ["DEK:a:v1", "DEK:b:v1"])
            self.assertEqual(rep["new_kek"]["version"], 2)
            self.assertEqual(self.kh.active("DEK", "a").parent, ("state", 2))
            ok, _, entries = audit.verify_file(Path(d) / "a.jsonl")
            self.assertTrue(ok)
            self.assertIn("key.compromise", [e["action"] for e in entries])
        with self.assertRaises(Inv08Error):
            self.kh.compromise("nope")


# ======================================================================= 39
class AuditLogTests(TmpDir):
    def make(self, n=5):
        p = self.dir / "audit.jsonl"
        log = audit.AuditLog(p)
        for i in range(n):
            log.append("ctl", "tick", f"pool-{i}", "SUCCESS", {"i": i, "token": "secret-xyz"})
        return p, log

    def lines(self, p):
        return p.read_bytes().splitlines()

    def test_schema_fields_and_redaction(self):
        p, _ = self.make(2)
        ok, problems, entries = audit.verify_file(p)
        self.assertTrue(ok, problems)
        for e in entries:
            self.assertTrue(set(audit.REQUIRED) <= set(e))
            self.assertEqual(e["schema"], audit.SCHEMA)
            self.assertEqual(e["details"]["token"], "[REDACTED]")
        with self.assertRaises(ValueError):
            audit.AuditLog(self.dir / "x.jsonl").append("", "a", "r", "o")

    def test_hash_chain_and_signed_checkpoint(self):
        p, log = self.make(3)
        trust = TrustRoot()
        trust.add("cp", K1)
        cp = log.checkpoint(trust, "cp")
        self.assertEqual(audit.verify_against_checkpoint(p, cp, trust), (True, "ok"))
        cp2 = copy.deepcopy(cp)
        cp2["checkpoint"]["head"] = "0" * 64
        self.assertFalse(audit.verify_against_checkpoint(p, cp2, trust)[0])
        self.assertFalse(trust.verify(cp["checkpoint"], cp["signature"], require_production=True))

    def test_sequence_and_timestamp_monotonic(self):
        p = self.dir / "t.jsonl"
        log = audit.AuditLog(p, clock=Clock(10.0))
        log.append("a", "b", "r", "o")
        with self.assertRaises(ValueError):
            log.append("a", "b", "r", "o", ts=5.0)
        log.append("a", "b", "r", "o", ts=10.0)  # equal allowed
        self.assertEqual([e["seq"] for e in audit.read_entries(p)], [1, 2])
        reopened = audit.AuditLog(p)
        self.assertEqual(reopened.append("a", "b", "r", "o", ts=11)["seq"], 3)

    def test_tamper_detected(self):
        p, _ = self.make(4)
        ls = self.lines(p)
        e = json.loads(ls[1])
        e["outcome"] = "FAILURE"
        ls[1] = canonical(e)
        p.write_bytes(b"\n".join(ls) + b"\n")
        ok, problems, _ = audit.verify_file(p)
        self.assertFalse(ok)
        self.assertTrue(any("hash mismatch" in x for x in problems))
        with self.assertRaises(ValueError):
            audit.AuditLog(p)  # refuses to append to tampered log

    def test_reorder_detected(self):
        p, _ = self.make(4)
        ls = self.lines(p)
        ls[1], ls[2] = ls[2], ls[1]
        p.write_bytes(b"\n".join(ls) + b"\n")
        ok, problems, _ = audit.verify_file(p)
        self.assertFalse(ok)
        self.assertTrue(any("reorder" in x or "chain break" in x for x in problems))

    def test_deletion_of_middle_detected(self):
        p, _ = self.make(4)
        ls = self.lines(p)
        del ls[1]
        p.write_bytes(b"\n".join(ls) + b"\n")
        self.assertFalse(audit.verify_file(p)[0])

    def test_truncation_only_detected_by_checkpoint(self):
        p, log = self.make(5)
        trust = TrustRoot()
        trust.add("cp", K1)
        cp = log.checkpoint(trust, "cp")
        ls = self.lines(p)
        p.write_bytes(b"\n".join(ls[:3]) + b"\n")
        self.assertTrue(audit.verify_file(p)[0])  # bare chain cannot see tail truncation
        ok, why = audit.verify_against_checkpoint(p, cp, trust)
        self.assertFalse(ok)
        self.assertIn("truncated", why)

    def test_corrupt_line_detected(self):
        p, _ = self.make(3)
        with open(p, "ab") as fh:
            fh.write(b'{"schema": "PK_DYN_AUD')  # torn write
        ok, problems, _ = audit.verify_file(p)
        self.assertFalse(ok)
        self.assertIn("unparseable", problems[0])
        self.assertEqual(audit.main([str(p)]), 1)
        self.assertEqual(audit.main([]), 64)

    def test_forged_checkpoint_signature(self):
        p, log = self.make(2)
        trust = TrustRoot()
        trust.add("cp", K1)
        cp = log.checkpoint(trust, "cp")
        other = TrustRoot()
        other.add("cp", K2)
        self.assertEqual(audit.verify_against_checkpoint(p, cp, other), (False, "checkpoint signature invalid"))

    def test_retention_and_legal_hold(self):
        days = audit.RETENTION_POLICY["security_audit"]["retain_days"]
        self.assertFalse(audit.may_delete(days - 1, False))
        self.assertFalse(audit.may_delete(days, False))      # boundary: strictly older
        self.assertTrue(audit.may_delete(days + 1, False))
        self.assertFalse(audit.may_delete(days * 10, True))  # legal hold wins
        with self.assertRaises(KeyError):
            audit.may_delete(1, False, "unknown_class")


# ======================================================================= 40
class FuzzParsers(unittest.TestCase):
    SEED = 80808

    def _rand_json(self, rng, depth=0):
        k = rng.randrange(7 if depth < 4 else 4)
        if k == 0:
            return rng.randint(-2 ** 70, 2 ** 70)
        if k == 1:
            return rng.uniform(-1e300, 1e300)
        if k == 2:
            return "".join(chr(rng.choice([rng.randrange(32, 127), rng.randrange(0x80, 0x2fff)])) for _ in range(rng.randrange(8)))
        if k == 3:
            return rng.choice([None, True, False])
        if k == 4:
            return [self._rand_json(rng, depth + 1) for _ in range(rng.randrange(4))]
        return {self._rand_json(rng, 4) if False else str(rng.random()): self._rand_json(rng, depth + 1) for _ in range(rng.randrange(4))}

    def test_canonical_json_roundtrip(self):
        rng = random.Random(self.SEED)
        for _ in range(1500):
            o = self._rand_json(rng)
            b = canonical(o)
            self.assertEqual(canonical(json.loads(b)), b)
        for bad in (float("nan"), {"a": float("inf")}, {1: 2}):
            with self.assertRaises((ValueError, TypeError)):
                canonical(bad)

    def test_pool_tick_random_inputs(self):
        rng = random.Random(self.SEED + 1)
        cands = [0, 1, -1, 2 ** 64, 10 ** 400, 0.5, -0.0, float("nan"), float("inf"), True, None, "3", [], 1e308]
        for _ in range(800):
            p = Pool(min_nodes=rng.randrange(3), max_nodes=rng.randrange(3, 30), per_node=rng.randrange(1, 5),
                     lease_ttl=rng.randrange(1, 5))
            now = 0
            for _ in range(5):
                now_v = rng.choice([now + rng.randrange(3), rng.choice(cands)])
                dem = rng.choice(cands + [rng.uniform(0, 200)])
                before = p.snapshot()
                try:
                    r = p.tick(now_v, dem)
                    now = now_v
                    self.assertLessEqual(r["size"], p.max_nodes)
                    self.assertGreaterEqual(r["size"], min(p.min_nodes, p.max_nodes))
                except (ValueError, OverflowError):
                    self.assertEqual(p.snapshot(), before)  # transactional: no partial commit

    def test_traceparent_fuzz(self):
        rng = random.Random(self.SEED + 2)
        alphabet = "0123456789abcdefABCDEF-xz "
        for _ in range(3000):
            s = "".join(rng.choice(alphabet) for _ in range(rng.randrange(60)))
            ctx = lt.parse_traceparent(s)
            if ctx is not None:
                self.assertEqual(lt.parse_traceparent(ctx.traceparent()), ctx)
        good = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        self.assertIsNotNone(lt.parse_traceparent(good))
        for bad in (good.upper(), good + "\n", good + "-x", "ff" + good[2:], "00-" + "0" * 32 + good[35:], None, 5):
            self.assertIsNone(lt.parse_traceparent(bad))

    def test_attestation_evidence_mutation_fuzz(self):
        clock = Clock(0)
        trust = TrustRoot()
        ni = at.NonceIssuer(clock, random.Random(3))
        dev = at.SimulatedDevice("n", "d", K1, trust)
        dev.measure(0, b"x")
        v = at.AttestationVerifier(trust, ni, at.AttestationPolicy(), clock)
        rng = random.Random(self.SEED + 3)
        base = dev.quote(ni.issue(), 0)
        for _ in range(400):
            ev = copy.deepcopy(base)
            key = rng.choice(["node_id", "nonce", "ts", "rot", "pcrs", "event_log", "quote", "schema"])
            ev[key] = rng.choice([None, 1, "x", [], {}, float("inf"), {"type": "sim"}])
            self.assertFalse(v.evaluate(ev).admitted)

    def test_audit_line_fuzz(self):
        rng = random.Random(self.SEED + 4)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.jsonl"
            log = audit.AuditLog(p)
            for i in range(5):
                log.append("a", "b", str(i), "o")
            raw = p.read_bytes()
            for _ in range(200):
                b = bytearray(raw)
                i = rng.randrange(len(b))
                b[i] = (b[i] + rng.randrange(1, 255)) % 256
                if bytes(b) == raw:
                    continue
                p.write_bytes(bytes(b))
                try:
                    ok, problems, _ = audit.verify_file(p)
                except UnicodeDecodeError:
                    continue  # known audit.py defect, pinned by test_invalid_utf8_reported_not_raised
                if ok:  # only whitespace-insignificant flips may survive
                    self.assertEqual([json.loads(x) for x in bytes(b).splitlines() if x.strip()],
                                     [json.loads(x) for x in raw.splitlines()])


class AuditKnownDefects(TmpDir):
    def test_invalid_utf8_reported_not_raised(self):
        """Regression: found by the seeded audit-line fuzzer (read_entries caught only
        JSONDecodeError, so a non-UTF-8 byte raised UnicodeDecodeError).  Fixed in
        audit.py by also catching UnicodeDecodeError; must now report, not raise."""
        p = self.dir / "a.jsonl"
        audit.AuditLog(p).append("a", "b", "r", "o")
        p.write_bytes(p.read_bytes() + b"\x80garbage\n")
        ok, problems, _ = audit.verify_file(p)
        self.assertFalse(ok)
        self.assertIn("unparseable", problems[0])
        with self.assertRaises(ValueError):
            audit.AuditLog(p)


class AdversarialReplaySpoof(unittest.TestCase):
    def test_trustroot_spoof_and_replay(self):
        t = TrustRoot()
        t.add("a", K1)
        sig = t.sign("a", {"op": "scale", "n": 5})
        self.assertTrue(t.verify({"op": "scale", "n": 5}, sig))
        self.assertFalse(t.verify({"op": "scale", "n": 6}, sig))              # payload swap
        self.assertFalse(t.verify({"op": "scale", "n": 5}, dict(sig, kid="b")))  # unknown kid
        self.assertFalse(t.verify({"op": "scale", "n": 5}, dict(sig, alg="none")))
        self.assertFalse(t.verify({"op": "scale", "n": 5}, "garbage"))
        t.revoke("a")
        self.assertFalse(t.verify({"op": "scale", "n": 5}, sig))
        with self.assertRaises(PermissionError):
            t.sign("a", {})

    def test_log_and_json_injection(self):
        lines = []
        lg = lt.StructuredLogger(lines.append, Clock(1))
        ctx = lt.new_root(random.Random(1))
        lg.log("info", "pool.tick", 'evil\n{"schema":"PK_DYN_LOG/1","seq":99}', ctx=ctx, op_id="op1")
        self.assertEqual(len(lines), 1)
        self.assertTrue(lt.verify_lines(lines)[0])
        self.assertEqual(json.loads(lines[0])["seq"], 1)
        with self.assertRaises(ValueError):
            lg.log("info", "Bad Event\n", "m", ctx=ctx, op_id="op")

    def test_nonce_replay_across_verifiers_is_unknown(self):
        clock = Clock(0)
        trust = TrustRoot()
        dev = at.SimulatedDevice("n", "d", K1, trust)
        v1 = at.AttestationVerifier(trust, at.NonceIssuer(clock, random.Random(1)), at.AttestationPolicy(), clock)
        v2 = at.AttestationVerifier(trust, at.NonceIssuer(clock, random.Random(2)), at.AttestationPolicy(), clock)
        ev = dev.quote(v1.nonces.issue(), 0)
        self.assertTrue(v1.evaluate(ev).admitted)
        self.assertEqual(v2.evaluate(ev).reasons, ["unknown_nonce"])


class AdversarialAuthz(unittest.TestCase):
    def test_production_gate_cannot_be_satisfied(self):
        t = TrustRoot()
        with self.assertRaises(PermissionError):
            t.add("p", K1, production=True)
        t.add("np", K1)
        self.assertFalse(t.verify({}, t.sign("np", {}), require_production=True))
        with self.assertRaises(ValueError):
            t.add("weak", b"short")

    def test_tenant_cannot_escalate(self):
        back = {}
        iso.NamespacedState(back, "alpha")["secret"] = 1
        beta = iso.NamespacedState(back, "beta")
        for probe in ("alpha\x00secret", "../alpha/secret", "secret"):
            try:
                self.assertNotIn(probe, beta)
            except Inv08Error:
                pass
        self.assertEqual(list(beta.keys()), [])

    def test_explain_role_denied_and_tenant_view_minimal(self):
        with tempfile.TemporaryDirectory() as d:
            j = explain.DecisionJournal(Path(d) / "j.jsonl", Clock(0))
            j.record_tick(Pool(min_nodes=1, max_nodes=4), 1, 3)
            with self.assertRaises(Inv08Error):
                j.explain("d-1", role="root")
            v = j.explain("d-1", role="tenant")
            self.assertNotIn("pre_state", v)
            self.assertNotIn("graph", v)

    def test_revoked_key_unusable(self):
        kh = keys.KeyHierarchy(K1, Clock(0))
        kh.create_kek("s")
        kh.revoke("KEK", "s", 1, "t")
        for purpose in ("encrypt", "decrypt"):
            with self.assertRaises(Inv08Error):
                kh.material_for("KEK", "s", 1, purpose=purpose)
        with self.assertRaises(Inv08Error):
            kh.create_dek("d", "s")


class AdversarialExhaustion(unittest.TestCase):
    def assertFast(self, fn, limit=1.0):
        t0 = time.perf_counter()
        fn()
        self.assertLess(time.perf_counter() - t0, limit)

    def test_huge_demand_bounded(self):
        p = Pool(min_nodes=0, max_nodes=10000, per_node=1)
        self.assertFast(lambda: p.tick(0, 10 ** 100000), 2.0)
        self.assertEqual(len(p.nodes), 10000)
        self.assertFast(lambda: p.tick(1, 0), 2.0)

    def test_parser_inputs_bounded(self):
        self.assertFast(lambda: lt.parse_traceparent("0" * 10 ** 6))
        deep = "[" * 100000 + "]" * 100000
        with self.assertRaises(RecursionError):
            json.loads(deep)  # stdlib bounds recursion; callers must catch
        ev = {"schema": at.SCHEMA, "node_id": "n", "nonce": "x", "ts": 0, "rot": {"type": "sim", "device_id": "d"},
              "pcrs": {}, "event_log": [{"pcr": 0, "digest": "0" * 64}] * (at.MAX_EVENTS + 1), "quote": {}}
        self.assertFalse(at._well_formed(ev))

    def test_metrics_cardinality_bounded(self):
        r = metrics.Registry(Clock(0))
        for i in range(10000):
            r.inc("inv08_tick_errors_total", reason=f"r{i}")
        self.assertEqual(len(r._v["inv08_tick_errors_total"]), 20)
        self.assertEqual(r.value("inv08_exporter_cardinality_rejections_total", metric="inv08_tick_errors_total"), 9980)

    def test_saturation_trials_bounded(self):
        with self.assertRaises(Inv08Error):
            capacity.saturation_probability(max_nodes=1, per_node=1, demand_mean=1, demand_sd=0,
                                            node_failure_p=0, trials=10 ** 9, rng=random.Random(0))


class AdversarialLeakage(unittest.TestCase):
    SECRETS = ["password=hunter2", "api_key: AKIAABCDEFGHIJKLMNOP", "ops@example.com",
               "-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----"]

    def test_error_to_dict_redacts(self):
        for s in self.SECRETS:
            inner = Inv08Error("INV08.X.Y", f"inner {s}", details={"token": "tok123", "note": s})
            e = Inv08Error("INV08.X.Z", f"failed with {s}", details={"password": "hunter2", "n": [s]}, cause=inner)
            out = json.dumps(e.to_dict())
            for frag in ("hunter2", "AKIAABCDEFGHIJKLMNOP", "ops@example.com", "MIIE", "tok123"):
                self.assertNotIn(frag, out)

    def test_redact_nested_and_logger(self):
        r = redact({"Authorization": "Bearer x", "a": [{"secret": 1}, "token=abc"]})
        self.assertEqual(r["Authorization"], "[REDACTED]")
        self.assertEqual(r["a"][0]["secret"], "[REDACTED]")
        self.assertNotIn("abc", json.dumps(r))
        lines = []
        lt.StructuredLogger(lines.append, Clock(0)).log("error", "x.y", "password=hunter2", ctx=lt.new_root(random.Random(0)),
                                                         op_id="o", api_key="zzz")
        self.assertNotIn("hunter2", lines[0])
        self.assertNotIn("zzz", lines[0])

    def test_key_material_never_serialised(self):
        kh = keys.KeyHierarchy(K1, Clock(0))
        kv = kh.create_kek("s")
        blob = json.dumps(kv.describe()) + repr(kv) + repr(kh)
        self.assertNotIn(kv._material.hex(), blob)
        self.assertNotIn(K1.hex(), blob)

    def test_constant_time_compare_used(self):
        import inspect
        from .. import core
        self.assertIn("compare_digest", inspect.getsource(core.TrustRoot.verify))
        self.assertIn("compare_digest", inspect.getsource(av.verify_digest))


# ======================================================================= 47 / 48
class BenchTests(TmpDir):
    def test_harness_warmup_and_stats(self):
        calls = []
        ticks = iter(range(10 ** 6))
        r = bench.run_case(lambda: calls.append(1), warmup=7, iterations=10, repeats=2,
                           timer=lambda: float(next(ticks)), profile=False)
        self.assertEqual(len(calls), 27)
        self.assertEqual(r["samples"], 20)
        self.assertEqual((r["p50"], r["max"]), (1.0, 1.0))
        with self.assertRaises(ValueError):
            bench.run_case(lambda: None, iterations=0)

    def test_percentile_nearest_rank(self):
        v = list(range(1, 101))
        self.assertEqual([bench.percentile(v, q) for q in (50, 95, 99, 100, 0)], [50, 95, 99, 100, 1])
        with self.assertRaises(ValueError):
            bench.percentile([], 50)

    def test_baseline_suite_quick(self):
        res = bench.run_suite(quick=True)
        c = res["cases"]["tick_100"]
        self.assertLessEqual(c["p50"], c["p95"])
        self.assertLessEqual(c["p99"], c["max"])
        self.assertGreater(c["throughput_per_s"], 0)
        self.assertIsNotNone(c["peak_alloc_bytes"])
        self.assertGreater(c["cpu_seconds"], 0)
        self.assertEqual(res["cases"]["convergence_100"]["value"], 1)
        self.assertIn("startup_pool_100", res["cases"])

    def test_convergence_failure(self):
        self.assertEqual(bench.convergence_ticks(5, 12), 1)
        with self.assertRaises(Inv08Error):
            bench.convergence_ticks(5, 12, limit=0)

    def test_env_capture_and_storage(self):
        res = bench.run_suite(quick=True)
        for k in ("python", "platform", "cpu_count", "model_sha256"):
            self.assertIn(k, res["env"])
        p = self.dir / "r.json"
        bench.save(res, p)
        self.assertEqual(bench.load(p), json.loads(json.dumps(res)))
        p.write_text('{"schema":"x"}')
        with self.assertRaises(Inv08Error):
            bench.load(p)

    def _res(self, p50, machine="x86_64"):
        return {"schema": bench.SCHEMA, "env": {"machine": machine, "implementation": "CPython"},
                "cases": {"tick": {"unit": "seconds", "p50": p50, "p95": p50 * 2, "p99": p50 * 3}}}

    def test_budgets_proposed_and_checked(self):
        self.assertEqual(bench.LATENCY_BUDGETS["status"], "PROPOSED")
        good = {"cases": {"tick_100": {"p50": 1e-6, "p95": 1e-6, "p99": 1e-6, "max": 1e-6}}}
        self.assertEqual(bench.check_budgets(good), [])
        bad = {"cases": {"tick_100": {"p50": 1.0, "p95": 1e-6, "p99": 1e-6, "max": 1e-6}}}
        self.assertEqual(len(bench.check_budgets(bad)), 1)
        self.assertEqual(bench.check_budgets({"cases": {}}), ["tick_100: missing"])

    def test_slo_error_budget(self):
        self.assertEqual(bench.error_budget_remaining(1000, 1000, 0.999), 1.0)
        self.assertAlmostEqual(bench.error_budget_remaining(999, 1000, 0.999), 0.0)
        self.assertLess(bench.error_budget_remaining(990, 1000, 0.999), 0)
        self.assertEqual(bench.error_budget_remaining(0, 0, 0.99), 1.0)
        with self.assertRaises(ValueError):
            bench.error_budget_remaining(5, 4, 0.99)

    def test_regression_gate_noise_tolerance(self):
        base = self._res(0.001)
        self.assertTrue(bench.compare(base, self._res(0.00120))["passed"])      # +20%: noise
        v = bench.compare(base, self._res(0.0015))
        self.assertFalse(v["passed"])
        self.assertEqual({r["metric"] for r in v["regressions"]}, {"p50", "p95", "p99"})
        tiny = self._res(1e-6)
        self.assertTrue(bench.compare(tiny, self._res(3e-6))["passed"])       # below absolute floor
        self.assertFalse(bench.compare(base, self._res(0.001, machine="arm64"))["passed"])
        self.assertFalse(bench.compare(base, dict(self._res(0.001), cases={}))["passed"])
        with self.assertRaises(Inv08Error):
            bench.compare(base, {"schema": "x"})

    def test_ci_gate_cli(self):
        out, basep = self.dir / "o.json", self.dir / "b.json"
        self.assertEqual(bench.main(["--quick", "--out", str(basep)]), 0)
        b = bench.load(basep)
        b["cases"]["convergence_100"]["value"] = 0  # impossible baseline -> regression
        bench.save(b, basep)
        self.assertEqual(bench.main(["--quick", "--out", str(out), "--baseline", str(basep)]), 1)


# ======================================================================= 49
class CapacityTests(unittest.TestCase):
    def test_churn_model_deterministic(self):
        cm = capacity.ChurnModel(base_demand=40)
        a = cm.simulate(Pool(min_nodes=1, max_nodes=30), 200, random.Random(5))
        b = cm.simulate(Pool(min_nodes=1, max_nodes=30), 200, random.Random(5))
        self.assertEqual(a, b)
        self.assertLessEqual(a["peak_nodes"], 30)
        with self.assertRaises(Inv08Error):
            capacity.ChurnModel(base_demand=-1)
        with self.assertRaises(Inv08Error):
            cm.simulate(Pool(min_nodes=0, max_nodes=1), 0, random.Random(0))

    def test_latency_inputs_marked(self):
        self.assertEqual(capacity.ASSUMED_PROVISION.source, "assumed")
        self.assertEqual(capacity.ASSUMED_PROVISION.quantile(0.5), 90)
        self.assertEqual(capacity.ASSUMED_PROVISION.quantile(1.0), 300)
        with self.assertRaises(Inv08Error):
            capacity.LatencyDistribution([1.0], "measured")
        with self.assertRaises(Inv08Error):
            capacity.LatencyDistribution([float("nan")])
        capacity.LatencyDistribution([1.0], "measured", provenance="run-123")

    def test_quota_model(self):
        q = capacity.QuotaModel(max_instances=10, creates_per_minute=4)
        self.assertEqual(q.admit(0, 6, 0.0), {"admitted": 4, "quota_denied": 0, "rate_limited": 2})
        self.assertEqual(q.admit(4, 10, 1.0)["quota_denied"], 4)
        with self.assertRaises(Inv08Error):
            q.admit(0, 1, 0.5)
        with self.assertRaises(Inv08Error):
            capacity.QuotaModel(max_instances=1, creates_per_minute=0)

    def test_saturation_probability(self):
        rng = random.Random
        lo = capacity.saturation_probability(max_nodes=100, per_node=4, demand_mean=100, demand_sd=10,
                                             node_failure_p=0.0, trials=2000, rng=rng(1))
        hi = capacity.saturation_probability(max_nodes=26, per_node=4, demand_mean=100, demand_sd=10,
                                             node_failure_p=0.05, trials=2000, rng=rng(1))
        q = capacity.saturation_probability(max_nodes=100, per_node=4, demand_mean=100, demand_sd=10,
                                            node_failure_p=0.0, quota=20, trials=2000, rng=rng(1))
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.3)
        self.assertGreater(q, 0.9)
        with self.assertRaises(Inv08Error):
            capacity.saturation_probability(max_nodes=1, per_node=1, demand_mean=1, demand_sd=1,
                                            node_failure_p=2, rng=rng(0))

    def test_headroom_policy(self):
        r = capacity.headroom_policy(per_node=4, demand_mean=100, demand_sd=10, node_failure_p=0.01, quota=40, trials=500)
        self.assertLessEqual(r["saturation_probability"], 0.01)
        self.assertGreaterEqual(r["headroom_fraction"], 0.15)
        self.assertEqual(r["status"], "PROPOSED")
        self.assertTrue(r["quota_ok"])
        r2 = capacity.headroom_policy(per_node=4, demand_mean=100, demand_sd=10, node_failure_p=0.01, quota=10, trials=500)
        self.assertFalse(r2["quota_ok"])


# ======================================================================= 50
class PowerTests(unittest.TestCase):
    def test_power_telemetry_validation(self):
        ok = power.validate_power({"node": "n1", "ts": 100, "watts": 120, "source": "sim"}, now=110)
        self.assertEqual(ok["watts"], 120.0)
        for bad in ({"node": "n1", "ts": 100, "watts": -1, "source": "sim"},
                    {"node": "n1", "ts": 100, "watts": 1e9, "source": "sim"},
                    {"node": "n1", "ts": 100, "watts": float("nan"), "source": "sim"},
                    {"node": "n1", "ts": 0, "watts": 1, "source": "sim"},
                    {"node": "n1", "ts": 100, "watts": 1, "source": "guess"}, None):
            with self.assertRaises(Inv08Error):
                power.validate_power(bad, now=110)

    def test_thermal_telemetry_validation(self):
        power.validate_thermal({"node": "n", "ts": 1, "sensor": "cpu", "celsius": 50}, now=1)
        for c in (-41, 151, True, "hot"):
            with self.assertRaises(Inv08Error):
                power.validate_thermal({"node": "n", "ts": 1, "sensor": "cpu", "celsius": c}, now=1)

    def test_budget_model(self):
        b = power.PowerBudget(budget_w=1000, idle_w=50, peak_w=200, margin=0.1)
        self.assertEqual(b.max_nodes(), 4)
        self.assertFalse(b.check({"a": {"busy": True}, "b": {"busy": False}})["over_budget"])
        self.assertTrue(b.check({str(i): {"busy": True} for i in range(5)})["over_budget"])
        with self.assertRaises(Inv08Error):
            power.PowerBudget(budget_w=1, idle_w=10, peak_w=5)

    def test_derating_response(self):
        pol = power.ThermalPolicy(80, 90)
        self.assertEqual([pol.factor(c) for c in (70, 85, 95)], [1.0, 0.5, 0.0])
        pool = Pool(min_nodes=0, max_nodes=10)
        pool.tick(0, 40)
        b = power.PowerBudget(budget_w=100000, idle_w=50, peak_w=200)
        names = sorted(pool.nodes)
        samples = [{"node": n, "ts": 0, "sensor": "cpu", "celsius": 95 if i < 6 else 60} for i, n in enumerate(names)]
        samples.append({"node": names[0], "ts": 0, "sensor": "gpu", "celsius": "bad"})
        d = power.derate(pool, b, pol, samples, now=0)
        self.assertEqual(d["cap_nodes"], 4)
        self.assertEqual(sum(a == "SHED" for a in d["actions"].values()), 6)
        self.assertEqual(d["invalid_samples"], [names[0]])
        r = power.capped_tick(pool, 1, 40, d["cap_nodes"])
        self.assertEqual(r["size"], 4)
        self.assertEqual(pool.max_nodes, 10)  # limits never mutated
        with self.assertRaises(Inv08Error):
            power.ThermalPolicy(90, 80)

    def test_derating_missing_telemetry_fails_safe(self):
        pool = Pool(min_nodes=0, max_nodes=4)
        pool.tick(0, 16)
        d = power.derate(pool, power.PowerBudget(budget_w=1e6, idle_w=1, peak_w=2), power.ThermalPolicy(), [], now=0)
        self.assertEqual(d["cap_nodes"], 2)
        self.assertEqual(set(d["actions"].values()), {"DERATE"})

    def test_energy_efficiency(self):
        s = [{"node": f"n{i}", "ts": 0, "watts": 100, "source": "sim"} for i in range(3)]
        r = power.energy_efficiency(s, work_units=30, now=0, interval_s=3600)
        self.assertEqual(r["joules_per_unit"], 3 * 100 * 3600 / 30)
        with self.assertRaises(Inv08Error):
            power.energy_efficiency(s, work_units=0, now=0, interval_s=1)


# ======================================================================= 51
class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.reg = metrics.Registry(Clock(42.0))

    def test_exporter_exposition_and_wsgi(self):
        ip = metrics.InstrumentedPool(Pool(min_nodes=1, max_nodes=8), self.reg, iter([0.0, 0.001] * 100).__next__)
        ip.tick(0, 10)
        text = self.reg.scrape()
        self.assertIn("# TYPE inv08_pool_nodes gauge", text)
        self.assertIn("inv08_pool_nodes 3", text)
        self.assertIn('inv08_decision_latency_seconds_bucket{le="+Inf"} 1', text)
        got = {}
        body = metrics.wsgi_app(self.reg)({"PATH_INFO": "/metrics", "REQUEST_METHOD": "GET"},
                                          lambda s, h: got.update(status=s, headers=h))
        self.assertEqual(got["status"], "200 OK")
        self.assertIn(b"inv08_exporter_scrapes_total 2", body[0])
        metrics.wsgi_app(self.reg)({"PATH_INFO": "/x"}, lambda s, h: got.update(status=s))
        self.assertEqual(got["status"], "404 Not Found")

    def test_naming_and_units(self):
        metrics.validate_catalog()
        for bad in ({"inv08_x": ("gauge", "", (), 1, None)}, {"inv08_x_seconds": ("counter", "", (), 1, None)},
                    {"Bad_total": ("counter", "", (), 1, None)}, {"inv08_x_seconds": ("histogram", "", (), 1, (2, 1))},
                    {"inv08_x_total": ("counter", "", ("le",), 1, None)}):
            with self.assertRaises(Inv08Error):
                metrics.validate_catalog(bad)
        with self.assertRaises(Inv08Error):
            self.reg.inc("inv08_pool_nodes")          # wrong type
        with self.assertRaises(Inv08Error):
            self.reg.inc("inv08_pool_nodes_added_total", -1)
        with self.assertRaises(Inv08Error):
            self.reg.set("inv08_nope", 1)

    def test_histograms_latency_and_lease_age(self):
        for v in (0.00005, 0.003, 5.0):
            self.reg.observe("inv08_decision_latency_seconds", v)
        h = self.reg.value("inv08_decision_latency_seconds")
        self.assertEqual(h["count"], 3)
        self.assertEqual(h["b"][0], 1)
        self.assertEqual(h["b"][-1], 2)   # 5.0 only in +Inf
        timer = iter([float(i) * 1e-4 for i in range(1000)]).__next__
        ip = metrics.InstrumentedPool(Pool(min_nodes=0, max_nodes=4, lease_ttl=2), self.reg, timer)
        ip.tick(0, 16)
        ip.tick(5, 0)
        la = self.reg.value("inv08_lease_age_seconds")
        self.assertEqual(la["count"], 4)
        self.assertEqual(la["sum"], 4 * 5 * 3600.0)
        with self.assertRaises(Inv08Error):
            self.reg.observe("inv08_decision_latency_seconds", float("nan"))

    def test_label_cardinality_governance(self):
        with self.assertRaises(Inv08Error):
            self.reg.inc("inv08_tick_errors_total", tenant="x")
        with self.assertRaises(Inv08Error):
            self.reg.inc("inv08_tick_errors_total")
        for i in range(25):
            self.reg.inc("inv08_tick_errors_total", reason=f"r{i}")
        self.assertEqual(len(self.reg._v["inv08_tick_errors_total"]), 20)
        self.reg.inc("inv08_policy_rejections_total", check='a"b\nc\\')
        self.assertIn('check="a\\"b\\nc\\\\"', self.reg.render())

    def test_scrape_failure_self_health(self):
        self.reg.fail_next_render = True
        out = self.reg.scrape()
        self.assertIn("inv08_exporter_scrape_errors_total 1", out)
        self.assertIn("inv08_exporter_scrape_errors_total 1", self.reg.scrape())
        self.assertEqual(self.reg.value("inv08_exporter_last_scrape_timestamp_seconds"), 42.0)

    def test_tick_error_counted(self):
        ip = metrics.InstrumentedPool(Pool(min_nodes=0, max_nodes=2), self.reg, lambda: 0.0)
        with self.assertRaises(ValueError):
            ip.tick(0, -1)
        self.assertEqual(self.reg.value("inv08_tick_errors_total", reason="ValueError"), 1)
        ip.tick(0, 10 ** 400)
        self.assertGreater(self.reg.value("inv08_pool_demand_units"), 1e300)


# ======================================================================= 52
class LoggingTraceTests(unittest.TestCase):
    def setUp(self):
        self.lines = []
        self.rng = random.Random(9)
        self.lg = lt.StructuredLogger(self.lines.append, Clock(7.0))
        self.ctx = lt.new_root(self.rng)

    def test_schema(self):
        rec = self.lg.log("info", "pool.tick", "ok", ctx=self.ctx, op_id="op-1", size=3)
        self.assertEqual(set(rec), {"schema", "seq", "ts", "level", "event", "msg", "service", "corr", "trace",
                                    "attrs", "prev", "hash"})
        self.assertEqual(json.loads(self.lines[0]), rec)
        self.assertIsNone(self.lg.log("debug", "pool.tick", "x", ctx=self.ctx, op_id="o"))
        for bad in (("verbose", "a"), ("info", "Bad")):
            with self.assertRaises(ValueError):
                self.lg.log(bad[0], bad[1], "m", ctx=self.ctx, op_id="o")

    def test_correlation_ids(self):
        rec = self.lg.log("info", "lease.renew", "m", ctx=self.ctx, op_id="op-9", tenant="alpha", workload="w1", node="node-3")
        self.assertEqual(rec["corr"], {"op_id": "op-9", "tenant": "alpha", "workload": "w1", "node": "node-3"})
        with self.assertRaises(ValueError):
            self.lg.log("info", "a.b", "m", ctx=self.ctx, op_id="")

    def test_trace_propagation(self):
        child = self.ctx.child(self.rng)
        self.assertEqual((child.trace_id, child.parent_span_id), (self.ctx.trace_id, self.ctx.span_id))
        carrier = lt.inject(child, {})
        got, link = lt.extract(carrier, self.rng, trusted=True)
        self.assertEqual((got.trace_id, got.parent_span_id, link), (child.trace_id, child.span_id, None))
        fresh, link = lt.extract({"traceparent": "garbage"}, self.rng, trusted=True)
        self.assertIsNone(fresh.parent_span_id)
        self.assertFalse(lt.parse_traceparent("00-" + "a" * 32 + "-" + "b" * 16 + "-00").sampled)

    def test_provider_boundary(self):
        span, headers = lt.provider_span(self.ctx, "sim-cloud", self.rng)
        self.assertEqual(lt.parse_traceparent(headers["traceparent"]).span_id, span.span_id)
        spoof = {"traceparent": "00-" + "c" * 32 + "-" + "d" * 16 + "-01"}
        got, link = lt.extract(spoof, self.rng, trusted=False)
        self.assertNotEqual(got.trace_id, "c" * 32)
        self.assertEqual(link, {"link_trace_id": "c" * 32, "link_span_id": "d" * 16})

    def test_redaction_and_integrity(self):
        for i in range(4):
            self.lg.log("info", "a.b", f"n={i} password=pw{i}", ctx=self.ctx, op_id="o", token="t")
        self.assertTrue(lt.verify_lines(self.lines)[0])
        self.assertFalse(any("pw1" in l for l in self.lines))
        for mut in (lambda l: l.__delitem__(1), lambda l: l.reverse(),
                    lambda l: l.__setitem__(2, l[2].replace("n=2", "n=9")), lambda l: l.append("{bad")):
            ls = list(self.lines)
            mut(ls)
            self.assertFalse(lt.verify_lines(ls)[0])
        with self.assertRaises(ValueError):
            self.lg.log("info", "a.b", "m", ctx=self.ctx, op_id="o", x=float("nan"))
        self.lg.log("info", "a.b", "after failure", ctx=self.ctx, op_id="o")
        self.assertTrue(lt.verify_lines(self.lines)[0])   # failed write left no gap


# ======================================================================= 53
class ExplainTests(TmpDir):
    def setUp(self):
        super().setUp()
        self.path = self.dir / "j.jsonl"
        self.j = explain.DecisionJournal(self.path, Clock(1.0))
        self.pool = Pool(min_nodes=1, max_nodes=10, lease_ttl=2)

    def test_journal_schema_durable(self):
        self.j.record_tick(self.pool, 0, 20)
        self.j.record_tick(self.pool, 1, 4)
        recs = self.j.records()
        self.assertEqual([r["id"] for r in recs], ["d-1", "d-2"])
        self.assertTrue(explain.verify_records(recs)[0])
        j2 = explain.DecisionJournal(self.path, Clock(2.0))
        j2.record_tick(self.pool, 2, 4)
        self.assertEqual(j2.records()[-1]["seq"], 3)
        with self.assertRaises(ValueError):
            j2.record_tick(self.pool, 0, 1)  # time regression is journalled as error
        self.assertEqual(explain.DecisionJournal(self.path, Clock(0)).records()[-1]["error"]["type"], "ValueError")

    def test_tampered_journal_refused(self):
        self.j.record_tick(self.pool, 0, 20)
        raw = self.path.read_text().replace('"demand":20', '"demand":21')
        self.path.write_text(raw)
        with self.assertRaises(Inv08Error):
            explain.DecisionJournal(self.path, Clock(0))

    def test_reason_graph(self):
        self.j.record_tick(self.pool, 0, 20)
        self.pool.set_busy("node-1")
        self.j.record_tick(self.pool, 1, 4)
        self.j.record_tick(self.pool, 5, 4)
        g = self.j.records()[1]["graph"]
        ids = {n["id"] for n in g["nodes"]}
        self.assertTrue({"input:demand", "policy:per_node", "constraint:demand_nodes", "decision:target",
                         "action:renew:node-1"} <= ids)
        reasons = {n["reason"] for n in g["nodes"] if n["id"].startswith("action:reclaim")}
        self.assertEqual(reasons, {"idle surplus over target"})
        for a, b, _ in g["edges"]:
            self.assertIn(a, ids)
            self.assertIn(b, ids)

    def test_reason_graph_expiry(self):
        self.j.record_tick(self.pool, 0, 4)
        self.j.record_tick(self.pool, 3, 4)  # lease_ttl=2 -> expired
        g = self.j.records()[1]["graph"]
        self.assertIn("lease expired while idle", {n.get("reason") for n in g["nodes"]})

    def test_explain_query(self):
        self.j.record_tick(self.pool, 0, 20)
        self.j.record_tick(self.pool, 1, 20)
        ex = self.j.explain("d-1")
        self.assertTrue(any("decision:target" in s for s in ex["narrative"]))
        self.assertEqual(len(self.j.query(kind="scaled")), 1)
        self.assertEqual(len(self.j.query(since_ts=5)), 0)
        with self.assertRaises(Inv08Error):
            self.j.explain("d-99")

    def test_replay_and_diff(self):
        self.j.record_tick(self.pool, 0, 20)
        self.pool.set_busy("node-2")
        self.j.record_tick(self.pool, 1, 3)
        self.j.record_tick(self.pool, 2, 10 ** 30)
        for r in self.j.records():
            self.assertEqual(explain.replay(r), {})
        r = copy.deepcopy(self.j.records()[1])
        r["result"]["size"] = 99
        self.assertEqual(explain.replay(r)["size"]["recorded"], 99)
        with self.assertRaises(Inv08Error):
            explain.replay({"schema": explain.SCHEMA, "result": None})

    def test_retention_and_access(self):
        self.assertEqual(explain.RETENTION["owner"], "UNASSIGNED")
        self.assertFalse(explain.may_purge(91, True))
        self.assertTrue(explain.may_purge(91, False))
        self.assertFalse(explain.may_purge(90, False))
        self.j.record_tick(self.pool, 0, 20)
        t = self.j.explain("d-1", role="tenant")
        self.assertEqual(set(t), {"id", "ts", "inputs", "result"})
        self.assertEqual(set(t["result"]), {"size", "target"})
        with self.assertRaises(Inv08Error):
            explain.view({}, "anonymous")


# ======================================================================= 54
class TelemetryGovTests(unittest.TestCase):
    def test_retention_classes(self):
        self.assertEqual(tg.retention_class("audit"), ("security_audit", 400))
        self.assertTrue(set(tg.KIND_CLASS.values()) <= set(tg.RETENTION_CLASSES))
        with self.assertRaises(Inv08Error):
            tg.retention_class("mystery")
        self.assertTrue(tg.expired("span", 8))
        self.assertFalse(tg.expired("span", 8, legal_hold=True))
        self.assertFalse(tg.expired("span", 7))

    def test_sampling_and_aggregation(self):
        ids = ["%032x" % random.Random(i).getrandbits(128) for i in range(4000)]
        kept = sum(tg.keep_sample(t, "info", 0.1) for t in ids)
        self.assertTrue(300 < kept < 500)
        self.assertEqual([tg.keep_sample(t, "info", 0.1) for t in ids[:50]], [tg.keep_sample(t, "info", 0.1) for t in ids[:50]])
        self.assertTrue(all(tg.keep_sample(t, "error", 0.0) for t in ids[:10]))
        with self.assertRaises(Inv08Error):
            tg.keep_sample("x", "info", 1.5)
        r = tg.rollup([(0, 1), (10, 3), (60, 5)], 60)
        self.assertEqual(r, [{"start": 0, "count": 2, "mean": 2.0, "max": 3}, {"start": 60, "count": 1, "mean": 5.0, "max": 5}])
        with self.assertRaises(Inv08Error):
            tg.rollup([], 0)

    def test_minimization(self):
        salt = b"s" * 16
        rec = {"schema": "PK_DYN_LOG/1", "msg": "email me at a@b.io", "corr": {"tenant": "alpha", "op_id": "o"},
               "internal_debug_blob": "x" * 100}
        m = tg.minimize("log", rec, salt)
        self.assertNotIn("internal_debug_blob", m)
        self.assertNotIn("a@b.io", m["msg"])
        self.assertTrue(m["corr"]["tenant"].startswith("p-"))
        self.assertEqual(m["corr"]["tenant"], tg.minimize("log", rec, salt)["corr"]["tenant"])
        self.assertNotEqual(m["corr"]["tenant"], tg.minimize("log", rec, b"t" * 16)["corr"]["tenant"])
        with self.assertRaises(Inv08Error):
            tg.minimize("log", rec, b"short")
        with self.assertRaises(Inv08Error):
            tg.minimize("unknown", rec, salt)

    def test_egress_residency(self):
        tg.check_egress("central-observability", "operational", "eu", "eu", True)
        tg.check_egress("local-store", "security_audit", "eu", "us", False)
        for args in (("central-observability", "operational", "eu", "us", True),
                     ("central-observability", "security_audit", "eu", "eu", True),
                     ("central-observability", "operational", "eu", "eu", False),
                     ("pastebin", "operational", "eu", "eu", True)):
            with self.assertRaises(Inv08Error):
                tg.check_egress(*args)

    def test_high_cardinality_detection(self):
        series = [("inv08_x_total", {"node": f"n{i}", "zone": "a"}) for i in range(150)]
        f = tg.detect_high_cardinality(series)
        self.assertEqual([(x["label"], x["distinct"]) for x in f], [("node", 150)])
        f2 = tg.detect_high_cardinality(series, {"per_metric_series": 100})
        self.assertEqual(f2[-1]["est_bytes"], 150 * tg.BYTES_PER_SERIES)
        self.assertEqual(tg.detect_high_cardinality(series[:5]), [])


# ======================================================================= 55
class DashboardTests(TmpDir):
    def test_fleet_overview_dashboard(self):
        d = dashboards.load_dashboards()["fleet_overview"]
        self.assertIn("inv08_pool_nodes", {p["metric"] for p in d["panels"]})

    def test_capacity_lease_dashboard(self):
        d = dashboards.load_dashboards()["capacity_lease"]
        self.assertTrue({"inv08_lease_age_seconds", "inv08_reconcile_drift_nodes"} <= {p["metric"] for p in d["panels"]})

    def test_security_dashboard(self):
        d = dashboards.load_dashboards()["security_policy"]
        self.assertIn("inv08_attestation_results_total", {p["metric"] for p in d["panels"]})

    def test_provider_dashboard(self):
        d = dashboards.load_dashboards()["provider_degradation"]
        self.assertIn("inv08_provider_errors_total", {p["metric"] for p in d["panels"]})

    def test_dashboard_unknown_metric_rejected(self):
        for did in dashboards.DASHBOARD_IDS:
            src = json.loads((dashboards.FIXTURES / f"{did}.json").read_text())
            if did == "fleet_overview":
                src["panels"][0]["metric"] = "inv08_made_up"
            (self.dir / f"{did}.json").write_text(json.dumps(src))
        with self.assertRaises(Inv08Error):
            dashboards.load_dashboards(self.dir)

    def test_every_alert_references_metric_and_runbook(self):
        alerts = dashboards.load_alerts()
        anchors = dashboards.runbook_anchors()
        for a in alerts:
            self.assertIn(a["metric"], metrics.CATALOG)
            self.assertIn(a["runbook"].split("#")[1], anchors)
            self.assertEqual(a["route"], "UNASSIGNED")
        self.assertEqual({a["severity"] for a in alerts}, {"page", "ticket", "info"})

    def test_alert_bad_runbook_rejected(self):
        src = json.loads((dashboards.FIXTURES / "alerts.json").read_text())
        src["alerts"][0]["runbook"] = "docs/55_runbooks.md#nope"
        (self.dir / "alerts.json").write_text(json.dumps(src))
        with self.assertRaises(Inv08Error):
            dashboards.load_alerts(self.dir)

    def test_alerts_evaluate(self):
        reg = metrics.Registry(Clock(0))
        firing = {a["name"] for a in dashboards.evaluate_alerts(reg)}
        self.assertEqual(firing, {"ExporterAbsent"})
        reg.scrape()
        reg.inc("inv08_tick_errors_total", reason="ValueError")
        reg.inc("inv08_attestation_results_total", action="QUARANTINE")
        reg.inc("inv08_attestation_results_total", action="DENY")
        firing = {a["name"]: a for a in dashboards.evaluate_alerts(reg)}
        self.assertEqual(set(firing), {"PoolTickFailing", "AttestationQuarantine"})
        self.assertEqual(firing["PoolTickFailing"]["severity"], "page")


if __name__ == "__main__":
    unittest.main()
