"""Packaging lane: build a wheel offline and import from it in a clean interpreter.

Declared lane PACKAGING: skips with its reason when setuptools/pip are absent.
"""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]


@unittest.skipIf(importlib.util.find_spec("setuptools") is None, "lane PACKAGING not available: setuptools missing")
class WheelTest(unittest.TestCase):
    def test_wheel_builds_and_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Build from a copy: an in-tree build writes *.egg-info/ and build/
            # into the repository and breaks its checksum manifest.
            import shutil
            src = pathlib.Path(tmp) / "src"
            shutil.copytree(PKG_DIR, src, ignore=shutil.ignore_patterns("__pycache__", "evidence", "build",
                                                                        "*.egg-info", "dist"))
            r = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                                "-w", tmp, str(src)], capture_output=True, text=True)
            if r.returncode and "install_layout" in (r.stdout + r.stderr):
                self.skipTest("lane PACKAGING not available: host setuptools is distro-patched "
                              "(AttributeError install_layout); CI 'package' job builds on a clean runner")
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            wheel = next(pathlib.Path(tmp).glob("*.whl"))
            names = zipfile.ZipFile(wheel).namelist()
            self.assertIn("inv44_wasm_hardening_system/schemas/pk_wasm_hardening.v1.schema.json", names)
            self.assertFalse([n for n in names if "/tests/" in n or "/evidence/" in n])
            code = ("import inv44_wasm_hardening_system as m, inv44_wasm_hardening_system.config as c;"
                    "print(m.__version__, len(c.load('pk_wasm_instance.v1.schema.json')) > 0)")
            out = subprocess.run([sys.executable, "-S", "-c", f"import sys; sys.path.insert(0, {str(wheel)!r}); {code}"],
                                 capture_output=True, text=True, cwd=tmp)
            self.assertEqual(out.stdout.split(), ["4.3.0", "True"], out.stderr)


class PyprojectTest(unittest.TestCase):
    """Always-on: metadata is parseable and consistent with VERSION (py3.11+ tomllib)."""

    @unittest.skipIf(sys.version_info < (3, 11), "tomllib needs Python 3.11")
    def test_metadata(self):
        import tomllib
        meta = tomllib.loads((PKG_DIR / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(meta["project"]["version"], (PKG_DIR / "VERSION").read_text().strip())
        self.assertEqual(meta["project"]["dependencies"], [])
        self.assertEqual(meta["project"]["requires-python"], ">=3.10")
        self.assertIn("schemas/*.json", meta["tool"]["setuptools"]["package-data"]["inv44_wasm_hardening_system"])


if __name__ == "__main__":
    unittest.main()
