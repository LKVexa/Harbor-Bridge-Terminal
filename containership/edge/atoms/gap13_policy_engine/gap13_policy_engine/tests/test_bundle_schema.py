"""G13-MC-002/003/004/017: schemas, strict parser, golden fixtures, compatibility."""
import json
import pathlib
import unittest

import testkit as k
from gap13_policy_engine import bundle as B, errors as E
from gap13_policy_engine.canonical import canonical_bytes

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
FX = ROOT / "fixtures"


def schema(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text())


class ParserTests(unittest.TestCase):
    def parse(self, doc_or_bytes, **lim):
        data = doc_or_bytes if isinstance(doc_or_bytes, bytes) else canonical_bytes(doc_or_bytes)
        return B.parse_bundle(data, k.g.Limits(**lim) if lim else k.g.Limits())

    def test_valid(self):
        b = self.parse(k.bundle_doc(3))
        self.assertEqual((b.generation, len(b.rules)), (3, 2))
        self.assertTrue(b.digest.startswith("sha256:"))

    def test_rejections(self):
        base = k.bundle_doc()
        cases = {
            "dup": (b'{"schema":"PK_POLICY_BUNDLE/1","schema":"x"}', E.BundleParseError),
            "float": (canonical_bytes({**base, "generation": 1}).replace(b'"generation":1', b'"generation":1.0'), E.BundleParseError),
            "nan": (b'{"a":NaN}', E.BundleParseError),
            "utf8": (b'{"a":"\xff"}', E.BundleParseError),
            "trunc": (canonical_bytes(base)[:-5], E.BundleParseError),
            "deep": (b"[" * 50 + b"]" * 50, E.BundleTooLarge),
            "noncanon": (json.dumps(base, indent=1).encode(), E.BundleParseError),
            "schema": ({**base, "schema": "PK_POLICY_BUNDLE/2"}, E.SchemaMismatch),
            "unknown": ({**base, "zzz": 1}, E.BundleSemanticError),
            "missing": ({x: y for x, y in base.items() if x != "issuer"}, E.BundleSemanticError),
            "gen0": ({**base, "generation": 0}, E.BundleSemanticError),
            "overflow": ({**base, "generation": 2**60}, E.BundleSemanticError),
            "boolgen": ({**base, "generation": True}, E.BundleSemanticError),
            "expiry": ({**base, "expires_at": base["issued_at"]}, E.BundleSemanticError),
            "effect": ({**base, "rules": [{"name": "r", "effect": "maybe", "scope": "estate", "match": {}}]}, E.BundleSemanticError),
            "rulekeys": ({**base, "rules": [{"name": "r", "effect": "allow", "scope": "estate", "match": {}, "x": 1}]}, E.BundleSemanticError),
            "attrname": ({**base, "rules": [{"name": "r", "effect": "allow", "scope": "estate", "match": {"Bad Key": 1}}]}, E.BundleSemanticError),
            "control": ({**base, "bundle_id": "a‮b"}, E.BundleSemanticError),
            "dupnames": ({**base, "rules": [{"name": "r", "effect": "allow", "scope": "estate", "match": {}}] * 2}, E.BundleSemanticError),
            "nested": ({**base, "rules": [{"name": "r", "effect": "allow", "scope": "estate", "match": {"a": [[1]]}}]}, E.BundleSemanticError),
            "ext": ({**base, "extensions": {"foo": 1}}, E.BundleSemanticError),
        }
        for name, (doc, exc) in cases.items():
            with self.subTest(name), self.assertRaises(exc):
                self.parse(doc)

    def test_limits(self):
        with self.assertRaises(E.BundleTooLarge):
            self.parse(k.bundle_doc(), max_bundle_bytes=100)
        with self.assertRaises(E.BundleTooLarge):
            self.parse(k.bundle_doc(), max_rules=1)
        with self.assertRaises(E.BundleTooLarge):
            self.parse(k.bundle_doc(bundle_id="a" * 50), max_string_length=10)

    def test_extensions_namespace_allowed(self):
        self.assertEqual(self.parse({**k.bundle_doc(), "extensions": {"x-note": "hi"}}).generation, 1)

    def test_bundle_objects_immutable(self):
        b = self.parse(k.bundle_doc())
        with self.assertRaises(Exception):
            b.generation = 9


@unittest.skipIf(jsonschema is None, "jsonschema not installed")
class SchemaArtifactTests(unittest.TestCase):
    def test_schemas_are_valid(self):
        for p in SCHEMAS.glob("*.schema.json"):
            jsonschema.Draft202012Validator.check_schema(json.loads(p.read_text()))

    def test_fixtures_validate(self):
        jsonschema.validate(json.loads((FX / "bundle_v1.json").read_text()), schema("PK_POLICY_BUNDLE_1"))
        jsonschema.validate(json.loads((FX / "envelope_v1.json").read_text()), schema("PK_POLICY_SIGNED_BUNDLE_1"))
        for f in FX.glob("verdict_*.golden.json"):
            jsonschema.validate(json.loads(f.read_text()), schema("PK_POLICY_VERDICT_1"))
        jsonschema.validate(json.loads((FX / "explanation.golden.json").read_text()), schema("PK_POLICY_EXPLANATION_1"))

    def test_error_objects_validate(self):
        s = schema("PK_POLICY_ERROR_1")
        for code, cls in E.registry().items():
            jsonschema.validate(cls("m").to_dict(), s)

    def test_service_verdict_validates(self):
        svc, c = k.service(require_separation_of_duties=False)
        svc.load(k.principal("alice", clock=c), k.envelope(1))
        v = svc.evaluate(k.principal("svc-a", ("service",), kind="service", clock=c), {"action": "read"})
        jsonschema.validate(v, schema("PK_POLICY_VERDICT_1"))


class GoldenTests(unittest.TestCase):
    def test_goldens_reproduce_exactly(self):
        import importlib
        mf = importlib.import_module("gap13_policy_engine.tools.make_fixtures")
        for name, doc in mf.build().items():
            with self.subTest(name):
                self.assertEqual(json.loads((FX / name).read_text()), json.loads(json.dumps(doc)))

    def test_fixture_envelope_verifies(self):
        env = (FX / "envelope_v1.json").read_text()
        env_b = canonical_bytes(json.loads(env))
        self.assertTrue(k.verifier().verify(env_b, now=k.T0).verified)


class CompatTests(unittest.TestCase):
    def test_matrix_consistent(self):
        from gap13_policy_engine import compat, __version__
        self.assertEqual(compat.MATRIX["engine_release"], __version__)
        self.assertEqual(compat.MATRIX["bundle_schemas"]["accept"], list(B.SUPPORTED_BUNDLE_SCHEMAS))
        self.assertTrue(compat.python_supported())


if __name__ == "__main__":
    unittest.main()
