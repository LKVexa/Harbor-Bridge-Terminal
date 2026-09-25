"""Standalone tests for the INV-09 validator policy kernel.

These tests deliberately do not require pk_core, so the security-critical input
validation remains exercised even when the wider post-Kubernetes harness is not
installed in the test environment.
"""
import importlib.util
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inv09_validator_standalone", PKG_DIR / "validator.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not construct import spec for validator.py")
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)

FeatureRefused = validator.FeatureRefused
Module = validator.Module
ValidationFailed = validator.ValidationFailed
validate = validator.validate


class ValidatorTest(unittest.TestCase):
    def test_accepts_valid_deterministic_descriptor(self):
        module = Module("svc", {"core", "bulk-memory"}, {"core"})
        result = validate(module, profile="deterministic")
        self.assertTrue(result["valid"])
        self.assertTrue(result["deterministic"])
        self.assertEqual(result["declared_unused"], ["bulk-memory"])
        self.assertEqual(result["declared_unsupported"], [])

    def test_result_is_repeatable(self):
        module = Module("svc", frozenset({"core"}), frozenset({"core"}))
        self.assertEqual(validate(module, profile="deterministic"), validate(module, profile="deterministic"))

    def test_used_but_undeclared_is_rejected(self):
        module = Module("sneaky", {"core"}, {"core", "threads"})
        with self.assertRaises(ValidationFailed):
            validate(module, profile="permissive")

    def test_used_feature_outside_profile_is_refused(self):
        module = Module("simd", {"core", "simd"}, {"core", "simd"})
        with self.assertRaises(FeatureRefused):
            validate(module, profile="deterministic")

    def test_declared_but_unused_feature_outside_profile_is_refused(self):
        module = Module("declared-only", {"core", "threads"}, {"core"})
        with self.assertRaises(FeatureRefused):
            validate(module, profile="deterministic")

    def test_unknown_feature_is_fail_closed(self):
        module = Module("future", {"core", "future-magic"}, {"core"})
        with self.assertRaises(ValidationFailed):
            validate(module, profile="permissive")

    def test_non_string_feature_is_rejected(self):
        module = Module("bad-feature", {"core", 7}, {"core"})
        with self.assertRaises(ValidationFailed):
            validate(module, profile="deterministic")

    def test_invalid_feature_spelling_is_rejected(self):
        module = Module("bad-feature", {"core", "WALL CLOCK"}, {"core"})
        with self.assertRaises(ValidationFailed):
            validate(module, profile="deterministic")

    def test_invalid_profile_values_do_not_leak_type_errors(self):
        for profile in (None, [], {"deterministic"}):
            with self.subTest(profile=profile):
                with self.assertRaises(ValueError):
                    validate(Module("svc", {"core"}, {"core"}), profile=profile)

    def test_numeric_limits_reject_bool_negative_and_over_limit(self):
        cases = [
            Module("bool-sections", set(), set(), sections=True),
            Module("negative-sections", set(), set(), sections=-1),
            Module("oversize", set(), set(), size_bytes=validator.MAX_BYTES + 1),
            Module("too-many-sections", set(), set(), sections=validator.MAX_SECTIONS + 1),
        ]
        for module in cases:
            with self.subTest(module=module.name):
                with self.assertRaises(ValidationFailed):
                    validate(module, profile="deterministic")

    def test_well_formed_requires_real_bool(self):
        for value in (1, "yes", None):
            with self.subTest(value=value):
                with self.assertRaises(ValidationFailed):
                    validate(Module("svc", set(), set(), well_formed=value), profile="deterministic")

    def test_module_name_is_bounded_and_control_free(self):
        bad_names = ["", " svc", "svc ", "svc\nlog-forge", "x" * (validator.MAX_MODULE_NAME_CHARS + 1)]
        for name in bad_names:
            with self.subTest(name=repr(name)):
                with self.assertRaises(ValidationFailed):
                    validate(Module(name, set(), set()), profile="deterministic")

    def test_feature_count_is_bounded(self):
        features = {f"f{i}" for i in range(validator.MAX_FEATURES + 1)}
        with self.assertRaises(ValidationFailed):
            validate(Module("many", features, set()), profile="deterministic")

    def test_permissive_nondeterminism_is_explicit(self):
        module = Module("threaded", {"core", "threads"}, {"core", "threads"})
        result = validate(module, profile="permissive")
        self.assertFalse(result["deterministic"])


if __name__ == "__main__":
    unittest.main()
