"""Standalone tests for the INV-10 linker; requires only the Python stdlib."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = PKG_DIR / "composition.py"
SPEC = importlib.util.spec_from_file_location("inv10_composition_standalone", MODULE_PATH)
LINKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LINKER
assert SPEC.loader is not None
SPEC.loader.exec_module(LINKER)

Unit = LINKER.Unit
compose = LINKER.compose
CompositionLimits = LINKER.CompositionLimits
InvalidComposition = LINKER.InvalidComposition
UnsatisfiedImport = LINKER.UnsatisfiedImport
AmbiguousExport = LINKER.AmbiguousExport
CompositionCycle = LINKER.CompositionCycle
ResourceLimitExceeded = LINKER.ResourceLimitExceeded


class LinkerTest(unittest.TestCase):
    def test_package_import_exposes_linker_without_pk_core(self):
        parent = str(PKG_DIR.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        package = __import__(PKG_DIR.name)
        self.assertEqual(package.__version__, "4.3.0")
        result = package.compose([package.Unit("a", frozenset(), frozenset({"i"}))])
        self.assertTrue(result["closed"])

    def test_deterministic_identity_is_input_order_independent(self):
        parts = [
            Unit("store", frozenset(), frozenset({"wasi:kv/store"})),
            Unit("api", frozenset({"wasi:kv/store"}), frozenset({"wasi:http/handler"})),
        ]
        first = compose(parts)
        second = compose(reversed(parts))
        self.assertEqual(first["composition"], second["composition"])
        self.assertEqual(first["order"], ["store", "api"])
        self.assertEqual(len(first["composition"]), 64)
        self.assertEqual(first["digest_algorithm"], "sha256")
        self.assertEqual(first["identity_profile"], "PK_COMPOSITION_ID/2")

    def test_identity_covers_binding_graph_not_just_names_and_order(self):
        shared = [
            Unit("a", frozenset(), frozenset({"i-a"})),
            Unit("b", frozenset(), frozenset({"i-b"})),
        ]
        via_a = shared + [Unit("c", frozenset({"i-a"}), frozenset())]
        via_b = shared + [Unit("c", frozenset({"i-b"}), frozenset())]
        left = compose(via_a)
        right = compose(via_b)
        self.assertEqual(left["components"], right["components"])
        self.assertEqual(left["exports"], right["exports"])
        self.assertEqual(left["order"], right["order"])
        self.assertNotEqual(left["composition"], right["composition"])

    def test_self_dependency_is_a_cycle(self):
        with self.assertRaises(CompositionCycle) as caught:
            compose([Unit("self", frozenset({"i"}), frozenset({"i"}))])
        self.assertEqual(caught.exception.details["cycle"], ["self", "self"])

    def test_multi_node_cycle_is_refused_with_cycle_path(self):
        with self.assertRaises(CompositionCycle) as caught:
            compose([
                Unit("a", frozenset({"i-b"}), frozenset({"i-a"})),
                Unit("b", frozenset({"i-a"}), frozenset({"i-b"})),
            ])
        self.assertGreaterEqual(len(caught.exception.details["cycle"]), 3)

    def test_unsatisfied_import_is_refused(self):
        with self.assertRaises(UnsatisfiedImport) as caught:
            compose([Unit("api", frozenset({"missing"}), frozenset())])
        self.assertEqual(caught.exception.as_dict()["code"], "UNSATISFIED_IMPORT")

    def test_ambiguous_export_is_refused(self):
        with self.assertRaises(AmbiguousExport):
            compose([
                Unit("a", frozenset(), frozenset({"i"})),
                Unit("b", frozenset(), frozenset({"i"})),
            ])

    def test_duplicate_component_name_is_refused(self):
        with self.assertRaises(AmbiguousExport):
            compose([
                Unit("dup", frozenset(), frozenset({"i-a"})),
                Unit("dup", frozenset(), frozenset({"i-b"})),
            ])

    def test_external_import_is_explicit_and_in_binding_metadata(self):
        result = compose(
            [Unit("api", frozenset({"wasi:http/outgoing"}), frozenset())],
            external=frozenset({"wasi:http/outgoing"}),
        )
        self.assertEqual(result["external_imports"], ["wasi:http/outgoing"])
        self.assertEqual(
            result["bindings"],
            [{"consumer": "api", "interface": "wasi:http/outgoing", "external": True}],
        )

    def test_control_char_and_noncanonical_identifiers_are_refused(self):
        for bad in [" x", "x ", "x\nlog-injection", "e\u0301"]:
            with self.subTest(bad=repr(bad)), self.assertRaises(InvalidComposition):
                compose([Unit(bad, frozenset(), frozenset())])

    def test_resource_limits_fail_closed(self):
        limits = CompositionLimits(max_components=1)
        with self.assertRaises(ResourceLimitExceeded):
            compose(
                [Unit("a", frozenset(), frozenset()), Unit("b", frozenset(), frozenset())],
                limits=limits,
            )

    def test_empty_composition_is_deterministic(self):
        first = compose([])
        second = compose([])
        self.assertTrue(first["closed"])
        self.assertEqual(first["composition"], second["composition"])


if __name__ == "__main__":
    unittest.main()
