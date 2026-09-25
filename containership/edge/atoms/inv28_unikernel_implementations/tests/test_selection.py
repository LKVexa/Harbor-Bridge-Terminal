"""Selection semantics: every reason code, policy, waivers, site, features, determinism (MC-011..MC-026,
MC-094, MC-097, MC-099, MC-100)."""
import datetime as dt
import unittest

from harness import F, Reason, RefusalError, ValidationError, codes_for, refusal
from inv28_unikernel_implementations.model import Limitation
from inv28_unikernel_implementations.policy import EnvironmentRule, SelectionPolicy, SitePolicy, Waiver, default_policy
from inv28_unikernel_implementations.selection import SelectionRequest, SelectionResult

R = Reason


def only(rec, **kw):
    return F.world(records=[rec], **kw)


class ReasonCodes(unittest.TestCase):
    """One positive and one negative case per capability dimension, asserted by code (not text)."""

    CASES = [
        ("language", {"language": "ocaml"}, R.LANGUAGE_UNSUPPORTED),
        ("runtime", {"runtime": "jvm"}, R.RUNTIME_UNSUPPORTED),
        ("architecture", {"architecture": "riscv64"}, R.ARCH_UNSUPPORTED),
        ("devices", {"devices": frozenset({"nvme"})}, R.DEVICE_UNSUPPORTED),
        ("features", {"features": frozenset({"smp"})}, R.FEATURE_UNSUPPORTED),
        ("hypervisor", {"hypervisor": "firecracker"}, R.HYPERVISOR_UNSUPPORTED),
        ("provider", {"provider": "aws"}, R.PROVIDER_UNSUPPORTED),
        ("abi", {"abi": "linux-binary-compat"}, R.ABI_UNSUPPORTED),
    ]

    def test_each_capability_mismatch_has_its_code(self):
        w = only(F.record("t"))
        for name, kw, code in self.CASES:
            with self.subTest(name=name):
                c, ref = refusal(lambda: w["selector"].select(F.request(**kw), now=F.NOW))
                self.assertEqual(c, R.NO_SUITABLE_TOOLCHAIN.value)
                got = set(codes_for(ref, "t@1.0.0-fixture"))
                self.assertIn(code.value, got)
                # an unsupported architecture also has no GAP-15 certificate; nothing else may appear
                self.assertLessEqual(got, {code.value, R.NOT_CERTIFIED.value})

    def test_each_capability_match_selects(self):
        w = only(F.record("t"))
        for kw in ({"runtime": "posix-libc"}, {"devices": frozenset({"virtio-net"})},
                   {"features": frozenset({"net-stack"})}, {"hypervisor": "qemu-kvm"},
                   {"provider": "generic-cloud"}, {"abi": "posix-subset"}):
            with self.subTest(kw=kw):
                self.assertEqual(w["selector"].select(F.request(**kw), now=F.NOW).toolchain, "t")

    def test_all_unmet_constraints_reported_not_just_first(self):          # MC-026
        w = only(F.record("t", maturity="beta", contact=""))
        _, ref = refusal(lambda: w["selector"].select(F.request(language="ocaml", architecture="aarch64"), now=F.NOW))
        self.assertGreaterEqual(set(codes_for(ref, "t@1.0.0-fixture")),
                         {R.LANGUAGE_UNSUPPORTED.value, R.ARCH_UNSUPPORTED.value, R.MATURITY_BELOW_POLICY.value,
                          R.NO_SECURITY_CONTACT.value})

    def test_limitation_conflict(self):                                     # MC-019
        lim = Limitation("no-smp", "single core", frozenset({"smp"}), frozenset({"staging"}))
        w = only(F.record("t", features=("net-stack", "smp"), limitations=(lim,)))
        _, ref = refusal(lambda: w["selector"].select(F.request(features=frozenset({"smp"})), now=F.NOW))
        self.assertIn(R.LIMITATION_CONFLICT.value, codes_for(ref, "t@1.0.0-fixture"))
        _, ref = refusal(lambda: w["selector"].select(F.request(environment="staging"), now=F.NOW))
        self.assertIn(R.LIMITATION_CONFLICT.value, codes_for(ref, "t@1.0.0-fixture"))
        self.assertEqual(w["selector"].select(F.request(), now=F.NOW).toolchain, "t")


