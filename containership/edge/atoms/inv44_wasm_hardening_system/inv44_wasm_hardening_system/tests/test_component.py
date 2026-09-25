"""Conformance and security tests for INV-44 -- stdlib unittest, no network.

The runtime security tests are deliberately independent of ``pk_core`` so a
missing external conformance framework cannot make the entire suite skip.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib
import importlib.util
import os
import pathlib
import subprocess
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent


def _load_runtime():
    name = "_inv44_runtime_under_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, PKG_DIR / "runtime.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load runtime.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = _load_runtime()

for p in filter(None, [os.environ.get("PK_CORE_PATH"), str(ROOT.parent), str(ROOT)]):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import pk_core  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    pk_core = None

def _load_package():
    name = PKG_DIR.name if ROOT.name != "pk_components" else "pk_components." + PKG_DIR.name
    return importlib.import_module(name)


class RepositoryInvariantTest(unittest.TestCase):
    def test_version_is_consistent(self):
        version = (PKG_DIR / "VERSION").read_text(encoding="utf-8").strip()
        init_text = (PKG_DIR / "__init__.py").read_text(encoding="utf-8")
        readme_text = (PKG_DIR / "README.md").read_text(encoding="utf-8")
        self.assertEqual(version, "4.3.0")
        self.assertIn('__version__ = "4.3.0"', init_text)
        self.assertIn("**Version:** 4.3.0", readme_text)

    def test_declared_local_files_exist(self):
        readme = (PKG_DIR / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("carried verbatim for audit", readme)
        for name in ("CHECKLIST.json", "MISSING_COMPONENTS.md", "runtime.py"):
            self.assertTrue((PKG_DIR / name).is_file(), name)


class RuntimeSecurityTest(unittest.TestCase):
    def setUp(self):
        self.Engine = runtime.Engine
        self.Instance = runtime.Instance
        self.features = runtime.REQUIRED_HARDENING

    def test_every_required_feature_is_load_bearing(self):
        for feature in self.features:
            with self.subTest(feature=feature):
                engine = self.Engine("swivel-reference", self.features - {feature})
                with self.assertRaises(runtime.HardeningIncomplete):
                    engine.instantiate("svc", output_valid=True, fuel=10)

    def test_direct_instance_construction_is_denied(self):
        engine = self.Engine("swivel-reference", self.features)
        with self.assertRaises(runtime.InstanceConstructionDenied):
            self.Instance("svc", engine, 10, 1)

    def test_unverified_and_non_boolean_verdicts_fail_closed(self):
        engine = self.Engine("swivel-reference", self.features)
        with self.assertRaises(runtime.OutputUnverified):
            engine.instantiate("svc", output_valid=False, fuel=10)
        with self.assertRaises(TypeError):
            engine.instantiate("svc", output_valid=1, fuel=10)

    def test_zero_negative_and_boolean_step_costs_are_rejected(self):
        instance = self.Engine("swivel-reference", self.features).instantiate(
            "svc", output_valid=True, fuel=10
        )
        for cost in (0, -1):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                instance.step(cost)
        with self.assertRaises(TypeError):
            instance.step(True)
        self.assertEqual(instance.remaining_fuel, 10)

    def test_fuel_exhaustion_is_sticky(self):
        instance = self.Engine("swivel-reference", self.features).instantiate(
            "svc", output_valid=True, fuel=2
        )
        self.assertEqual(instance.step(2), 0)
        with self.assertRaises(runtime.FuelExhausted):
            instance.step(1)
        self.assertEqual(instance.trapped, "fuel exhausted")
        with self.assertRaises(RuntimeError):
            instance.step(1)

    def test_environment_specific_memory_ceiling_is_enforced(self):
        engine = self.Engine("swivel-reference", self.features, memory_page_ceiling=3)
        instance = engine.instantiate("svc", output_valid=True, fuel=10, pages=2)
        self.assertEqual(instance.grow(1), 3)
        with self.assertRaises(runtime.MemoryCeiling):
            instance.grow(1)
        with self.assertRaises(ValueError):
            instance.grow(-1)
        with self.assertRaises(TypeError):
            instance.grow(True)

    def test_public_accounting_state_is_immutable(self):
        instance = self.Engine("swivel-reference", self.features).instantiate(
            "svc", output_valid=True, fuel=10
        )
        for attr, value in (("fuel", 999), ("pages", 0), ("consumed", -1), ("trapped", None)):
            with self.subTest(attr=attr), self.assertRaises(FrozenInstanceError):
                setattr(instance, attr, value)

    def test_control_characters_are_rejected_from_identifiers(self):
        with self.assertRaises(ValueError):
            self.Engine("bad\nengine", self.features)
        engine = self.Engine("swivel-reference", self.features)
        with self.assertRaises(ValueError):
            engine.instantiate("bad\rmodule", output_valid=True, fuel=10)

    def test_accounting_is_thread_safe(self):
        instance = self.Engine("swivel-reference", self.features).instantiate(
            "svc", output_valid=True, fuel=1000
        )
        errors: list[BaseException] = []

        def worker() -> None:
            try:
                for _ in range(100):
                    instance.step(1)
            except BaseException as exc:  # test harness captures thread failures
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(instance.consumed, 1000)
        self.assertEqual(instance.remaining_fuel, 0)


@unittest.skipIf(pk_core is None, "pk_core not importable; set PK_CORE_PATH")
class PkCoreConformanceTest(unittest.TestCase):
    def test_all_100_requirements_are_enumerated(self):
        comp = _load_package().COMPONENT()
        findings = [f for fs in comp.assess_all().values() for f in fs]
        self.assertEqual(len(findings), 100)
        self.assertEqual(len({f.check_id for f in findings}), 100)
        # Do not self-certify all findings as passing here. The independent
        # post-audit matrix documents repository-local evidence gaps, and the
        # external pk_core gate owns final estate-level certification.

    def test_checks_survive_optimised_mode(self):
        code = (
            "import sys; sys.path[:0]=%r; import importlib; "
            "m=importlib.import_module(%r); c=m.COMPONENT(); "
            "print(sum(len(v) for v in c.assess_all().values()))"
        ) % ([p for p in sys.path[:3]], _load_package().__name__)
        out = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "100")


if __name__ == "__main__":
    unittest.main()
