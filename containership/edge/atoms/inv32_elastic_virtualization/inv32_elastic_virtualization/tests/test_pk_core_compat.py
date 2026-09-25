"""WS 2 -- pk_core dependency contract: every consumed symbol exists and behaves (skips without pk_core)."""
from __future__ import annotations

import importlib.util
import unittest

from _support import pkg  # noqa: F401  (path setup)

REQUIRED = {
    "pk_core.contract": ["Contract", "Dependency", "Slo"],
    "pk_core.checklist": ["ChecklistItem", "Finding"],
    "pk_core.component": ["Component"],
}
COMPONENT_METHODS = ["assess_implementation", "assess_security", "assess_resilience", "satisfied", "_evidence",
                     "assess_all"]


@unittest.skipIf(importlib.util.find_spec("pk_core") is None, "pk_core not installed (optional extra; BLOCKED pin)")
class PkCoreCompatTest(unittest.TestCase):
    def test_symbols(self):
        import importlib
        for mod, names in REQUIRED.items():
            m = importlib.import_module(mod)
            for n in names:
                self.assertTrue(hasattr(m, n), f"{mod}.{n}")
        from pk_core.component import Component
        for meth in COMPONENT_METHODS:
            self.assertTrue(hasattr(Component, meth), meth)

    def test_contract_builds(self):
        from inv32_elastic_virtualization import build_contract
        c = build_contract()
        self.assertEqual(c.element, "INV-32")


class LazyImportTest(unittest.TestCase):
    def test_control_plane_imports_without_pk_core(self):
        from inv32_elastic_virtualization import controller, store  # noqa: F401

    def test_missing_pk_core_fails_at_activation_with_clear_error(self):
        if importlib.util.find_spec("pk_core") is not None:
            self.skipTest("pk_core present")
        import inv32_elastic_virtualization as p
        with self.assertRaises(ImportError) as cm:
            p.COMPONENT  # noqa: B018
        self.assertIn("pk_core", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