class ProductionMaturityPolicy(unittest.TestCase):                          # MC-094
    def test_matrix(self):
        expect = {("production", "mature"): True, ("production", "beta"): False, ("production", "experimental"): False,
                  ("staging", "mature"): True, ("staging", "beta"): True, ("staging", "experimental"): False,
                  ("dev", "mature"): True, ("dev", "beta"): True, ("dev", "experimental"): True}
        for (env, mat), ok in expect.items():
            with self.subTest(env=env, maturity=mat):
                w = only(F.record("t", maturity=mat))
                if ok:
                    self.assertEqual(w["selector"].select(F.request(environment=env), now=F.NOW).maturity, mat)
                else:
                    _, ref = refusal(lambda: w["selector"].select(F.request(environment=env), now=F.NOW))
                    self.assertIn(R.MATURITY_BELOW_POLICY.value, codes_for(ref, "t@1.0.0-fixture"))

    def _waived(self, maturity, *, approver="alice", status="approved", expires="2026-12-31T00:00:00Z", env="production"):
        w = Waiver("W-1", "t@1.0.0-fixture", frozenset({R.MATURITY_BELOW_POLICY.value}), frozenset({env}),
                   owner="bob", approver=approver, reason="pilot", expires=expires, status=status)
        base = default_policy()
        return SelectionPolicy(base.policy_id, base.revision + 1, base.environments, {}, (w,))

    def test_beta_in_production_only_with_approved_waiver(self):
        w = only(F.record("t", maturity="beta"), policy=self._waived("beta"))
        res = w["selector"].select(F.request(), now=F.NOW)
        self.assertEqual(res.waivers, ("W-1",))

    def test_waiver_never_admits_experimental_in_production(self):
        w = only(F.record("t", maturity="experimental"), policy=self._waived("experimental"))
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertIn(R.MATURITY_BELOW_POLICY.value, codes_for(ref, "t@1.0.0-fixture"))

    def test_waiver_invalid_variants(self):
        for kw in ({"expires": "2026-09-01T00:00:00Z"}, {"status": "proposed"}, {"approver": ""},
                   {"approver": "bob"}, {"approver": "release-bot"}, {"approver": "claude"}, {"env": "staging"}):
            with self.subTest(kw=kw):
                w = only(F.record("t", maturity="beta"), policy=self._waived("beta", **kw))
                _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
                self.assertIn(R.MATURITY_BELOW_POLICY.value, codes_for(ref, "t@1.0.0-fixture"))

    def test_unwaivable_codes_rejected_at_policy_load(self):              # MC-038
        with self.assertRaises(ValidationError):
            Waiver("W", "t@1", frozenset({R.NOT_CERTIFIED.value}), frozenset({"production"}), "o", "a", "r",
                   "2027-01-01T00:00:00Z")

    def test_production_rule_floor(self):
        for kw in ({"min_maturity": "experimental"}, {"require_certification": False}, {"require_review": False},
                   {"require_integrity": False}, {"require_security_contact": False}, {"require_advisory_feed": False}):
            with self.subTest(kw=kw), self.assertRaises(ValidationError) as cm:
                EnvironmentRule(**kw)
            self.assertEqual(cm.exception.code, R.POLICY_INVALID)

    def test_undeclared_environment_refused(self):
        w = F.world()
        c, _ = refusal(lambda: w["selector"].select(F.request(environment="prod-eu"), now=F.NOW))
        self.assertEqual(c, R.POLICY_INVALID.value)

    def test_policy_revision_must_increase(self):
        w = F.world()
        with self.assertRaises(ValidationError):
            w["selector"].set_policy(default_policy())


class SecurityGates(unittest.TestCase):
    def test_review_states(self):
        cases = {"missing": (dict(review=False), R.REVIEW_MISSING), "rejected": (dict(review_result="rejected"), R.REVIEW_REJECTED),
                 "conditional": (dict(review_result="conditional"), R.REVIEW_REJECTED),
                 "stale": (dict(reviewed_at="2025-01-01T00:00:00Z"), R.REVIEW_STALE)}
        for name, (kw, code) in cases.items():
            with self.subTest(name=name):
                w = only(F.record("t", **kw))
                _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
                self.assertIn(code.value, codes_for(ref, "t@1.0.0-fixture"))

    def test_conditional_review_accepted_in_staging(self):
        w = only(F.record("t", review_result="conditional"))
        self.assertEqual(w["selector"].select(F.request(environment="staging"), now=F.NOW).toolchain, "t")

    def test_sla_policy(self):                                              # MC-016
        base = default_policy()
        strict = SelectionPolicy(base.policy_id, 2, {**base.environments,
                                                    "production": EnvironmentRule(min_response_sla_hours=24)})
        w = only(F.record("t", sla=72), policy=strict)
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertIn(R.SECURITY_RESPONSE_INADEQUATE.value, codes_for(ref, "t@1.0.0-fixture"))
        self.assertEqual(only(F.record("t", sla=12), policy=strict)["selector"].select(F.request(), now=F.NOW).toolchain, "t")

    def test_integrity_required_in_production(self):                       # MC-021
        w = only(F.record("t", integrity=False))
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertEqual(set(codes_for(ref, "t@1.0.0-fixture")), {R.INTEGRITY_MISSING.value, R.NOT_CERTIFIED.value})

    def test_lifecycle_states(self):                                        # MC-020, MC-027
        expect = {"candidate": R.LIFECYCLE_NOT_SELECTABLE, "deprecated": R.LIFECYCLE_NOT_SELECTABLE,
                  "eol": R.EOL, "retired": R.LIFECYCLE_NOT_SELECTABLE, "quarantined": R.LIFECYCLE_NOT_SELECTABLE,
                  "disabled": R.DISABLED}
        for lc, code in expect.items():
            with self.subTest(lifecycle=lc):
                w = only(F.record("t"))
                rec = w["registry"].entries[0]
                w["registry"]._entries[rec.key] = rec.replace(lifecycle=lc)  # direct state for the matrix
                w["registry"]._notify()
                _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
                self.assertIn(code.value, codes_for(ref, "t@1.0.0-fixture"))

    def test_deprecated_allowed_outside_production(self):
        w = only(F.record("t", lifecycle="active"))
        w["registry"].transition("t@1.0.0-fixture", "deprecated", actor="operator",
                                 expected_revision=w["registry"].revision, reason="superseded")
        self.assertEqual(w["selector"].select(F.request(environment="staging"), now=F.NOW).toolchain, "t")

    def test_eol_date_passed(self):
        w = only(F.record("t", eol_date="2026-09-01"))
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertIn(R.EOL.value, codes_for(ref, "t@1.0.0-fixture"))

    def test_catalog_status_example_refused_in_production(self):          # MC-006, MC-095
        w = only(F.record("t", catalog_status="example"))
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertIn(R.POLICY_DENIED.value, codes_for(ref, "t@1.0.0-fixture"))


