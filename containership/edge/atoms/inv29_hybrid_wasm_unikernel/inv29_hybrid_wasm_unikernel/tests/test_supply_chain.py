"""Supply-chain artifacts (MC014-MC019, MC021, MC022, MC103): the scanner
detects planted secrets, and generated SBOM/checksums/manifest are consistent
with the tree (run tools/build_release.py first; skipped otherwise, and the
skip is visible in conformance/test_results.json)."""
import hashlib
import json
import pathlib
import sys
import tempfile
import tomllib
import unittest

import _fixtures as F  # noqa: F401
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
import secret_scan  # noqa: E402


class SupplyChainTest(unittest.TestCase):
    def test_secret_scanner_detects_planted_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "leak.py"
            p.write_text('AWS = "AKIA' + 'ABCDEFGHIJKLMNOP"\napi_key = "' + 'q8Zr2LxV9mN4pT7w' + '"\n'
                         + "-----BEGIN " + "PRIVATE KEY-----\n")
            kinds = {f["kind"] for f in secret_scan.scan(pathlib.Path(d))["findings"]}
            self.assertEqual(kinds, {"aws-access-key", "generic-assignment", "private-key"})

    def test_repository_is_clean(self):
        self.assertTrue(secret_scan.scan()["clean"])

    def test_metadata_is_consistent(self):
        meta = tomllib.loads((PKG / "pyproject.toml").read_text())["project"]
        import inv29_hybrid_wasm_unikernel as pkg
        self.assertEqual(meta["version"], pkg.__version__)
        self.assertEqual((PKG / "VERSION").read_text().strip(), pkg.__version__)
        self.assertEqual(meta["dependencies"], [])
        self.assertIn(">=3.10", meta["requires-python"])
        self.assertIn(pkg.__version__, (PKG / "CHANGELOG.md").read_text())

    @unittest.skipUnless((PKG / "release" / "SHA256SUMS").exists(), "run tools/build_release.py first")
    def test_generated_artifacts_match_tree(self):
        for line in (PKG / "release" / "SHA256SUMS").read_text().splitlines():
            digest, rel = line.split("  ", 1)
            p = PKG / rel
            if rel.startswith(("tests/", "tools/")) or rel in ("MISSING_COMPONENTS_STATUS.json",):
                continue  # may legitimately change between build and this run in development
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), digest, rel)
        sbom = json.loads((PKG / "sbom" / "inv29.cdx.json").read_text())
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        self.assertIn("pk_core", {c["name"] for c in sbom["components"]})
        man = json.loads((PKG / "release" / "evidence-manifest.json").read_text())
        # test_results.json is produced by the very run that executes this test
        self.assertLessEqual(set(man["missing"]), {"conformance/test_results.json"})


if __name__ == "__main__":
    unittest.main()
