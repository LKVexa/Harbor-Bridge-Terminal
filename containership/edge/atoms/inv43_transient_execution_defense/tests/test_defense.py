"""Standalone tests for the INV-43 policy model; no network or pk_core required."""
from __future__ import annotations

import ast
import importlib
import json
import math
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)


class PolicyModelTest(unittest.TestCase):
    def _full(self, **kwargs):
        node = pkg.MitigationState("node-a", smt_enabled=False, **kwargs)
        for name, cost in [("spectre_v2", 3.1), ("l1tf", 1.4), ("mds", 2.0), ("mmio_stale_data", 0.8)]:
            node.record(name, pkg.ACTIVE, cost)
        return node

    def test_package_import_and_version_do_not_require_pk_core(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text(encoding="utf-8").strip(), "4.3.0")
        self.assertEqual(pkg.ELEMENT_ID, "INV-43")

    def test_report_contains_per_mitigation_status_and_cost(self):
        report = self._full().report()
        self.assertEqual(report["schema"], "PK_MITIGATIONS/1")
        self.assertEqual(report["total_cost_percent"], 7.3)
        self.assertEqual(report["inactive_or_unknown"], [])
        self.assertEqual(report["mitigations"]["spectre_v2"], {"status": "active", "cost_percent": 3.1})

    def test_missing_required_mitigation_fails_closed_with_machine_error(self):
        node = pkg.MitigationState("node-a", smt_enabled=False)
        node.record("spectre_v2", pkg.ACTIVE, 1.0)
        with self.assertRaises(pkg.MitigationMissing) as caught:
            node.may_cotenant("tenant-a", "tenant-b")
        self.assertEqual(caught.exception.code, "required_mitigation_missing")
        error = caught.exception.to_dict()
        self.assertEqual(error["schema"], "PK_ERROR/1")
        self.assertIn("mds", error["details"]["missing"])

    def test_smt_without_core_scheduling_fails_closed(self):
        node = pkg.MitigationState("node-a", smt_enabled=True, core_scheduling=False)
        for name in pkg.REQUIRED_FOR_COTENANCY:
            node.record(name, pkg.ACTIVE, 1.0)
        with self.assertRaises(pkg.MitigationMissing) as caught:
            node.may_cotenant("tenant-a", "tenant-b")
        self.assertEqual(caught.exception.code, "unsafe_smt")

    def test_custom_required_set_is_enforced_and_unknown_fails_closed(self):
        node = self._full()
        with self.assertRaises(pkg.MitigationMissing) as caught:
            node.may_cotenant("tenant-a", "tenant-b", ["spectre_v2", "future_class"])
        self.assertEqual(caught.exception.details["missing"], ["future_class"])

    def test_same_tenant_is_allowed_without_cross_tenant_mitigations(self):
        result = pkg.MitigationState("node-a").may_cotenant("tenant-a", "tenant-a")
        self.assertTrue(result["permitted"])
        self.assertEqual(result["tenants"], ["tenant-a"])

    def test_record_validation(self):
        node = pkg.MitigationState("node-a")
        bad = [math.nan, math.inf, -1.0]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    node.record("spectre_v2", pkg.ACTIVE, value)
        with self.assertRaises(ValueError):
            node.record("spectre_v2", pkg.ACTIVE, 0.0)
        with self.assertRaises(TypeError):
            node.record("spectre_v2", pkg.ACTIVE, True)
        with self.assertRaises(ValueError):
            node.record("spectre_v2", pkg.INACTIVE, 1.0)
        with self.assertRaises(ValueError):
            node.record("", pkg.ACTIVE, 1.0)
        with self.assertRaises(ValueError):
            node.record("spectre_v2", "claimed", 1.0)

    def test_constructor_revalidates_supplied_state(self):
        with self.assertRaises(ValueError):
            pkg.MitigationState("node-a", mitigations={"spectre_v2": (pkg.ACTIVE, 0.0)})
        with self.assertRaises(TypeError):
            pkg.MitigationState("node-a", smt_enabled=1)

    def test_report_is_a_snapshot_not_mutable_backdoor(self):
        node = self._full()
        report = node.report()
        report["mitigations"]["spectre_v2"]["status"] = "inactive"
        self.assertEqual(node.status("spectre_v2"), pkg.ACTIVE)

    def test_no_bare_asserts_in_runtime_modules(self):
        for filename in ["defense.py", "component.py", "contract.py", "__init__.py"]:
            tree = ast.parse((PKG_DIR / filename).read_text(encoding="utf-8"), filename=filename)
            self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)], filename)

    def test_schemas_and_examples_are_present_and_parseable(self):
        schema_names = ["PK_MITIGATIONS_1.schema.json", "PK_COTENANCY_1.schema.json", "PK_ERROR_1.schema.json"]
        for name in schema_names:
            data = json.loads((PKG_DIR / "schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual(data["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(data["type"], "object")
        for path in sorted((PKG_DIR / "tests" / "fixtures").glob("*.json")):
            json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class NotAffectedStatusTest(unittest.TestCase):
    """4.3.0: ``not_affected`` satisfies a requirement at zero cost and forces v2."""

    def test_not_affected_satisfies_and_costs_nothing(self):
        node = pkg.MitigationState("n", smt_enabled=False)
        for m in pkg.REQUIRED_FOR_COTENANCY:
            node.record(m, pkg.NOT_AFFECTED, 0.0)
        self.assertTrue(node.may_cotenant("a", "b")["permitted"])
        self.assertEqual(node.total_cost(), 0.0)
        with self.assertRaises(ValueError):
            node.record("mds", pkg.NOT_AFFECTED, 1.0)

    def test_v1_report_refuses_unrepresentable_status(self):
        node = pkg.MitigationState("n", smt_enabled=False)
        node.record("mds", pkg.NOT_AFFECTED, 0.0)
        with self.assertRaises(pkg.MitigationMissing) as cm:
            node.report()
        self.assertEqual(cm.exception.code, "schema_version_unrepresentable")
        self.assertEqual(node.report(version=2)["not_affected"], ["mds"])
        with self.assertRaises(ValueError):
            node.report(version=3)
