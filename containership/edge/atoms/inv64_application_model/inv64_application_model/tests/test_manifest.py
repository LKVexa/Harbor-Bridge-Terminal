"""Standalone tests for the INV-64 parser/validator; no pk_core required."""
from __future__ import annotations

import importlib.util
import math
import pathlib
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inv64_manifest_standalone", PKG_DIR / "manifest.py")
manifest = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
import sys
sys.modules[SPEC.name] = manifest
SPEC.loader.exec_module(manifest)


def good_manifest():
    return {
        "schema": "app/v1",
        "components": [{"name": "api"}, {"name": "worker"}],
        "providers": [{"name": "kv"}],
        "links": [{"from": "api", "to": "kv"}],
        "traits": [{"type": "spread", "component": "api"}],
    }


class ManifestTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(manifest.validate(good_manifest()), [])

    def test_reports_multiple_independent_errors(self):
        value = {
            "schema": "app/v9",
            "components": [{"name": "api"}],
            "providers": [],
            "links": [{"from": "ghost", "to": "missing"}],
            "traits": [{"type": "spread", "component": "ghost"}],
        }
        issues = manifest.validate_issues(value)
        self.assertEqual(
            {issue.code for issue in issues},
            {
                "schema.unsupported",
                "link.from.undeclared",
                "link.to.undeclared",
                "trait.component.undeclared",
            },
        )

    def test_section_type_errors_are_aggregated(self):
        value = {"schema": 1, "components": {}, "providers": "bad", "links": 7, "traits": None}
        issues = manifest.validate_issues(value)
        self.assertEqual(len(issues), 5)
        self.assertEqual(issues[0].code, "schema.type")

    def test_invalid_and_duplicate_names(self):
        value = good_manifest()
        value["components"] = [{"name": "api"}, {"name": "api"}, {"name": "bad name"}, {"name": ""}]
        codes = [x.code for x in manifest.validate_issues(value)]
        self.assertIn("name.duplicate", codes)
        self.assertEqual(codes.count("name.invalid"), 2)

    def test_duplicate_json_key_is_rejected(self):
        raw = '{"schema":"app/v1","schema":"app/v9","components":[],"providers":[],"links":[],"traits":[]}'
        with self.assertRaises(manifest.DuplicateKeyError):
            manifest.parse_manifest_json(raw)

    def test_parse_rejects_semantically_invalid_manifest(self):
        raw = '{"schema":"app/v9","components":[],"providers":[],"links":[],"traits":[]}'
        with self.assertRaises(manifest.ManifestValidationError) as ctx:
            manifest.parse_manifest_json(raw)
        self.assertEqual(ctx.exception.issues[0].code, "schema.unsupported")

    def test_canonical_is_order_insensitive_for_set_like_sections(self):
        a = good_manifest()
        b = good_manifest()
        b["components"] = list(reversed(b["components"]))
        self.assertEqual(manifest.canonical(a), manifest.canonical(b))
        b["components"] = [{"name": "api"}]
        self.assertNotEqual(manifest.canonical(a), manifest.canonical(b))

    def test_canonical_does_not_mutate_input(self):
        value = good_manifest()
        value["components"] = list(reversed(value["components"]))
        before = repr(value)
        manifest.canonical(value)
        self.assertEqual(repr(value), before)

    def test_canonical_fails_closed_on_invalid_manifest(self):
        value = good_manifest()
        value["links"] = [{"from": "api", "to": "ghost"}]
        with self.assertRaises(manifest.ManifestValidationError):
            manifest.canonical(value)

    def test_non_finite_values_are_rejected(self):
        value = good_manifest()
        value["extension"] = {"weight": math.nan}
        with self.assertRaises(ValueError):
            manifest.canonical(value)
        raw = '{"schema":"app/v1","components":[],"providers":[],"links":[],"traits":[],"x":NaN}'
        with self.assertRaises(ValueError):
            manifest.parse_manifest_json(raw)

    def test_size_limit(self):
        raw = b" " * (manifest.MAX_MANIFEST_BYTES + 1)
        with self.assertRaises(ValueError):
            manifest.parse_manifest_json(raw)

    def test_decoded_collection_limit_is_reported(self):
        value = good_manifest()
        value["components"] = [{"name": "x"}] * (manifest.MAX_COMPONENTS + 1)
        issues = manifest.validate_issues(value)
        self.assertTrue(any(i.code == "section.limit" and i.path == "components" for i in issues))

    def test_json_schema_artifact_is_valid_json(self):
        import json
        schema = json.loads((PKG_DIR / "schema" / "app-v1.schema.json").read_text())
        self.assertEqual(schema["properties"]["schema"]["const"], "app/v1")
        self.assertEqual(schema["properties"]["components"]["maxItems"], manifest.MAX_COMPONENTS)

    def test_top_level_core_api_import_does_not_require_pk_core(self):
        import importlib
        root = str(PKG_DIR.parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        pkg = importlib.import_module(PKG_DIR.name)
        self.assertEqual(pkg.__version__, (PKG_DIR / "VERSION").read_text(encoding="utf-8").strip())
        self.assertEqual(pkg.validate(good_manifest()), [])


if __name__ == "__main__":
    unittest.main()
