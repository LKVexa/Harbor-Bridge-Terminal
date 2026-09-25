"""Standalone resolver tests for PLN-02; stdlib only and no network."""
from __future__ import annotations

import copy
import json
import pathlib
import sys
import unittest

try:
    import jsonschema
except ModuleNotFoundError:  # optional test dependency
    jsonschema = None

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pln02_application_plane as app


def valid_components(version: str = "1.2"):
    return [
        {
            "name": "api",
            "requires": {"state": True, "tracing": False},
            "imports": {"store": version},
            "exports": {},
        },
        {
            "name": "store",
            "requires": {"state": True},
            "exports": {"store": version},
            "imports": {},
        },
    ]


class ResolverTest(unittest.TestCase):
    def test_package_import_does_not_require_pk_core(self):
        self.assertEqual(app.__version__, (PKG_DIR / "VERSION").read_text().strip())
        self.assertEqual(app.ELEMENT_ID, "PLN-02")

    def test_versioned_document_contract_fixture(self):
        fixture_dir = PKG_DIR / "tests" / "fixtures"
        application = json.loads((fixture_dir / "application.json").read_text())
        catalogue = json.loads((fixture_dir / "catalogue.json").read_text())
        revision = app.resolve_document(application, catalogue)
        self.assertEqual(revision["schema"], app.REVISION_SCHEMA)
        self.assertTrue(app.verify_revision(revision))

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_fixtures_and_revision_validate_against_published_schemas(self):
        fixture_dir = PKG_DIR / "tests" / "fixtures"
        schema_dir = PKG_DIR / "schemas"
        application = json.loads((fixture_dir / "application.json").read_text())
        catalogue = json.loads((fixture_dir / "catalogue.json").read_text())
        application_schema = json.loads((schema_dir / "PK_APPLICATION-1.schema.json").read_text())
        catalogue_schema = json.loads((schema_dir / "PK_PROVIDER_CATALOGUE-1.schema.json").read_text())
        revision_schema = json.loads((schema_dir / "PK_APPLICATION_REVISION-1.schema.json").read_text())
        jsonschema.Draft202012Validator.check_schema(application_schema)
        jsonschema.Draft202012Validator.check_schema(catalogue_schema)
        jsonschema.Draft202012Validator.check_schema(revision_schema)
        jsonschema.validate(application, application_schema)
        jsonschema.validate(catalogue, catalogue_schema)
        revision = app.resolve_document(application, catalogue)
        jsonschema.validate(revision, revision_schema)

    def test_unknown_document_schema_is_refused(self):
        with self.assertRaises(app.ValidationError):
            app.resolve_document(
                {"schema": "PK_APPLICATION/999", "components": [], "edges": []},
                {"schema": app.CATALOGUE_SCHEMA, "providers": {}},
            )

    def test_resolve_is_deterministic_and_integrity_checked(self):
        first = app.resolve(valid_components(), [("store", "api", "store")], {"state": "redis"})
        second = app.resolve(
            list(reversed(valid_components())),
            [("store", "api", "store")],
            {"state": "redis"},
        )
        self.assertEqual(first["revision"], second["revision"])
        self.assertRegex(first["revision"], r"^[0-9a-f]{64}$")
        self.assertTrue(app.verify_revision(first))
        self.assertEqual(first["dropped_optional"], ["api:tracing"])

    def test_interface_change_changes_revision_identity(self):
        first = app.resolve(valid_components("1.2"), [("store", "api", "store")], {"state": "redis"})
        second = app.resolve(valid_components("1.3"), [("store", "api", "store")], {"state": "redis"})
        self.assertNotEqual(first["revision"], second["revision"])

    def test_tampering_is_detected(self):
        revision = app.resolve(valid_components(), [("store", "api", "store")], {"state": "redis"})
        tampered = copy.deepcopy(revision)
        tampered["bindings"]["api:state"] = "attacker"
        with self.assertRaises(app.RevisionIntegrityError):
            app.verify_revision(tampered)

    def test_missing_required_capability_fails_closed_with_code(self):
        with self.assertRaises(app.UnsatisfiedRequirement) as ctx:
            app.resolve([{"name": "api", "requires": {"state": True}}], [], {})
        self.assertEqual(ctx.exception.as_dict()["code"], "UNSATISFIED_CAPABILITY")

    def test_optional_capability_may_be_dropped(self):
        revision = app.resolve([{"name": "api", "requires": {"tracing": False}}], [], {})
        self.assertEqual(revision["dropped_optional"], ["api:tracing"])

    def test_unknown_component_edge_is_refused(self):
        with self.assertRaises(app.IncompatibleInterface):
            app.resolve([{"name": "a", "exports": {"i": "1"}}], [("a", "b", "i")], {})

    def test_unbound_import_is_refused(self):
        with self.assertRaises(app.IncompatibleInterface):
            app.resolve([{"name": "api", "imports": {"store": "1"}}], [], {})

    def test_ambiguous_import_is_refused(self):
        components = [
            {"name": "a", "exports": {"i": "1"}},
            {"name": "b", "exports": {"i": "1"}},
            {"name": "c", "imports": {"i": "1"}},
        ]
        with self.assertRaises(app.IncompatibleInterface):
            app.resolve(components, [("a", "c", "i"), ("b", "c", "i")], {})

    def test_duplicate_component_is_validation_error(self):
        with self.assertRaises(app.ValidationError):
            app.resolve([{"name": "a"}, {"name": "a"}], [], {})

    def test_component_name_cannot_collide_with_binding_separator(self):
        with self.assertRaises(app.ValidationError):
            app.resolve([{"name": "a:b", "requires": {"c": True}}], [], {"c": "p"})

    def test_duplicate_edge_is_validation_error(self):
        components = [{"name": "a", "exports": {"i": "1"}}, {"name": "b", "imports": {"i": "1"}}]
        edge = ("a", "b", "i")
        with self.assertRaises(app.ValidationError):
            app.resolve(components, [edge, edge], {})

    def test_non_boolean_required_flag_is_refused(self):
        with self.assertRaises(app.ValidationError):
            app.resolve([{"name": "a", "requires": {"state": "yes"}}], [], {})

    def test_unsupported_component_field_is_refused(self):
        with self.assertRaises(app.ValidationError):
            app.resolve([{"name": "a", "secret": "should-not-be-silently-ignored"}], [], {})

    def test_provider_identifier_is_validated(self):
        with self.assertRaises(app.ValidationError):
            app.resolve([{"name": "a", "requires": {"state": True}}], [], {"state": ""})

    def test_input_objects_are_not_mutated(self):
        components = valid_components()
        before = copy.deepcopy(components)
        app.resolve(components, [("store", "api", "store")], {"state": "redis"})
        self.assertEqual(components, before)


if __name__ == "__main__":
    unittest.main()