class Certification(unittest.TestCase):                                     # MC-097
    def test_uncertified_refused_in_production(self):
        w = only(F.record("t"), with_certs=False)
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertIn(R.NOT_CERTIFIED.value, codes_for(ref, "t@1.0.0-fixture"))

    def test_certificate_for_other_arch_does_not_count(self):
        w = only(F.record("t", architectures=("x86_64", "aarch64")), with_certs=False)
        from inv28_unikernel_implementations.certification import issue
        rec = w["registry"].entries[0]
        w["certs"].ingest(issue(w["ring"], toolchain="t", version=rec.version,
                                artifact_sha256=rec.integrity.artifact_sha256, architecture="aarch64",
                                issued_at="2026-09-01T00:00:00Z", expires_at="2026-12-01T00:00:00Z"))
        refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertEqual(w["selector"].select(F.request(architecture="aarch64"), now=F.NOW).toolchain, "t")

    def test_expired_certificate_does_not_count(self):
        w = F.world(records=[F.record("t")])
        later = F.NOW + dt.timedelta(days=120)
        rec = w["registry"].entries[0]
        # keep review fresh so only certification decides
        w["registry"]._entries[rec.key] = rec.replace(review={**rec.review.to_dict(), "reviewed_at": "2027-01-10T00:00:00Z"})
        w["registry"]._notify()
        w["advisories"].ingest(__import__("inv28_unikernel_implementations.advisories", fromlist=["x"]).sign_feed(
            w["ring"], [], "2027-01-20T00:00:00Z"))
        w["selector"].invalidate()
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=later))
        self.assertIn(R.NOT_CERTIFIED.value, codes_for(ref, "t@1.0.0-fixture"))

    def test_certificate_for_other_artifact_digest_does_not_count(self):
        w = only(F.record("t"), with_certs=False)
        from inv28_unikernel_implementations.certification import issue
        w["certs"].ingest(issue(w["ring"], toolchain="t", version="1.0.0-fixture", artifact_sha256="f" * 64,
                                architecture="x86_64", issued_at="2026-09-01T00:00:00Z",
                                expires_at="2026-12-01T00:00:00Z"))
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertIn(R.NOT_CERTIFIED.value, codes_for(ref, "t@1.0.0-fixture"))

    def test_certified_preferred_on_tie_outside_production(self):
        w = F.world(records=[F.record("aaa", integrity=False), F.record("zzz")])
        self.assertEqual(w["selector"].select(F.request(environment="dev"), now=F.NOW).toolchain, "zzz")


