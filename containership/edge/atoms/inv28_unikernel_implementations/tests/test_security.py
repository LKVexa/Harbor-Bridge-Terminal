"""Threat-derived security tests (MC-048).  One test per threat in docs/THREAT_MODEL.md; the last test
fails if the threat model and this suite drift apart."""
import datetime as dt
import json
import pathlib
import re
import unittest

from harness import BindingError, F, Reason, RegistryError, ValidationError, codes_for, refusal
from inv28_unikernel_implementations.advisories import sign_feed
from inv28_unikernel_implementations.certification import issue
from inv28_unikernel_implementations.model import fmt_utc
from inv28_unikernel_implementations.policy import EnvironmentRule, SelectionPolicy, Waiver, default_policy
from inv28_unikernel_implementations.registry import Authorizer, Registry, verify_snapshot
from inv28_unikernel_implementations.trust import KeyRing

R = Reason
PKG = pathlib.Path(F.__file__).resolve().parent


class ThreatDerived(unittest.TestCase):
    def test_T01_experimental_reaches_production(self):
        w = F.world(records=[F.record("x", maturity="experimental")])
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertIn(R.MATURITY_BELOW_POLICY.value, codes_for(ref, "x@1.0.0-fixture"))

    def test_T02_silent_runtime_downgrade(self):
        w = F.world(records=[F.record("x", runtimes=("posix-libc",))])
        _, ref = refusal(lambda: w["selector"].select(F.request(runtime="rust-std"), now=F.NOW))
        self.assertEqual(codes_for(ref, "x@1.0.0-fixture"), [R.RUNTIME_UNSUPPORTED.value])

    def test_T03_unmaintained_toolchain_lingers(self):
        for kw, code in ((dict(contact=""), R.NO_SECURITY_CONTACT), (dict(reviewed_at="2025-01-01T00:00:00Z"), R.REVIEW_STALE),
                         (dict(eol_date="2026-01-01"), R.EOL)):
            with self.subTest(code=code):
                w = F.world(records=[F.record("x", **kw)])
                _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
                self.assertIn(code.value, codes_for(ref, "x@1.0.0-fixture"))

    def test_T04_substitution_between_selection_and_build(self):
        w = F.world()
        res = w["selector"].select(F.request(), now=F.NOW)
        with self.assertRaises(BindingError):
            w["inv27"].verify(res.ticket, b"evil", now=F.NOW)

    def test_T05_forged_register(self):
        w = F.world()
        snap = json.loads(json.dumps(w["registry"].snapshot()))
        snap["entries"].append(F.record("evil").to_dict())
        with self.assertRaises(RegistryError):
            verify_snapshot(w["ring"], snap)

    def test_T06_forged_certification(self):
        w = F.world(with_certs=False)
        attacker = KeyRing.ephemeral()
        r = w["registry"].get("rumprun@1.0.0-fixture")
        forged = issue(attacker, toolchain="rumprun", version=r.version, artifact_sha256=r.integrity.artifact_sha256,
                       architecture="x86_64", issued_at="2026-09-01T00:00:00Z", expires_at="2027-01-01T00:00:00Z")
        with self.assertRaises(ValidationError):
            w["certs"].ingest(forged)

    def test_T07_advisory_feed_suppression(self):
        w = F.world()
        w["advisories"].ingest(sign_feed(w["ring"], [{"id": "A", "toolchain": "rumprun", "affected_versions": ["1.0.0-fixture"],
                                                      "severity": "critical", "published": "x"}], fmt_utc(F.NOW)))
        replay_empty = sign_feed(w["ring"], [], fmt_utc(F.NOW - dt.timedelta(hours=2)))
        with self.assertRaises(ValidationError):
            w["advisories"].ingest(replay_empty)
        w["selector"].invalidate()
        refusal(lambda: w["selector"].select(F.request(), now=F.NOW))

    def test_T08_waiver_abuse(self):
        base = default_policy()
        for kw in ({"approver": "mallory", "owner": "mallory"}, {"approver": "deploy-bot"},
                   {"expires": "2026-01-01T00:00:00Z"}):
            with self.subTest(kw=kw):
                args = dict(owner="alice", approver="bob", expires="2027-01-01T00:00:00Z")
                args.update(kw)
                wv = Waiver("W", "unikraft@1.0.0-fixture", frozenset({R.MATURITY_BELOW_POLICY.value}),
                            frozenset({"production"}), reason="r", **args)
                w = F.world(policy=SelectionPolicy(base.policy_id, 2, base.environments, {}, (wv,)))
                _, ref = refusal(lambda: w["selector"].select(F.request(language="rust"), now=F.NOW))
                self.assertIn(R.MATURITY_BELOW_POLICY.value, codes_for(ref, "unikraft@1.0.0-fixture"))
        with self.assertRaises(ValidationError):
            Waiver("W", "x@1", frozenset({R.INTEGRITY_MISSING.value}), frozenset({"production"}), "a", "b", "r",
                   "2027-01-01T00:00:00Z")

    def test_T09_key_purpose_confusion(self):
        ring = KeyRing.ephemeral()
        body = {"a": 1}
        self.assertFalse(ring.verify("gap15", body, ring.sign("advisory", body)))
        self.assertFalse(ring.verify("ticket", body, ring.sign("registry", body)))
        with self.assertRaises(ValueError):
            ring.add("registry", "short", b"x" * 8)

    def test_T10_telemetry_leakage(self):
        w = F.world()
        w["selector"].select(F.request(tenant="tenant-secret-name", workload_id="payroll-db"), now=F.NOW)
        blob = "\n".join(w["logger"].lines) + w["metrics"].exposition()
        self.assertNotIn("tenant-secret-name", blob)
        self.assertNotIn("payroll-db", blob)

    def test_T11_resource_exhaustion(self):
        with self.assertRaises(ValidationError):
            F.request(features=frozenset(f"f{i}" for i in range(100)))
        reg = Registry(KeyRing.ephemeral(), capacity=1)
        reg.register(F.record("a"), actor="operator", expected_revision=0)
        with self.assertRaises(RegistryError):
            reg.register(F.record("b"), actor="operator", expected_revision=1)

    def test_T12_unauthorised_mutation(self):
        reg = Registry(KeyRing.ephemeral(), Authorizer({"reader": set()}))
        with self.assertRaises(RegistryError) as cm:
            reg.register(F.record("a"), actor="reader", expected_revision=0)
        self.assertEqual(cm.exception.code, R.REGISTRY_UNAUTHORIZED)

    def test_T13_clock_manipulation(self):
        w = F.world()
        code, _ = refusal(lambda: w["selector"].select(F.request(), now=dt.datetime(2026, 9, 23)))
        self.assertEqual(code, R.CLOCK_UNTRUSTED.value)
        with self.assertRaises(ValidationError):
            F.record("x", reviewed_at="2026-09-20T00:00:00+05:00")

    def test_T14_policy_weakening(self):
        with self.assertRaises(ValidationError):
            EnvironmentRule(min_maturity="beta", require_certification=False)
        bad = default_policy().to_dict()
        bad["environments"]["production"]["require_integrity"] = False
        with self.assertRaises(ValidationError):
            SelectionPolicy.from_dict(bad)

    def test_T15_audit_tampering(self):
        w = F.world()
        w["selector"].select(F.request(), now=F.NOW)
        del w["audit"]._entries[1]
        self.assertTrue(w["audit"].verify())


class ThreatModelConsistency(unittest.TestCase):
    def test_every_threat_has_a_test_and_vice_versa(self):
        doc = (PKG / "docs" / "THREAT_MODEL.md").read_text()
        ids = set(re.findall(r"^\| (T-\d\d) \|", doc, flags=re.M))
        tests = {"T-" + m.group(1) for n in dir(ThreatDerived) if (m := re.match(r"test_T(\d\d)_", n))}
        self.assertEqual(ids, tests)
        self.assertGreaterEqual(len(ids), 15)


if __name__ == "__main__":
    unittest.main()
