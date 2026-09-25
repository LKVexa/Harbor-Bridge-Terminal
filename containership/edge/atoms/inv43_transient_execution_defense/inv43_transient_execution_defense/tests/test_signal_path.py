"""Checklist 09-14, 16-18: collector, freshness, attestation, authz, policy, config."""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from _harness import (COSTS, FULL, Fleet, W, attestation, authz, collector, config, make_sysfs, pkg, policy,
                      SYSFS_FIXTURES)

MATRIX = json.loads((pathlib.Path(__file__).parent / "fixtures" / "kernel_strings.json").read_text())


class CollectorTest(unittest.TestCase):
    def test_classifier_is_fail_closed(self):
        c = collector.classify
        self.assertEqual(c("Not affected")[0], pkg.NOT_AFFECTED)
        self.assertEqual(c("Mitigation: PTI")[0], pkg.ACTIVE)
        self.assertEqual(c("Mitigation: Enhanced IBRS; BHI: Vulnerable")[0], pkg.INACTIVE)
        self.assertEqual(c("Vulnerable")[0], pkg.INACTIVE)
        self.assertEqual(c("Vulnerable: Clear CPU buffers attempted, no microcode")[0], pkg.INACTIVE)
        self.assertEqual(c("Unknown: Dependent on hypervisor status")[0], pkg.UNKNOWN)
        self.assertEqual(c("KVM: Mitigation: VMX disabled")[0], pkg.ACTIVE)
        for junk in (None, "", "mitigation: lowercase", "Processor vulnerable", "\x00"):
            self.assertEqual(c(junk)[0], pkg.UNKNOWN, junk)

    def test_smt_classification(self):
        self.assertEqual(collector.classify_smt("on", None)[0], True)
        self.assertEqual(collector.classify_smt("notsupported", None)[0], False)
        self.assertEqual(collector.classify_smt("forceoff", None)[0], False)
        self.assertIsNone(collector.classify_smt(None, None)[0])
        self.assertIsNone(collector.classify_smt("garbage", None)[0])

    def test_unknown_smt_is_treated_as_enabled(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_sysfs(pathlib.Path(d), FULL, smt="garbage")
            rb = collector.collect("n", root=root)
            state, _ = rb.to_state(COSTS)
            self.assertTrue(state.smt_enabled)

    def test_active_without_measured_cost_becomes_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            rb = collector.collect("n", root=make_sysfs(pathlib.Path(d), FULL))
            state, notes = rb.to_state({})  # no benchmark costs
            self.assertEqual(state.status("spectre_v2"), pkg.UNKNOWN)
            self.assertIn("active_without_measured_cost", {n["code"] for n in notes})
            with self.assertRaises(pkg.MitigationMissing):
                state.may_cotenant("a", "b")

    def test_oversized_or_binary_sysfs_is_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_sysfs(pathlib.Path(d), FULL)
            (root / collector.SYSFS_VULN_DIR / "mds").write_bytes(b"Not affected" + b" " * 10000)
            (root / collector.SYSFS_VULN_DIR / "l1tf").write_bytes(b"\xffNot affected")
            rb = collector.collect("n", root=root)
            st = {o.mitigation: o.status for o in rb.observations}
            self.assertEqual(st["mds"], pkg.UNKNOWN)
            self.assertEqual(st["l1tf"], pkg.UNKNOWN)

    def test_path_traversal_mitigation_names_refused(self):
        with self.assertRaises(ValueError):
            collector.collect("n", root="/", mitigations=("../../etc/passwd",))

    def test_freshness_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            rb = collector.collect("n", root=make_sysfs(pathlib.Path(d), FULL), ttl_s=10, clock=lambda: 5.0,
                                   mono=lambda: 100.0)
            o = rb.observations[0]
            self.assertEqual((o.collector_id, o.observed_at_unix, o.ttl_s), (collector.COLLECTOR_ID, 5.0, 10.0))
            self.assertTrue(o.source.startswith("sysfs:"))
            self.assertTrue(o.is_fresh(109.0))
            self.assertFalse(o.is_fresh(111.0))

    def test_compatibility_matrix_strings_classify_without_crash(self):
        # checklist 43: every catalogued kernel format yields a defined status
        for label, entry in MATRIX.items():
            if label.startswith("_"):
                continue
            for name, raw in entry["vulns"].items():
                st, _ = collector.classify(raw)
                self.assertIn(st, pkg.VALID_STATUSES, (label, name, raw))

    def test_real_host_readback(self):
        # checklist 09 evidence: read this machine's actual kernel report
        rb = collector.collect(collector.local_node_id())
        if not rb.observations:
            self.skipTest("host exposes no /sys vulnerabilities directory")
        for o in rb.observations:
            self.assertEqual(o.status, collector.classify(o.raw)[0])


class AttestationTest(unittest.TestCase):
    def setUp(self):
        self.reg = attestation.KeyRegistry()
        self.kid, self.sec = self.reg.enrol("node-a")
        self.payload = {"node": "node-a", "x": 1}

    def seal(self, seq=1, **kw):
        return attestation.seal(self.payload, node="node-a", key_id=self.kid, secret=self.sec, seq=seq,
                                now=kw.pop("now", 1000.0), **kw)

    def code(self, env, now=1000.0):
        with self.assertRaises(attestation.AttestationError) as cm:
            attestation.verify(env, self.reg, now=now)
        return cm.exception.code

    def test_roundtrip(self):
        self.assertEqual(attestation.verify(self.seal(), self.reg, now=1000.0), self.payload)

    def test_replay_rejected(self):
        env = self.seal(seq=5)
        attestation.verify(env, self.reg, now=1000.0)
        self.assertEqual(self.code(env), "attestation_replay")
        self.assertEqual(self.code(self.seal(seq=4)), "attestation_replay")

    def test_tamper_rejected(self):
        env = self.seal()
        env["payload"] = {"node": "node-a", "x": 2}
        self.assertEqual(self.code(env), "attestation_payload_mismatch")
        env = self.seal()
        env["header"]["seq"] = 99
        self.assertEqual(self.code(env), "attestation_bad_mac")

    def test_wrong_node_binding(self):
        kid_b, sec_b = self.reg.enrol("node-b")
        env = attestation.seal({"node": "node-a"}, node="node-a", key_id=kid_b, secret=sec_b, seq=1, now=1000.0)
        self.assertEqual(self.code(env), "attestation_node_mismatch")

    def test_unknown_revoked_expired(self):
        env = self.seal()
        env["header"]["key_id"] = "nope"
        self.assertEqual(self.code(env), "attestation_unknown_key")
        self.reg.revoke(self.kid)
        self.assertEqual(self.code(self.seal(seq=2)), "attestation_revoked_key")
        kid, sec = self.reg.enrol("node-a", not_after_unix=500.0)
        env = attestation.seal(self.payload, node="node-a", key_id=kid, secret=sec, seq=1, now=1000.0)
        self.assertEqual(self.code(env), "attestation_expired_key")

    def test_expired_and_future_envelopes(self):
        self.assertEqual(self.code(self.seal(ttl_s=10), now=1011.0), "attestation_expired")
        self.assertEqual(self.code(self.seal(now=2000.0), now=1000.0), "attestation_clock_skew")

    def test_malformed(self):
        for bad in (None, {}, {"header": {}, "payload": {}}, {"header": {}, "payload": {}, "mac": "!!", "x": 1}):
            with self.assertRaises(attestation.AttestationError):
                attestation.verify(bad, self.reg, now=1000.0)

    def test_short_secret_refused_and_repr_hides_secret(self):
        with self.assertRaises(ValueError):
            self.reg.enrol("node-c", secret=b"short")
        self.assertNotIn(self.sec.hex(), repr(self.reg._get(self.kid)))
        self.assertNotIn(repr(self.sec), repr(self.reg._get(self.kid)))

    def test_rotation(self):
        new_kid, new_sec = self.reg.rotate(self.kid)
        self.assertEqual(self.code(self.seal(seq=3)), "attestation_revoked_key")
        env = attestation.seal(self.payload, node="node-a", key_id=new_kid, secret=new_sec, seq=1, now=1000.0)
        self.assertEqual(attestation.verify(env, self.reg, now=1000.0), self.payload)


class AuthzTest(unittest.TestCase):
    def setUp(self):
        self.az = authz.Authorizer()
        self.az.grant("c1", {"collector"}, node_scope={"n1"})
        self.az.grant("s", {"scheduler"})

    def test_deny_by_default(self):
        with self.assertRaises(authz.AuthzDenied):
            self.az.check("nobody", authz.CAP_POSTURE_READ, "n1")
        with self.assertRaises(authz.AuthzDenied):
            self.az.check(None, authz.CAP_POSTURE_READ, "n1")
        with self.assertRaises(authz.AuthzDenied):
            self.az.check("s", "*", "n1")

    def test_least_privilege(self):
        self.az.check("c1", authz.CAP_POSTURE_WRITE, "n1")
        for cap, node in ((authz.CAP_POSTURE_WRITE, "n2"), (authz.CAP_COTENANCY_DECIDE, "n1"),
                          (authz.CAP_POSTURE_WRITE, None)):
            with self.assertRaises(authz.AuthzDenied):
                self.az.check("c1", cap, node)
        with self.assertRaises(authz.AuthzDenied):
            self.az.check("s", authz.CAP_POSTURE_WRITE, "n1")  # scheduler cannot forge posture
        with self.assertRaises(authz.AuthzDenied):
            self.az.check("s", authz.CAP_CONTROL, "n1")

    def test_collector_separation_of_duty(self):
        with self.assertRaises(ValueError):
            self.az.grant("c2", {"collector"})
        with self.assertRaises(ValueError):
            self.az.grant("c3", {"collector", "operator"}, node_scope={"n1"})
        with self.assertRaises(ValueError):
            self.az.grant("x", {"root"})

    def test_revoke(self):
        self.az.revoke("s")
        with self.assertRaises(authz.AuthzDenied):
            self.az.check("s", authz.CAP_POSTURE_READ, "n1")


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.p = policy.Policy.load()

    def test_union_of_both_sides_and_tier(self):
        r = self.p.requirement("public-untrusted", "platform-internal", tier="container")
        for m in pkg.REQUIRED_FOR_COTENANCY + ("spec_store_bypass", "retbleed", "spectre_v1"):
            self.assertIn(m, r.mitigations)
        self.assertTrue(r.cross_tenant_allowed)
        self.assertEqual(r.policy_digest, self.p.digest)

    def test_forbidden_classes_tiers_lineages(self):
        self.assertFalse(self.p.requirement("regulated-secret", "tenant-standard", tier="microvm").cross_tenant_allowed)
        self.assertFalse(self.p.requirement("tenant-standard", "tenant-standard", tier="dedicated-host").cross_tenant_allowed)
        self.assertFalse(self.p.requirement("tenant-standard", "tenant-standard", tier="microvm",
                                            cpu_lineage="x86-eol-no-microcode").cross_tenant_allowed)
        self.assertFalse(self.p.requirement("tenant-standard", "tenant-standard", tier="microvm",
                                            cpu_lineage="riscv-unknown").cross_tenant_allowed)
        legacy = self.p.requirement("tenant-standard", "tenant-standard", tier="microvm", cpu_lineage="x86-legacy-inv34")
        self.assertIn("tsx_async_abort", legacy.mitigations)

    def test_unknown_inputs_refused(self):
        for a, t in (("nope", "microvm"), ("tenant-standard", "nope")):
            with self.assertRaises(policy.PolicyError):
                self.p.requirement(a, "tenant-standard", tier=t)

    def test_tampered_or_weak_policy_refused(self):
        doc = json.loads(policy.DEFAULT_POLICY_PATH.read_text())
        doc["baseline"] = ["spectre_v2"]
        with self.assertRaises(policy.PolicyError) as cm:
            policy.Policy(doc)
        self.assertEqual(cm.exception.code, "policy_digest_mismatch")
        with self.assertRaises(policy.PolicyError) as cm:
            policy.Policy(policy.seal_policy(doc))
        self.assertEqual(cm.exception.code, "policy_below_floor")

    def test_gap02_contradiction(self):
        c = policy.gap02_contradictions({"affected": ["mds", "l1tf"]}, {"mds": "not_affected", "l1tf": "active"})
        self.assertEqual([x["mitigation"] for x in c], ["mds"])


class ConfigTest(unittest.TestCase):
    def test_secure_defaults_validate(self):
        config.validate(config.merge())

    def test_override_may_only_tighten(self):
        self.assertEqual(config.merge(site={"posture_ttl_s": 60.0})["posture_ttl_s"], 60.0)
        for ov in ({"posture_ttl_s": 900.0}, {"log_redact_tenants": False}, {"unknown_smt_is_enabled": False}):
            with self.assertRaises(config.ConfigError) as cm:
                config.merge(environment=ov)
            self.assertEqual(cm.exception.code, "config_loosening_refused")

    def test_bad_values_refused(self):
        for ov in ({"max_inflight": 0}, {"max_inflight": True}, {"typo": 1}, {"rate_per_s": "fast"}):
            with self.assertRaises(config.ConfigError):
                config.merge(site=ov)

    def test_transaction_and_rollback(self):
        store = config.ConfigStore()
        d0 = store.provenance["digest"]
        with self.assertRaises(config.ConfigError):
            store.activate(site={"max_inflight": -1}, source="bad", author="t")
        self.assertEqual(store.provenance["digest"], d0)  # failed activation changed nothing
        p1 = store.activate(site={"max_inflight": 8}, source="site.json", author="alice")
        self.assertEqual(p1["parent"], d0)
        self.assertEqual(store.active["max_inflight"], 8)
        with self.assertRaises(config.ConfigError):
            store.activate(site={"max_inflight": 9}, source="x", author="a", precheck=lambda c: False)
        back = store.rollback("bob")
        self.assertEqual(back["digest"], d0)
        self.assertEqual(back["rolled_back_by"], "bob")


if __name__ == "__main__":
    unittest.main()
