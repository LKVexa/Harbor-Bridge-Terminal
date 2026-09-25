"""PK_TOOLCHAIN/2 model validation (MC-009..MC-021, MC-039, MC-078, MC-096)."""
import unittest

from harness import F, ValidationError
from inv28_unikernel_implementations.model import (
    IntegrityIdentity,
    Limitation,
    ReviewRecord,
    SecurityResponse,
    ToolchainRecord,
    canonical,
    parse_utc,
)


class RecordValidation(unittest.TestCase):
    def test_roundtrip_is_lossless_and_digest_stable(self):
        r = F.record("unikraft", maturity="beta")
        again = ToolchainRecord.from_dict(r.to_dict())
        self.assertEqual(again, r)
        self.assertEqual(again.digest, r.digest)
        self.assertEqual(canonical(r.to_dict()), canonical(again.to_dict()))

    def test_version_field_required_and_exact(self):                       # MC-009
        for bad in ("", ">=1.0", "1.*", "^1.2", "1.0 beta", "~1"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                F.record("x", version=bad)
        self.assertEqual(F.record("x", version="0.16.3").ref, "x@0.16.3")

    def test_same_name_different_versions_are_distinct_keys(self):
        self.assertNotEqual(F.record("x", version="1").key, F.record("x", version="2").key)

    def test_runtime_device_feature_hv_provider_abi_are_normalised_sets(self):   # MC-010..MC-015
        r = F.record("x", runtimes=(" POSIX-libc ",), devices=("VIRTIO-net",), features=("Net-Stack",),
                     hypervisors=("QEMU-KVM",), providers=("Generic-Cloud",), abis=("Posix-Subset",))
        self.assertEqual(r.runtimes, frozenset({"posix-libc"}))
        self.assertEqual(r.devices, frozenset({"virtio-net"}))
        self.assertEqual(r.features, frozenset({"net-stack"}))
        self.assertEqual(r.hypervisors, frozenset({"qemu-kvm"}))
        self.assertEqual(r.providers, frozenset({"generic-cloud"}))
        self.assertEqual(r.abis, frozenset({"posix-subset"}))

    def test_string_instead_of_set_rejected(self):
        d = F.record("x").to_dict()
        d["languages"] = "ocaml"
        with self.assertRaises(ValidationError):
            ToolchainRecord.from_dict(d)

    def test_duplicates_after_normalisation_rejected(self):
        with self.assertRaises(ValidationError):
            F.record("x", languages=("C", "c"))

    def test_empty_language_or_arch_rejected(self):
        for kw in ({"languages": ()}, {"architectures": ()}):
            with self.subTest(kw=kw), self.assertRaises(ValidationError):
                F.record("x", **kw)

    def test_malformed_tokens_rejected(self):
        for bad in ("", " ", "has space", "semi;colon", "x" * 65, "-leading"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                F.record("x", languages=(bad,))

    def test_non_string_token_rejected(self):
        with self.assertRaises(ValidationError):
            F.record("x", languages=(1,))

    def test_bounded_collections(self):                                      # MC-078
        with self.assertRaises(ValidationError):
            F.record("x", features=tuple(f"f{i}" for i in range(65)))

    def test_unknown_maturity_and_lifecycle_rejected(self):
        with self.assertRaises(ValidationError):
            F.record("x", maturity="stable")
        with self.assertRaises(ValidationError):
            F.record("x", lifecycle="gone")

    def test_bad_name_rejected(self):
        for bad in ("", "  ", "a b", "x" * 80, 5):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                F.record(bad)

    def test_unknown_fields_rejected_on_load(self):
        d = F.record("x").to_dict()
        d["surprise"] = 1
        with self.assertRaises(ValidationError):
            ToolchainRecord.from_dict(d)

    def test_unknown_nested_fields_rejected(self):
        d = F.record("x").to_dict()
        d["security"]["extra"] = 1
        with self.assertRaises(ValidationError):
            ToolchainRecord.from_dict(d)

    def test_v1_schema_refused_by_v2_loader(self):
        with self.assertRaises(ValidationError):
            ToolchainRecord.from_dict({**F.record("x").to_dict(), "schema": "PK_TOOLCHAIN/1"})

    def test_missing_required_rejected(self):
        d = F.record("x").to_dict()
        del d["maturity"]
        with self.assertRaises(ValidationError):
            ToolchainRecord.from_dict(d)


class SecurityAndReview(unittest.TestCase):
    def test_security_response_is_structured(self):                         # MC-016
        s = SecurityResponse("mailto:sec@x.invalid", "https://x.invalid/feed", "https://x.invalid/policy", 48)
        self.assertTrue(s.has_contact)
        self.assertFalse(SecurityResponse().has_contact)
        for bad in (-1, 10 ** 6, True, "48"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                SecurityResponse("x", response_sla_hours=bad)

    def test_review_provenance_required_fields(self):                        # MC-017
        with self.assertRaises(ValidationError):
            ReviewRecord("", "2026-01-01T00:00:00Z", "approved", "u", F.EVIDENCE)
        with self.assertRaises(ValidationError):
            ReviewRecord("r", "2026-01-01T00:00:00Z", "approved", "u", "not-a-hash")
        with self.assertRaises(ValidationError):
            ReviewRecord("r", "2026-01-01T00:00:00Z", "maybe", "u", F.EVIDENCE)

    def test_review_time_must_be_utc(self):                                  # MC-096
        for bad in ("2026-01-01T00:00:00", "2026-01-01T00:00:00+02:00", "yesterday", 1700000000):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                ReviewRecord("r", bad, "approved", "u", F.EVIDENCE)
        r = ReviewRecord("r", "2026-01-01T00:00:00+00:00", "approved", "u", F.EVIDENCE)
        self.assertEqual(r.reviewed_at, "2026-01-01T00:00:00Z")

    def test_per_toolchain_review_interval(self):                           # MC-018
        short = ReviewRecord("r", "2026-09-01T00:00:00Z", "approved", "u", F.EVIDENCE, interval_days=7)
        long_ = ReviewRecord("r", "2026-09-01T00:00:00Z", "approved", "u", F.EVIDENCE, interval_days=90)
        self.assertTrue(short.stale(F.NOW))
        self.assertFalse(long_.stale(F.NOW))
        for bad in (0, 731, 1.5):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                ReviewRecord("r", "2026-09-01T00:00:00Z", "approved", "u", F.EVIDENCE, interval_days=bad)

    def test_review_boundary_is_inclusive(self):
        r = ReviewRecord("r", "2026-09-01T00:00:00Z", "approved", "u", F.EVIDENCE, interval_days=1)
        self.assertFalse(r.stale(parse_utc("2026-09-02T00:00:00Z", "t")))
        self.assertTrue(r.stale(parse_utc("2026-09-02T00:00:01Z", "t")))


class LimitationsLifecycleIntegrity(unittest.TestCase):
    def test_limitations_structured_and_unique(self):                       # MC-019
        lim = Limitation("no-smp", "single core", frozenset({"SMP"}), frozenset({"Production"}))
        self.assertEqual(lim.excludes_features, frozenset({"smp"}))
        with self.assertRaises(ValidationError):
            F.record("x", limitations=(lim, lim))
        with self.assertRaises(ValidationError):
            F.record("x", limitations=("free text",))

    def test_eol_date_validated_and_evaluated(self):                        # MC-020
        with self.assertRaises(ValidationError):
            F.record("x", eol_date="31/12/2026")
        r = F.record("x", eol_date="2026-09-22")
        self.assertTrue(r.eol_passed(F.NOW))
        self.assertFalse(F.record("x", eol_date="2026-09-23").eol_passed(F.NOW))

    def test_integrity_identity(self):                                       # MC-021
        with self.assertRaises(ValidationError):
            IntegrityIdentity("u", "ABC")
        with self.assertRaises(ValidationError):
            IntegrityIdentity("u", "a" * 64, sbom_sha256="nothex")
        i = IntegrityIdentity("u", "a" * 64)
        self.assertEqual(i.sbom_sha256, "")

    def test_catalog_status(self):
        with self.assertRaises(ValidationError):
            F.record("x", catalog_status="official")

    def test_digest_changes_with_any_field(self):
        base = F.record("x")
        for change in ({"maturity": "beta"}, {"features": ["net-stack", "tls"]}, {"lifecycle": "deprecated"}):
            with self.subTest(change=change):
                self.assertNotEqual(base.replace(**change).digest, base.digest)


if __name__ == "__main__":
    unittest.main()
