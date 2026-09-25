"""M30/M31 - build metadata and deterministic SBOM."""
import pathlib
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PackagingTest(unittest.TestCase):
    def test_pyproject_metadata_matches_version_and_pins(self):
        meta = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertEqual(meta["project"]["version"], (ROOT / "VERSION").read_text().strip())
        deps = meta["project"]["dependencies"]
        self.assertTrue(all("==" in d for d in deps), deps)         # exact pins only

    def test_sbom_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            outs = []
            for n in ("1", "2"):
                subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "sbom.py"), "--out", f"{d}/s{n}.json",
                                "--sums", f"{d}/sums{n}"], check=True, capture_output=True)
                outs.append((pathlib.Path(f"{d}/s{n}.json").read_bytes(), pathlib.Path(f"{d}/sums{n}").read_bytes()))
            self.assertEqual(outs[0], outs[1])
            self.assertIn(b'"name": "pk_core"', outs[0][0])


if __name__ == "__main__":
    unittest.main()
