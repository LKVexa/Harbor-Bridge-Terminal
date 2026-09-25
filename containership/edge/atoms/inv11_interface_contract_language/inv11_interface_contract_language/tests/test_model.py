"""Dependency-free unit tests for the INV-11 structural compatibility model."""
from __future__ import annotations

import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv11_interface_contract_language import (  # noqa: E402
    ADDITIVE,
    BREAKING,
    COMPATIBLE,
    Func,
    Incompatible,
    Interface,
    check_link,
    classify,
)


class ModelValidationTest(unittest.TestCase):
    def test_rejects_duplicate_function_names(self):
        with self.assertRaisesRegex(ValueError, "duplicate function"):
            Interface(
                "i",
                "1.0.0",
                frozenset(
                    {
                        Func("f", (("a", "string"),), ("ok",)),
                        Func("f", (("a", "u32"),), ("ok",)),
                    }
                ),
            )

    def test_rejects_duplicate_parameter_names(self):
        with self.assertRaisesRegex(ValueError, "duplicate parameter"):
            Func("f", (("a", "string"), ("a", "u32")), ("ok",))

    def test_repeated_result_types_remain_representable(self):
        func = Func("f", (), ("u32", "u32"))
        self.assertEqual(func.results, ("u32", "u32"))

    def test_rejects_empty_identifiers(self):
        with self.assertRaises(ValueError):
            Func("", (), ())
        with self.assertRaises(ValueError):
            Interface("", "1.0.0", frozenset())


class CompatibilityTest(unittest.TestCase):
    def setUp(self):
        self.get = Func("get", (("key", "string"),), ("ok", "not-found"))
        self.old = Interface("wasi:kv/store", "1.0.0", frozenset({self.get}))

    def test_version_only_change_is_compatible(self):
        new = Interface("wasi:kv/store", "9.9.9", frozenset({self.get}))
        diff = classify(self.old, new)
        self.assertEqual(diff["class"], COMPATIBLE)
        self.assertTrue(diff["linkable"])

    def test_added_function_is_additive_and_old_consumer_links(self):
        delete = Func("delete", (("key", "string"),), ("ok",))
        new = Interface("wasi:kv/store", "1.1.0", frozenset({self.get, delete}))
        diff = classify(self.old, new)
        self.assertEqual(diff["class"], ADDITIVE)
        self.assertIn("functions added", diff["reasons"][0])
        self.assertTrue(check_link(new, self.old)["linked"])

    def test_removed_function_is_breaking(self):
        old = Interface(
            "i",
            "1.0.0",
            frozenset({Func("f", (), ("ok",)), Func("g", (), ("ok",))}),
        )
        new = Interface("i", "2.0.0", frozenset({Func("f", (), ("ok",))}))
        diff = classify(old, new)
        self.assertEqual(diff["class"], BREAKING)
        self.assertFalse(diff["linkable"])

    def test_result_addition_is_breaking(self):
        old = Interface("i", "1.0.0", frozenset({Func("f", (), ("ok", "err"))}))
        new = Interface(
            "i", "2.0.0", frozenset({Func("f", (), ("ok", "err", "throttled"))})
        )
        diff = classify(old, new)
        self.assertEqual(diff["class"], BREAKING)
        self.assertTrue(any("added ['throttled']" in reason for reason in diff["reasons"]))

    def test_mixed_breaking_and_additive_changes_report_both(self):
        old = Interface(
            "i",
            "1.0.0",
            frozenset({Func("old", (), ("ok",)), Func("keep", (), ("ok",))}),
        )
        new = Interface(
            "i",
            "2.0.0",
            frozenset({Func("new", (), ("ok",)), Func("keep", (), ("ok",))}),
        )
        diff = classify(old, new)
        self.assertEqual(diff["class"], BREAKING)
        joined = " | ".join(diff["reasons"])
        self.assertIn("functions removed", joined)
        self.assertIn("functions added", joined)

    def test_name_mismatch_refuses_link(self):
        other = Interface("other", "1.0.0", frozenset({self.get}))
        with self.assertRaises(Incompatible):
            check_link(other, self.old)

    def test_signature_mismatch_refuses_link(self):
        narrowed = Interface(
            "wasi:kv/store",
            "1.0.1",
            frozenset({Func("get", (("key", "u32"),), ("ok", "not-found"))}),
        )
        with self.assertRaises(Incompatible):
            check_link(narrowed, self.old)


if __name__ == "__main__":
    unittest.main()
