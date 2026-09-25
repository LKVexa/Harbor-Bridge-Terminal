"""Standalone INV-22 core-logic tests that do not require pk_core."""
import ast
import pathlib
import sys
import types
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]

# Minimal stubs let component.py load while keeping tests independent of pk_core.
pk_core = types.ModuleType("pk_core")
checklist = types.ModuleType("pk_core.checklist")
component_mod = types.ModuleType("pk_core.component")
contract_mod = types.ModuleType("pk_core.contract")
class ChecklistItem: pass
class Finding: pass
class Component: pass
class Contract:
    def __init__(self, **kwargs): self.__dict__.update(kwargs)
class Dependency:
    def __init__(self, *args): self.args = args
class Slo:
    def __init__(self, *args): self.args = args
checklist.ChecklistItem = ChecklistItem
checklist.Finding = Finding
component_mod.Component = Component
contract_mod.Contract = Contract
contract_mod.Dependency = Dependency
contract_mod.Slo = Slo
sys.modules.update({"pk_core": pk_core, "pk_core.checklist": checklist,
                    "pk_core.component": component_mod, "pk_core.contract": contract_mod})

pkg = types.ModuleType("inv22_testpkg")
pkg.__path__ = [str(PKG_DIR)]
sys.modules[pkg.__name__] = pkg

import importlib.util
for name in ("contract", "component"):
    spec = importlib.util.spec_from_file_location(f"{pkg.__name__}.{name}", PKG_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

c = sys.modules[f"{pkg.__name__}.component"]


class CoreLogicTest(unittest.TestCase):
    def test_matrix_is_immutable_and_valid(self):
        c.validate_matrix(c.MATRIX)
        with self.assertRaises(TypeError):
            c.MATRIX["new"] = c.IDENTICAL
        with self.assertRaises(c.InvalidClassification):
            c.validate_matrix({"x": "maybe"})

    def test_unknown_and_bad_inputs_fail_closed(self):
        with self.assertRaises(c.Unclassified): c.classify("new-interface")
        with self.assertRaises(ValueError): c.classify("   ")
        with self.assertRaises(ValueError): c.shim("clocks", 1, "bogus", "fork")

    def test_translation_paths(self):
        token = object()
        self.assertIs(c.shim("clocks", token, "standards", "fork"), token)
        self.assertIs(c.shim("filesystem", token, "fork", "fork"), token)
        env = c.shim("filesystem", "x", "standards", "fork")
        self.assertEqual((env["source_branch"], env["branch"], env["value"]), ("standards", "fork", "x"))
        with self.assertRaises(c.SemanticDivergence): c.shim("sockets", None, "standards", "fork")

    def test_certification(self):
        cert = c.Certification("worker", "standards")
        self.assertEqual(cert.run_on("standards"), "ok")
        with self.assertRaises(c.UncertifiedBranch): cert.run_on("fork")
        self.assertEqual(cert.uncertified_runs, 1)
        with self.assertRaises(ValueError): c.Certification(" ", "standards")

    def test_drift(self):
        d = c.DriftReport()
        self.assertEqual(d.record("r1", {"a": c.IDENTICAL}), 0)
        self.assertEqual(d.record("r2", c.MATRIX), 2)
        self.assertTrue(d.growing())
        self.assertEqual(d.delta(), 2)

    def test_no_runtime_assert_statements(self):
        tree = ast.parse((PKG_DIR / "component.py").read_text(encoding="utf-8"))
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Assert)])


if __name__ == "__main__":
    unittest.main()