class SiteAndWorkload(unittest.TestCase):                                   # MC-099, MC-100
    def test_site_arch_refused_request_level(self):
        w = F.world()
        c, _ = refusal(lambda: w["selector"].select(F.request(site=F.site(architectures=("aarch64",))), now=F.NOW))
        self.assertEqual(c, R.SITE_ARCH_UNSUPPORTED.value)

    def test_site_hypervisor(self):
        w = only(F.record("t", hypervisors=("xen",)))
        _, ref = refusal(lambda: w["selector"].select(F.request(site=F.site(hypervisors=("qemu-kvm",))), now=F.NOW))
        self.assertIn(R.SITE_HYPERVISOR_UNSUPPORTED.value, codes_for(ref, "t@1.0.0-fixture"))
        self.assertEqual(w["selector"].select(F.request(site=F.site(hypervisors=("xen",))), now=F.NOW).toolchain, "t")

    def test_site_provider(self):
        w = only(F.record("t", providers=("bare-metal",)))
        _, ref = refusal(lambda: w["selector"].select(F.request(site=F.site(providers=("aws",))), now=F.NOW))
        self.assertIn(R.PROVIDER_UNSUPPORTED.value, codes_for(ref, "t@1.0.0-fixture"))

    def test_site_policy_deny_and_allow(self):
        base = default_policy()
        pol = SelectionPolicy(base.policy_id, 2, base.environments, {"edge-1": SitePolicy(frozenset({"t"}))})
        w = only(F.record("t"), policy=pol)
        _, ref = refusal(lambda: w["selector"].select(F.request(site=F.site()), now=F.NOW))
        self.assertIn(R.POLICY_DENIED.value, codes_for(ref, "t@1.0.0-fixture"))
        pol2 = SelectionPolicy(base.policy_id, 2, base.environments, {"edge-1": SitePolicy(frozenset(), frozenset({"other"}))})
        w2 = only(F.record("t"), policy=pol2)
        refusal(lambda: w2["selector"].select(F.request(site=F.site()), now=F.NOW))
        self.assertEqual(w2["selector"].select(F.request(), now=F.NOW).toolchain, "t")

    def test_request_cannot_name_toolchain(self):
        with self.assertRaises(ValidationError):
            SelectionRequest.from_dict({"workload_id": "w", "tenant": "t", "environment": "dev", "language": "c",
                                        "architecture": "x86_64", "toolchain": "nanos"})

    def test_request_validation(self):                                      # MC-023
        good = F.request().to_dict()
        self.assertEqual(SelectionRequest.from_dict(good), F.request())
        for mutate in ({"schema": "X/1"}, {"language": ""}, {"features": "smp"}, {"tenant": ""},
                       {"site": {"site_id": "s", "architectures": []}}):
            with self.subTest(mutate=mutate), self.assertRaises(ValidationError):
                SelectionRequest.from_dict({**good, **mutate})
        with self.assertRaises(ValidationError):
            SelectionRequest.from_dict({"workload_id": "w"})

    def test_untrusted_clock_rejected(self):
        w = F.world()
        for bad in (dt.datetime(2026, 9, 23), dt.datetime(2026, 9, 23, tzinfo=dt.timezone(dt.timedelta(hours=2))), 5):
            with self.subTest(bad=bad):
                c, _ = refusal(lambda: w["selector"].select(F.request(), now=bad))
                self.assertEqual(c, R.CLOCK_UNTRUSTED.value)


class ResultShapeAndDeterminism(unittest.TestCase):                         # MC-024, MC-025
    def test_result_is_immutable(self):
        r = F.world()["selector"].select(F.request(), now=F.NOW)
        self.assertIsInstance(r, SelectionResult)
        with self.assertRaises(Exception):
            r.toolchain = "nanos"

    def test_decision_id_deterministic_and_input_sensitive(self):
        a = F.world()["selector"].select(F.request(), now=F.NOW)
        b = F.world()["selector"].select(F.request(), now=F.NOW)
        self.assertEqual(a.decision_id, b.decision_id)
        self.assertEqual(a.to_dict()["eliminated"], b.to_dict()["eliminated"])
        c = F.world()["selector"].select(F.request(), now=F.NOW + dt.timedelta(seconds=1))
        self.assertNotEqual(a.decision_id, c.decision_id)

    def test_registration_order_independent(self):
        for order in (F.standard_records(), F.standard_records()[::-1]):
            self.assertEqual(F.world(records=order)["selector"].select(F.request(), now=F.NOW).toolchain, "rumprun")

    def test_newest_version_wins_among_equals(self):
        w = F.world(records=[F.record("t", version="1.9.0"), F.record("t", version="1.10.0"), F.record("t", version="1.2.0")])
        self.assertEqual(w["selector"].select(F.request(), now=F.NOW).version, "1.10.0")

    def test_refusal_error_carries_structured_refusal(self):
        w = F.world()
        with self.assertRaises(RefusalError) as cm:
            w["selector"].select(F.request(language="cobol"), now=F.NOW)
        d = cm.exception.refusal.to_dict()
        self.assertEqual(d["outcome"], "REFUSED")
        self.assertEqual(cm.exception.code, R.NO_SUITABLE_TOOLCHAIN)

    def test_reason_codes_are_unique_and_prefixed(self):
        vals = [r.value for r in R]
        self.assertEqual(len(vals), len(set(vals)))
        self.assertTrue(all(v.split("_")[0] in ("TC", "SEL", "REG", "BIND") for v in vals))


if __name__ == "__main__":
    unittest.main()
