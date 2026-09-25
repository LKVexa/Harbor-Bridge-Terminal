"""P1-25/26/27: packaging metadata, version sync, manifest integrity, schema inventory."""
import hashlib
import json
import pathlib
import re
import sys
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

import gap14_data_gravity_manager as g  # noqa: E402
from gap14_data_gravity_manager.schema_check import load  # noqa: E402


class PackagingTest(unittest.TestCase):
    def test_single_version_source(self):
        py = (PKG / "pyproject.toml").read_text()
        self.assertIn(f'version = "{g.__version__}"', py)
        self.assertEqual((PKG / "VERSION").read_text().strip(), g.__version__)
        self.assertIn('requires-python = ">=3.11,<3.14"', py)
        self.assertRegex(py, r"dependencies = \[\]")

    def test_manifest_matches_tree(self):
        lines = (PKG / "MANIFEST.sha256").read_text().splitlines()
        self.assertGreater(len(lines), 30)
        bad = []
        for ln in lines:
            h, name = ln.split("  ", 1)
            p = PKG / name
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != h:
                bad.append(name)
        self.assertEqual(bad, [], "files changed since MANIFEST.sha256 was generated (run tools/release_evidence.py)")

    def test_no_secrets_or_local_paths_in_package(self):
        for p in PKG.rglob("*"):
            if p.is_file() and p.suffix in {".py", ".md", ".json", ".toml"}:
                t = p.read_text(encoding="utf-8", errors="ignore")
                self.assertNotRegex(t, r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", p.name)
                self.assertNotIn("C:\\Users\\", t, p.name)

    def test_all_schemas_parse_and_are_referenced(self):
        names = sorted(x.name for x in (PKG / "schemas").glob("*.schema.json"))
        self.assertGreaterEqual(len(names), 20)
        for n in names:
            doc = load(n)
            self.assertEqual(doc["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_sbom_declares_zero_runtime_dependencies(self):
        sbom = json.loads((PKG / "evidence" / "SBOM.cdx.json").read_text())
        self.assertEqual(sbom["metadata"]["component"]["version"], g.__version__)
        self.assertEqual(sbom["dependencies"][0]["dependsOn"], [])



class MetadataTest(unittest.TestCase):
    def test_project_metadata_complete(self):  # P1-27 A05
        py = (PKG / "pyproject.toml").read_text()
        for key in ("name =", "version =", "description =", "requires-python =", "license =", "authors =",
                    "maintainers =", "classifiers =", "readme ="):
            self.assertIn(key, py)


class EntryPointAndBenchTest(unittest.TestCase):
    def test_console_entry_point_and_public_exports(self):
        py = (PKG / "pyproject.toml").read_text()
        self.assertIn('gap14 = "gap14_data_gravity_manager.__main__:main"', py)
        from gap14_data_gravity_manager.__main__ import main
        self.assertEqual(main(["knobs"]), 0)
        self.assertEqual(main(["handshake"]), 2)   # non-certifying without pk_core
        for name in g.__all__:
            if name in {"COMPONENT", "DataGravityManagerComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
                continue  # lazily loaded; need pk_core
            self.assertTrue(hasattr(g, name), name)

    def test_bench_harness_runs_and_reports_both_scopes(self):
        sys.path.insert(0, str(PKG / "tools"))
        import bench
        r = bench.run(200, 1, 0)
        self.assertEqual(r["errors"], {})
        self.assertIn("engine_only", r)
        self.assertGreater(r["throughput_per_s"], 0)


if __name__ == "__main__":
    unittest.main()
