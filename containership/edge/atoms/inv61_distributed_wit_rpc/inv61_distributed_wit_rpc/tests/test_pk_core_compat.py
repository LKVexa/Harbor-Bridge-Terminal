"""M01 - the pk_core dependency fails loudly, never by silent skip."""
import os
import pathlib
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from wrpc import pkcore_compat as P  # noqa: E402


class PkCoreProbeTest(unittest.TestCase):
    def test_symbol_inventory_matches_source_imports(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        src = (root / "contract.py").read_text() + (root / "component.py").read_text()
        for mod, names in P.REQUIRED_SYMBOLS.items():
            for n in names:
                self.assertIn(n, src, f"{mod}.{n} listed but not imported")
        self.assertEqual(src.count("from pk_core"), len(P.REQUIRED_SYMBOLS))

    def test_absent_package_raises_with_requirement(self):
        saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith("pk_core")}
        real_path = list(sys.path)
        try:
            sys.path[:] = [p for p in sys.path if not (pathlib.Path(p) / "pk_core").exists()]
            try:
                P.probe()
            except P.PkCoreUnavailable as e:
                self.assertIn("pk_core is required", str(e))
                self.assertNotIn(os.environ.get("HOME", "\0"), str(e))   # no environment disclosure
            else:
                self.skipTest("a pk_core is importable here; absence path not exercisable")
        finally:
            sys.path[:] = real_path
            sys.modules.update(saved)

    def test_missing_symbol_detected(self):
        fakes = {m: types.ModuleType(m) for m in ["pk_core"] + list(P.REQUIRED_SYMBOLS)}
        for m, names in P.REQUIRED_SYMBOLS.items():
            for n in names:
                setattr(fakes[m], n, object())
        delattr(fakes["pk_core.contract"], "Slo")
        saved = {k: sys.modules.get(k) for k in fakes}
        sys.modules.update(fakes)
        try:
            self.assertEqual(P.probe(), {"pk_core.contract": ["Slo"]})
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    @unittest.skipUnless(os.environ.get("INV61_REQUIRE_PK_CORE") == "1", "set INV61_REQUIRE_PK_CORE=1 in the release CI job")
    def test_release_gate_requires_pk_core(self):
        self.assertEqual(P.probe(), {})


if __name__ == "__main__":
    unittest.main()
